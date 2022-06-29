# -*- coding: utf-8 -*-
#
# Copyright (C) 2022 GEO Secretariat.
#
# invenio-geographic-identifiers is free software; you can redistribute it
# and/or modify it under the terms of the MIT License; see LICENSE file for
# more details.

"""Regions datastreams."""

import shapefile

from invenio_access.permissions import system_identity
from invenio_vocabularies.datastreams.errors import TransformerError

from ...datastreams.readers import ShapefileReader
from ...datastreams.transformers import GeoIdentifierTransformer
from ...datastreams.writers import GeoIdentifierServiceWriter


def record_validator(record):
    """Regions filter.

    This is a very specific filter for the Regions dataset.
    In this filter, we are removing the Antarctica (ISO 25 - "AQ") to avoid
    errors with the Elasticsearch. For some reason, this geometry cause
    errors in the Lucene tessellator, event the geometry is valid (e.g.,
    softwares like QGIS and shapely can open and validate the geometry).
    """
    if record.record.ISO == "AQ":
        return False
    return True


class RegionsIdentifierTransformer(GeoIdentifierTransformer):
    """Region data transformer.

    Transforms ArcGIS Hub World Countries (Generalized) shapefile into a
    valid GeoIdentifier document.

    See:
        For more information about the ArcGIS Hub World Countries data, please,
        check the ArcGIS Hub (https://hub.arcgis.com/datasets/2b93b06dc0dc4e809d3c8db5cb96ba69_0/explore)
    """
    IDENTIFIER_SCHEME = "Regions"
    """Identifier scheme."""

    IDENTIFIER_PREFIX = "https://www.iso.org/obp/ui/#iso:code:3166:"
    """Prefix for the document identifier."""

    def apply(self, stream_entry, *args, **kwargs):
        """Transform the data."""

        if not isinstance(stream_entry.entry, shapefile.ShapeRecord):
            raise TransformerError("To transform the region data you must "
                                   "use `shapefile.ShapeRecord` objects.")

        # extracting the shapefile record (defined by `ShapefileReader`)
        record = stream_entry.entry.record

        # extracting the shapefile shape (defined by `ShapefileReader`)
        shape = stream_entry.entry.shape

        stream_entry.entry = {
            "id": f"{self.IDENTIFIER_PREFIX}{record.ISO}",
            "scheme": self.IDENTIFIER_SCHEME,
            "name": record.COUNTRY,
            "locations": [
                {
                    "geometry": shape.__geo_interface__  # https://pypi.org/project/geojson/
                }
            ]
        }

        return stream_entry


VOCABULARIES_DATASTREAM_TRANSFORMERS = {
    "regions-transformer": RegionsIdentifierTransformer,
}

VOCABULARIES_DATASTREAM_WRITERS = {
    "regions-service": GeoIdentifierServiceWriter
}

VOCABULARIES_DATASTREAM_READERS = {
    "regions-shp-reader": ShapefileReader
}

DATASTREAM_CONFIG = {
    "reader": {
        "type": "regions-shp-reader",
        "args": {
            "record_validator": record_validator
        }
    },
    "transformers": [{"type": "regions-transformer"}],
    "writers": [
        {
            "type": "regions-service",
            "args": {
                "service_or_name": "geoidentifiers",
                "identity": system_identity,
            },
        }
    ],
}
