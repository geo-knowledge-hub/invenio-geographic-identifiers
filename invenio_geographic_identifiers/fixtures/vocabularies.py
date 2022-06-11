# -*- coding: utf-8 -*-
#
# Copyright (C) 2022 GEO Secretariat.
#
# invenio-geographic-identifiers is free software; you can redistribute it
# and/or modify it under the terms of the MIT License; see LICENSE file for
# more details.

from pathlib import Path

from invenio_db import db
from invenio_vocabularies.proxies import current_service
from invenio_vocabularies.records.models import VocabularyScheme

from .tasks import create_vocabulary_record
from .iterators import file_iterator


class VocabularyEntry:
    """Loading vocabulary superclass."""

    def __init__(self, service_str, directory, id_, entry):
        """Constructor."""
        self._id = id_
        self._entry = entry
        self._dir = Path(directory)
        self.service_str = service_str

    # Interface properties
    @property
    def covered_ids(self):
        """Just the id of the vocabulary covered by this entry as a list."""
        return [self._id]

    # Template methods
    def pre_load(self, identity, ignore):
        """Actions taken before iteratively creating records."""
        if self._id not in ignore:
            pid_type = self._entry["pid-type"]
            current_service.create_type(identity, self._id, pid_type)

    def iterate(self, ignore):
        """Iterate over dicts of file content."""
        if self._id not in ignore:
            filepath = self._dir / self._entry["data-file"]
            for data in file_iterator(filepath):
                yield data

    def loaded(self):
        """Vocabularies actually loaded."""
        return [self._id]

    def load(self, identity, ignore=None, delay=False):
        """Template method design pattern for loading entries."""
        ignore = ignore or set()
        self.pre_load(identity, ignore=ignore)
        for data in self.iterate(ignore=ignore):
            self.create_record(data, delay=delay)
        return self.loaded()

    def create_record(self, data, delay=False):
        """Create the record."""
        if delay:
            create_vocabulary_record.delay(self.service_str, data)
        else:  # mostly for tests
            create_vocabulary_record(self.service_str, data)


class VocabularyEntryWithSchemes(VocabularyEntry):
    """Vocabulary fixture for specific vocabulary with schemes."""

    def __init__(self, service_str, directory, id_, entry):
        """Constructor."""
        super().__init__(service_str, directory, id_, entry)
        self._loaded = []

    # Template methods
    def pre_load(self, identity, ignore):
        """Actions taken before iteratively creating records."""
        for scheme in self.schemes():
            id_ = f"{self._id}.{scheme['id']}"
            if id_ not in ignore:
                self.create_scheme(scheme)

    def iterate(self, ignore):
        """Iterate over dicts of file content."""
        self._loaded = []

        for scheme in self.schemes():
            id_ = f"{self._id}.{scheme['id']}"
            if id_ not in ignore:
                self._loaded.append(id_)
                filepath = self._dir / scheme.get("data-file")
                yield from file_iterator(filepath)

    def loaded(self):
        """Vocabularies actually loaded."""
        return self._loaded

    # Other interface methods
    @property
    def covered_ids(self):
        """List of ids of the subvocabularies covered by this entry."""
        return [f"{s['id']}" for s in self.schemes()]

    # Helpers
    def schemes(self):
        """Return schemes."""
        return self._entry.get("schemes", [])

    def create_scheme(self, metadata):
        """Create the vocabulary scheme row."""
        id_ = metadata["id"]
        name = metadata.get("name", "")
        uri = metadata.get("uri", "")
        VocabularyScheme.create(id=id_, parent_id=self._id, name=name, uri=uri)
        db.session.commit()
