# -*- coding: utf-8 -*-
#
# Copyright (C) 2022 GEO Secretariat.
#
# invenio-geographic-identifiers is free software; you can redistribute it
# and/or modify it under the terms of the MIT License; see LICENSE file for
# more details.

"""Geographic Identifiers schema."""

from marshmallow_utils.fields import SanitizedUnicode

from invenio_vocabularies.services.schema import BaseVocabularySchema


class GeographicIdentifiersSchema(BaseVocabularySchema):
    """Service schema for geographic identifiers."""

    # following the definition made in the ``invenio-vocabularies (subjects)``, here
    # the ``id`` is ``required``
    id = SanitizedUnicode(required=True)
    scheme = SanitizedUnicode(required=True)
    name = SanitizedUnicode(required=True)
    location = SanitizedUnicode(required=True)  # test
