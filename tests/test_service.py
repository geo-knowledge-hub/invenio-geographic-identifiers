# -*- coding: utf-8 -*-
#
# Copyright (C) 2022 GEO Secretariat.
#
# invenio-geographic-identifiers is free software; you can redistribute it
# and/or modify it under the terms of the MIT License; see LICENSE file for
# more details.

"""Geographic identifiers service tests."""

import pytest
from invenio_access.permissions import system_identity
from invenio_pidstore.errors import PIDDeletedError
from invenio_records_resources.proxies import current_service_registry


def test_service_is_registered(app):
    """The service is reachable under the id the CLI and the writers use."""
    service = current_service_registry.get("geoidentifiers")

    assert service.config.service_id == "geoidentifiers"


def test_indexer_is_registered(app):
    """The indexer is registered alongside the service."""
    registry = app.extensions["invenio-indexer"].registry

    assert registry.get("geoidentifiers") is not None


def test_create_and_read(app, db, service, geoidentifier_data, search_clear):
    """A geographic identifier round-trips through the service."""
    data = {
        **geoidentifier_data,
        "id": "geonames::2661552",
        "name": "Bern",
    }

    # Create the identifier
    created = service.create(system_identity, data)

    # Confirm result
    assert created.id == "geonames::2661552"

    # Read the identifier
    read = service.read(system_identity, "geonames::2661552").to_dict()

    # Confirm result
    assert read["name"] == "Bern"
    assert read["scheme"] == "geonames"
    assert read["locations"][0]["geometry"]["type"] == "Point"


def test_extras_are_returned(app, geoidentifier, service, geoidentifier_data):
    """The extra metadata comes back out of the service."""
    read = service.read(system_identity, geoidentifier_data["id"]).to_dict()

    assert read["extras"] == geoidentifier_data["extras"]


def test_search(app, geoidentifier, service):
    """The indexed identifier is searchable by name."""
    assert service.search(system_identity, q="Zürich").total == 1
    assert service.search(system_identity, q="Lisbon").total == 0


@pytest.mark.parametrize(
    "query",
    [
        "Zürich",  # the name
        "Zuri",  # a partial name, which is what autocomplete really sees
        "Zuerich",  # the ascii transliteration GeoNames records
        "Turicum",  # an alternate name
        "Switzerland",  # the country
        "Zurich",  # the first-order administrative division
    ],
)
def test_suggest(app, geoidentifier, service, query):
    """Autocomplete finds a place by any of the names attached to it."""
    # Run the search
    results = service.search(system_identity, suggest=query).to_dict()

    # Confirm result
    assert [hit["id"] for hit in results["hits"]["hits"]] == ["geonames::2657896"]


def test_suggest_ignores_unrelated_terms(app, geoidentifier, service):
    """A query matching nothing returns nothing."""
    assert service.search(system_identity, suggest="Reykjavik").total == 0


def test_suggest_folds_accents(app, geoidentifier, service):
    """An unaccented query finds an accented place."""
    assert service.search(system_identity, suggest="Zuri").total == 1


def test_suggest_ranks_by_population(app, db, service, search_clear):
    """Among identical names, the larger place comes first."""
    places = [
        ("geonames::4250542", "Illinois", 114394),
        ("geonames::4068446", "Alabama", 0),
        ("geonames::5262708", "Wisconsin", 158),
    ]

    for id_, division, population in places:
        service.create(
            system_identity,
            {
                "id": id_,
                "scheme": "geonames",
                "name": "Springfield",
                "locations": [{"geometry": {"type": "Point", "coordinates": [0, 0]}}],
                "extras": {
                    "admin": {"level1": {"name": division}},
                    "population": population,
                },
            },
        )

    service.indexer.refresh()

    # Search
    results = service.search(system_identity, suggest="Springfiel").to_dict()

    # Get ranked
    ranked = [hit["extras"]["population"] for hit in results["hits"]["hits"]]

    # Confirm result
    assert ranked == sorted(ranked, reverse=True)


def test_suggest_is_filtered_by_scheme(app, geoidentifier, service):
    """A `<scheme>:` prefix on the suggestion restricts it to that scheme."""
    # geonames
    assert service.search(system_identity, suggest="geonames:Zuri").total == 1

    # other
    assert service.search(system_identity, suggest="other:Zuri").total == 0


def test_delete(app, geoidentifier, service, geoidentifier_data):
    """Deleting tombstones the identifier."""
    service.delete(system_identity, geoidentifier_data["id"])

    with pytest.raises(PIDDeletedError):
        service.read(system_identity, geoidentifier_data["id"])
