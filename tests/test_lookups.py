# -*- coding: utf-8 -*-
#
# Copyright (C) 2022 GEO Secretariat.
#
# invenio-geographic-identifiers is free software; you can redistribute it
# and/or modify it under the terms of the MIT License; see LICENSE file for
# more details.

"""GeoNames code lookup tests."""

import pytest

from invenio_geographic_identifiers.contrib.geonames.lookups import (
    FEATURE_CLASSES,
    admin1_name,
    feature_class_name,
    feature_name,
)


@pytest.mark.parametrize(
    "feature_class,feature_code,expected",
    [
        ("P", "PPLA", "seat of a first-order administrative division"),
        ("P", "PPLC", "capital of a political entity"),
        ("L", "AREA", "area"),
    ],
)
def test_feature_name(feature_class, feature_code, expected):
    """A feature code resolves to its description."""
    assert feature_name(feature_class, feature_code) == expected


@pytest.mark.parametrize(
    "feature_class,feature_code",
    [
        ("P", "NOT-A-CODE"),
        ("", ""),
        (None, None),
        # GeoNames' own sentinel for "not available", which is a row in the
        # table and must not come back as a description.
        ("P", "null"),
    ],
)
def test_unresolvable_feature_name(feature_class, feature_code):
    """An unknown, absent or placeholder feature code resolves to nothing."""
    # Confirm result
    assert feature_name(feature_class, feature_code) is None


def test_feature_classes():
    """Every feature class GeoNames publishes is described."""
    assert set(FEATURE_CLASSES) == set("AHLPRSTUV")
    assert feature_class_name("P") == "city, village,..."
    assert feature_class_name("X") is None


@pytest.mark.parametrize(
    "country_code,admin1_code,expected",
    [
        ("CH", "ZH", "Zurich"),
        ("US", "CA", "California"),
        ("FR", "11", "Île-de-France"),
        ("IT", "07", "Lazio"),
        ("BR", "27", "São Paulo"),
    ],
)
def test_admin1_name(country_code, admin1_code, expected):
    """A first-order division code resolves to its name."""
    assert admin1_name(country_code, admin1_code) == expected


@pytest.mark.parametrize(
    "country_code,admin1_code",
    [("CH", "NOT-A-CODE"), ("ZZ", "ZH"), ("", "ZH"), ("CH", ""), (None, None)],
)
def test_unresolvable_admin1_name(country_code, admin1_code):
    """An unknown or absent division code resolves to nothing."""
    assert admin1_name(country_code, admin1_code) is None
