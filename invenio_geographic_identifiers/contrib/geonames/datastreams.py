# -*- coding: utf-8 -*-
#
# Copyright (C) 2022 GEO Secretariat.
#
# invenio-geographic-identifiers is free software; you can redistribute it
# and/or modify it under the terms of the MIT License; see LICENSE file for
# more details.

"""Geonames datastreams."""

import csv

import pycountry
from invenio_vocabularies.datastreams.errors import ReaderError
from invenio_vocabularies.datastreams.transformers import BaseTransformer

from ...datastreams.download import setting
from ...datastreams.readers import ZippedCSVReader
from ...datastreams.writers import GeoIdentifierServiceWriter
from .lookups import NO_ELEVATION, admin1_name, feature_class_name, feature_name

#
# Constant - Administrative levels columns
#
ADMIN_LEVELS = (
    "admin1_code",
    "admin2_code",
    "admin3_code",
    "admin4_code",
)


#
# Helpers
#
def _feature_class_set(feature_classes):
    """Normalise the feature classes to keep.

    Args:
        feature_classes: A list or a comma-separated string of
                         feature classes to keep.

    Returns:
        A set of feature classes to keep.
    """
    if feature_classes is None:
        return None

    # Split string into a list if required
    if isinstance(feature_classes, str):
        feature_classes = feature_classes.split(",")

    # Keep only the values that are not empty
    values_to_keep = {value.strip() for value in feature_classes if value.strip()}

    # Empty values are not allowed
    if not values_to_keep:
        # An empty selection is a mistake worth naming: read as "keep nothing"
        # it imports an empty vocabulary, and as "keep everything" it silently
        # ignores what was asked for.
        raise ReaderError("`feature_classes` was given, but names no class.")

    # Return!
    return values_to_keep


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
# Readers
#
class GeoNamesReader(ZippedCSVReader):
    """Reads a GeoNames dump, optionally restricted to some feature classes.

    A full `allCountries` dump is 13.4 million rows, and more than half of them
    are streams, farm buildings, hills and stretches of road. An instance that
    wants a place-name vocabulary can say so and skip the rest: `P` and `A`
    alone, populated places and administrative divisions, are 5.8 million.

    Filtering here, rather than in `DataStream.filter`, is deliberate. A row
    dropped by the reader is never transformed, and `DataStreamFactory` always
    builds a plain `DataStream`, so its `filter` hook cannot be reached without
    replacing the factory.

    Shards are unaffected: the rows are numbered before the filter runs, so the
    same shard covers the same rows whatever the filter is set to.
    """

    def __init__(self, *args, feature_classes=None, **kwargs):
        """Initializer.

        Args:
            *args: Arguments for the parent class.

            feature_classes: GeoNames feature classes to keep, as a list or
                             a comma-separated string. `None` keeps all.

            **kwargs: Keyword arguments for the parent class.
        """
        # Setup the feature classes to keep
        self.feature_classes = _feature_class_set(feature_classes)

        # Initialize the parent class
        super().__init__(*args, **kwargs)

        # Check if the feature classes are not None and the rows
        # are not read as dicts
        if self.feature_classes is not None and not self.as_dict:
            raise ReaderError("`feature_classes` needs the rows read as dicts.")

    def _default_origin_url(self):
        """Where a dump comes from when the caller did not say.

        Returns:
            The configured GeoNames dump URL.
        """
        return setting("INVENIO_GEOGRAPHIC_IDENTIFIERS_GEONAMES_DUMP_URL")

    def _iter(self, fp, *args, **kwargs):
        """Read the dump."""
        # Read the rows from the file
        rows = super()._iter(fp, *args, **kwargs)

        # If no feature classes are specified, yield all rows
        if self.feature_classes is None:
            yield from rows
            return

        # Otherwise, iterate over the rows
        for row in rows:
            # Get the feature class from the row
            row_feature_class = (row.get("feature_class") or "").strip()

            # Check if we should keep the row
            row_to_keep = row_feature_class in self.feature_classes

            # Yield the row if we should keep it
            if row_to_keep:
                yield row


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

VOCABULARIES_DATASTREAM_READERS = {"geonames-reader": GeoNamesReader}

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
                    # A GeoNames dump is unquoted: tabs separate the fields and
                    # nothing escapes anything. Left to its default the `csv`
                    # module treats a leading double quote as a quoted field and
                    # eats it, which rewrites some names in the current dump.
                    "quoting": csv.QUOTE_NONE,
                }
            },
        }
    ],
    "transformers": [{"type": "geonames-transformer"}],
    "writers": [
        {
            "type": "geonames-service",
            # No `identity` here on purpose. The writer defaults to
            # `system_identity`, and an `Identity` object cannot be serialized:
            # this configuration travels to a Celery worker as a task argument,
            # and both serializers Invenio can be configured with refuse it.
            "args": {"service_or_name": "geoidentifiers"},
        }
    ],
    "batch_size": 1000,
    "write_many": False,
}
