# -*- coding: utf-8 -*-
#
# Copyright (C) 2022 GEO Secretariat.
#
# invenio-geographic-identifiers is free software; you can redistribute it
# and/or modify it under the terms of the MIT License; see LICENSE file for
# more details.

"""Geographic Identifiers vocabulary for the InvenioRDM"""

from flask import Blueprint

blueprint = Blueprint("invenio_geographic_identifiers_ext", __name__)


@blueprint.record_once
def init(state):
    """Init app."""
    app = state.app
    # Register services - cannot be done in extension because
    # Invenio-Records-Resources might not have been initialized.
    sregistry = app.extensions["invenio-records-resources"].registry
    ext = app.extensions["invenio-geographic-identifiers"]
    sregistry.register(ext.geoidentifiers_service, service_id="geoidentifiers")
    # Register indexers
    iregistry = app.extensions["invenio-indexer"].registry
    iregistry.register(ext.geoidentifiers_service.indexer, indexer_id="geoidentifiers")


def create_geoidentifiers_blueprint_from_app(app):
    """Create app blueprint."""
    return app.extensions["invenio-geographic-identifiers"].geoidentifiers_resource.as_blueprint()
