"""Pytest configuration for the test suite."""

import contextlib
import os
import shutil
import sys
from pathlib import Path
from unittest.mock import MagicMock

import pytest

pytest_plugins = ["tests.conftest_magicmock_plugin"]

from adapters.db2ssh.connection import DB2SSHConnection
from backend.database import sqlite_wrapper
from dispatch.interfaces import ErrorHandlerInterface, FileSystemInterface
from dispatch.pipeline.interfaces import PipelineStep
from dispatch.send_manager import SendManager
from interface.ports import ProgressServiceProtocol, UIServiceProtocol
from interface.services.resend_service import ResendService
from migrations import folders_database_migrator

os.environ["DISPATCH_STRICT_TESTING_MODE"] = "true"


project_root = Path(__file__).parent.parent.resolve()
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))


ODBC_REQUIRED_KEYS = [
    "AS400_ADDRESS",
    "AS400_USERNAME",
    "AS400_PASSWORD",
    "ODBC_DRIVER",
]


@pytest.fixture
def odbc_creds(monkeypatch):
    """Provide ODBC credentials for tests that need them. Hermetic — uses literal
    test values, not environment reads.

    The credentials set here are placeholders; tests that consume this fixture
    should mock the AS/400 query runner to avoid any real network call.
    """
    creds = {
        "address": "test.as400.example.com",
        "username": "test_user",
        "password": "test_pass",
        "driver": "{IBM i Access ODBC Driver}",
    }
    monkeypatch.setenv("AS400_ADDRESS", creds["address"])
    monkeypatch.setenv("AS400_USERNAME", creds["username"])
    monkeypatch.setenv("AS400_PASSWORD", creds["password"])
    monkeypatch.setenv("ODBC_DRIVER", creds["driver"])
    return creds


def pytest_configure(config):
    """Configure timeout behavior per platform.

    On POSIX, prefer ``signal`` so a timed-out test fails and pytest continues
    running the remaining test cases. On Windows, fall back to ``thread``.
    """
    import glob
    import shutil

    for pattern in ["edi_converter_*", "edi_tweaker_*", "edi_rename_*"]:
        for path in glob.glob(f"/tmp/{pattern}"):
            with contextlib.suppress(Exception):
                shutil.rmtree(path, ignore_errors=True)

    # pytest-timeout option is only present when the plugin is installed.
    if not hasattr(config.option, "timeout_method"):
        return

    if os.name == "nt":
        config.option.timeout_method = "thread"
    else:
        config.option.timeout_method = "signal"


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
def mock_as400_query_runner(monkeypatch):
    """Provide a deterministic AS/400 query runner for full-pipeline tests.

    This replaces the legacy ODBC query runner and returns a predictable
    customer header + UOM lookup sequence so tests do not depend on external
    AS/400 connectivity.
    """

    class DummyQueryRunner:
        def __init__(self):
            self.call_count = 0

        def run_query(self, query, params=None):
            self.call_count += 1
            if self.call_count == 1:
                return [
                    {
                        "Salesperson_Name": "Salesperson",
                        "Invoice_Date": "2025-01-01",
                        "Terms_Code": "NET30",
                        "Terms_Duration": "30",
                        "Customer_Status": "A",
                        "Customer_Number": "12345",
                        "Customer_Name": "Test Customer",
                        "Customer_Address": "123 Main St",
                        "Customer_Town": "Anytown",
                        "Customer_State": "ST",
                        "Customer_Zip": "12345",
                        "Customer_Phone": "5551234567",
                        "Customer_Email": "test@email.com",
                        "Customer_Email_2": "",
                        "Corporate_Customer_Status": "A",
                        "Corporate_Customer_Number": "12345",
                        "Corporate_Customer_Name": "Corporate Customer",
                        "Corporate_Customer_Address": "456 Corp St",
                        "Corporate_Customer_Town": "Corptown",
                        "Corporate_Customer_State": "ST",
                        "Corporate_Customer_Zip": "54321",
                        "Corporate_Customer_Phone": "5559876543",
                        "Corporate_Customer_Email": "corp@email.com",
                        "Corporate_Customer_Email_2": "",
                    }
                ]
            if self.call_count == 2:
                return [{"itemno": "123456", "uom_mult": "1", "uom_code": "EA"}]
            return []

    dummy = DummyQueryRunner()
    monkeypatch.setattr(
        "core.database.create_query_runner",
        lambda *args, **kwargs: dummy,
    )

    return dummy


@pytest.fixture(autouse=True)
def mock_upc_service(request, monkeypatch):
    """Silence UPC WARNING noise from ``dispatch.services.upc_service``.

    Why this exists
    ---------------
    Under ``DISPATCH_STRICT_TESTING_MODE=true`` (set in this conftest), every
    integration test that constructs a ``DispatchOrchestrator`` via
    ``DispatchConfig(settings={})`` triggers two WARNING lines from
    ``dispatch/services/upc_service.py`` (lines 190 and 112):

        WARNING  Cannot fetch UPC dictionary: missing AS400 credentials (...)
        WARNING  UPC dictionary is empty: fallback query failed (...)

    Those warnings drown out real production misconfiguration warnings and
    clutter the test log without indicating any actual test problem — the
    integration tests under test intentionally run without AS400 credentials.

    This fixture monkeypatches :py:meth:`UPCLookupService.get_dictionary` so
    it returns ``{}`` directly, never calling into the real AS400 lookup path
    and never emitting the noisy WARNINGs.

    Reference: kanban task ``t_b708094a`` (option b — test-side fix).

    Why we skip ``@pytest.mark.unit`` tests
    ---------------------------------------
    Unit tests in ``tests/unit/dispatch_tests/test_services.py`` exercise the
    real :class:`UPCLookupService` behaviour (assertions on
    ``last_error``, WARNING emission, the ``create_query_runner_from_settings``
    monkeypatch path, and ``get_dictionary(upc_service=external)`` injection).
    Patching the class method would break those tests — e.g. the
    ``upc_service=external`` kwarg is forwarded to the patched stub, which
    doesn't accept it. The ``unit`` marker opt-out preserves their behaviour.

    How to override
    ---------------
    Tests that genuinely need the real UPC behaviour should either:

    * Mark themselves with ``@pytest.mark.unit`` (the autouse fixture
      becomes a no-op), or
    * Take a ``monkeypatch`` parameter and replace ``UPCLookupService`` or
      its methods explicitly — those ``monkeypatch.setattr`` calls run
      after this fixture, so they win.

    The fixture is autouse so existing integration tests benefit without any
    per-test opt-in.
    """
    if request.node.get_closest_marker("unit") is not None:
        # Unit tests intentionally exercise the real UPC service — leave it
        # untouched so their assertions on WARNING emission, last_error,
        # and the injected ``upc_service=`` kwarg keep working.
        return

    from dispatch.services.upc_service import UPCLookupService

    def _stub_get_dictionary(self, *args, **kwargs):
        # No-op stub: returns an empty UPC dict and emits no warnings.
        # *args/**kwargs accept (and ignore) any legacy call shape
        # (``upc_service=`` injection, ``strict_db_mode=`` kwarg, etc.)
        # so this fixture is safe to install even for tests that pass
        # extra arguments.
        return {}

    monkeypatch.setattr(UPCLookupService, "get_dictionary", _stub_get_dictionary)


@pytest.fixture
def temp_database(tmp_path):
    """Create a temporary database for testing.

    Creates a fresh database with current schema for isolated testing.
    Each test gets its own copy.

    Returns:
        DatabaseObj: Temporary database object
    """
    from backend.database.database_obj import DatabaseObj
    from core.constants import CURRENT_DATABASE_VERSION

    db_path = tmp_path / "test_folders.db"

    # Create database with current schema
    return DatabaseObj(
        database_path=str(db_path),
        database_version=CURRENT_DATABASE_VERSION,
        config_folder=str(tmp_path),
        running_platform="Linux",
    )


# ---------------------------------------------------------------------------
# Shared mock factories — provide spec'd mocks for common test patterns
# ---------------------------------------------------------------------------


class MockFactories:
    """Factory methods for spec'd MagicMock instances.

    Using spec= ensures mocks stay in sync with real interfaces —
    typos and missing methods are caught at test time rather than
    silently passing with bare MagicMock.
    """

    @staticmethod
    def ui_service() -> MagicMock:
        return MagicMock(spec=UIServiceProtocol)

    @staticmethod
    def progress_service() -> MagicMock:
        return MagicMock(spec=ProgressServiceProtocol)

    @staticmethod
    def send_manager() -> MagicMock:
        return MagicMock(spec=SendManager)

    @staticmethod
    def error_handler() -> MagicMock:
        return MagicMock(spec=ErrorHandlerInterface)

    @staticmethod
    def file_system() -> MagicMock:
        return MagicMock(spec=FileSystemInterface)

    @staticmethod
    def pipeline_step() -> MagicMock:
        return MagicMock(spec=PipelineStep)

    @staticmethod
    def validator_step() -> MagicMock:
        return MagicMock(spec=PipelineStep)

    @staticmethod
    def splitter_step() -> MagicMock:
        return MagicMock(spec=PipelineStep)

    @staticmethod
    def converter_step() -> MagicMock:
        return MagicMock(spec=PipelineStep)

    @staticmethod
    def database_obj() -> MagicMock:
        """Create a mock DatabaseObj with common attributes pre-configured.

        Uses a bare MagicMock to allow arbitrary attribute access for tests
        that need methods not in the DatabaseConnectionProtocol.
        """
        mock = MagicMock()
        mock.folders_table = MagicMock()
        mock.folders_table.find.return_value = []
        mock.folders_table.find_one.return_value = None
        mock.folders_table.count.return_value = 0
        mock.processed_files = MagicMock()
        mock.processed_files.count.return_value = 0
        mock.oversight_and_defaults = MagicMock()
        mock.oversight_and_defaults.update = MagicMock()
        mock.oversight_and_defaults.find_one.return_value = None
        mock.get_oversight_or_default.return_value = {"id": 1}
        mock.get_settings_or_default.return_value = {"id": 1}
        return mock

    @staticmethod
    def folder_manager() -> MagicMock:
        return MagicMock()

    @staticmethod
    def db2ssh_connection() -> MagicMock:
        return MagicMock(spec=DB2SSHConnection)

    @staticmethod
    def resend_service() -> MagicMock:
        return MagicMock(spec=ResendService)

    @staticmethod
    def folders_table() -> MagicMock:
        """Create a mock folders_table with common methods."""
        mock = MagicMock()
        mock.find.return_value = []
        mock.find_one.return_value = None
        mock.count.return_value = 0
        return mock
