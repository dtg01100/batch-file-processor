"""Shared fixtures and configuration for integration tests."""

import os

# Ensure Qt runs in offscreen mode for all integration tests.
# This prevents segfaults from display-server-dependent rendering
# and matches the pattern already used in tests/qt/conftest.py.
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import shutil

import pytest

from interface.database import sqlite_wrapper
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
