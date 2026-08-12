# -*- coding: utf-8 -*-
#
# Copyright (C) 2022 GEO Secretariat.
#
# invenio-geographic-identifiers is free software; you can redistribute it
# and/or modify it under the terms of the MIT License; see LICENSE file for
# more details.

"""Geographic identifiers REST resource tests."""

import pytest


def test_search(client, geoidentifier, headers):
    """The search endpoint returns the indexed identifier."""
    response = client.get("/geoidentifiers", headers=headers)

    assert response.status_code == 200
    assert response.json["hits"]["total"] == 1
    assert response.json["hits"]["hits"][0]["name"] == "Zürich"


def test_read_item(client, geoidentifier, headers):
    """An identifier is readable by its id."""
    response = client.get("/geoidentifiers/geonames::2657896", headers=headers)

    assert response.status_code == 200
    assert response.json["id"] == "geonames::2657896"
    assert response.json["locations"][0]["geometry"] == {
        "type": "Point",
        "coordinates": [8.55, 47.36667],
    }


def test_read_missing_item(client, geoidentifier, headers):
    """An unknown identifier is a 404."""
    response = client.get("/geoidentifiers/geonames::0", headers=headers)

    assert response.status_code == 404


def test_extras_are_exposed(client, geoidentifier, headers):
    """The extra metadata reaches the client, nested and intact."""
    response = client.get("/geoidentifiers/geonames::2657896", headers=headers)
    extras = response.json["extras"]

    assert extras["country"]["name"] == "Switzerland"
    assert extras["admin"]["level1"] == {"code": "ZH", "name": "Zurich"}
    assert extras["feature"]["name"] == "seat of a first-order administrative division"
    assert extras["population"] == 415367


def test_extras_are_returned_by_search(client, geoidentifier, headers):
    """Search hits carry the extra metadata too, not just item reads."""
    response = client.get("/geoidentifiers", headers=headers)

    assert response.json["hits"]["hits"][0]["extras"]["country"]["code"] == "CH"


@pytest.mark.parametrize(
    "query",
    [
        "Zürich",  # the name itself
        "Zuerich",  # the ascii transliteration GeoNames records
        "Turicum",  # an alternate name
        "Switzerl",  # the country, partially typed
    ],
)
def test_suggest(client, geoidentifier, headers, query):
    """Autocomplete matches the name and the names around it."""
    response = client.get(f"/geoidentifiers?suggest={query}", headers=headers)

    assert response.status_code == 200
    assert response.json["hits"]["total"] == 1


def test_suggest_is_filtered_by_scheme(client, geoidentifier, headers):
    """A `<scheme>:` prefix restricts the suggestions to that scheme."""
    matching = client.get("/geoidentifiers?suggest=geonames:Zuri", headers=headers)
    other = client.get("/geoidentifiers?suggest=other:Zuri", headers=headers)

    assert matching.json["hits"]["total"] == 1
    assert other.json["hits"]["total"] == 0


def test_anonymous_create_is_rejected(client, app, headers):
    """Only a system process may write to the vocabulary."""
    response = client.post(
        "/geoidentifiers",
        headers=headers,
        json={
            "id": "geonames::1",
            "scheme": "geonames",
            "name": "Nowhere",
            "locations": [
                {
                    "geometry": {
                        "type": "Point",
                        "coordinates": [0, 0],
                    },
                },
            ],
        },
    )

    # Confirm result
    assert response.status_code in (403, 405)
