"""Pytest configuration for the test suite."""

import os
import shutil
import sys
from pathlib import Path

import pytest

import migrations.folders_database_migrator
from backend.database import sqlite_wrapper
from tests.fakes import FakeEvent

os.environ["DISPATCH_STRICT_TESTING_MODE"] = "true"

project_root = Path(__file__).parent.parent.resolve()
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))


def pytest_configure(config):
    """Configure timeout behavior per platform.

    On POSIX, prefer ``signal`` so a timed-out test fails and pytest continues
    running the remaining test cases. On Windows, fall back to ``thread``.
    """
    # pytest-timeout option is only present when the plugin is installed.
    if not hasattr(config.option, "timeout_method"):
        return

    if os.name == "nt":
        config.option.timeout_method = "thread"
    else:
        config.option.timeout_method = "signal"


@pytest.fixture
def mock_event():
    """Create a fake event object for testing event handlers."""
    return FakeEvent(
        x=10,
        y=20,
        x_root=100,
        y_root=200,
        num=4,  # Button 4 for scroll up on Linux
        delta=120,  # Scroll delta for Windows
    )


@pytest.fixture
def mock_event_none_coords():
    """Create a fake event with None coordinates for edge case testing."""
    return FakeEvent(
        x=None,
        y=None,
        x_root=None,
        y_root=None,
        num=4,
        delta=120,
    )


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
    """Provide a fully migrated v42 database connection (v32 -> v42).

    Connects to the copied legacy database via *sqlite_wrapper*, runs the full
    migration pipeline through ``folders_database_migrator.upgrade_database``,
    and yields the open connection.  The connection is closed automatically
    on teardown.

    Yields:
        sqlite_wrapper.Database: An open database connection to the migrated database.
    """
    db = sqlite_wrapper.Database.connect(legacy_v32_db)
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


@pytest.fixture
def temp_database(tmp_path):
    """Create a temporary database for testing.

    Creates a fresh database with current schema for isolated testing.
    Each test gets its own copy.

    Returns:
        DatabaseObj: Temporary database object
    """
    from core.constants import CURRENT_DATABASE_VERSION
    from backend.database.database_obj import DatabaseObj

    db_path = tmp_path / "test_folders.db"

    # Create database with current schema
    db = DatabaseObj(
        database_path=str(db_path),
        database_version=CURRENT_DATABASE_VERSION,
        config_folder=str(tmp_path),
        running_platform="Linux",
    )

    return db
