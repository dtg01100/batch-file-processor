"""Pytest configuration for the test suite."""

import os
import shutil
import sys
from pathlib import Path
from unittest.mock import MagicMock

import dataset
import pytest

import folders_database_migrator

project_root = Path(__file__).parent.parent.resolve()
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))


@pytest.fixture
def mock_event():
    """Create a mock event object for testing event handlers."""
    event = MagicMock()
    event.x = 10
    event.y = 20
    event.x_root = 100
    event.y_root = 200
    event.widget = MagicMock()
    event.num = 4  # Button 4 for scroll up on Linux
    event.delta = 120  # Scroll delta for Windows
    return event


@pytest.fixture
def mock_event_none_coords():
    """Create a mock event with None coordinates for edge case testing."""
    event = MagicMock()
    event.x = None
    event.y = None
    event.x_root = None
    event.y_root = None
    event.widget = MagicMock()
    event.num = 4
    event.delta = 120
    return event


# ---------------------------------------------------------------------------
# Paths to the shared fixture database
# ---------------------------------------------------------------------------

FIXTURES_DIR = Path(__file__).parent / "fixtures"
LEGACY_DB_PATH = FIXTURES_DIR / "legacy_v32_folders.db"


# ---------------------------------------------------------------------------
# Shared database fixtures (backed by real legacy v32 production data)
# ---------------------------------------------------------------------------


@pytest.fixture
def legacy_v32_db(tmp_path):
    """Copy the real legacy v32 database to a temp directory for testing.

    Each test gets its own isolated copy so mutations never leak between tests.
    Automatically skips if the fixture file is not present on disk.

    Returns:
        str: Filesystem path to the copied database.
    """
    if not LEGACY_DB_PATH.exists():
        pytest.skip("Legacy v32 database fixture not found")
    dest = str(tmp_path / "folders.db")
    shutil.copy2(LEGACY_DB_PATH, dest)
    return dest


@pytest.fixture
def migrated_v42_db(legacy_v32_db, tmp_path):
    """Provide a fully migrated v42 dataset connection (v32 -> v42).

    Connects to the copied legacy database via *dataset*, runs the full
    migration pipeline through ``folders_database_migrator.upgrade_database``,
    and yields the open connection.  The connection is closed automatically
    on teardown.

    Yields:
        dataset.Database: An open dataset connection to the migrated database.
    """
    db = dataset.connect("sqlite:///" + legacy_v32_db)
    folders_database_migrator.upgrade_database(db, str(tmp_path), "Linux")
    yield db
    db.close()


@pytest.fixture
def real_folder_row(migrated_v42_db):
    """Return a single known-good folder row from the migrated database.

    Queries folder **id=21** (alias ``"012258"``, convert_to_format ``"csv"``),
    which is a representative production row useful for unit-level assertions.

    Returns:
        dict: The folder row as an ``OrderedDict``/dict.
    """
    return migrated_v42_db["folders"].find_one(id=21)


@pytest.fixture
def real_folder_rows(migrated_v42_db):
    """Return a list of 5 diverse real folder rows from the migrated database.

    Includes two specifically chosen rows (ids 21 and 29) plus the first three
    rows by rowid, giving a mix of folder configurations for parameterised or
    multi-row tests.

    Returns:
        list[dict]: A list of 5 folder row dicts.
    """
    rows = []
    for fid in (21, 29):
        row = migrated_v42_db["folders"].find_one(id=fid)
        if row is not None:
            rows.append(row)
    for row in migrated_v42_db["folders"].find(_limit=5):
        if row not in rows:
            rows.append(row)
        if len(rows) >= 5:
            break
    return rows


@pytest.fixture
def real_settings_row(migrated_v42_db):
    """Return the primary settings row (id=1) from the migrated database.

    Returns:
        dict: The settings row as a dict.
    """
    return migrated_v42_db["settings"].find_one(id=1)


@pytest.fixture
def real_admin_row(migrated_v42_db):
    """Return the primary administrative row (id=1) from the migrated database.

    Returns:
        dict: The administrative row as a dict.
    """
    return migrated_v42_db["administrative"].find_one(id=1)
