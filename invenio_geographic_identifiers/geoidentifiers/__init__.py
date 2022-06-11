# -*- coding: utf-8 -*-
#
# Copyright (C) 2022 GEO Secretariat.
#
# invenio-geographic-identifiers is free software; you can redistribute it
# and/or modify it under the terms of the MIT License; see LICENSE file for
# more details.

"""Geographic Identifiers module."""

from .facets import GeographicIdentifiersLabels
from .resources import GeographicIdentifiersResource, GeographicIdentifiersResourceConfig
from .services import GeographicIdentifiersService, GeographicIdentifiersServiceConfig

__all__ = (
    "GeographicIdentifiersLabels",
    "GeographicIdentifiersResource",
    "GeographicIdentifiersResourceConfig",
    "GeographicIdentifiersService",
    "GeographicIdentifiersServiceConfig"
)
