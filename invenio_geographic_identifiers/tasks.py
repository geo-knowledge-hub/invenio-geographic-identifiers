# -*- coding: utf-8 -*-
#
# Copyright (C) 2022 GEO Secretariat.
#
# invenio-geographic-identifiers is free software; you can redistribute it
# and/or modify it under the terms of the MIT License; see LICENSE file for
# more details.

"""Celery tasks for the geographic identifiers vocabularies."""

from copy import deepcopy

from celery import shared_task
from flask import current_app
from invenio_vocabularies.datastreams import DataStreamFactory
from invenio_vocabularies.datastreams.errors import ReaderError

from .datastreams.download import ensure_local_copy, is_url, probe, setting


def _describe(result):
    """Describe exception raised by an entry.

    Args:
        result: The result of the entry.

    Returns:
        The description of the exception.
    """
    entry = result.entry or {}
    identifier = entry.get("id", "<no id>") if isinstance(entry, dict) else "<no id>"
    exception = result.exc

    return f"{identifier}: {type(exception).__name__}: {exception}".rstrip(": ")


def process_datastream(config, limit=None, on_error=None):
    """Process a datastream.

    Args:
        config: The datastream configuration.

        limit: The number of entries to process.

        on_error: The function to call when an error occurs.

    Returns:
        The number of successful, errored and filtered entries.
    """
    # Set the default error handler
    on_error = on_error or current_app.logger.error

    # Create the data stream
    stream = DataStreamFactory.create(
        readers_config=config["readers"],
        transformers_config=config.get("transformers"),
        writers_config=config["writers"],
        batch_size=config.get("batch_size", 1000),
        write_many=config.get("write_many", False),
    )

    # Initialize the counts
    counts = {
        "success": 0,
        "errored": 0,
        "filtered": 0,
    }

    # Set the limit
    left = limit

    # Process the data stream
    for result in stream.process():

        # If the entry is filtered, increment the filtered count
        if result.filtered:
            counts["filtered"] += 1

        # An entry can fail in two ways, and only one of them fills `errors`.
        # `create_or_update_many` catches whatever a record raises and hands it
        # back as `exc`. For example, a deleted identifier arrives that way, so counting
        # only `errors` reports entries as written that were not written at all.
        if result.errors or result.exc:

            # Iterate over the errors
            for error in result.errors:
                on_error(error)

            # If there is an exception, describe it and increment
            # the errored count
            if result.exc:
                on_error(_describe(result))

            # Increment the errored count
            counts["errored"] += 1

        else:
            counts["success"] += 1

        # If the limit is set, decrement the limit and
        # break if it is 0
        if left is not None:
            left -= 1

            if left == 0:
                break

    return counts


@shared_task
def import_geoidentifiers(config):
    """Import one datastream, or one shard of one, into the vocabulary.

    Sharding is a property of the reader, so a shard is an ordinary datastream
    run and this task needs to know nothing about it: give each of them a
    configuration whose reader carries its own `shard_index`, and between them
    they cover the source exactly once.
    """
    # Process the data stream
    counts = process_datastream(config)

    # Output the result
    current_app.logger.info(
        f"Geographic identifiers import finished: {counts['success']} succeeded, "
        f"{counts['errored']} contained errors, {counts['filtered']} were filtered."
    )

    # Return!
    return counts


def resolve_origin(config, default_url=None, refresh=False):
    """Resolve URL or missing origin into a valid local path.

    Args:
        config: The datastream configuration.

        default_url: What to fetch when the configuration names no origin.

        refresh: Fetch again even if a complete copy is already here.

    Returns:
        dict: A copy of the configuration whose reader reads a file on this machine,
        and which also records where that file came from, so a shard dispatched
        to a worker with its own filesystem can fetch the same snapshot rather
        than fail on a path it cannot see.
    """
    config = deepcopy(config)
    reader_args = config["readers"][0].setdefault("args", {})

    origin = reader_args.get("origin")

    # Local file and is available, is considered valid
    if origin and not is_url(origin):
        return config

    # Get the URL to fetch
    url = origin or default_url

    # If there is no URL to fetch, raise an error
    if not url:
        raise ReaderError("No `origin` was given, and there is nothing to fetch.")

    # Probed once and pinned, so every shard is reading the same geonames dump. The
    # dump is rebuilt daily, and two shards on two snapshots would renumber the
    # rows between them and quietly stop covering the source exactly once
    source = probe(url)

    # Ensure the local copy
    local_copy_path = ensure_local_copy(
        url=url,
        expect=source,
        refresh=refresh,
    )

    # Update configuration
    reader_args["origin"] = local_copy_path
    reader_args["origin_url"] = url
    reader_args["origin_expect"] = source

    # Return!
    return config


def dispatch_shards(config, shards):
    """Send one `import_geoidentifiers` task per shard.

    Args:
        config: The datastream configuration.

        shards: The number of shards to split the source into.

    Returns:
        The dispatched `AsyncResult`s, in shard order.
    """
    # Initialize the dispatched tasks
    dispatched = []

    # Iterate over the shards
    for index in range(shards):
        shard_config = deepcopy(config)

        shard_config["readers"][0].setdefault("args", {})["shard_total"] = shards
        shard_config["readers"][0]["args"]["shard_index"] = index

        dispatched.append(import_geoidentifiers.delay(shard_config))

    # Return!
    return dispatched


@shared_task
def import_geoidentifiers_sharded(config, shards=1, refresh=False):
    """Fan an import out across shards.

    Args:
        config: The datastream configuration.

        shards: The number of shards to split the source into.

        refresh: Fetch the source again even if a complete copy is already here.

    Returns:
        The dispatched `AsyncResult`s, in shard order.
    """
    # Fetch the source first, if there is one to fetch, so that the shards all
    # read one file rather than each fetching a copy of it
    config = resolve_origin(
        config=config,
        default_url=setting("INVENIO_GEOGRAPHIC_IDENTIFIERS_GEONAMES_DUMP_URL"),
        refresh=refresh,
    )

    # Dispatch the shards
    dispatched = dispatch_shards(config=config, shards=shards)

    # Output the result
    current_app.logger.info(
        f"Geographic identifiers import split into {shards} shards: "
        + ", ".join(task.id for task in dispatched)
    )

    # Return!
    return [task.id for task in dispatched]
