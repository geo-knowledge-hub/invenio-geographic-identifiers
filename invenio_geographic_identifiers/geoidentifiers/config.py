# -*- coding: utf-8 -*-
#
# Copyright (C) 2022 GEO Secretariat.
#
# invenio-geographic-identifiers is free software; you can redistribute it
# and/or modify it under the terms of the MIT License; see LICENSE file for
# more details.

"""Geographic Identifiers configuration."""

from invenio_i18n import lazy_gettext as _
from invenio_records_resources.services import SearchOptions
from invenio_records_resources.services.records.components import DataComponent
from invenio_records_resources.services.records.queryparser import (
    CompositeSuggestQueryParser,
)
from invenio_search.engine import dsl
from invenio_vocabularies.services.components import PIDComponent


class PopulationRankedSuggestQueryParser(CompositeSuggestQueryParser):
    """Suggestion parser that breaks ties by population.

    Place names repeat: For instance, the United States alone has 68 populated
    places called "Springfield", and they are textually indistinguishable. Left
    to the text score the order among them is arbitrary, which puts hamlets of no
    inhabitants above state capitals.

    Population is the tiebreaker a reader expects, so the text score is scaled
    by it. The logarithm keeps it a tiebreaker rather than a ranking of its own:
    a place a thousand times larger scores a few times higher, so a better
    textual match still wins.
    """

    def parse(self, query_str):
        """Parse the query and weight it by population."""
        return dsl.Q(
            "function_score",
            query=super().parse(query_str),
            boost_mode="multiply",
            functions=[
                {
                    "field_value_factor": {
                        "field": "extras.population",
                        # `log2p` is log(2 + population), so it stays positive
                        # for the unpopulated places that would otherwise score
                        # zero and disappear entirely
                        "modifier": "log2p",
                        # A scheme that reports no population at all is scaled by
                        # the same constant throughout, so the order within it is
                        # unaffected.
                        "missing": 0,
                    }
                }
            ],
        )


class GeographicIdentifiersSearchOptions(SearchOptions):
    """Search options for the Geographic identifiers vocabulary."""

    suggest_parser_cls = PopulationRankedSuggestQueryParser.factory(
        # A `<scheme>:` prefix on the query restricts the suggestions to that
        # scheme, e.g. `geonames:zuri`.
        filter_field="scheme",
        fields=[
            # The name is what a user types, so it leads. `.suggest` is the
            # `search_as_you_type` sub-field that makes a partial word match
            "name^100",
            "name.suggest^100",
            # Then the other names a place goes by: the ascii transliteration
            # (GeoNames records Zürich as "Zuerich") and the alternate names
            # (which is where "Zurich" itself lives).
            "extras.ascii_name^50",
            "extras.ascii_name.suggest^50",
            "extras.alternate_names^50",
            "extras.alternate_names.suggest^50",
            # Finally the containing place, so "springfield illinois" narrows to
            # one of the many Springfields names.
            "extras.country.name^10",
            "extras.admin.level1.name^10",
        ],
        clauses=[
            # Spelled out rather than left to the parser defaults, which omit
            # `bool_prefix`. Without it a half-typed word matches nothing, all
            # autocomplete has is all half-typed words.
            {"type": "bool_prefix", "boost": 3},
            {"type": "cross_fields", "boost": 2},
            {"type": "most_fields", "boost": 1, "fuzziness": "AUTO"},
        ],
    )

    sort_default = "bestmatch"

    sort_default_no_query = "name"

    sort_options = {
        "bestmatch": dict(
            title=_("Best match"),
            fields=["_score"],  # ES defaults to desc on `_score` field
        ),
        "name": dict(
            title=_("Name"),
            fields=["name_sort"],
        ),
        "newest": dict(
            title=_("Newest"),
            fields=["-created"],
        ),
        "oldest": dict(
            title=_("Oldest"),
            fields=["created"],
        ),
    }


service_components = [
    # Order of components are important!
    DataComponent,
    PIDComponent,
]
