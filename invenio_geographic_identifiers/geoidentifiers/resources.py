# -*- coding: utf-8 -*-
#
# Copyright (C) 2022 GEO Secretariat.
#
# invenio-geographic-identifiers is free software; you can redistribute it
# and/or modify it under the terms of the MIT License; see LICENSE file for
# more details.

"""Geographic Identifiers resources."""

from .geoidentifiers import record_type

GeographicIdentifiersResourceConfig = record_type.resource_config_cls
GeographicIdentifiersResourceConfig.routes["item"] = "/<path:pid_value>"

GeographicIdentifiersResource = record_type.resource_cls
