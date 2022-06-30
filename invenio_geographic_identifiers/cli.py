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
from invenio_vocabularies.datastreams import DataStreamFactory

from .contrib.geonames.datastreams import DATASTREAM_CONFIG as geonames_ds_config


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
        config["reader"]["args"]["origin"] = origin

    return config


@click.group()
def geoidentifiers():
    """Geoidentifiers command."""


def _process_vocab(config, num_samples=None):
    """Import a vocabulary."""
    ds = DataStreamFactory.create(
        reader_config=config["reader"],
        transformers_config=config.get("transformers"),
        writers_config=config["writers"],
    )

    success, errored = 0, 0
    left = num_samples or -1
    for result in ds.process():
        left = left - 1
        if result.errors:
            for err in result.errors:
                click.secho(err, fg="red")
            errored += 1
        else:
            success += 1
        if left == 0:
            click.secho(f"Number of samples reached {num_samples}", fg="green")
            break
    return success, errored


def _output_process(vocabulary, op, success, errored):
    """Outputs the result of an operation."""
    total = success + errored

    color = "green"
    if errored:
        color = "yellow" if success else "red"

    click.secho(
        f"Vocabulary {vocabulary} {op}. Total items {total}. \n"
        f"{success} items succeeded, {errored} contained errors.",
        fg=color,
    )


@geoidentifiers.command(name="import")
@click.option("-v", "--vocabulary", type=click.STRING, required=True)
@click.option("-f", "--filepath", type=click.STRING)
@click.option("-o", "--origin", type=click.STRING)
@click.option("-n", "--num-samples", type=click.INT)
@with_appcontext
def import_vocab(vocabulary, filepath=None, origin=None, num_samples=None):
    """Import a vocabulary."""
    if not filepath and not origin:
        click.secho("One of --filepath or --origin must be present", fg="red")
        exit(1)

    config = get_config_for_ds(vocabulary, filepath, origin)
    success, errored = _process_vocab(config, num_samples)

    _output_process(vocabulary, "imported", success, errored)


@geoidentifiers.command()
@click.option("-v", "--vocabulary", type=click.STRING, required=True)
@click.option("-f", "--filepath", type=click.STRING)
@click.option("-o", "--origin", type=click.STRING)
@with_appcontext
def update(vocabulary, filepath=None, origin=None):
    """Import a vocabulary."""
    if not filepath and not origin:
        click.secho("One of --filepath or --origin must be present", fg="red")
        exit(1)

    config = get_config_for_ds(vocabulary, filepath, origin)

    for w_conf in config["writers"]:
        w_conf["args"]["update"] = True

    success, errored = _process_vocab(config)

    _output_process(vocabulary, "updated", success, errored)


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
    if not id and not all:
        click.secho("An identifier or the --all flag "
                    "must be present.", fg="red")
        exit(1)

    service = get_service_for_vocabulary(vocabulary)
    if identifier:
        try:
            if service.delete(identifier, system_identity):
                click.secho(f"{identifier} deleted "
                            f"from {vocabulary}.", fg="green")
        except (PIDDeletedError, PIDDoesNotExistError):
            click.secho(f"PID {identifier} not found.")
