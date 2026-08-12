# -*- coding: utf-8 -*-
#
# Copyright (C) 2022 GEO Secretariat.
#
# invenio-geographic-identifiers is free software; you can redistribute it
# and/or modify it under the terms of the MIT License; see LICENSE file for
# more details.

"""Geographic identifiers datastreams tests."""

import copy

import pytest
from invenio_access.permissions import system_identity
from invenio_vocabularies.datastreams import DataStreamFactory, StreamEntry

from invenio_geographic_identifiers.contrib.geonames.datastreams import (
    DATASTREAM_CONFIG,
    GeoNamesTransformer,
)


def config_for(origin):
    """The GeoNames datastream configuration."""
    config = copy.deepcopy(DATASTREAM_CONFIG)
    config["readers"][0]["args"]["origin"] = origin

    return config


def run(config):
    """Process a datastream and return its results."""
    stream = DataStreamFactory.create(
        readers_config=config["readers"],
        transformers_config=config.get("transformers"),
        writers_config=config["writers"],
    )

    return list(stream.process())


def transform(**row):
    """Run a raw GeoNames row through the transformer."""
    row.setdefault("latitude", "47.36667")
    row.setdefault("longitude", "8.55")

    return GeoNamesTransformer().apply(StreamEntry(row)).entry


#
# Transformer
#
def test_transformer_maps_a_geonames_row():
    """A GeoNames row becomes a geographic identifier."""
    entry = transform(
        geonameid="2657896",
        name="Zürich",
        asciiname="Zuerich",
        alternatenames="Zurich,Zürich,Turicum",
        feature_class="P",
        feature_code="PPLA",
        country_code="CH",
        admin1_code="ZH",
        admin2_code="112",
        population="415367",
        dem="429",
        timezone="Europe/Zurich",
        modification_date="2026-04-13",
    )

    assert entry["id"] == "geonames::2657896"
    assert entry["scheme"] == "geonames"
    assert entry["name"] == "Zürich"

    # Coordinates are numbers, in GeoJSON order
    assert entry["locations"] == [
        {
            "geometry": {
                "type": "Point",
                "coordinates": [8.55, 47.36667],
            },
        },
    ]

    assert entry["extras"] == {
        "ascii_name": "Zuerich",
        "alternate_names": ["Zurich", "Zürich", "Turicum"],
        "country": {
            "code": "CH",
            "name": "Switzerland",
            "official_name": "Swiss Confederation",
        },
        "admin": {
            "level1": {"code": "ZH", "name": "Zurich"},
            "level2": {"code": "112"},
        },
        "feature": {
            "class": "P",
            "class_name": "city, village,...",
            "code": "PPLA",
            "name": "seat of a first-order administrative division",
        },
        "population": 415367,
        "dem": 429,
        "timezone": "Europe/Zurich",
        "modified": "2026-04-13",
    }


def test_transformer_names_a_fips_administrative_division():
    """Division names come from GeoNames table, not from ISO 3166-2."""
    entry = transform(
        geonameid="3169070",
        name="Rome",
        country_code="IT",
        admin1_code="07",
    )

    # Confirm result
    assert entry["extras"]["admin"]["level1"] == {"code": "07", "name": "Lazio"}


def test_transformer_without_a_country():
    """A row belonging to no country transforms anyway."""
    entry = transform(
        geonameid="6295630",
        name="Earth",
        asciiname="Earth",
        country_code="",
    )

    # Confirm result
    assert entry["extras"] == {"ascii_name": "Earth"}


def test_transformer_keeps_an_unknown_country_code():
    """A country code ISO does not know is kept."""
    entry = transform(
        geonameid="1",
        name="Nowhere",
        country_code="XX",
    )

    # Confirm result
    assert entry["extras"]["country"] == {"code": "XX"}


def test_transformer_without_an_official_country_name():
    """A country with no official name resolves to the rest of its names."""
    entry = transform(
        geonameid="2147714",
        name="Sydney",
        country_code="AU",
    )

    # Confirm result
    assert entry["extras"]["country"] == {"code": "AU", "name": "Australia"}


def test_transformer_drops_the_elevation_sentinel():
    """`-9999` is the digital elevation model's no-data value, not a depth."""
    entry = transform(
        geonameid="1",
        name="Nowhere",
        dem="-9999",
        elevation="",
        timezone="UTC",
    )

    # Confirm result
    assert entry["extras"] == {"timezone": "UTC"}


def test_transformer_omits_empty_extras():
    """A row with nothing to say about itself carries no extras at all."""
    entry = transform(
        geonameid="1",
        name="Nowhere",
    )

    # Confirm result
    assert "extras" not in entry


def test_transformer_keeps_a_zero_population():
    """Zero is a measurement, and empty is the absence of one."""
    entry = transform(
        geonameid="1",
        name="Nowhere",
        population="0",
    )

    # Confirm result
    assert entry["extras"]["population"] == 0


def test_transformer_with_an_unknown_feature_code():
    """An unrecognised feature code keeps the code but gains no description."""
    entry = transform(
        geonameid="1",
        name="Nowhere",
        feature_class="P",
        feature_code="ZZZZ",
    )

    # Confirm result
    assert entry["extras"]["feature"] == {
        "class": "P",
        "class_name": "city, village,...",
        "code": "ZZZZ",
    }


def test_transformer_falls_back_to_the_ascii_name():
    """A row with no name is named by its transliteration."""
    entry = transform(
        geonameid="1",
        name="",
        asciiname="Nowhere",
    )

    # Confirm result
    assert entry["name"] == "Nowhere"


def test_transformer_omits_unusable_coordinates():
    """A row whose coordinates cannot be read yields no geometry."""
    entry = transform(
        geonameid="1",
        name="Broken",
        latitude="",
        longitude="not-a-number",
    )

    # Confirm result
    assert "locations" not in entry


#
# Whole stream
#
def test_import_populates_the_vocabulary(
    app, db, service, geonames_archive, search_clear
):
    """The whole reader/transformer/writer chain loads the vocabulary."""
    # Run the chain
    results = run(config_for(geonames_archive))

    # Confirm results
    assert len(results) == 3
    assert not [error for result in results for error in result.errors]

    # Refresh the index and confirm search
    service.indexer.refresh()
    assert service.search(system_identity, q="Zürich").total == 1

    # Confirm stored and search
    stored = service.read(system_identity, "geonames::2661552").to_dict()
    assert stored["name"] == "Bern"
    assert stored["locations"][0]["geometry"]["type"] == "Point"
    assert stored["extras"]["country"]["name"] == "Switzerland"
    assert stored["extras"]["admin"]["level1"] == {"code": "BE", "name": "Bern"}


def test_import_reports_duplicates(app, db, service, geonames_archive, search_clear):
    """Re-importing without `update` reports the entries as errors."""
    # Run the chain
    run(config_for(geonames_archive))

    # Run again and confirm duplicates
    results = run(config_for(geonames_archive))

    # Confirm errors
    assert all(result.errors for result in results)


def test_update_rewrites_existing_entries(
    app, db, service, geonames_archive, search_clear
):
    """With `update` set, a second pass rewrites instead of failing."""
    # Run the chain
    run(config_for(geonames_archive))

    # Configure the writer to update
    config = config_for(geonames_archive)
    for writer in config["writers"]:
        writer["args"]["update"] = True

    # Run again and confirm no errors
    results = run(config)

    # Confirm no errors
    assert not [error for result in results for error in result.errors]


def test_update_reports_a_deleted_entry(
    app, db, service, geonames_archive, search_clear
):
    """A tombstoned identifier is reported, and the rest of the run finishes."""
    # Run the chain
    run(config_for(geonames_archive))

    # Delete the entry
    service.delete(system_identity, "geonames::2661552")

    # Configure the writer to update
    config = config_for(geonames_archive)
    for writer in config["writers"]:
        writer["args"]["update"] = True

    # Run again and confirm the error
    results = run(config)

    # Confirm errors
    errored = [result for result in results if result.errors]
    assert len(errored) == 1
    assert "deleted" in errored[0].errors[0]
