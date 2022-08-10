# -*- coding: utf-8 -*-
#
# Copyright (C) 2022 GEO Secretariat.
#
# invenio-geographic-identifiers is free software; you can redistribute it
# and/or modify it under the terms of the MIT License; see LICENSE file for
# more details.

"""Module tests."""

from flask import Flask

from invenio_geographic_identifiers import InvenioGeographicIdentifiers


def test_version():
    """Test version import."""
    from invenio_geographic_identifiers import __version__

    assert __version__


def test_init():
    """Test extension initialization."""
    app = Flask("testapp")
    ext = InvenioGeographicIdentifiers(app)
    assert "invenio-geographic-identifiers" in app.extensions

    app = Flask("testapp")
    ext = InvenioGeographicIdentifiers()
    assert "invenio-geographic-identifiers" not in app.extensions
    ext.init_app(app)
    assert "invenio-geographic-identifiers" in app.extensions
