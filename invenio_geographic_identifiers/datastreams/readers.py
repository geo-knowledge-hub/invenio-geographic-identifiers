# -*- coding: utf-8 -*-
#
# Copyright (C) 2022 GEO Secretariat.
#
# invenio-geographic-identifiers is free software; you can redistribute it
# and/or modify it under the terms of the MIT License; see LICENSE file for
# more details.

"""Datastreams readers."""

import csv
import io
import os
import zipfile

from invenio_vocabularies.datastreams.errors import ReaderError
from invenio_vocabularies.datastreams.readers import BaseReader


def _validate_shard(index, total):
    """Check a shard is valid.

    A valid shard is one where the index is between 0 and the total minus 1.

    A shard misconfigured silently drops or duplicates rows, which on a
    multi-million row import is expensive to notice and worse to undo. It costs
    nothing to refuse it here instead.
    """
    # If both index and total are None, is valid
    if index is None and total is None:
        return None, None

    # If either index or total is None, invalid
    if index is None or total is None:
        raise ReaderError("Sharding needs both `shard_index` and `shard_total`.")

    # If total is less than 1, invalid
    if total < 1:
        raise ReaderError(f"`shard_total` must be at least 1, got {total}.")

    # If index is not between 0 and total minus 1, invalid
    if not 0 <= index < total:
        raise ReaderError(
            f"`shard_index` must be between 0 and {total - 1}, got {index}."
        )

    # Return!
    return index, total


class ZippedCSVReader(BaseReader):
    """Read `csv` files stored in a `zip` file."""

    def __init__(
        self,
        *args,
        csv_options=None,
        zip_options=None,
        as_dict=True,
        shard_index=None,
        shard_total=None,
        origin_url=None,
        origin_expect=None,
        **kwargs,
    ):
        """Constructor."""
        self.csv_options = csv_options or {}
        self.zip_options = zip_options or {}
        self.as_dict = as_dict

        # Where `origin` came from, when something fetched it on our behalf, and
        # the snapshot it was fetched at. Only set by the fan-out. See
        # `_local_origin` for why that distinction matters.
        self.origin_url = origin_url
        self.origin_expect = origin_expect

        # Validate the shard settings and save it
        self.shard_index, self.shard_total = _validate_shard(
            index=shard_index,
            total=shard_total,
        )

        # Initialize the parent class
        super().__init__(*args, **kwargs)

    def _owns(self, position):
        """Whether the row at this position belongs to this shard."""
        if self.shard_total is None:
            return True

        return position % self.shard_total == self.shard_index

    def _default_origin_url(self):
        """What to fetch when no origin was given at all."""
        return None

    def _local_origin(self):
        """Resolve the origin to a path on this machine, fetching it if needed.

        The rules, in the order they are checked:

        - a path that is here is opened;
        - a path that is *not* here is an error. A mistyped `--origin` has to fail immediately
          rather than quietly pull hundreds of megabytes;
        - a URL, or nothing at all, is fetched.

        Only the fan-out sets `origin_url`, so only a path this package generated
        is allowed to fallback to the network. This is what lets a shard dispatched
        to a worker, that does not share a filesystem with the one that did the
        fetching, get hold of the same bytes instead of failing on a path that is not there.
        """
        # Imported here: the datastreams package is imported to register readers
        # long before anything is fetched, and `requests` need not be paid for by an
        # instance that only ever imports from a local file
        from .download import ensure_local_copy, is_url

        # Get the origin
        origin = self._origin

        # If the origin is a local path that is here, which is the ordinary case
        if origin and not is_url(origin) and os.path.exists(origin):
            return origin

        # If the origin is a local path that is not here, and nothing to fetch it from
        if origin and not is_url(origin) and not self.origin_url:
            raise ReaderError(f"`{origin}` does not exist.")

        # Get the URL to fetch, whatever we were told to fetch, or wherever this reader gets its
        # source from when nobody said
        url = (
            origin
            if is_url(origin)
            else (self.origin_url or self._default_origin_url())
        )

        # If there is no URL to fetch, raise an error
        if not url:
            raise ReaderError("No `origin` was given, and there is nothing to fetch.")

        # Check local copy and download if needed
        local_copy_path = ensure_local_copy(
            url=url,
            expect=self.origin_expect,
        )

        # Return!
        return local_copy_path

    def _iter(self, fp, *args, **kwargs):
        """Reads a csv file and returns a dictionary per element."""
        # Positions run across the archive, not within a member, so that a shard
        # of a multi-member archive stays balanced too.
        position = 0

        # Iterate over the members in the archive
        for member in fp.infolist():
            if not member.is_dir():
                # Open target file
                csvfile = fp.open(member)

                # Check if the file is not a text file
                if not isinstance(csvfile, io.TextIOBase):
                    # Wrap the file in a text file
                    csvfile = io.TextIOWrapper(csvfile)

                # Create a reader depending on the format
                if self.as_dict:
                    # Create a dictionary reader
                    reader = csv.DictReader(csvfile, **self.csv_options)

                else:
                    # Create a reader
                    reader = csv.reader(csvfile, **self.csv_options)

                # Iterate over the rows in the file
                for row in reader:

                    if self._owns(position):
                        yield row

                    position += 1

    def read(self, item=None, *args, **kwargs):
        """Open a `zip` archive or uses the given file pointer."""
        # https://docs.python.org/3/library/zipfile.html
        if item:
            yield from self._iter(fp=item, *args, **kwargs)

        else:
            with zipfile.ZipFile(self._local_origin(), **self.zip_options) as archive:
                yield from self._iter(fp=archive, *args, **kwargs)
