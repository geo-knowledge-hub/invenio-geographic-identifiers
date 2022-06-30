# -*- coding: utf-8 -*-
#
# Copyright (C) 2022 GEO Secretariat.
#
# invenio-geographic-identifiers is free software; you can redistribute it
# and/or modify it under the terms of the MIT License; see LICENSE file for
# more details.

"""Geonames datastreams."""

from invenio_access.permissions import system_identity
from invenio_vocabularies.datastreams.transformers import BaseTransformer
from invenio_vocabularies.datastreams.writers import ServiceWriter

from ...datastreams.readers import ZippedCSVReader


#
# Transformers
#
class GeoNamesTransformer(BaseTransformer):
    """Transforms a GeoNames record into an Invenio GeoNames record."""

    def apply(self, stream_entry, *args, **kwargs):
        """Applies the transformation to the entry."""
        stream_entry.entry = {
            "id": f"geonames::{stream_entry.entry['geonameid']}",
            "scheme": "GeoNames",
            "name": (
                stream_entry.entry.get("asciiname")
                or stream_entry.entry.get("name")
                or stream_entry.entry.get("alternativenames")
            ),
            "locations": [
                {
                    "geometry": {
                        "type": "Point",
                        "coordinates": [
                            stream_entry.entry.get("longitude"),
                            stream_entry.entry.get("latitude"),
                        ],
                    }
                }
            ],
        }

        return stream_entry


#
# Writers
#
class GeoNamesServiceWriter(ServiceWriter):
    """GeoNames service writer."""

    def _entry_id(self, entry):
        return entry["id"]


VOCABULARIES_DATASTREAM_TRANSFORMERS = {
    "geonames-transformer": GeoNamesTransformer,
}

VOCABULARIES_DATASTREAM_WRITERS = {"geonames-service": GeoNamesServiceWriter}

VOCABULARIES_DATASTREAM_READERS = {"geonames-reader": ZippedCSVReader}

DATASTREAM_CONFIG = {
    "reader": {
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
    },
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
