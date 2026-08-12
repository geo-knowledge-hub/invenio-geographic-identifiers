# -*- coding: utf-8 -*-
#
# Copyright (C) 2022 GEO Secretariat.
#
# invenio-geographic-identifiers is free software; you can redistribute it
# and/or modify it under the terms of the MIT License; see LICENSE file for
# more details.

"""Geographic identifiers schema tests."""

import pytest
from marshmallow import ValidationError

from invenio_geographic_identifiers.geoidentifiers.schema import (
    GeographicIdentifiersSchema,
)

#
# Constant - valid polygon
#
POLYGON = [
    [
        [5.9, 46.1],
        [6.3, 46.1],
        [6.3, 46.4],
        [5.9, 46.4],
        [5.9, 46.1],
    ],
]


def load(geometry):
    """Load an identifier carrying a single geometry."""
    return GeographicIdentifiersSchema().load(
        {
            "id": "geonames::2657896",
            "scheme": "geonames",
            "name": "Zürich",
            "locations": [{"geometry": geometry}],
        }
    )


@pytest.mark.parametrize(
    "geometry",
    [
        {"type": "Point", "coordinates": [8.55, 47.36]},
        {"type": "Polygon", "coordinates": POLYGON},
    ],
)
def test_supported_geometries(geometry):
    """Geometry supported must be loaded."""
    loaded = load(geometry)

    assert loaded["locations"][0]["geometry"]["type"] == geometry["type"]


@pytest.mark.parametrize("geometry_type", ["LineString", "MultiLineString"])
def test_unsupported_geometries(geometry_type):
    """Line geometries are rejected rather than stored half-formed."""
    with pytest.raises(ValidationError):
        load(
            {
                "type": geometry_type,
                "coordinates": [[5.9, 46.1], [6.3, 46.4]],
            }
        )


def test_multipolygon_rejects_an_unclosed_ring():
    """A MultiPolygon ring that does not close is invalid GeoJSON."""
    unclosed = [
        [
            [
                [5.9, 46.1],
                [6.3, 46.1],
                [6.3, 46.4],
                [5.9, 46.4],
            ]
        ],
    ]

    with pytest.raises(ValidationError):
        load({"type": "MultiPolygon", "coordinates": unclosed})


@pytest.mark.parametrize("missing", ["id", "scheme", "name", "locations"])
def test_required_fields(missing, geoidentifier_data):
    """An identifier without one of its required fields is rejected."""
    data = dict(geoidentifier_data)

    del data[missing]

    with pytest.raises(ValidationError):
        GeographicIdentifiersSchema().load(data)


#
# Extras
#
def test_extras_round_trip(geoidentifier_data):
    """The extra metadata survives a load and a dump unchanged."""
    schema = GeographicIdentifiersSchema()
    dumped = schema.dump(schema.load(geoidentifier_data))

    assert dumped["extras"] == geoidentifier_data["extras"]


def test_extras_are_optional(geoidentifier_data):
    """A scheme that has no extra metadata is still valid."""
    data = dict(geoidentifier_data)
    del data["extras"]

    assert "extras" not in GeographicIdentifiersSchema().load(data)


def test_extras_are_partial(geoidentifier_data):
    """Every extra field may be absent on its own."""
    data = {
        **geoidentifier_data,
        "extras": {"population": 415367},
    }

    # Confirm result
    assert GeographicIdentifiersSchema().load(data)["extras"] == {"population": 415367}


@pytest.mark.parametrize(
    "extras",
    [
        {"population": "many"},
        {"modified": "the day before yesterday"},
        {"alternate_names": "Zurich"},
        {"country": "Switzerland"},
        {"admin": {"level1": "Zurich"}},
    ],
)
def test_malformed_extras_are_rejected(extras, geoidentifier_data):
    """Extra metadata of the wrong shape does not pass silently."""
    with pytest.raises(ValidationError):
        GeographicIdentifiersSchema().load(
            {
                **geoidentifier_data,
                "extras": extras,
            }
        )
