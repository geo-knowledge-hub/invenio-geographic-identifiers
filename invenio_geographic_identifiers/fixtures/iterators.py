# -*- coding: utf-8 -*-
#
# Copyright (C) 2022 GEO Secretariat.
#
# invenio-geographic-identifiers is free software; you can redistribute it
# and/or modify it under the terms of the MIT License; see LICENSE file for
# more details.

import yaml
from os.path import splitext


class YamlIterator:
    """YAML data iterator that loads records from YAML files."""

    def __init__(self, data_file):
        self._data_file = data_file

    def __iter__(self):
        """Iterate over records."""
        with open(self._data_file) as fp:
            # Allow empty files
            data = yaml.safe_load(fp) or []
            for entry in data:
                yield entry


def file_iterator(data_file):
    """Creates an iterator from a file."""
    ext = splitext(data_file)[1].lower()
    if ext == ".yaml":
        return YamlIterator(data_file)
    raise RuntimeError(f"Unknown data format: {ext}")
