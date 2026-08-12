# -*- coding: utf-8 -*-
#
# Copyright (C) 2022 GEO Secretariat.
#
# invenio-geographic-identifiers is free software; you can redistribute it
# and/or modify it under the terms of the MIT License; see LICENSE file for
# more details.

"""Lookups for the codes used in a GeoNames dump."""

import csv
from functools import lru_cache

try:  # pragma: no cover

    from importlib.resources import files as _resource_files

except ImportError:  # pragma: no cover
    from importlib_resources import files as _resource_files


#
# Constants - Feature classes
#
FEATURE_CLASSES = {
    "A": "country, state, region,...",
    "H": "stream, lake, ...",
    "L": "parks, area, ...",
    "P": "city, village,...",
    "R": "road, railroad",
    "S": "spot, building, farm",
    "T": "mountain, hill, rock,...",
    "U": "undersea",
    "V": "forest, heath,...",
}
"""Descriptions of the nine GeoNames feature classes.

Hardcoded because ``featureCodes_en.txt`` only describes ``class.code`` pairs and
carries no rows for the classes themselves. Transcribed from
https://www.geonames.org/export/codes.html.
"""

#
# Constant - No feature code
#
NO_FEATURE_CODE = "null"
"""Sentinel GeoNames uses in ``featureCodes_en.txt`` for "not available"."""

#
# Constant - No elevation
#
NO_ELEVATION = -9999
"""Sentinel GeoNames uses in the ``dem`` column for "no data"."""


#
# Helpers
#
def _read(filename):
    """Read a vendored tab-separated table."""
    # Get the source
    source = _resource_files(__package__).joinpath("data", filename)

    # Read the file
    with source.open("r", encoding="utf-8", newline="") as fp:
        yield from csv.reader(fp, delimiter="\t", quoting=csv.QUOTE_NONE)


#
# Cache - Feature names
#
@lru_cache(maxsize=1)
def _feature_names():
    """Map `<class>.<code>` to its human readable name."""
    return {
        row[0]: row[1]
        for row in _read("featureCodes_en.txt")
        if len(row) >= 2 and row[0] != NO_FEATURE_CODE
    }


@lru_cache(maxsize=1)
def _admin1_names():
    """Map `<country>.<admin1>` to its name."""
    return {row[0]: row[1] for row in _read("admin1CodesASCII.txt") if len(row) >= 2}


#
# High-level functions
#
def admin1_name(country_code, admin1_code):
    """Name a first-order administrative division."""
    if not country_code or not admin1_code:
        return None

    # Return the name
    return _admin1_names().get(f"{country_code}.{admin1_code}")


def feature_name(feature_class, feature_code):
    """Name a feature code."""
    if not feature_class or not feature_code or feature_code == NO_FEATURE_CODE:
        return None

    # Return the name
    return _feature_names().get(f"{feature_class}.{feature_code}")


def feature_class_name(feature_class):
    """Describe a feature class."""
    return FEATURE_CLASSES.get(feature_class)
