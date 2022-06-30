# -*- coding: utf-8 -*-
#
# Copyright (C) 2022 GEO Secretariat.
#
# invenio-geographic-identifiers is free software; you can redistribute it
# and/or modify it under the terms of the MIT License; see LICENSE file for
# more details.

"""Geographic Identifiers schema."""

from geojson import MultiPolygon
from invenio_vocabularies.services.schema import BaseVocabularySchema
from marshmallow import Schema, fields
from marshmallow.fields import Constant, Float, List
from marshmallow_utils import schemas as base_schemas
from marshmallow_utils.fields import SanitizedUnicode
from marshmallow_utils.schemas.geojson import GeometryValidator


#
# Geometries
#
class MultiPolygonSchema(Schema):
    """GeoJSON MultiPolygon schema.

    See https://datatracker.ietf.org/doc/html/rfc7946#section-3.1.7
    """

    coordinates = List(
        List(List(List(Float))),
        required=True,
        validate=GeometryValidator(MultiPolygon)
    )
    type = Constant("MultiPolygon")


class GeometryObjectSchema(base_schemas.GeometryObjectSchema):
    """A GeoJSON Geometry Object schema.

    See https://tools.ietf.org/html/rfc7946#section-3.1
    """

    type_schemas = {
        "Point": base_schemas.PointSchema,
        "MultiPoint": base_schemas.MultiPointSchema,
        "Polygon": base_schemas.PolygonSchema,
        "MultiPolygon": MultiPolygonSchema,
    }


class LocationSchema(Schema):
    """Location schema."""

    geometry = fields.Nested(GeometryObjectSchema)


class GeographicIdentifiersSchema(BaseVocabularySchema):
    """Service schema for geographic identifiers."""

    # following the definition made in the ``invenio-vocabularies
    # (subjects)``, here the ``id`` is ``required``
    id = SanitizedUnicode(required=True)
    scheme = SanitizedUnicode(required=True)
    name = SanitizedUnicode(required=True)
    locations = fields.List(
        required=True,
        cls_or_instance=fields.Nested(LocationSchema)
    )
