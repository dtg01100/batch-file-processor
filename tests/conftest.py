"""
Pytest configuration and shared fixtures for batch-file-processor tests.

This module provides common fixtures and setup for testing the batch file processor.
Tests capture the current production functionality to ensure stability and prevent regressions.
"""

import os
import pytest
import tempfile
import shutil
from pathlib import Path


@pytest.fixture
def temp_dir():
    """Create a temporary directory for test files."""
    test_dir = tempfile.mkdtemp()
    yield test_dir
    # Cleanup after test
    shutil.rmtree(test_dir, ignore_errors=True)


@pytest.fixture
def sample_file(temp_dir):
    """Create a sample test file."""
    file_path = os.path.join(temp_dir, "test_sample.txt")
    with open(file_path, "w") as f:
        f.write("test content\n")
    return file_path


@pytest.fixture
def sample_csv_file(temp_dir):
    """Create a sample CSV file for testing."""
    file_path = os.path.join(temp_dir, "test_sample.csv")
    with open(file_path, "w") as f:
        f.write("header1,header2,header3\n")
        f.write("value1,value2,value3\n")
    return file_path


@pytest.fixture
def sample_edi_file(temp_dir):
    """Create a sample EDI file for testing."""
    file_path = os.path.join(temp_dir, "test_sample.edi")
    edi_content = """UNA:*'~
UNB+UNOC:3+SENDER+RECEIVER+210101:1200+1'
UNH+1+ORDERS:D:96A:UN'
BGM+220+ORDER001+9'
DTM+137:20210101:102'
NAD+BY+BuyerCode'
NAD+SU+SupplierCode'
LIN+1++ProductCode:EN'
QTY+1:100'
UNT+9+1'
UNZ+1+1'"""
    with open(file_path, "w") as f:
        f.write(edi_content)
    return file_path


@pytest.fixture
def project_root():
    """Get the project root directory."""
    return Path(__file__).parent.parent


# Qt Testing Fixtures
@pytest.fixture(scope="session")
def qapp():
    """
    Create QApplication for the test session.

    This fixture is session-scoped so QApplication is created once
    and shared across all tests.
    """
    from PyQt6.QtWidgets import QApplication
    import sys

    # QApplication must be created before any widgets
    app = QApplication.instance()
    if app is None:
        app = QApplication(sys.argv)

    yield app

    # Cleanup is automatic when session ends


@pytest.fixture
def qtbot(qapp, request):
    """
    Provide QtBot for widget testing.

    QtBot allows testing Qt widgets with proper event processing.
    """
    try:
        from pytestqt.qtbot import QtBot

        return QtBot(request)
    except ImportError:
        # Fallback if pytest-qt not installed
        from unittest.mock import Mock

        mock_bot = Mock()
        mock_bot.addWidget = Mock()
        mock_bot.waitSignal = Mock()
        return mock_bot


@pytest.fixture
def mock_db_manager():
    """
    Create a mock database manager for testing.

    This mock provides the database interface without requiring
    actual database files.
    """
    from unittest.mock import Mock

    db = Mock()
    db.oversight_and_defaults = Mock()
    db.folders_table = Mock()
    db.emails_table = Mock()
    db.processed_files = Mock()
    db.settings = Mock()
    db.session_database = {}
    db.database_connection = Mock()

    # Setup common return values
    db.oversight_and_defaults.find_one.return_value = {
        "id": 1,
        "single_add_folder_prior": "/home",
        "batch_add_folder_prior": "/home",
        "logs_directory": "/tmp/logs",
        "errors_folder": "/tmp/errors",
        "enable_reporting": "False",
        "report_printing_fallback": "False",
    }

    db.folders_table.find.return_value = []
    db.folders_table.count.return_value = 0

    return db


@pytest.fixture
def sample_folders():
    """Provide sample folder data for testing."""
    return [
        {
            "id": 1,
            "alias": "Test Folder 1",
            "folder_name": "/test/folder1",
            "folder_is_active": "True",
        },
        {
            "id": 2,
            "alias": "Test Folder 2",
            "folder_name": "/test/folder2",
            "folder_is_active": "False",
        },
        {
            "id": 3,
            "alias": "Another Folder",
            "folder_name": "/test/folder3",
            "folder_is_active": "True",
        },
    ]


# Pytest markers for test categorization
def pytest_configure(config):
    """Register custom markers."""
    config.addinivalue_line("markers", "unit: mark test as a unit test")
    config.addinivalue_line("markers", "integration: mark test as an integration test")
    config.addinivalue_line("markers", "slow: mark test as slow running")
    config.addinivalue_line(
        "markers", "smoke: mark test as smoke test (quick production validation)"
    )
    config.addinivalue_line(
        "markers", "convert_backend: mark test as convert backend regression test"
    )
    config.addinivalue_line(
        "markers", "convert_smoke: mark test as quick convert backend smoke test"
    )
    config.addinivalue_line(
        "markers", "convert_parameters: mark test as convert parameter variation test"
    )
    config.addinivalue_line(
        "markers", "convert_integration: mark test as convert integration test"
    )
    config.addinivalue_line("markers", "qt: mark test as requiring PyQt6/Qt")
