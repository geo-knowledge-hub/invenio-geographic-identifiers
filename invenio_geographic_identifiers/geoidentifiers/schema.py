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
from marshmallow.fields import Constant, Float, Integer, List
from marshmallow_utils import schemas as base_schemas
from marshmallow_utils.fields import EDTFDateString, SanitizedUnicode
from marshmallow_utils.schemas.geojson import GeometryValidator


#
# Geometries
#
class MultiPolygonSchema(Schema):
    """GeoJSON MultiPolygon schema.

    See https://datatracker.ietf.org/doc/html/rfc7946#section-3.1.7
    """

    coordinates = List(
        List(List(List(Float))), required=True, validate=GeometryValidator(MultiPolygon)
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


#
# Extra metadata
#
class CountrySchema(Schema):
    """Country an identifier belongs to."""

    code = SanitizedUnicode()
    name = SanitizedUnicode()
    official_name = SanitizedUnicode()


class AdministrativeLevelSchema(Schema):
    """One order of administrative division."""

    code = SanitizedUnicode()
    name = SanitizedUnicode()


class AdministrativeSchema(Schema):
    """Administrative divisions containing an identifier."""

    level1 = fields.Nested(AdministrativeLevelSchema)
    level2 = fields.Nested(AdministrativeLevelSchema)
    level3 = fields.Nested(AdministrativeLevelSchema)
    level4 = fields.Nested(AdministrativeLevelSchema)


class FeatureSchema(Schema):
    """Kind of place an identifier denotes."""

    # `class` is a reserved word in Python but the term GeoNames uses, so it is
    # kept in the data and only renamed on the Python side
    feature_class = SanitizedUnicode(data_key="class", attribute="class")

    class_name = SanitizedUnicode()
    code = SanitizedUnicode()
    name = SanitizedUnicode()


class ExtrasSchema(Schema):
    """Extra metadata that makes an identifier recognisable.

    Place names are far from unique. GeoNames alone has thousands of
    "Springfield", so a client needs the country, the administrative division
    and the kind of place to tell two results apart, and the alternate names to
    find them in the first place
    """

    ascii_name = SanitizedUnicode()
    alternate_names = fields.List(SanitizedUnicode())
    country = fields.Nested(CountrySchema)
    admin = fields.Nested(AdministrativeSchema)
    feature = fields.Nested(FeatureSchema)
    population = Integer()
    elevation = Integer()
    dem = Integer()
    timezone = SanitizedUnicode()
    modified = EDTFDateString()


class GeographicIdentifiersSchema(BaseVocabularySchema):
    """Service schema for geographic identifiers."""

    #
    # Identifier
    #
    id = SanitizedUnicode(required=True)

    #
    # Scheme
    #
    scheme = SanitizedUnicode(required=True)

    #
    # Identifier name (e.g., Geonames feature name)
    #
    name = SanitizedUnicode(required=True)

    #
    # Location (e.g., list of points)
    #
    locations = fields.List(
        required=True, cls_or_instance=fields.Nested(LocationSchema)
    )

    #
    # Extra metadata
    #
    extras = fields.Nested(ExtrasSchema)
