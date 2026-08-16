# -*- coding: utf-8 -*-
#
# Copyright (C) 2022 GEO Secretariat.
#
# invenio-geographic-identifiers is free software; you can redistribute it
# and/or modify it under the terms of the MIT License; see LICENSE file for
# more details.

"""Tests for reading a dump in parallel."""

import copy

import pytest
from invenio_vocabularies.datastreams.errors import ReaderError
from kombu.serialization import dumps

from invenio_geographic_identifiers.contrib.geonames.datastreams import (
    DATASTREAM_CONFIG,
    GeoNamesReader,
)

#
# Constants
#
READER_ARGS = copy.deepcopy(DATASTREAM_CONFIG["readers"][0]["args"])


#
# Helper
#
def read_geonames(origin, **kwargs):
    """Read a dump, returning the identifier of every row that came back."""
    reader = GeoNamesReader(origin=origin, **{**READER_ARGS, **kwargs})

    return [row["geonameid"] for row in reader.read()]


#
# Sharding
#
@pytest.mark.parametrize("shards", [1, 3, 64])
def test_shards_cover_the_source_exactly_once(geonames_mixed_archive, shards):
    """Every row is read by one shard, by no more than one."""
    # Read the geonames
    geonames_data = read_geonames(geonames_mixed_archive)

    # Read by a shard
    parts = [
        read_geonames(geonames_mixed_archive, shard_index=index, shard_total=shards)
        for index in range(shards)
    ]

    # Read by a shard
    read_by_a_shard = [identifier for part in parts for identifier in part]

    # Confirm results
    assert sorted(read_by_a_shard) == sorted(geonames_data)
    assert len(set(read_by_a_shard)) == len(read_by_a_shard)

    # Confirm no shard left carrying meaningfully more of it than another
    assert max(len(part) for part in parts) - min(len(part) for part in parts) <= 1


@pytest.mark.parametrize(
    "shard_args",
    [
        {"shard_index": 0},  # no total
        {"shard_index": 4, "shard_total": 4},  # past the end
        {"shard_index": 0, "shard_total": 0},  # no shards at all
    ],
)
def test_an_unusable_shard_is_refused(geonames_mixed_archive, shard_args):
    """A shard that would drop or duplicate rows is refused."""
    with pytest.raises(ReaderError):
        GeoNamesReader(origin=geonames_mixed_archive, **{**READER_ARGS, **shard_args})


#
# Feature classes
#
@pytest.mark.parametrize("feature_classes", ["P,A", [" P ", "A"]])
def test_the_filter_accepts_a_list_or_a_string(
    geonames_mixed_archive, geonames_mixed_rows, feature_classes
):
    """The same selection can come from a CLI flag or a job argument."""
    expected = [
        row["geonameid"]
        for row in geonames_mixed_rows
        if row["feature_class"] in ("P", "A")
    ]

    # Read the geonames
    generated = read_geonames(geonames_mixed_archive, feature_classes=feature_classes)

    # Confirm results
    assert generated == expected


def test_no_filter_keeps_every_class(geonames_mixed_archive, geonames_mixed_rows):
    """Importing everything stays the default."""
    assert len(read_geonames(geonames_mixed_archive)) == len(geonames_mixed_rows)


def test_an_empty_filter_is_refused(geonames_mixed_archive):
    """Empty feature classes are refused."""
    with pytest.raises(ReaderError):
        GeoNamesReader(origin=geonames_mixed_archive, **READER_ARGS, feature_classes=[])


def test_the_filter_does_not_move_rows_between_shards(geonames_mixed_archive):
    """Filter does not move rows between shards."""
    # Read the geonames
    kept = set(read_geonames(geonames_mixed_archive, feature_classes="P,A"))

    # Read by a shard
    for index in range(4):
        unfiltered = read_geonames(
            geonames_mixed_archive, shard_index=index, shard_total=4
        )

        # Read by a shard
        filtered = read_geonames(
            geonames_mixed_archive,
            shard_index=index,
            shard_total=4,
            feature_classes="P,A",
        )

        # Confirm results
        assert set(filtered) == set(unfiltered) & kept


#
# Quoting
#
def test_a_name_holding_quotes_is_read_as_written(make_geonames_archive):
    """A name holding quotes is read as written."""
    # Make the archive
    archive = make_geonames_archive(
        [
            {
                "geonameid": "1",
                "name": '"Vatikan"',
                "asciiname": '"Vatikan"',
                "latitude": "0.0",
                "longitude": "0.0",
                "feature_class": "P",
            }
        ]
    )

    # Read the geonames
    reader = GeoNamesReader(origin=archive, **READER_ARGS)
    rows = list(reader.read())

    # Confirm results
    assert rows[0]["name"] == '"Vatikan"'


#
# The Celery boundary
#
@pytest.mark.parametrize("serializer", ["msgpack", "json"])
def test_the_configuration_can_reach_a_worker(serializer):
    """The whole configuration travels as a task argument, so it must encode."""
    # Dump the configuration
    dumps(DATASTREAM_CONFIG, serializer=serializer)
