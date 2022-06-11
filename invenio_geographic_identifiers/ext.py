# -*- coding: utf-8 -*-
#
# Copyright (C) 2022 GEO Secretariat.
#
# invenio-geographic-identifiers is free software; you can redistribute it
# and/or modify it under the terms of the MIT License; see LICENSE file for
# more details.

"""Geographic Identifiers vocabulary for the InvenioRDM"""

from . import config
from .geoidentifiers import (
    GeographicIdentifiersResource,
    GeographicIdentifiersResourceConfig,
    GeographicIdentifiersService,
    GeographicIdentifiersServiceConfig
)


class InvenioGeographicIdentifiers(object):
    """invenio-geographic-identifiers extension."""

    def __init__(self, app=None):
        """Extension initialization."""
        if app:
            self.init_app(app)

    def init_app(self, app):
        """Flask application initialization."""
        self.init_config(app)
        self.init_service(app)
        self.init_resource(app)

        app.extensions['invenio-geographic-identifiers'] = self

    def init_config(self, app):
        """Initialize configuration."""
        for k in dir(config):
            if k.startswith('INVENIO_GEOGRAPHIC_IDENTIFIERS_'):
                app.config.setdefault(k, getattr(config, k))

    def service_configs(self, app):
        """Customized service configs."""

        # following the `invenio-*-resources pattern`. This make easier
        # future configuration extensions.
        class ServiceConfig:
            geoidentifiers = GeographicIdentifiersServiceConfig

        return ServiceConfig

    def init_service(self, app):
        """Initialize services."""
        service_configs = self.service_configs(app)

        # Services
        self.geoidentifiers_service = GeographicIdentifiersService(
            config=service_configs.geoidentifiers
        )

    def init_resource(self, app):
        """Initialize resources."""
        self.geoidentifiers_resource = GeographicIdentifiersResource(
            service=self.geoidentifiers_service,
            config=GeographicIdentifiersResourceConfig
        )
