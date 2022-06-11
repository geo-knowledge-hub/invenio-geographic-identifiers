# -*- coding: utf-8 -*-
#
# Copyright (C) 2022 GEO Secretariat.
#
# invenio-geographic-identifiers is free software; you can redistribute it
# and/or modify it under the terms of the MIT License; see LICENSE file for
# more details.

"""Geographic Identifiers datastreams."""

from invenio_vocabularies.datastreams.writers import ServiceWriter
from invenio_vocabularies.datastreams.transformers import BaseTransformer


class GeoNamesServiceWriter(ServiceWriter):
    """GeoNames service writer."""

    def _entry_id(self, entry):
        return entry['id']


class GeoNamesTransformer(BaseTransformer):
    """Transforms a GeoNames record into an Invenio GeoNames record."""

    def apply(self, stream_entry, *args, **kwargs):
        """Applies the transformation to the entry."""

        stream_entry.entry = {
            "id": f"geonames::{stream_entry.entry['geonameid']}",
            "scheme": "GEONAMES",
            "name": (
                stream_entry.entry.get("asciiname") or
                stream_entry.entry.get("name") or
                stream_entry.entry.get("alternativenames")
            )
        }

        return stream_entry


GEOGRAPHIC_IDENTIFIERS_DATASTREAM_TRANSFORMERS = {
    "geonames-transformer": GeoNamesTransformer,
}

GEOGRAPHIC_DATASTREAM_WRITERS = {
    "geonames-service": GeoNamesServiceWriter
}
