# -*- coding: utf-8 -*-
#
# Copyright (C) 2022 GEO Secretariat.
#
# invenio-geographic-identifiers is free software; you can redistribute it
# and/or modify it under the terms of the MIT License; see LICENSE file for
# more details.

"""Datastreams readers."""

import csv
import io
import zipfile

from invenio_vocabularies.datastreams.readers import BaseReader


class ZippedCSVReader(BaseReader):
    """Read `csv` files stored in a `zip` file."""

    def __init__(
        self, *args, csv_options=None, zip_options=None, as_dict=True, **kwargs
    ):
        """Constructor."""
        self.csv_options = csv_options or {}
        self.zip_options = zip_options or {}
        self.as_dict = as_dict
        super().__init__(*args, **kwargs)

    def _iter(self, fp, *args, **kwargs):
        """Reads a csv file and returns a dictionary per element."""
        for member in fp.infolist():
            if not member.is_dir():
                csvfile = fp.open(member)

                if not isinstance(csvfile, io.TextIOBase):
                    csvfile = io.TextIOWrapper(csvfile)
                if self.as_dict:
                    reader = csv.DictReader(csvfile, **self.csv_options)
                else:
                    reader = csv.reader(csvfile, **self.csv_options)
                for row in reader:
                    yield row

    def read(self, item=None, *args, **kwargs):
        """Opens a `zip` archive or uses the given file pointer."""
        # https://docs.python.org/3/library/zipfile.html
        if item:
            yield from self._iter(fp=item, *args, **kwargs)
        else:
            with zipfile.ZipFile(self._origin, **self.zip_options) as archive:
                yield from self._iter(fp=archive, *args, **kwargs)
