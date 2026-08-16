# -*- coding: utf-8 -*-
#
# Copyright (C) 2022 GEO Secretariat.
#
# invenio-geographic-identifiers is free software; you can redistribute it
# and/or modify it under the terms of the MIT License; see LICENSE file for
# more details.

"""Fetching a datastream source to a local file."""

import fcntl
import hashlib
import logging
import os
import re
import shutil
import time
import zipfile
from contextlib import contextmanager
from urllib.parse import unquote, urlparse

import requests
from flask import current_app, has_app_context
from invenio_vocabularies.datastreams.errors import ReaderError

from .. import config

#
# Constants
#
IDENTITY = {"Accept-Encoding": "identity"}
"""Ask for the bytes as they are."""


#
# Errors
#
class DownloadError(ReaderError):
    """A source could not be fetched.

    A `ReaderError` because that is what it is from the outside, and because a
    single-reader datastream lets it propagate and fail the run, which is the
    behaviour wanted here. There is no sensible way to import "most of" a dump.
    """


class SourceChangedError(DownloadError):
    """A source changed while a run was pinned to an earlier snapshot."""


#
# Helpers
#
def _get_log():
    """Get the logger to report progress on."""
    if has_app_context():
        return current_app.logger

    # Return!
    return logging.getLogger(__name__)


def setting(name):
    """Read one of the package settings.

    Args:
        name: The setting name.

    Returns:
        The configured value, or the packaged default outside an application.
    """
    if has_app_context():
        return current_app.config[name]

    # Return!
    return getattr(config, name)


def is_url(origin):
    """Check if an origin names something to fetch rather than something to open.

    Args:
        origin: The origin to check.

    Returns:
        `True` for an http(s) URL, `False` for anything else, `None` included.
    """
    if not origin:
        return False

    # Return!
    return urlparse(str(origin)).scheme in ("http", "https")


@contextmanager
def _lock_path(path):
    """Hold an exclusive lock for the duration of the block.

    Args:
        path: The path to the lock file.

    Returns:
        A context manager that yields the lock.
    """
    descriptor = os.open(path, os.O_CREAT | os.O_RDWR, 0o600)

    try:
        try:
            fcntl.flock(descriptor, fcntl.LOCK_EX | fcntl.LOCK_NB)

        except BlockingIOError:
            # Somebody else got here first. Waiting is the point, when they
            # finish, their download is the one this process goes on to reuse.
            _get_log().info(f"Waiting for another process to finish fetching {path}.")

            # Acquire the lock
            fcntl.flock(descriptor, fcntl.LOCK_EX)

        # Yield the lock
        yield

    finally:
        os.close(descriptor)


#
# Sources
#
def probe(url, timeout=None):
    """Ask a source what fetching it would involve.

    Args:
        url: The source to ask about.

        timeout: Connect and read timeouts, in seconds.

    Returns:
        A dict of `url`, `length`, `etag`, `last_modified` and `resumable`.
    """
    timeout = timeout or setting("INVENIO_GEOGRAPHIC_IDENTIFIERS_DOWNLOAD_TIMEOUT")

    try:
        response = requests.head(
            url, timeout=timeout, allow_redirects=True, headers=IDENTITY
        )

        # Check for errors
        response.raise_for_status()

    except requests.RequestException as error:
        raise DownloadError(f"Could not reach {url}: {error}") from error

    # Get the length
    length = response.headers.get("Content-Length")

    # Return the result
    return {
        "url": url,
        "length": int(length) if length and length.isdigit() else None,
        "etag": response.headers.get("ETag"),
        "last_modified": response.headers.get("Last-Modified"),
        "resumable": response.headers.get("Accept-Ranges", "").lower() == "bytes",
    }


def local_path_for(url, directory=None):
    """Get the path where a copy of a source is kept.

    Args:
        url: The source.

        directory: Where copies are kept. Defaults to the configured directory.

    Returns:
        The path where a copy of a source is kept.
    """
    directory = directory or setting("INVENIO_GEOGRAPHIC_IDENTIFIERS_DOWNLOAD_DIR")

    # Get the name of the source
    name = os.path.basename(unquote(urlparse(url).path))
    name = re.sub(r"[^A-Za-z0-9._-]", "_", name) or "source"

    # Return!
    return os.path.join(
        directory, f"{hashlib.sha1(url.encode()).hexdigest()[:8]}-{name}"
    )


#
# Fetching
#
def _is_complete(path, length):
    """Check if a copy on disk is the whole of the source.

    Args:
        path: The path to the copy.

        length: The length of the source.

    Returns:
        `True` if the copy is the whole of the source, `False` otherwise.
    """
    if not os.path.exists(path):
        return False

    if length is None:
        _get_log().warning(
            f"{path} cannot be size-checked: the source reports no length."
        )

        return True

    # Return!
    return os.path.getsize(path) == length


def _check_space_for_transfer(directory, needed, url):
    """Check if there is enough room for a transfer.

    Args:
        directory: The directory to store the copy.

        needed: The amount of space needed.

        url: The URL of the source.
    """
    # If there is no space needed, return
    if needed is None:
        return

    # Get the margin
    margin = setting("INVENIO_GEOGRAPHIC_IDENTIFIERS_DOWNLOAD_FREE_SPACE_MARGIN")

    # Get the free space
    free = shutil.disk_usage(directory).free

    # If there is not enough free space, raise an error
    if free < needed + margin:
        raise DownloadError(
            f"Not enough room in {directory} to fetch {url}: {needed} bytes "
            f"needed plus a {margin} byte margin, {free} free. Set "
            "INVENIO_GEOGRAPHIC_IDENTIFIERS_DOWNLOAD_DIR to a filesystem with "
            "more room."
        )


def _transfer(url, part, have, timeout, chunk_size):
    """Transfer the source to a local copy.

    Args:
        url: The URL of the source.

        part: The path to the partial copy.

        have: The amount of the source that has already been transferred.

        timeout: The timeout for the request.

        chunk_size: The size of the chunks to read.

    Returns:
        The `ETag` the source served, so the caller can tell whether it is still
        the snapshot the run was pinned to.
    """
    # Initialize the headers
    headers = dict(IDENTITY)

    # If there is already some of the source, add the range header
    if have:
        headers["Range"] = f"bytes={have}-"

    # Make the request
    with requests.get(url, stream=True, timeout=timeout, headers=headers) as response:
        response.raise_for_status()

        # If the server ignores the range, answer 200 and start from the top,
        # so the bytes already held are not a prefix of what is arriving
        if have and response.status_code != 206:
            _get_log().warning(f"{url} ignored the range request; starting over.")

            # Reset the amount of the source that has already been transferred
            have = 0

        # Log the progress
        _get_log().info(
            f"Fetching {url}" + (f", resuming at {have} bytes." if have else ".")
        )

        # Write the chunks to the partial copy
        with open(part, "ab" if have else "wb") as handle:
            for chunk in response.iter_content(chunk_size=chunk_size):
                handle.write(chunk)

        # Return!
        return response.headers.get("ETag")


def _resume_transfer_from(part, length, source):
    """Get how much of a partial transfer can be kept.

    Args:
        part: The path to the partial copy.

        length: The length of the source.

        source: The source to fetch.

    Returns:
        The amount of the source that has already been transferred.
    """
    if not source.get("resumable") or not os.path.exists(part):
        return 0

    # Get the size of the partial copy
    have = os.path.getsize(part)

    # If the partial copy is the whole of the source, return 0
    if length is not None and have >= length:
        return 0

    # Return!
    return have


def _verify(path, length, url):
    """Check that what arrived is whole.

    Args:
        path: The path to the copy.

        length: The length of the source.

        url: The URL of the source.
    """
    # If the length is not None and the size of the copy is not
    # the length, raise an error
    if length is not None and os.path.getsize(path) != length:
        raise DownloadError(
            f"{url} was fetched incompletely: expected {length} bytes, "
            f"got {os.path.getsize(path)}."
        )

    # If the copy is not a zip, return
    if not path.endswith(".zip") and not url.lower().endswith(".zip"):
        return

    # Try to read the central directory
    try:
        # Reading the central directory is milliseconds and catches a truncated
        # archive. Testing the members would decompress the whole dump.
        with zipfile.ZipFile(path) as archive:
            archive.infolist()

    except zipfile.BadZipFile as error:
        raise DownloadError(f"{url} was fetched but is not a readable zip: {error}")


def ensure_local_copy(
    url,
    directory=None,
    expect=None,
    refresh=False,
    timeout=None,
    attempts=None,
    chunk_size=None,
):
    """Return the path of a complete local copy, fetching it if there is not one.

    Args:
        url: The source to fetch.

        directory: Where copies are kept. Defaults to the configured directory.

        expect: A `probe` result the copy must match, so that a run split across
                machines cannot end up reading two different snapshots.

        refresh: Fetch again even if a complete copy is already here.

        timeout: Connect and read timeouts, in seconds.

        attempts: How many times to try before giving up.

        chunk_size: How much to hold in memory at a time.

    Returns:
        The path of the copy.

    Raises:
        DownloadError: The source could not be fetched, or would not fit.

        SourceChangedError: The source is no longer the snapshot in `expect`.
    """
    # Get the directory, timeout, attempts and chunk size
    directory = directory or setting("INVENIO_GEOGRAPHIC_IDENTIFIERS_DOWNLOAD_DIR")
    timeout = timeout or setting("INVENIO_GEOGRAPHIC_IDENTIFIERS_DOWNLOAD_TIMEOUT")
    attempts = attempts or setting("INVENIO_GEOGRAPHIC_IDENTIFIERS_DOWNLOAD_ATTEMPTS")
    chunk_size = chunk_size or setting(
        "INVENIO_GEOGRAPHIC_IDENTIFIERS_DOWNLOAD_CHUNK_SIZE"
    )

    # Create the directory
    # Ours alone: a predictable name in a shared temporary directory is a symlink
    # target, and the download is not something to hand a stranger
    os.makedirs(directory, mode=0o700, exist_ok=True)

    # Get the target path
    target = local_path_for(url, directory)
    part = f"{target}.part"

    # Hold the lock
    with _lock_path(f"{target}.lock"):
        # Check if the copy is complete
        source = expect or probe(url, timeout=timeout)
        length = source.get("length")

        # If the copy is complete and not refreshed, return the target
        if not refresh and _is_complete(target, length):
            # Log the reuse
            _get_log().info(f"Reusing {target}.")

            # Return the target
            return target

        # If the copy is not complete and refreshed, remove the
        # partial copy
        if refresh and os.path.exists(part):
            os.remove(part)

        # Initialize the served ETag
        served = None

        for attempt in range(attempts):
            # Get the amount of the source that has already
            # been transferred
            have = _resume_transfer_from(part, length, source)

            # Check if there is room for the transfer
            _check_space_for_transfer(
                directory=directory,
                needed=None if length is None else length - have,
                url=url,
            )

            # Try to transfer the source
            try:
                served = _transfer(url, part, have, timeout, chunk_size)
                break

            # If the transfer failed, raise an error
            except (requests.RequestException, OSError) as error:
                # If this is the last attempt, raise an error
                if attempt == attempts - 1:
                    raise DownloadError(
                        f"Could not fetch {url} after {attempts} attempts: {error}"
                    ) from error

                # The next attempt resumes from wherever this one stopped, so a
                # long transfer makes progress across a flaky connection
                _get_log().warning(f"Fetching {url} failed ({error}); retrying.")

                # Wait before the next attempt
                time.sleep(2**attempt)

        # Verify the copy
        _verify(
            path=part,
            length=length,
            url=url,
        )

        # The operation is only meaningful against a pin: a source that rolled over to the next
        # day's dump mid-run would silently renumber every row, and the shards
        # of that run would no longer cover it exactly once.
        if expect and expect.get("etag") and served and served != expect["etag"]:
            # Raise an error
            raise SourceChangedError(
                f"{url} changed while it was being fetched: expected "
                f"{expect['etag']}, got {served}. Start the run again."
            )

        # Atomic, and on POSIX a reader already working through the previous
        # copy keeps reading it rather than having the ground moved
        os.replace(part, target)

        # Log the success
        _get_log().info(f"Fetched {url} to {target}.")

        # Return
        return target
