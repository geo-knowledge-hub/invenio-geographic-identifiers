# -*- coding: utf-8 -*-
#
# Copyright (C) 2022 GEO Secretariat.
#
# invenio-geographic-identifiers is free software; you can redistribute it
# and/or modify it under the terms of the MIT License; see LICENSE file for
# more details.

"""Geographic Identifiers configuration."""

from flask_babelex import lazy_gettext as _
from invenio_records_resources.services import SearchOptions
from invenio_records_resources.services.records.components import DataComponent
from invenio_vocabularies.services.components import PIDComponent
from invenio_vocabularies.services.querystr import FilteredSuggestQueryParser


class GeographicIdentifiersSearchOptions(SearchOptions):
    """Search options for the Geographic identifiers vocabulary."""

    suggest_parser_cls = FilteredSuggestQueryParser.factory(
        filter_field="scheme",
        fields=[  # suggest fields
            "extras^100",
            "extras._2gram",
            "extras._3gram",
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
