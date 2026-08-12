# -*- coding: utf-8 -*-
#
# Copyright (C) 2022 GEO Secretariat.
#
# invenio-geographic-identifiers is free software; you can redistribute it
# and/or modify it under the terms of the MIT License; see LICENSE file for
# more details.

"""Writers for Geographic Identifiers Datastreams."""

from invenio_pidstore.errors import PIDDeletedError
from invenio_vocabularies.datastreams.errors import WriterError
from invenio_vocabularies.datastreams.writers import ServiceWriter


class GeoIdentifierServiceWriter(ServiceWriter):
    """Geographic Identifier ServiceWriter class."""

    def _entry_id(self, entry):
        return entry["id"]

    def _do_update(self, entry):
        """Update an entry.

        Deleting an identifier leaves a tombstone behind, and resolving it
        raises. Upstream handles a missing identifier but not a deleted one, so
        the exception escapes `process()` and abandons the whole run.

        Reporting it as an error for that entry alone lets the rest of the run finish.
        """
        try:
            return super()._do_update(entry)

        except PIDDeletedError:
            raise WriterError(
                [f"Vocabulary entry is deleted, and was left alone: {entry}"]
            )
