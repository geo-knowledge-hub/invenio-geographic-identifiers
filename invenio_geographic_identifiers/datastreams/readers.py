# -*- coding: utf-8 -*-
#
# Copyright (C) 2022 GEO Secretariat.
#
# invenio-geographic-identifiers is free software; you can redistribute it
# and/or modify it under the terms of the MIT License; see LICENSE file for
# more details.

"""Datastreams readers."""

import io
import csv
import zipfile
import shapefile

from invenio_vocabularies.datastreams.errors import ReaderError
from invenio_vocabularies.datastreams.readers import BaseReader
from invenio_vocabularies.datastreams.datastreams import StreamEntry


class ZippedCSVReader(BaseReader):
    """Read a CSV data from a zip file."""

    def __init__(self, *args, csv_options=None, zip_options=None, as_dict=True, **kwargs):
        """Constructor."""
        self.csv_options = csv_options or {}
        self.zip_options = zip_options or {}
        self.as_dict = as_dict
        super().__init__(*args, **kwargs)

    def _iter(self, fp, *args, **kwargs):
        """Reads a csv file and returns a dictionary per element."""
        csvfile = fp
        if not isinstance(fp, io.TextIOBase):
            csvfile = io.TextIOWrapper(fp)
        if self.as_dict:
            reader = csv.DictReader(csvfile, **self.csv_options)
        else:
            reader = csv.reader(csvfile, **self.csv_options)
        for row in reader:
            yield StreamEntry(row)

    def read(self, item=None, *args, **kwargs):
        """Opens a Zip archive or uses the given file pointer."""
        # https://docs.python.org/3/library/zipfile.html
        if item:
            yield from self._iter(fp=item, *args, **kwargs)
        else:
            with zipfile.ZipFile(self._origin, **self.zip_options) as archive:
                yield from self._iter(fp=archive, *args, **kwargs)


class ShapefileReader(BaseReader):

    def __init__(self, origin=None, mode="r", record_validator=None, *args, **kwargs):
        self._origin = origin
        self._mode = mode
        self._record_validator = record_validator

        if self._record_validator and not callable(self._record_validator):
            raise ReaderError("`Record Validator` must be callable.")

        super(ShapefileReader, self).__init__(origin, mode, *args, **kwargs)

    def _iter(self, fp, *args, **kwargs):
        """Reads a shapefile file and returns a dictionary per element."""
        iterator = fp
        if isinstance(fp, shapefile.Reader):
            iterator = fp.iterShapeRecords()

        for shape_record in iterator:
            is_record_valid = True

            if self._record_validator:
                is_record_valid = self._record_validator(shape_record)

            if is_record_valid:
                yield StreamEntry(shape_record)

    def read(self, item=None, *args, **kwargs):
        """Reads from iter or opens the file descriptor from origin."""
        if item:
            yield from self._iter(fp=item, *args, **kwargs)
        else:
            with shapefile.Reader(self._origin, self._mode) as shp:
                yield from self._iter(fp=shp, *args, **kwargs)
