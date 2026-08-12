# -*- coding: utf-8 -*-
#
# Copyright (C) 2022 GEO Secretariat.
#
# invenio-geographic-identifiers is free software; you can redistribute it
# and/or modify it under the terms of the MIT License; see LICENSE file for
# more details.

"""Geographic Identifiers vocabulary for the InvenioRDM."""


def create_geoidentifiers_blueprint_from_app(app):
    """Create app blueprint."""
    return app.extensions[
        "invenio-geographic-identifiers"
    ].geoidentifiers_resource.as_blueprint()
