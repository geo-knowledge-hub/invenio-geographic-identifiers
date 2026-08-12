# -*- coding: utf-8 -*-
#
# Copyright (C) 2022 GEO Secretariat.
#
# invenio-geographic-identifiers is free software; you can redistribute it
# and/or modify it under the terms of the MIT License; see LICENSE file for
# more details.

"""Pytest configuration."""

import csv
import io
import zipfile

import pytest
from invenio_access.permissions import system_identity
from invenio_app.factory import create_api
from invenio_records_resources.proxies import current_service_registry

from invenio_geographic_identifiers.contrib.geonames.datastreams import (
    VOCABULARIES_DATASTREAM_READERS,
    VOCABULARIES_DATASTREAM_TRANSFORMERS,
    VOCABULARIES_DATASTREAM_WRITERS,
)

#
# GeoNames sample.
#
GEONAMES_FIELDNAMES = [
    "geonameid",
    "name",
    "asciiname",
    "alternatenames",
    "latitude",
    "longitude",
    "feature_class",
    "feature_code",
    "country_code",
    "cc2",
    "admin1_code",
    "admin2_code",
    "admin3_code",
    "admin4_code",
    "population",
    "elevation",
    "dem",
    "timezone",
    "modification_date",
]
"""Column layout of the GeoNames `allCountries` dump."""


GEONAMES_ROWS = [
    {
        "geonameid": "2657896",
        "name": "Zürich",
        "asciiname": "Zuerich",
        "alternatenames": "Zurich,Zürich,Turicum",
        "latitude": "47.36667",
        "longitude": "8.55",
        "feature_class": "P",
        "feature_code": "PPLA",
        "country_code": "CH",
        "admin1_code": "ZH",
        "admin2_code": "112",
        "admin3_code": "261",
        "population": "415367",
        "elevation": "",
        "dem": "429",
        "timezone": "Europe/Zurich",
        "modification_date": "2026-04-13",
    },
    {
        "geonameid": "2661552",
        "name": "Bern",
        "asciiname": "Bern",
        "alternatenames": "Berna,Berne",
        "latitude": "46.94809",
        "longitude": "7.44744",
        "feature_class": "P",
        "feature_code": "PPLC",
        "country_code": "CH",
        "admin1_code": "BE",
        "admin2_code": "246",
        "population": "121631",
        "dem": "549",
        "timezone": "Europe/Zurich",
        "modification_date": "2019-09-18",
    },
    {
        # Italy numbers its first-order divisions, and those numbers are FIPS
        # rather than ISO: `IT.07` is Lazio here but Abruzzo in ISO 3166-2.
        "geonameid": "3169070",
        "name": "Rome",
        "asciiname": "Rome",
        "alternatenames": "Roma,Rzym",
        "latitude": "41.89193",
        "longitude": "12.51133",
        "feature_class": "P",
        "feature_code": "PPLC",
        "country_code": "IT",
        "admin1_code": "07",
        "admin2_code": "RM",
        "population": "2318895",
        "elevation": "20",
        "dem": "52",
        "timezone": "Europe/Rome",
        "modification_date": "2025-07-22",
    },
]


#
# Application
#
@pytest.fixture(scope="module")
def app_config(app_config):
    """Override pytest-invenio app_config fixture."""
    app_config["RECORDS_REFRESOLVER_CLS"] = (
        "invenio_records.resolver.InvenioRefResolver"
    )
    app_config["RECORDS_REFRESOLVER_STORE"] = (
        "invenio_jsonschemas.proxies.current_refresolver_store"
    )
    app_config["JSONSCHEMAS_HOST"] = "not-used"

    # The datastream factories resolve reader/transformer/writer names from the
    # application config, so an instance has to register the contrib ones. This
    # mirrors what a real instance does in its `invenio.cfg`.
    app_config["VOCABULARIES_DATASTREAM_READERS"] = {
        **app_config.get("VOCABULARIES_DATASTREAM_READERS", {}),
        **VOCABULARIES_DATASTREAM_READERS,
    }
    app_config["VOCABULARIES_DATASTREAM_TRANSFORMERS"] = {
        **app_config.get("VOCABULARIES_DATASTREAM_TRANSFORMERS", {}),
        **VOCABULARIES_DATASTREAM_TRANSFORMERS,
    }
    app_config["VOCABULARIES_DATASTREAM_WRITERS"] = {
        **app_config.get("VOCABULARIES_DATASTREAM_WRITERS", {}),
        **VOCABULARIES_DATASTREAM_WRITERS,
    }

    return app_config


@pytest.fixture(scope="module")
def create_app(instance_path):
    """Application factory fixture."""
    return create_api


@pytest.fixture()
def headers():
    """Default headers for making requests."""
    return {
        "content-type": "application/json",
        "accept": "application/json",
    }


#
# Service
#
@pytest.fixture()
def service():
    """The registered geographic identifiers service."""
    return current_service_registry.get("geoidentifiers")


@pytest.fixture()
def geoidentifier_data():
    """A valid geographic identifier, as the GeoNames transformer emits one."""
    return {
        "id": "geonames::2657896",
        "scheme": "geonames",
        "name": "Zürich",
        "locations": [
            {
                "geometry": {
                    "type": "Point",
                    "coordinates": [8.55, 47.36667],
                },
            },
        ],
        "extras": {
            "ascii_name": "Zuerich",
            "alternate_names": ["Zurich", "Zürich", "Turicum"],
            "country": {
                "code": "CH",
                "name": "Switzerland",
                "official_name": "Swiss Confederation",
            },
            "admin": {
                "level1": {"code": "ZH", "name": "Zurich"},
                "level2": {"code": "112"},
            },
            "feature": {
                "class": "P",
                "class_name": "city, village,...",
                "code": "PPLA",
                "name": "seat of a first-order administrative division",
            },
            "population": 415367,
            "dem": 429,
            "timezone": "Europe/Zurich",
            "modified": "2026-04-13",
        },
    }


@pytest.fixture()
def geoidentifier(app, db, service, geoidentifier_data, search_clear):
    """A created and indexed geographic identifier."""
    item = service.create(system_identity, geoidentifier_data)
    service.indexer.refresh()

    return item


@pytest.fixture(autouse=True)
def clean_geoidentifiers(request):
    """Remove the vocabulary rows once a test is done with them."""
    yield

    if "db" not in request.fixturenames:
        # The test never touched the database, so there is nothing to undo and
        # no session to do it with.
        return

    # Import db and model here to avoid circular imports
    from invenio_db import db as database
    from invenio_pidstore.models import PersistentIdentifier

    from invenio_geographic_identifiers.geoidentifiers.models import (
        GeographicIdentifiersMetadata,
    )

    GeographicIdentifiersMetadata.query.delete()
    PersistentIdentifier.query.filter_by(pid_type="geoid").delete()
    database.session.commit()


#
# Datastreams
#
@pytest.fixture()
def geonames_archive(tmp_path):
    """GeoNames dump fixture."""
    buffer = io.StringIO()
    writer = csv.DictWriter(
        buffer, fieldnames=GEONAMES_FIELDNAMES, delimiter="\t", lineterminator="\n"
    )

    # Write the rows
    for row in GEONAMES_ROWS:
        # The dump has no header and every column present, so absent keys are
        # written as the empty strings the reader would find there
        writer.writerow({name: row.get(name, "") for name in GEONAMES_FIELDNAMES})

    # Create the archive
    archive = tmp_path / "geonames.zip"

    # Write the file to the archive
    with zipfile.ZipFile(archive, "w") as zf:
        zf.writestr("allCountries.txt", buffer.getvalue())

    # Return path
    return str(archive)
