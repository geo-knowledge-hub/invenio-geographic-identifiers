# -*- coding: utf-8 -*-
#
# Copyright (C) 2022 GEO Secretariat.
#
# invenio-geographic-identifiers is free software; you can redistribute it
# and/or modify it under the terms of the MIT License; see LICENSE file for
# more details.

"""Geonames datastreams."""

import pycountry
from invenio_access.permissions import system_identity
from invenio_vocabularies.datastreams.transformers import BaseTransformer

from ...datastreams.readers import ZippedCSVReader
from ...datastreams.writers import GeoIdentifierServiceWriter
from .lookups import NO_ELEVATION, admin1_name, feature_class_name, feature_name

#
# Constant - Administrative levels columns
#
ADMIN_LEVELS = ("admin1_code", "admin2_code", "admin3_code", "admin4_code")


#
# Helpers
#
def _compact(mapping):
    """Drop the keys that carry no value."""
    return {
        key: value
        for key, value in mapping.items()
        if value is not None and value != "" and value != [] and value != {}
    }


def _text(row, column):
    """Read a column as text."""
    return (row.get(column) or "").strip() or None


def _number(row, column, cast):
    """Read a column as a number."""
    value = _text(row, column)

    try:
        return cast(value)

    except (TypeError, ValueError):
        return None


def _country(row):
    """Resolve the ISO 3166-1 alpha-2 country code to its names."""
    code = _text(row, "country_code")
    country = pycountry.countries.get(alpha_2=code) if code else None

    if country is None:
        # Either no country (oceans, and other features that belong to none) or a
        # code ISO does not know. Keep the raw code so nothing is lost.
        return _compact({"code": code})

    return _compact(
        {
            "code": country.alpha_2,
            "name": country.name,
            # Roughly a third of the countries pycountry knows have no official
            # name, Australia among them, so this cannot be read directly.
            "official_name": getattr(country, "official_name", None),
        }
    )


def _admin(row):
    """Collect the administrative division codes."""
    levels = {}
    country_code = _text(row, "country_code")

    # Iterate over the administrative division codes
    for order, column in enumerate(ADMIN_LEVELS, start=1):
        # Read the code
        code = _text(row, column)

        # Skip if the code is None
        if code is None:
            continue

        # Get the name
        name = admin1_name(country_code, code) if order == 1 else None

        # Add the code and name to the levels
        levels[f"level{order}"] = _compact({"code": code, "name": name})

    # Return!
    return levels


def _feature(row):
    """Describe the feature."""
    feature_class = _text(row, "feature_class")
    feature_code = _text(row, "feature_code")

    return _compact(
        {
            "class": feature_class,
            "class_name": feature_class_name(feature_class),
            "code": feature_code,
            "name": feature_name(feature_class, feature_code),
        }
    )


def _alternate_names(row):
    """Split the comma-separated alternate names."""
    names = _text(row, "alternatenames") or ""

    return [name.strip() for name in names.split(",") if name.strip()]


def _elevation(row):
    """Read the elevation."""
    dem = _number(row, "dem", int)

    if dem == NO_ELEVATION:
        return None

    return dem


def _extras(row):
    """Build the extra metadata."""
    return _compact(
        {
            "ascii_name": _text(row, "asciiname"),
            "alternate_names": _alternate_names(row),
            "country": _country(row),
            "admin": _admin(row),
            "feature": _feature(row),
            "population": _number(row, "population", int),
            "elevation": _number(row, "elevation", int),
            "dem": _elevation(row),
            "timezone": _text(row, "timezone"),
            "modified": _text(row, "modification_date"),
        }
    )


def _locations(row):
    """Build the point geometry."""
    longitude = _number(row, "longitude", float)
    latitude = _number(row, "latitude", float)

    if longitude is None or latitude is None:
        # Leave `locations` out rather than write half a geometry
        return None

    # Return object
    return [
        {
            "geometry": {
                "type": "Point",
                "coordinates": [longitude, latitude],
            },
        },
    ]


#
# Transformers
#
class GeoNamesTransformer(BaseTransformer):
    """Transforms a GeoNames record into an Invenio GeoNames record."""

    def apply(self, stream_entry, *args, **kwargs):
        """Applies the transformation to the entry."""
        row = stream_entry.entry

        stream_entry.entry = _compact(
            {
                "id": f"geonames::{row['geonameid']}",
                "scheme": "geonames",
                "name": _text(row, "name") or _text(row, "asciiname"),
                "locations": _locations(row),
                "extras": _extras(row),
            }
        )

        return stream_entry


#
# Writers
#
class GeoNamesServiceWriter(GeoIdentifierServiceWriter):
    """GeoNames service writer."""


#
# Configurations
#
VOCABULARIES_DATASTREAM_TRANSFORMERS = {
    "geonames-transformer": GeoNamesTransformer,
}

VOCABULARIES_DATASTREAM_WRITERS = {"geonames-service": GeoNamesServiceWriter}

VOCABULARIES_DATASTREAM_READERS = {"geonames-reader": ZippedCSVReader}

DATASTREAM_CONFIG = {
    "readers": [
        {
            "type": "geonames-reader",
            "args": {
                "csv_options": {
                    "fieldnames": [
                        "geonameid",
                        "name",
                        "asciiname",
                        "alternatenames",
                        "latitude",
                        "longitude",
                        "feature_class",
                        "feature_code",
                        "country_code",
                        "cc2",
                        "admin1_code",
                        "admin2_code",
                        "admin3_code",
                        "admin4_code",
                        "population",
                        "elevation",
                        "dem",
                        "timezone",
                        "modification_date",
                    ],
                    "delimiter": "\t",
                }
            },
        }
    ],
    "transformers": [{"type": "geonames-transformer"}],
    "writers": [
        {
            "type": "geonames-service",
            "args": {
                "service_or_name": "geoidentifiers",
                "identity": system_identity,
            },
        }
    ],
}
