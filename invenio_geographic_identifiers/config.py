# -*- coding: utf-8 -*-
#
# Copyright (C) 2022 GEO Secretariat.
#
# invenio-geographic-identifiers is free software; you can redistribute it
# and/or modify it under the terms of the MIT License; see LICENSE file for
# more details.

"""Geographic identifiers vocabulary for the InvenioRDM."""

import os
import tempfile

#
# Sources
#
INVENIO_GEOGRAPHIC_IDENTIFIERS_GEONAMES_DUMP_URL = (
    "https://download.geonames.org/export/dump/allCountries.zip"
)
"""Where a GeoNames dump is fetched from when no origin is given."""


#
# Downloads
#
INVENIO_GEOGRAPHIC_IDENTIFIERS_DOWNLOAD_DIR = os.path.join(
    tempfile.gettempdir(), "invenio-geographic-identifiers"
)
"""Where fetched sources are stored.

A dump is large: `allCountries.zip` is 400 MiB, and the temporary directory
is not always the best place to store it. Deployments that run several
worker containers should move this onto the volume they share, so the dump is
fetched once for the cluster instead of once per container.
"""

INVENIO_GEOGRAPHIC_IDENTIFIERS_DOWNLOAD_TIMEOUT = (10, 60)
"""Connect and read timeouts, in seconds.

The read timeout is per chunk, not for the transfer. A dump
takes hours at the GeoNames rates
"""

INVENIO_GEOGRAPHIC_IDENTIFIERS_DOWNLOAD_ATTEMPTS = 3
"""How many times a transfer is attempted before giving up."""

INVENIO_GEOGRAPHIC_IDENTIFIERS_DOWNLOAD_CHUNK_SIZE = 1024 * 1024
"""How much of a transfer is held in memory at a time."""

INVENIO_GEOGRAPHIC_IDENTIFIERS_DOWNLOAD_FREE_SPACE_MARGIN = 8 * 1024 * 1024
"""How much room to leave free beyond the size of the download.

Filling the filesystem a download lives on tends to take other things with it,
so a transfer that would come this close to the end is refused before it starts.
"""
