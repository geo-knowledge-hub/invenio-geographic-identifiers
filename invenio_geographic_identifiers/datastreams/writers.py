# -*- coding: utf-8 -*-
#
# Copyright (C) 2022 GEO Secretariat.
#
# invenio-geographic-identifiers is free software; you can redistribute it
# and/or modify it under the terms of the MIT License; see LICENSE file for
# more details.

"""Writers for Geographic Identifiers Datastreams."""

from invenio_vocabularies.datastreams.writers import ServiceWriter


class GeoIdentifierServiceWriter(ServiceWriter):
    """Geographic Identifier ServiceWriter class."""

    def _entry_id(self, entry):
        return entry["id"]
