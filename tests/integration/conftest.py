"""Shared fixtures and configuration for integration tests."""

import os

# Ensure Qt runs in offscreen mode for all integration tests.
# This prevents segfaults from display-server-dependent rendering
# and matches the pattern already used in tests/qt/conftest.py.
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import shutil
import sqlite3

import pytest

from backend.database import sqlite_wrapper
from schema import ensure_schema


@pytest.fixture(scope="session")
def db_template(tmp_path_factory):
    """Create a template database with schema applied once per session.

    Running ``ensure_schema()`` is the most expensive part of database setup.
    This fixture pays that cost once, producing a ready-to-copy SQLite file
    that individual tests can cheaply duplicate via :pyfunction:`fresh_db`.
    """
    template_dir = tmp_path_factory.mktemp("db_template")
    db_path = template_dir / "template.db"

    db_conn = sqlite_wrapper.Database.connect(str(db_path))
    ensure_schema(db_conn)

    # Insert a version record consistent with the pattern used by test fixtures.
    db_conn["version"].insert({"id": 1, "version": "41", "os": "Linux"})

    db_conn.close()
    return db_path


@pytest.fixture
def fresh_db(db_template, tmp_path):
    """Provide a per-test copy of the template database.

    Returns the :class:`pathlib.Path` to a new SQLite file that already has the
    full schema and a version record, ready for further setup (e.g. creating a
    :class:`DatabaseObj` or inserting test-specific rows).
    """
    dest = tmp_path / "test.db"
    shutil.copy2(str(db_template), str(dest))
    return dest


# =============================================================================
# InvFetcher Test Database Fixtures
# =============================================================================


class FakeQueryRunner:
    """Query runner for invFetcher tests using SQLite.

    Implements the QueryRunnerProtocol for invFetcher with a local SQLite
    database containing the tables that invFetcher queries (ohhst, odhst).
    """

    def __init__(self, conn: sqlite3.Connection):
        self.conn = conn

    def run_query(self, query: str, params: tuple = None) -> list[dict]:
        """Execute a query and return results as list of dicts."""
        cursor = self.conn.execute(query, params or ())
        rows = cursor.fetchall()
        # Convert to list of dicts
        columns = [desc[0] for desc in cursor.description] if cursor.description else []
        return [dict(zip(columns, row)) for row in rows]


@pytest.fixture
def invfetcher_test_db(tmp_path):
    """Create a test database for invFetcher with AS400-compatible schema.

    Creates a SQLite database with tables matching the AS400 schema that
    invFetcher queries (ohhst for invoice headers, odhst for invoice details).
    Populates with test data for invoice number 1 (0000000001).

    Returns:
        tuple: (db_path, query_runner) where query_runner can be passed to InvFetcher
    """
    db_path = tmp_path / "invfetcher_test.db"
    conn = sqlite3.connect(str(db_path))

    # Create schema-attached tables to match AS400 schema (dacdata.ohhst, dacdata.odhst)
    # SQLite supports "database.table" syntax, so we attach a dummy database
    conn.execute("ATTACH DATABASE ':memory:' AS dacdata")

    # Create ohhst table (invoice headers) - matches AS400 schema
    conn.execute(
        """
        CREATE TABLE dacdata.ohhst (
            BTHHNB INTEGER PRIMARY KEY,
            bte4cd TEXT,
            bthinb TEXT,
            btabnb INTEGER
        )
    """
    )

    # Create odhst table (invoice details/lines) - matches AS400 schema
    conn.execute(
        """
        CREATE TABLE dacdata.odhst (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            BUHHNB INTEGER,
            BUHUNB INTEGER,
            BUHXTX TEXT
        )
    """
    )

    # Insert test invoice header data for invoice 1
    # Invoice number 1 with PO number, customer name, and customer number
    conn.execute(
        "INSERT INTO dacdata.ohhst (BTHHNB, bte4cd, bthinb, btabnb)"
        " VALUES (?, ?, ?, ?)",
        (1, "PO12345", "Test Customer Name", 12345),
    )

    # Insert test invoice detail data for UOM lookups
    # Line 1: UOM description for item
    conn.execute(
        "INSERT INTO dacdata.odhst (BUHHNB, BUHUNB, BUHXTX) VALUES (?, ?, ?)",
        (1, 1, "EA"),
    )

    conn.commit()

    # Create query runner
    query_runner = FakeQueryRunner(conn)

    yield db_path, query_runner

    conn.close()


@pytest.fixture
def invfetcher_with_test_data(invfetcher_test_db):
    """Provide an invFetcher instance with test database.

    Creates and configures an InvFetcher instance that uses the test database,
    ready to use in converter tests.

    Returns:
        InvFetcher: Configured with test database
    """
    from core.edi.inv_fetcher import InvFetcher

    db_path, query_runner = invfetcher_test_db
    settings = {"database_lookup_mode": "test"}
    return InvFetcher(query_runner, settings)
