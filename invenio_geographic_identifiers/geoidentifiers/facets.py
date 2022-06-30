# -*- coding: utf-8 -*-
#
# Copyright (C) 2022 GEO Secretariat.
#
# invenio-geographic-identifiers is free software; you can redistribute it
# and/or modify it under the terms of the MIT License; see LICENSE file for
# more details.

"""Geographic Identifiers Elasticsearch facets."""


class GeographicIdentifiersLabels:
    """Fetching of Geographic identifiers labels for facets.

    Note:
        This class was imported from ``invenio-vocabularies``` (subject).
        We don't change anything because the same "human-readable" values
        are valid for the geographic identifiers.
    """

    def __call__(self, ids):
        """Return the mapping when evaluated."""
        unique_ids = list(set(ids))
        return {id_: id_ for id_ in unique_ids}
