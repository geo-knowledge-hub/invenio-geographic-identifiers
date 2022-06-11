# -*- coding: utf-8 -*-
#
# Copyright (C) 2022 GEO Secretariat.
#
# invenio-geographic-identifiers is free software; you can redistribute it
# and/or modify it under the terms of the MIT License; see LICENSE file for
# more details.

"""Geographic Identifiers service."""

from invenio_db import db
from invenio_vocabularies.records.models import VocabularyScheme

from .geoidentifiers import record_type

GeographicIdentifiersServiceConfig = record_type.service_config_cls


class GeographicIdentifiersService(record_type.service_cls):
    """Geographic Identifiers service."""

    def create_scheme(self, identity, id_, name="", uri=""):
        """Create a row for the Geographic Identifier scheme metadata."""
        self.required_permission(identity, "manage")
        scheme = VocabularyScheme.create(
            id=id_, parent_id="geoidentifiers", name=name, uri=uri
        )

        db.session.commit()
        return scheme
