# -*- coding: utf-8 -*-
#
# Copyright (C) 2022 GEO Secretariat.
#
# invenio-geographic-identifiers is free software; you can redistribute it
# and/or modify it under the terms of the MIT License; see LICENSE file for
# more details.

"""Tests for running an import across several workers."""

import copy

import click
import pytest
from invenio_access.permissions import system_identity
from kombu.serialization import dumps

from invenio_geographic_identifiers.cli import _shape_config, _validate_shard_options
from invenio_geographic_identifiers.contrib.geonames.datastreams import (
    DATASTREAM_CONFIG,
)
from invenio_geographic_identifiers.jobs import ImportGeoNamesJob
from invenio_geographic_identifiers.tasks import process_datastream


#
# Configuration
#
def config_for(origin, **kwargs):
    """A datastream configuration reading the given origin."""
    # Make a copy of the configuration
    config = copy.deepcopy(DATASTREAM_CONFIG)

    # Set the origin
    config["readers"][0]["args"]["origin"] = origin

    # Return!
    return _shape_config(config, **kwargs)


#
# CLI options
#
@pytest.mark.parametrize(
    "shards,shard,celery",
    [
        (None, 0, False),  # a shard of nothing
        (None, None, True),  # dispatch nothing
        (0, 0, False),  # no shards at all
        (4, 4, False),  # past the end
        (4, None, False),  # which shard?
        (4, 1, True),  # dispatch all, or run one?
    ],
)
def test_unusable_shard_options_are_refused(shards, shard, celery):
    """The combinations that would silently do the wrong thing are named."""
    with pytest.raises(click.UsageError):
        _validate_shard_options(shards, shard, celery)


@pytest.mark.parametrize(
    "shards,shard,celery",
    [
        (None, None, False),  # no shards at all
        (4, 0, False),  # first shard
        (4, 3, False),  # past the end
        (4, None, True),  # which shard?
    ],
)
def test_usable_shard_options_are_accepted(shards, shard, celery):
    """The combinations that make sense are accepted."""
    _validate_shard_options(shards, shard, celery)


def test_sharding_turns_batched_writing_on(geonames_archive):
    """Nobody shards a source in order to then commit one record at a time."""
    assert config_for(geonames_archive, shards=4, shard=0)["write_many"] is True

    # write_many is off for an ordinary run
    assert config_for(geonames_archive)["write_many"] is False


def test_batched_writing_can_be_asked_for_either_way(geonames_archive):
    """write_many can be asked for explicitly or implicitly."""
    # Explicitly
    assert (
        config_for(geonames_archive, shards=4, shard=0, write_many=False)["write_many"]
        is False
    )

    # Implicitly
    assert config_for(geonames_archive, write_many=True)["write_many"] is True


def test_only_a_shard_run_here_is_numbered(geonames_archive):
    """A dispatched run is numbered as it is queued, not before."""
    # A shard of four
    reader_args = config_for(geonames_archive, shards=4, shard=2)["readers"][0]["args"]
    assert (reader_args["shard_index"], reader_args["shard_total"]) == (2, 4)

    # No shard at all
    reader_args = config_for(geonames_archive, shards=4)["readers"][0]["args"]
    assert "shard_index" not in reader_args


#
# The job
#
def test_the_job_builds_a_configuration_a_worker_can_read():
    """The whole configuration is a task argument, so it has to encode."""
    arguments = ImportGeoNamesJob.build_task_arguments(
        job_obj=None,
        origin="allCountries.zip",
        shards=8,
        feature_classes="P,A",
    )

    # Dump the arguments
    dumps(arguments, serializer="msgpack")

    # Confirm properties
    assert arguments["shards"] == 8
    assert arguments["config"]["readers"][0]["args"]["origin"] == "allCountries.zip"
    assert arguments["config"]["readers"][0]["args"]["feature_classes"] == "P,A"

    # A job is a bulk load, and a repeat run of it is an update
    assert arguments["config"]["write_many"] is True
    assert arguments["config"]["writers"][0]["args"]["update"] is True


def test_the_job_leaves_the_shipped_configuration_untouched():
    """`build_task_arguments` works on a copy, so runs cannot bleed into each other."""
    # Build the arguments
    ImportGeoNamesJob.build_task_arguments(
        job_obj=None,
        origin="one.zip",
        shards=2,
    )

    # Confirm properties
    assert "origin" not in DATASTREAM_CONFIG["readers"][0]["args"]
    assert DATASTREAM_CONFIG["write_many"] is False


#
# Running a shard
#
def test_shards_together_import_the_whole_source(
    app, db, service, geonames_archive, search_clear
):
    """Three shards of a three-row dump import one row each, and all of them succeed."""
    # Process the shards
    counts = [
        process_datastream(config_for(geonames_archive, shards=3, shard=index))
        for index in range(3)
    ]

    # Confirm the counts
    assert [count["success"] for count in counts] == [1, 1, 1]
    assert not [count for count in counts if count["errored"]]

    # Confirm the identifiers
    for identifier in ("geonames::2657896", "geonames::2661552", "geonames::3169070"):
        assert service.read(system_identity, identifier).id == identifier


def test_a_batched_import_queues_the_records_for_indexing(
    app, db, service, geonames_archive, search_clear
):
    """Batched writing queues the records for indexing, not indexing them immediately."""
    # Process the datastream
    process_datastream(config_for(geonames_archive, write_many=True))

    # Confirm the stored record
    assert service.read(system_identity, "geonames::2661552").id == "geonames::2661552"

    # Confirm the indexed record
    service.indexer.refresh()
    assert service.search(system_identity, q="scheme:geonames").total == 0


def test_a_deleted_entry_is_reported_and_the_shard_finishes(
    app, db, service, geonames_archive, search_clear
):
    """A tombstoned identifier fails its own entry and nothing else succeeds."""
    # Process the datastream
    process_datastream(config_for(geonames_archive))

    # Delete the record
    service.delete(system_identity, "geonames::2661552")

    # Process the datastream
    reported = []
    counts = process_datastream(
        config=config_for(geonames_archive, write_many=True),
        on_error=reported.append,
    )

    # Confirm the counts
    assert counts["errored"] == 1  # the tombstoned entry
    assert counts["success"] == 2  # the other two entries

    # Confirm the reported errors
    assert reported == ["geonames::2661552: PIDDeletedError"]


def test_a_batched_import_rewrites_what_is_already_there(
    app, db, service, geonames_archive, search_clear
):
    """Batched writing upserts, so a re-run updates instead of reporting duplicates."""
    config = config_for(geonames_archive, write_many=True)

    first = process_datastream(config)
    second = process_datastream(config)

    # Confirm the counts
    assert first["success"] == 3
    assert second["success"] == 3
    assert second["errored"] == 0
