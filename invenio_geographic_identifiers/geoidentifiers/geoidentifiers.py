# -*- coding: utf-8 -*-
#
# Copyright (C) 2022 GEO Secretariat.
#
# invenio-geographic-identifiers is free software; you can redistribute it
# and/or modify it under the terms of the MIT License; see LICENSE file for
# more details.

"""Geographic Identifiers subjects."""

from invenio_records.dumpers import SearchDumper
from invenio_records.dumpers.indexedat import IndexedAtDumperExt
from invenio_records_resources.factories.factory import RecordTypeFactory
from invenio_vocabularies.records.pidprovider import PIDProviderFactory
from invenio_vocabularies.records.systemfields import BaseVocabularyPIDFieldContext
from invenio_vocabularies.services.permissions import PermissionPolicy

from .config import GeographicIdentifiersSearchOptions, service_components
from .schema import GeographicIdentifiersSchema

record_type = RecordTypeFactory(
    "GeoIdentifier",
    # Data Layer
    pid_field_kwargs={
        "create": False,
        "provider": PIDProviderFactory.create(pid_type="geoid"),
        "context_cls": BaseVocabularyPIDFieldContext,
    },
    schema_version="1.0.0",
    schema_path="local://geoidentifiers/geoidentifier-v1.0.0.json",
    record_dumper=SearchDumper(
        extensions=[
            IndexedAtDumperExt(),
        ]
    ),
    # Service Layer
    service_id="geoidentifier",
    service_schema=GeographicIdentifiersSchema,
    search_options=GeographicIdentifiersSearchOptions,
    service_components=service_components,
    permission_policy_cls=PermissionPolicy,
    # Resource Layer
    endpoint_route="/geoidentifiers",
)
