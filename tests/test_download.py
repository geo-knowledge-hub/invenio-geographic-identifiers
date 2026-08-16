# -*- coding: utf-8 -*-
#
# Copyright (C) 2022 GEO Secretariat.
#
# invenio-geographic-identifiers is free software; you can redistribute it
# and/or modify it under the terms of the MIT License; see LICENSE file for
# more details.

"""Tests for fetching a source before importing it."""

import copy
import os
import shutil
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

import pytest
from conftest import GEONAMES_ROWS, write_geonames_archive
from kombu.serialization import dumps

from invenio_geographic_identifiers import config as package_config
from invenio_geographic_identifiers.contrib.geonames.datastreams import (
    DATASTREAM_CONFIG,
    GeoNamesReader,
)
from invenio_geographic_identifiers.datastreams.download import (
    DownloadError,
    ensure_local_copy,
    local_path_for,
)
from invenio_geographic_identifiers.tasks import resolve_origin


#
# Test source
#
class _Handler(BaseHTTPRequestHandler):
    """Serves a body with ranges support."""

    def _respond(self, with_body):
        """Answer either a full or a partial body."""
        span = self.headers.get("Range")
        body = self.server.body
        status = 200

        if span:
            body = body[int(span.split("=")[1].split("-")[0]) :]
            status = 206

        # Only transfers are recorded: what the tests care about is how many
        # times the bytes were moved, and from what offset
        if with_body:
            self.server.transfers.append(span)

        # Send the response
        self.send_response(status)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Accept-Ranges", "bytes")
        self.end_headers()

        if with_body:
            self.wfile.write(body)

    def log_message(self, *args):
        """Keep the test output readable."""

    def do_HEAD(self):
        """Answer a probe."""
        self._respond(with_body=False)

    def do_GET(self):
        """Answer a transfer."""
        self._respond(with_body=True)


#
# Fixture
#
@pytest.fixture()
def source(tmp_path, monkeypatch):
    """A dump served over HTTP."""
    monkeypatch.setattr(
        package_config,
        "INVENIO_GEOGRAPHIC_IDENTIFIERS_DOWNLOAD_DIR",
        str(tmp_path / "downloads"),
    )

    # Write the archive
    path = write_geonames_archive(tmp_path / "served.zip", GEONAMES_ROWS)

    # Read the body
    with open(path, "rb") as handle:
        body = handle.read()

    # Start the server
    httpd = ThreadingHTTPServer(("127.0.0.1", 0), _Handler)
    httpd.body = body
    httpd.transfers = []
    httpd.url = "http://{}:{}/dump.zip".format(*httpd.server_address[:2])

    # Start the server
    threading.Thread(target=httpd.serve_forever, daemon=True).start()

    # Yield the server
    yield httpd

    # Stop the server
    httpd.shutdown()
    httpd.server_close()


#
# Fetching
#
def test_a_source_is_fetched_and_then_reused(source):
    """The first caller downloads the complete copy and second one reuses it."""
    path = ensure_local_copy(source.url)

    # Read the body
    with open(path, "rb") as handle:
        assert handle.read() == source.body

    # Confirm results
    assert not os.path.exists(f"{path}.part")
    assert ensure_local_copy(source.url) == path
    assert source.transfers == [None]


def test_a_partial_copy_is_resumed(source):
    """Only the missing bytes are downloaded."""
    current_part = f"{local_path_for(source.url)}.part"
    already_transfered = len(source.body) // 2

    # Pretend an earlier attempt got halfway
    os.makedirs(os.path.dirname(current_part), exist_ok=True)

    # Write the current part
    with open(current_part, "wb") as handle:
        handle.write(source.body[:already_transfered])

    # Read the body
    with open(ensure_local_copy(source.url), "rb") as handle:
        assert handle.read() == source.body

    # Confirm the transfer
    assert source.transfers == [f"bytes={already_transfered}-"]


def test_no_room_is_refused_before_anything_is_written(tmp_path, monkeypatch):
    """If there is no storage to save transferred bytes, the operation is refused."""
    monkeypatch.setattr(
        shutil, "disk_usage", lambda path: shutil._ntuple_diskusage(0, 0, 1)
    )

    # Try to fetch the source
    with pytest.raises(DownloadError) as error:
        # Try to fetch the source
        ensure_local_copy(
            url="http://127.0.0.1:1/dump.zip",
            directory=str(tmp_path),
            expect={"length": 1024, "etag": None, "resumable": True},
        )

    # Confirm the error
    assert "1 free" in str(error.value)
    assert "INVENIO_GEOGRAPHIC_IDENTIFIERS_DOWNLOAD_DIR" in str(error.value)


#
# Reaching the datastream
#
def test_the_fan_out_fetches_once_and_the_shards_read_it(source):
    """The fan-out resolves the source, so the shards never fetch it themselves."""
    # Make a copy of the configuration
    config = copy.deepcopy(DATASTREAM_CONFIG)

    # Set the origin to the source URL
    config["readers"][0]["args"]["origin"] = source.url

    # Resolve the origin
    reader_args = resolve_origin(config)["readers"][0]["args"]

    # A concrete path, plus where it came from, so a shard on a machine that
    # cannot see that path can fetch the same snapshot instead of failing
    assert os.path.exists(reader_args["origin"])
    assert reader_args["origin_url"] == source.url

    # Dump the reader arguments
    dumps(reader_args, serializer="msgpack")

    # Remove the pinned path
    os.remove(reader_args["origin"])

    # Read the rows
    rows = list(GeoNamesReader(**reader_args).read())

    # Confirm the rows
    assert [row["geonameid"] for row in rows] == [
        row["geonameid"] for row in GEONAMES_ROWS
    ]

    # Confirm the transfers
    assert source.transfers == [None, None]
