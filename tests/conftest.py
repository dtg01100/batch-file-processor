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


# Pytest markers for test categorization
def pytest_configure(config):
    """Register custom markers."""
    config.addinivalue_line(
        "markers", "unit: mark test as a unit test"
    )
    config.addinivalue_line(
        "markers", "integration: mark test as an integration test"
    )
    config.addinivalue_line(
        "markers", "slow: mark test as slow running"
    )
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
