# -*- coding: utf-8 -*-
#
# Copyright (C) 2022 GEO Secretariat.
#
# invenio-geographic-identifiers is free software; you can redistribute it
# and/or modify it under the terms of the MIT License; see LICENSE file for
# more details.

"""Invenio Geographic Identifiers proxies."""

from flask import current_app
from werkzeug.local import LocalProxy


def _ext_proxy(attr):
    """Get proxy from a specific extension attribute.

    Note:
        This code was adapted from Invenio Vocabularies.
    """
    return LocalProxy(
        lambda: getattr(current_app.extensions["invenio-geographic-identifiers"], attr)
    )


current_geoidentifier_service = _ext_proxy("geoidentifiers_service")
"""Proxy to the instantiated vocabulary service."""

current_geoidentifier_resource = _ext_proxy("geoidentifiers_resource")
"""Proxy to the instantiated vocabulary resource."""
