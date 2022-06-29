# -*- coding: utf-8 -*-
#
# Copyright (C) 2022 GEO Secretariat.
#
# invenio-geographic-identifiers is free software; you can redistribute it
# and/or modify it under the terms of the MIT License; see LICENSE file for
# more details.

"""Transformers for Geographic Identifiers Datastreams."""

from abc import ABC

from invenio_vocabularies.datastreams.transformers import BaseTransformer


class GeoIdentifierTransformer(BaseTransformer, ABC):
    """Base transformer class for GeoIdentifier transformers."""

    IDENTIFIER_SCHEME = None
    """Identifier scheme."""

    IDENTIFIER_PREFIX = None
    """Prefix for the document identifier."""
