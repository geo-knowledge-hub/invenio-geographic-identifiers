# -*- coding: utf-8 -*-
#
# Copyright (C) 2022 GEO Secretariat.
#
# invenio-geographic-identifiers is free software; you can redistribute it
# and/or modify it under the terms of the MIT License; see LICENSE file for
# more details.

"""Geographic identifiers vocabulary CLI."""

from copy import deepcopy

import click
import yaml
from flask.cli import with_appcontext
from invenio_access.permissions import system_identity
from invenio_pidstore.errors import PIDDeletedError, PIDDoesNotExistError
from invenio_records_resources.proxies import current_service_registry

from .contrib.geonames.datastreams import DATASTREAM_CONFIG as geonames_ds_config
from .datastreams.download import setting
from .tasks import dispatch_shards, process_datastream, resolve_origin


def get_service_for_vocabulary(vocabulary):
    """Generate the DataStream service."""
    return current_service_registry.get("geoidentifiers")


def get_config_for_ds(vocabulary, filepath=None, origin=None):
    """Generate the DataStream configuration."""
    config = None

    if vocabulary == "geonames":
        config = deepcopy(geonames_ds_config)
    else:
        raise ValueError("Invalid vocabulary type")

    if filepath:
        with open(filepath) as f:
            config = yaml.safe_load(f).get(vocabulary)

    if origin:
        config["readers"][0]["args"]["origin"] = origin

    return config


#
# Datastream options
#
def stream_options(command):
    """Add options that shape how a datastream runs.

    Args:
        command: The command to add the options to.

    Returns:
        The command with the options added.
    """
    # List of options to add
    options = [
        click.option(
            "--shards",
            type=click.INT,
            help=(
                "Split the source into this many shards. Each one reads the "
                "whole source but keeps only its own rows, so between them they "
                "cover it exactly once. Needs --shard or --celery."
            ),
        ),
        click.option(
            "--shard",
            type=click.INT,
            help="Run only this shard, in this process. Counts from 0.",
        ),
        click.option(
            "--celery",
            is_flag=True,
            default=False,
            help="Send every shard to a Celery worker instead of running here.",
        ),
        click.option(
            "--batch-size",
            type=click.INT,
            help="Entries to accumulate before writing them. Defaults to 1000.",
        ),
        click.option(
            "--write-many/--no-write-many",
            default=None,
            help=(
                "Write a batch at a time, in one transaction and one bulk index "
                "request. Much faster, but it upserts: an entry that already "
                "exists is rewritten rather than reported. On by default for "
                "sharded runs, off otherwise."
            ),
        ),
        click.option(
            "--feature-classes",
            type=click.STRING,
            help=(
                "Comma-separated GeoNames feature classes to keep, e.g. 'P,A' "
                "for populated places and administrative divisions. All by "
                "default."
            ),
        ),
        click.option(
            "--refresh",
            is_flag=True,
            default=False,
            help=(
                "Fetch the source again even if a copy was already downloaded. "
                "Only applies when the source is downloaded rather than given."
            ),
        ),
    ]

    for option in reversed(options):
        command = option(command)

    return command


def _shape_config(
    config,
    shard=None,
    shards=None,
    batch_size=None,
    write_many=None,
    feature_classes=None,
):
    """Apply run options to a datastream configuration.

    Args:
        config: The datastream configuration.

        shard: The shard to run.

        shards: The number of shards to split the source into.

        batch_size: The number of entries to accumulate before writing them.

        write_many: Whether to write many entries at a time.

        feature_classes: The feature classes to keep.

    Returns:
        The datastream configuration with the options applied.
    """
    # Copy the configuration
    config = deepcopy(config)
    reader_args = config["readers"][0].setdefault("args", {})

    # Only for a shard run in this process. A dispatched run gets its index from
    # `dispatch_shards`, which numbers the shards as it queues them.
    if shards is not None and shard is not None:
        reader_args["shard_total"] = shards
        reader_args["shard_index"] = shard

    # If no feature classes are specified, keep all
    if feature_classes is not None:
        reader_args["feature_classes"] = feature_classes

    # Set the batch size
    if batch_size is not None:
        config["batch_size"] = batch_size

    # Set the write many flag
    if write_many is None:
        # Nobody splits a source into shards in order to then commit one record
        # at a time. Say so out loud rather than quietly running fifty times
        # slower than the flag was asked for.
        write_many = shards is not None

    # Set the write many flag
    config["write_many"] = write_many

    # Return!
    return config


def _validate_shard_options(shards, shard, celery):
    """Validate shard options.

    Args:
        shards: The number of shards to split the source into.

        shard: The shard to run.

        celery: Whether to send every shard to a Celery worker.
    """
    # If no shards are specified, check if a shard is specified and
    # celery is enabled
    if shards is None:

        # If a shard is specified, raise an error
        if shard is not None:
            raise click.UsageError("--shard needs --shards.")

        # If celery is enabled, raise an error
        if celery:
            raise click.UsageError("--celery needs --shards.")

        return

    # If shards is less than 1, raise an error
    if shards < 1:
        raise click.UsageError("--shards must be at least 1.")

    # If celery is enabled and a shard is specified, raise an error
    if celery and shard is not None:
        raise click.UsageError("--celery runs every shard; drop --shard.")

    # If celery is not enabled and a shard is not specified, raise an error
    if not celery and shard is None:
        raise click.UsageError(
            "--shards needs either --shard, to run one here, or --celery, to "
            "send them all to workers."
        )

    # If a shard is specified and it is not between 0 and the number of
    # shards minus 1, raise an error
    if shard is not None and not 0 <= shard < shards:
        raise click.UsageError(f"--shard must be between 0 and {shards - 1}.")


#
# Running
#
def _process_vocab(config, num_samples=None):
    """Import a vocabulary.

    Args:
        config: The datastream configuration.

        num_samples: The number of samples to process.

    Returns:
        The number of successful, errored and filtered entries.
    """
    counts = process_datastream(
        config,
        limit=num_samples,
        on_error=lambda error: click.secho(error, fg="red"),
    )

    if num_samples is not None and counts["success"] + counts["errored"] == num_samples:
        click.secho(f"Number of samples reached {num_samples}", fg="green")

    return counts["success"], counts["errored"], counts["filtered"]


def _resolve_origin(config, refresh=False):
    """Fetch the source, when there is one to fetch, before anything else runs.

    Args:
        config: The datastream configuration.

        refresh: Fetch the source again even if a copy is already here.

    Returns:
        The configuration, with its origin resolved to a local path.
    """
    return resolve_origin(
        config,
        default_url=setting("INVENIO_GEOGRAPHIC_IDENTIFIERS_GEONAMES_DUMP_URL"),
        refresh=refresh,
    )


def _dispatch_shards(config, shards):
    """Send every shard to a Celery worker.

    Args:
        config: The datastream configuration.

        shards: The number of shards to split the source into.

    Returns:
        None. This function is used for its side effects.
    """
    # Iterate over the shards
    for index, task in enumerate(dispatch_shards(config, shards)):
        click.secho(f"Shard {index}/{shards} dispatched as {task.id}", fg="green")

    # Output a message
    click.secho(
        f"\n{shards} shards queued. They write in bulk, which does not index "
        "inline: run `invenio index run` alongside them, or the records land "
        "in the database while the index stays empty.",
        fg="yellow",
    )


def _output_process(vocabulary, op, success, errored, filtered):
    """Output the result of an operation.

    Args:
        vocabulary: The vocabulary name.

        op: The operation name.

        success: The number of successful entries.

        errored: The number of errored entries.

        filtered: The number of filtered entries.

    Returns:
        None. This function is used for its side effects.
    """
    # Calculate the total number of entries
    total = success + errored

    # Set the color based on the number of errored entries
    color = "green"
    if errored:
        color = "yellow" if success else "red"

    # Output the result
    click.secho(
        f"Vocabulary {vocabulary} {op}. Total items {total}. \n"
        f"{success} items succeeded\n"
        f"{errored} contained errors\n"
        f"{filtered} were filtered.",
        fg=color,
    )


#
# Commands
#
@click.group()
def geoidentifiers():
    """Geoidentifiers command."""


@geoidentifiers.command(name="import")
@click.option("-v", "--vocabulary", type=click.STRING, required=True)
@click.option("-f", "--filepath", type=click.STRING)
@click.option("-o", "--origin", type=click.STRING)
@click.option("-n", "--num-samples", type=click.INT)
@stream_options
@with_appcontext
def import_vocab(
    vocabulary,
    filepath=None,
    origin=None,
    num_samples=None,
    shards=None,
    shard=None,
    celery=False,
    batch_size=None,
    write_many=None,
    feature_classes=None,
    refresh=False,
):
    """Import a vocabulary."""
    # Validate the shard options
    _validate_shard_options(shards, shard, celery)

    # Shape the configuration
    config = get_config_for_ds(
        vocabulary=vocabulary,
        filepath=filepath,
        origin=origin,
    )
    config = _shape_config(
        config=config,
        shard=shard,
        shards=shards,
        batch_size=batch_size,
        write_many=write_many,
        feature_classes=feature_classes,
    )

    # Resolve the source
    config = _resolve_origin(
        config=config,
        refresh=refresh,
    )

    # If celery is enabled, dispatch the shards
    if celery:
        _dispatch_shards(config, shards)
        return

    # Process the vocabulary
    success, errored, filtered = _process_vocab(config, num_samples)

    # Output the result
    _output_process(vocabulary, "imported", success, errored, filtered)


@geoidentifiers.command()
@click.option("-v", "--vocabulary", type=click.STRING, required=True)
@click.option("-f", "--filepath", type=click.STRING)
@click.option("-o", "--origin", type=click.STRING)
@stream_options
@with_appcontext
def update(
    vocabulary,
    filepath=None,
    origin=None,
    shards=None,
    shard=None,
    celery=False,
    batch_size=None,
    write_many=None,
    feature_classes=None,
    refresh=False,
):
    """Import a vocabulary."""
    # Validate the shard options
    _validate_shard_options(shards, shard, celery)

    # Shape the configuration
    config = get_config_for_ds(vocabulary, filepath, origin)

    # Set the update flag
    for w_conf in config["writers"]:
        w_conf["args"]["update"] = True

    # Shape the configuration
    config = _shape_config(
        config,
        shard=shard,
        shards=shards,
        batch_size=batch_size,
        write_many=write_many,
        feature_classes=feature_classes,
    )

    # Resolve the source. No origin means "fetch the configured one".
    config = _resolve_origin(config, refresh=refresh)

    # If celery is enabled, dispatch the shards
    if celery:
        _dispatch_shards(config, shards)
        return

    # Process the vocabulary
    success, errored, filtered = _process_vocab(config)

    # Output the result
    _output_process(vocabulary, "updated", success, errored, filtered)


@geoidentifiers.command()
@click.option("-v", "--vocabulary", type=click.STRING, required=True)
@click.option("-o", "--origin", type=click.STRING)
@click.option(
    "--refresh",
    is_flag=True,
    default=False,
    help="Fetch again even if a copy was already downloaded.",
)
@with_appcontext
def download(vocabulary, origin=None, refresh=False):
    """Fetch a vocabulary source without importing it.

    Args:
        vocabulary: The vocabulary name.

        origin: The origin of the vocabulary.

        refresh: Fetch the source again even if a copy is already here.

    Returns:
        None. This function is used for its side effects.

    Notes:
        Worth doing on its own before a large run. A GeoNames dump takes hours to
        fetch, and a job or a shard that fetches it is holding a worker for all of
        that time. Once the copy is here, every later run reuses it.
    """
    # Get config object
    config = get_config_for_ds(
        vocabulary=vocabulary,
        origin=origin,
    )

    # Resolve origin
    config = _resolve_origin(config=config, refresh=refresh)

    # Output the path the local copy ended up at
    click.secho(config["readers"][0]["args"]["origin"], fg="green")


@geoidentifiers.command()
@click.option("-v", "--vocabulary", type=click.STRING, required=True)
@click.option(
    "-i",
    "--identifier",
    type=click.STRING,
    help="Identifier of the GeoIdentifiers vocabulary item to delete.",
)
@click.option("--all", is_flag=True, default=False, help="Not supported yet.")
@with_appcontext
def delete(vocabulary, identifier, all):
    """Delete all items or a specific one of the vocabulary."""
    if not identifier and not all:
        click.secho("An identifier or the --all flag " "must be present.", fg="red")
        exit(1)

    service = get_service_for_vocabulary(vocabulary)

    if identifier:
        try:
            if service.delete(system_identity, identifier):
                click.secho(f"{identifier} deleted " f"from {vocabulary}.", fg="green")

        except (PIDDeletedError, PIDDoesNotExistError):
            click.secho(f"PID {identifier} not found.")
