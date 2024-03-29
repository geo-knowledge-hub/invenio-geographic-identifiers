import pytest
from invenio_db.utils import drop_alembic_version_table


def assert_alembic(alembic, table_excludes):
    """Assert that metadata of alembic and db matches.
    This method allows omitting tables dynamically created for tests.
    """
    assert not list(
        filter(
            # x[0] is the operation and x[1] is the table
            lambda x: x[0] == "add_table" and x[1].name not in table_excludes,
            alembic.compare_metadata(),
        )
    )


def test_alembic(base_app, database):
    """Test alembic recipes."""
    db = database
    ext = base_app.extensions["invenio-db"]

    # see: https://invenio-db.readthedocs.io/en/latest/alembic.html
    if db.engine.name == "sqlite":
        raise pytest.skip("Upgrades are not supported on SQLite.")

    # Check that this package's SQLAlchemy models have been properly registered
    tables = [x.name for x in db.get_tables_for_bind()]
    assert "geoidentifier_metadata" in tables

    # Check that Alembic agrees that there's no further tables to create.
    assert_alembic(ext.alembic, ["mock_metadata"])

    # Drop everything and recreate tables all with Alembic
    db.drop_all()
    drop_alembic_version_table()
    ext.alembic.upgrade()
    assert_alembic(ext.alembic, ["mock_metadata"])

    # Try to upgrade and downgrade
    ext.alembic.stamp()
    ext.alembic.downgrade(target="96e796392533")
    ext.alembic.upgrade()
    assert_alembic(ext.alembic, ["mock_metadata"])

    # Cleanup
    drop_alembic_version_table()
