#
# This file is part of Invenio.
# Copyright (C) 2016-2018 CERN.
#
# Invenio is free software; you can redistribute it and/or modify it
# under the terms of the MIT License; see LICENSE file for more details.

"""Create Geoidentifiers revision."""

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "7fc575665183"
down_revision = None
branch_labels = ("invenio_geographic_identifiers",)
depends_on = "dbdbc1b19cf2"


def upgrade():
    """Upgrade database."""
    pass


def downgrade():
    """Downgrade database."""
    pass
