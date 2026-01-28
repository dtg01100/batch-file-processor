"""
Smoke tests for batch-file-processor - quick validation of current production state.

These tests perform quick validation to ensure the system is in a working state.
They should run quickly and catch major issues.
"""

import pytest
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import utils
import record_error


@pytest.mark.smoke
class TestUtilityFunctionsAvailable:
    """Verify all utility functions are available and callable."""

    def test_utils_module_loads(self):
        """Utils module can be imported."""
        assert hasattr(utils, "dac_str_int_to_int")
        assert hasattr(utils, "convert_to_price")
        assert hasattr(utils, "dactime_from_datetime")
        assert hasattr(utils, "datetime_from_dactime")
        assert hasattr(utils, "datetime_from_invtime")
        assert hasattr(utils, "calc_check_digit")
        assert hasattr(utils, "convert_UPCE_to_UPCA")

    def test_dac_str_int_to_int_callable(self):
        """dac_str_int_to_int function is callable."""
        result = utils.dac_str_int_to_int("100")
        assert isinstance(result, int)

    def test_convert_to_price_callable(self):
        """convert_to_price function is callable."""
        result = utils.convert_to_price("1000")
        assert isinstance(result, str)
        assert "." in result

    def test_datetime_conversions_callable(self):
        """DateTime conversion functions are callable."""
        from datetime import datetime

        dt = datetime.now()
        result = utils.dactime_from_datetime(dt)
        assert isinstance(result, str)

    def test_calc_check_digit_callable(self):
        """calc_check_digit function is callable."""
        result = utils.calc_check_digit("12345678901")
        assert isinstance(result, int)

    def test_convert_upce_to_upca_callable(self):
        """convert_UPCE_to_UPCA function is callable."""
        result = utils.convert_UPCE_to_UPCA("01234567")
        assert isinstance(result, str)
        assert len(result) == 12


@pytest.mark.smoke
class TestRecordErrorAvailable:
    """Verify record_error module is available."""

    def test_record_error_module_loads(self):
        """Record error module can be imported."""
        assert hasattr(record_error, "do")

    def test_record_error_do_callable(self):
        """record_error.do function is callable."""
        from io import StringIO, BytesIO

        run_log = BytesIO()
        errors_log = StringIO()

        # Should not raise any exception
        record_error.do(run_log, errors_log, "test", "test.txt", "test_module")
        assert run_log.getvalue() != b""


@pytest.mark.smoke
def test_basic_project_structure():
    """Verify basic project structure is intact."""
    project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

    assert os.path.exists(os.path.join(project_root, "utils.py"))
    assert os.path.exists(os.path.join(project_root, "record_error.py"))
    assert os.path.exists(os.path.join(project_root, "interface"))
    assert os.path.exists(os.path.join(project_root, "interface", "main.py"))


@pytest.mark.smoke
def test_tests_directory_structure():
    """Verify tests directory structure is in place."""
    test_root = os.path.dirname(os.path.abspath(__file__))

    # Check for test directories
    assert os.path.exists(os.path.join(test_root, "unit"))
    assert os.path.exists(os.path.join(test_root, "integration"))
    assert os.path.exists(os.path.join(test_root, "conftest.py"))
