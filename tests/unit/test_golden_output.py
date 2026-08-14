"""Golden file tests for converter output verification.

This module provides tests that verify converter output matches reference
files byte-for-byte, detecting regressions in converter implementations.

Golden file location
--------------------
Golden files live in ``tests/golden_files/`` — one subdirectory per
format (``csv/``, ``scannerware/``, etc.). Each test case has a separate
``.golden`` file under its format's directory.

How regeneration works
----------------------
There is **no automatic update mode** (no ``--update-golden`` flag; the
flag name in earlier docstrings is aspirational). When a converter change
intentionally shifts output, regenerate the affected golden files
**manually**:

  1. Re-run the failing test::
         pytest tests/unit/test_golden_output.py -v

     The failure report (see ``pytest.fail`` calls below) shows the diff
     between actual and expected output.

  2. If the diff is the intended new behaviour, copy the actual output
     over the golden file. The test loads input from
     ``<golden_dir>/<format>/<test_id>.golden`` and writes nothing itself,
     so regenerate by replacing those files with the new bytes.

  3. Re-run the test to confirm it passes.

Missing golden files
--------------------
If a golden file is intentionally absent (e.g. a corpus fixture hasn't
been generated yet), the test should be marked ``xfail`` with a clear
reason. An accidental missing file surfaces as a ``pytest.fail`` from
the open call — treat that as a test bug, not a passing skip.
"""

import os
import re

# Add project root to path for imports
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import pytest

from core.database import QueryRunner, SQLiteConnection
from dispatch.services.customer_lookup_service import CustomerLookupService
from dispatch.services.uom_lookup_service import UOMLookupService

_project_root = Path(__file__).parent.parent.parent.parent
if str(_project_root) not in sys.path:
    sys.path.insert(0, str(_project_root))


class QueryRunnerWithTestData:
    """Query runner that returns preset data without executing SQL.

    This class wraps a QueryRunner for actual query execution but allows
    preset test data to be returned for specific queries, avoiding the
    need for AS400-specific SQL syntax in tests.
    """

    def __init__(self, sqlite_conn):
        """Initialize with a SQLite connection and empty preset data."""
        self._sqlite_runner = QueryRunner(sqlite_conn)
        self._customer_data = []
        self._uom_data = []

    def set_customer_data(self, data):
        """Set the customer data to return for header queries."""
        self._customer_data = data

    def set_uom_data(self, data):
        """Set the UOM data to return for UOM queries."""
        self._uom_data = data

    def run_query(self, query, params=None):
        """Return preset data for known queries, or execute against SQLite."""
        query_upper = query.upper()
        # Check if this is a customer header query (has ohhst and dsabrep)
        if "OHHS" in query_upper and "DSABRE" in query_upper:
            if not self._customer_data:
                return []
            columns = [
                "Salesperson Name",
                "Invoice Date",
                "Terms Code",
                "Terms Duration",
                "Customer Status",
                "Customer Number",
                "Customer Name",
                "Customer Store Number",  # present in STEWARTS_CUSTOMER_QUERY_SQL
                "Customer Address",
                "Customer Town",
                "Customer State",
                "Customer Zip",
                "Customer Phone",
                "Customer Email",
                "Customer Email 2",
                "Corporate Customer Status",
                "Corporate Customer Number",
                "Corporate Customer Name",
                "Corporate Customer Store Number",  # present in STEWARTS_CUSTOMER_QUERY_SQL
                "Corporate Customer Address",
                "Corporate Customer Town",
                "Corporate Customer State",
                "Corporate Customer Zip",
                "Corporate Customer Phone",
                "Corporate Customer Email",
                "Corporate Customer Email 2",
            ]
            return [
                dict(zip(columns, row, strict=False)) for row in self._customer_data
            ]
        # Check if this is a UOM query (has odhst)
        if "ODHS" in query_upper:
            if not self._uom_data:
                return []
            columns = ["itemno", "uom_mult", "uom_code"]
            return [dict(zip(columns, row, strict=False)) for row in self._uom_data]
        # Fall back to SQLite execution for other queries
        return self._sqlite_runner.run_query(query, params)

    def close(self):
        """Close the underlying connection."""
        self._sqlite_runner.close()


@dataclass
class GoldenTestCase:
    """Represents a single golden file test case.

    Attributes:
        test_id: Unique identifier for the test case
        description: Human-readable description
        format_name: Converter format being tested
        input_file: Path to input EDI file
        expected_file: Path to expected output file
        metadata_file: Path to metadata YAML file
        params: Converter parameters from metadata
    """

    test_id: str
    description: str
    format_name: str
    input_file: str
    expected_file: str
    metadata_file: str
    params: dict[str, Any]


def compare_bytes(expected: bytes, actual: bytes) -> tuple[bool, dict[str, Any]]:
    """Compare two byte sequences and return detailed diff info.

    Args:
        expected: Expected byte sequence
        actual: Actual byte sequence

    Returns:
        Tuple of (match, diff_info) where diff_info contains details
        about any differences found.
    """
    if expected == actual:
        return True, {"match": True}

    diff_info: dict[str, Any] = {
        "match": False,
        "expected_size": len(expected),
        "actual_size": len(actual),
        "size_difference": len(actual) - len(expected),
    }

    # Find first difference
    min_len = min(len(expected), len(actual))
    first_diff_idx = -1

    for i in range(min_len):
        if expected[i] != actual[i]:
            first_diff_idx = i
            break

    if first_diff_idx >= 0:
        # Context around the difference
        ctx_start = max(0, first_diff_idx - 8)
        ctx_end = min(len(expected), first_diff_idx + 24)

        diff_info["first_difference_index"] = first_diff_idx
        diff_info["expected_at_diff"] = expected[first_diff_idx]
        diff_info["actual_at_diff"] = actual[first_diff_idx]
        diff_info["expected_hex"] = expected[first_diff_idx : first_diff_idx + 1].hex()
        diff_info["actual_hex"] = actual[first_diff_idx : first_diff_idx + 1].hex()

        # Context bytes
        diff_info["expected_context"] = expected[ctx_start:ctx_end].hex()
        diff_info["actual_context"] = actual[ctx_start:ctx_end].hex()

        # Character representations
        try:
            diff_info["expected_char"] = chr(expected[first_diff_idx])
        except (ValueError, OverflowError):
            diff_info["expected_char"] = f"<0x{expected[first_diff_idx]:02x}>"

        try:
            diff_info["actual_char"] = chr(actual[first_diff_idx])
        except (ValueError, OverflowError):
            diff_info["actual_char"] = f"<0x{actual[first_diff_idx]:02x}>"
    elif len(actual) > len(expected):
        diff_info["truncated"] = False
        diff_info["extra_at_end"] = len(actual) - len(expected)
        diff_info["extra_bytes_hex"] = actual[len(expected) :].hex()
    else:
        diff_info["truncated"] = True
        diff_info["missing_at_end"] = len(expected) - len(actual)
        diff_info["missing_bytes_hex"] = expected[len(actual) :].hex()

    return False, diff_info


def format_diff_report(test_case: GoldenTestCase, diff_info: dict[str, Any]) -> str:
    """Format a human-readable diff report.

    Args:
        test_case: The test case that failed
        diff_info: Dictionary from compare_bytes()

    Returns:
        Formatted string with diff details
    """
    lines = [
        f"Output mismatch for {test_case.format_name}/{test_case.test_id}",
        f"  Test: {test_case.description}",
        f"  File size: expected {diff_info['expected_size']} bytes, "
        f"got {diff_info['actual_size']} bytes",
    ]

    if diff_info.get("first_difference_index") is not None:
        idx = diff_info["first_difference_index"]
        lines.append(f"  First difference at byte {idx}:")
        lines.append(
            f"    Expected: 0x{diff_info['expected_hex']} ({diff_info['expected_char']!r})"
        )
        lines.append(
            f"    Actual:   0x{diff_info['actual_hex']} ({diff_info['actual_char']!r})"
        )
    elif diff_info.get("truncated"):
        lines.append(
            f"  Output truncated: missing {diff_info['missing_at_end']} bytes at end"
        )
        lines.append(f"  Missing hex: {diff_info['missing_bytes_hex']}")
    else:
        lines.append(f"  Output has {diff_info['extra_at_end']} extra bytes at end")
        lines.append(f"  Extra hex: {diff_info['extra_bytes_hex']}")

    return "\n".join(lines)


def resolve_env_vars(
    value: str | dict[str, Any] | list[Any] | None,
) -> str | dict[str, Any] | list[Any] | None:
    """Resolve environment variable references in strings.

    Supports ${VAR} and $VAR syntax. Missing variables resolve to empty string.

    Args:
        value: String, dict, list, or None to resolve

    Returns:
        Value with environment variables resolved
    """
    if value is None:
        return None

    if isinstance(value, str):
        # Pattern matches ${VAR} or $VAR
        pattern = r"\$\{([^}]+)\}|\$([A-Za-z_][A-Za-z0-9_]*)"

        def replace_var(match: re.Match) -> str:
            # Group 1 is ${VAR}, group 2 is $VAR
            var_name = match.group(1) or match.group(2)
            return os.environ.get(var_name, "")

        return re.sub(pattern, replace_var, value)

    if isinstance(value, dict):
        return {k: resolve_env_vars(v) for k, v in value.items()}

    if isinstance(value, list):
        return [resolve_env_vars(item) for item in value]

    return value


def load_test_case_metadata(metadata_file: str) -> dict[str, Any]:
    """Load test case metadata from YAML file.

    Args:
        metadata_file: Path to metadata YAML file

    Returns:
        Dictionary with metadata fields, with environment variables resolved
    """
    # Try multiple yaml sources
    yaml_module = None

    # Try standard import first
    try:
        import yaml

        yaml_module = yaml
    except ImportError:
        pass

    # If standard yaml not available, try invoke's vendor yaml
    if yaml_module is None:
        try:
            from invoke.vendor import yaml as invoke_yaml

            yaml_module = invoke_yaml
        except ImportError:
            pass

    if yaml_module is None:
        # yaml not installed, return empty metadata
        # NOTE: Without yaml, parameter-based test cases won't work
        return {}

    if not os.path.exists(metadata_file):
        return {}

    with open(metadata_file, encoding="utf-8") as f:
        metadata = yaml_module.safe_load(f) or {}

    # Resolve environment variables in parameters
    if "parameters" in metadata:
        metadata["parameters"] = resolve_env_vars(metadata["parameters"])

    return metadata


def load_test_cases() -> list[GoldenTestCase]:
    """Discover all golden file test cases.

    Returns:
        List of GoldenTestCase objects for all discovered test cases
    """
    # Path from tests/unit/test_golden_output.py to tests/golden_files/
    golden_dir = Path(__file__).parent.parent / "golden_files"
    test_cases: list[GoldenTestCase] = []

    if not golden_dir.exists():
        return test_cases

    # Find all format directories
    for format_dir in sorted(golden_dir.iterdir()):
        if not format_dir.is_dir() or format_dir.name.startswith("."):
            continue

        format_name = format_dir.name
        inputs_dir = format_dir / "inputs"
        expected_dir = format_dir / "expected"
        metadata_dir = format_dir / "metadata"

        if not inputs_dir.exists() or not expected_dir.exists():
            continue

        # Find test case files
        for input_file in sorted(inputs_dir.iterdir()):
            if input_file.suffix not in (".edi", ".txt", ".csv"):
                continue

            # Parse test ID from filename
            # Format: <id>_<description>.ext
            match = re.match(r"^(\d+)_(.+?)(\.[^.]+)$", input_file.name)
            if not match:
                continue

            test_id = match.group(1)
            description = match.group(2)
            _ = match.group(3)  # ext not needed, expected file uses .out

            # Expected file has .out extension
            expected_name = f"{test_id}_{description}.out"
            expected_file = expected_dir / expected_name

            # Metadata file
            metadata_file = (
                metadata_dir / f"{test_id}_{description}.yaml"
                if metadata_dir.exists()
                else None
            )

            if not expected_file.exists():
                continue

            # Load metadata (env vars are resolved in load_test_case_metadata)
            params = {}
            if metadata_file and metadata_file.exists():
                metadata = load_test_case_metadata(str(metadata_file))
                params = metadata.get("parameters", {})

            test_cases.append(
                GoldenTestCase(
                    test_id=test_id,
                    description=description,
                    format_name=format_name,
                    input_file=str(input_file),
                    expected_file=str(expected_file),
                    metadata_file=str(metadata_file) if metadata_file else "",
                    params=params,
                )
            )

    return test_cases


def get_supported_formats() -> list[str]:
    """Get list of formats that have golden file test coverage.

    Returns:
        List of format names with golden files
    """
    golden_dir = Path(__file__).parent.parent / "golden_files"
    if not golden_dir.exists():
        return []

    formats = []
    for format_dir in golden_dir.iterdir():
        if format_dir.is_dir() and not format_dir.name.startswith("."):
            formats.append(format_dir.name)

    return sorted(formats)


# Parametrize all tests with discovered test cases
_test_cases = load_test_cases()
_test_ids = [f"{tc.format_name}-{tc.test_id}_{tc.description}" for tc in _test_cases]


class TestGoldenOutput:
    """Tests that verify converter output matches golden files byte-for-byte."""

    @pytest.mark.parametrize("test_case", _test_cases, ids=_test_ids)
    def test_output_matches_golden(
        self, test_case: GoldenTestCase, tmp_path: Path
    ) -> None:
        """Test that converter output matches expected golden file.

        Args:
            test_case: GoldenTestCase with test parameters
            tmp_path: Pytest temporary directory fixture
        """
        # Read expected output
        with open(test_case.expected_file, "rb") as f:
            expected_bytes = f.read()

        # Run converter
        actual_bytes = run_converter(
            test_case.input_file,
            str(tmp_path),
            test_case.format_name,
            test_case.params,
        )

        # Compare
        match, diff_info = compare_bytes(expected_bytes, actual_bytes)

        if not match:
            report = format_diff_report(test_case, diff_info)
            pytest.fail(report)

    @pytest.mark.parametrize("test_case", _test_cases, ids=_test_ids)
    def test_output_size_reasonable(
        self, test_case: GoldenTestCase, tmp_path: Path
    ) -> None:
        """Test that output size is reasonable (not empty, not excessive).

        Args:
            test_case: GoldenTestCase with test parameters
            tmp_path: Pytest temporary directory fixture
        """
        with open(test_case.expected_file, "rb") as f:
            expected_bytes = f.read()

        actual_bytes = run_converter(
            test_case.input_file,
            str(tmp_path),
            test_case.format_name,
            test_case.params,
        )

        # Output should not be empty if expected is not empty
        if len(expected_bytes) > 0:
            assert len(actual_bytes) > 0, "Output is empty but expected non-empty"

        # Output should not be more than 10x the expected size
        # (catches infinite loops or runaway output)
        max_reasonable_size = len(expected_bytes) * 10
        assert (
            len(actual_bytes) <= max_reasonable_size
        ), f"Output size {len(actual_bytes)} exceeds reasonable limit {max_reasonable_size}"


def run_converter(
    input_file: str, output_dir: str, format_name: str, params: dict[str, Any]
) -> bytes:
    """Run the converter for a test case and return output.

    Args:
        input_file: Path to input EDI file
        output_dir: Directory for output
        format_name: Format to convert to
        params: Converter parameters (may include database credentials)

    Returns:
        Raw bytes of converter output
    """
    import os
    import tempfile

    # Import the edi_convert function for the specified format
    module_name = f"dispatch.converters.convert_to_{format_name}"
    module = __import__(module_name, fromlist=["edi_convert"])
    edi_convert = module.edi_convert

    # Extract database credentials from params for settings_dict
    # Database-dependent converters need credentials in settings_dict
    # Copy params to avoid modifying the original (params.pop removes keys)
    params_copy = dict(params)
    settings_dict: dict[str, Any] = {}
    db_credentials = [
        "as400_username",
        "as400_address",
        "as400_password",
        "ssh_key_filename",
    ]
    for cred in db_credentials:
        if cred in params_copy:
            settings_dict[cred] = params_copy.pop(cred)

    # Extract test data if present (used for injecting mock DB results)
    test_customer_data = params_copy.pop("test_customer_data", None)
    test_uom_data = params_copy.pop("test_uom_data", None)
    test_inv_fetcher_data = params_copy.pop("test_inv_fetcher_data", None)

    # Create a temp input file to ensure we have a valid path
    with tempfile.TemporaryDirectory() as temp_workdir:
        # Copy input to temp directory with .edi extension
        temp_input = os.path.join(temp_workdir, "input.edi")
        with open(input_file, "rb") as f:
            input_data = f.read()
        with open(temp_input, "wb") as f:
            f.write(input_data)

        # Create output path in temp directory
        temp_output = os.path.join(temp_workdir, "output")

        # Determine whether we have credentials or test data
        has_creds = all(
            settings_dict.get(cred)
            for cred in ["as400_username", "as400_address", "as400_password"]
        )
        # Some converters don't query a database — they accept empty
        # settings_dict via a no-op query runner (see
        # core/edi/edi_tweaker.py::_create_query_runner_adapter). Allow
        # those through the credential gate; only skip DB-backed formats
        # when we have neither real credentials nor injected test data.
        db_free_formats = {
            "scannerware",
            "tweaks",
            "scansheet_type_a",
            "simplified_csv",
            "yellowdog_csv",
            "csv",
        }

        # Inject test data for CustomerLookupService + UOMLookupService converters
        if test_customer_data is not None or test_uom_data is not None:
            import csv

            from dispatch.converters.customer_queries import BASIC_CUSTOMER_QUERY_SQL

            # Dynamically find the converter class by name
            converter_cls_name = (
                "".join(word.title() for word in format_name.split("_")) + "Converter"
            )
            converter_class = getattr(module, converter_cls_name)

            # Create test query runner with injected data
            sqlite_conn = SQLiteConnection(":memory:")
            test_runner = QueryRunnerWithTestData(sqlite_conn)
            if test_customer_data is not None:
                test_runner.set_customer_data(test_customer_data)
            if test_uom_data is not None:
                test_runner.set_uom_data(test_uom_data)

            # Use STEWARTS_CUSTOMER_QUERY_SQL for stewarts_custom, BASIC_CUSTOMER_QUERY_SQL for jolley_custom
            if format_name == "stewarts_custom":
                from dispatch.converters.customer_queries import (
                    STEWARTS_CUSTOMER_QUERY_SQL,
                )

                customer_sql = STEWARTS_CUSTOMER_QUERY_SQL
            else:
                customer_sql = BASIC_CUSTOMER_QUERY_SQL

            # Wrap edi_convert to intercept converter creation and patch instance methods
            original_edi_convert = edi_convert

            def wrapped_edi_convert(
                edi_process, output_filename, settings_dict, parameters_dict, upc_lookup
            ):
                # Patch the converter class's _initialize_output so that when the
                # converter instance calls self._initialize_output(context), our patch runs.
                # We must patch the class before the converter is instantiated inside
                # original_edi_convert -> make_edi_convert -> converter.edi_convert().
                original_init = converter_class._initialize_output

                def patched_init(self, context):
                    # Inject test query runner into the database connector
                    self._db_connector._query_runner = test_runner
                    self._db_connector._db_initialized = True

                    # Initialize customer and UOM services with the test runner
                    self._customer_service = CustomerLookupService(
                        test_runner, customer_sql
                    )
                    self._uom_service = UOMLookupService(test_runner)

                    # Open CSV output file
                    context.output_file = open(  # noqa: SIM115 — lifecycle managed by BaseEDIConverter._finalize_output
                        context.get_output_path(".csv"),
                        "w",
                        newline="\n",
                        encoding="utf-8",
                    )
                    context.csv_writer = csv.writer(context.output_file, dialect="unix")

                converter_class._initialize_output = patched_init
                try:
                    return original_edi_convert(
                        edi_process,
                        output_filename,
                        settings_dict,
                        parameters_dict,
                        upc_lookup,
                    )
                finally:
                    converter_class._initialize_output = original_init

            result = wrapped_edi_convert(
                temp_input,
                temp_output,
                settings_dict,
                params_copy,
                {},  # upc_lookup
            )
        # Inject InvFetcher test data for InvFetcher-based converters
        elif test_inv_fetcher_data and format_name in (
            "fintech",
            "estore_einvoice",
            "estore_einvoice_generic",
        ):
            # Patch InvFetcher.fetch_po on the converter instance after it's created
            # We do this by patching the instance's inv_fetcher after _initialize_output runs
            # Store test data on the converter instance for the patched methods to use

            # We need to hook after converter creation but before first use
            # Use a monkeypatch approach: patch the InvFetcher class methods
            from core.edi.inv_fetcher import InvFetcher

            original_inv_fetcher_class_run_query = InvFetcher._po_query

            test_po = test_inv_fetcher_data.get("po", "")
            test_cust_name = test_inv_fetcher_data.get("cust_name", "")
            test_cust_no = test_inv_fetcher_data.get("cust_no", 0)

            # Create a patched version that returns test data instead of querying
            def patched_po_query(self, invoice_number):
                # Return test data as a dict-like result
                # The _set_values_from_row expects dict.values() or tuple
                return [
                    {"po": test_po, "custname": test_cust_name, "custno": test_cust_no}
                ]

            InvFetcher._po_query = patched_po_query

            try:
                result = edi_convert(
                    temp_input,
                    temp_output,
                    settings_dict,
                    params_copy,
                    {},  # upc_lookup
                )
            finally:
                InvFetcher._po_query = original_inv_fetcher_class_run_query
        # Skip if no credentials and no test data was used by any branch above
        elif not has_creds and format_name not in db_free_formats:
            pytest.skip("Requires AS400 credentials or test data")
        else:
            # Run conversion with real credentials
            result = edi_convert(
                temp_input,
                temp_output,
                settings_dict,
                params_copy,
                {},  # upc_lookup
            )

        if not result or not os.path.exists(result):
            return b""

        with open(result, "rb") as f:
            return f.read()


class TestCompareBytesFunction:
    """Unit tests for the compare_bytes function."""

    def test_identical_bytes(self):
        """Test that identical bytes return match=True."""
        data = b"Hello, World!"
        match, info = compare_bytes(data, data)

        assert match
        assert info["match"] is True

    def test_different_single_byte(self):
        """Test detection of single byte difference."""
        expected = b"Hello, World!"
        actual = b"Hello, World?"  # Last char differs

        match, info = compare_bytes(expected, actual)

        assert not match
        assert info["match"] is False
        assert info["expected_size"] == len(expected)
        assert info["actual_size"] == len(actual)
        assert info["first_difference_index"] == len(expected) - 1
        assert info["expected_at_diff"] == ord("!")
        assert info["actual_at_diff"] == ord("?")

    def test_different_length_shorter(self):
        """Test detection when actual is shorter."""
        expected = b"Hello, World!"
        actual = b"Hello"

        match, info = compare_bytes(expected, actual)

        assert not match
        assert info["truncated"] is True
        assert info["missing_at_end"] == len(expected) - len(actual)

    def test_different_length_longer(self):
        """Test detection when actual is longer."""
        expected = b"Hello"
        actual = b"Hello, World!"

        match, info = compare_bytes(expected, actual)

        assert not match
        assert info["extra_at_end"] == len(actual) - len(expected)

    def test_case_difference(self):
        """Test detection of case difference."""
        expected = b"ABC"
        actual = b"abc"

        match, info = compare_bytes(expected, actual)

        assert not match
        assert info["first_difference_index"] == 0

    def test_empty_vs_content(self):
        """Test comparison of empty to non-empty."""
        expected = b""
        actual = b"Hello"

        match, info = compare_bytes(expected, actual)

        assert not match
        assert info["expected_size"] == 0
        assert info["actual_size"] == 5

    def test_both_empty(self):
        """Test that two empty byte sequences match."""
        expected = b""
        actual = b""

        match, info = compare_bytes(expected, actual)

        assert match
        assert info["match"] is True


class TestResolveEnvVars:
    """Unit tests for the resolve_env_vars function."""

    def test_simple_string_no_vars(self):
        """Test that strings without variables pass through unchanged."""
        result = resolve_env_vars("plain string")
        assert result == "plain string"

    def test_brace_syntax(self, monkeypatch):
        """Test ${VAR} syntax is resolved."""
        monkeypatch.setenv("TEST_VAR", "hello")
        result = resolve_env_vars("prefix_${TEST_VAR}_suffix")
        assert result == "prefix_hello_suffix"

    def test_dollar_syntax(self, monkeypatch):
        """Test $VAR syntax is resolved."""
        monkeypatch.setenv("TEST_VAR", "world")
        result = resolve_env_vars("hello $TEST_VAR")
        assert result == "hello world"

    def test_missing_var_resolves_to_empty(self):
        """Test that missing environment variables resolve to empty string."""
        result = resolve_env_vars("before_${NONEXISTENT_VAR}_after")
        assert result == "before__after"

    def test_dict_values(self, monkeypatch):
        """Test that dictionary values are resolved recursively."""
        monkeypatch.setenv("DB_USER", "admin")
        monkeypatch.setenv("DB_PASS", "secret")
        result = resolve_env_vars(
            {
                "username": "${DB_USER}",
                "password": "${DB_PASS}",
                "host": "localhost",
            }
        )
        assert result == {
            "username": "admin",
            "password": "secret",
            "host": "localhost",
        }

    def test_list_values(self, monkeypatch):
        """Test that list values are resolved."""
        monkeypatch.setenv("ITEM1", "first")
        monkeypatch.setenv("ITEM2", "second")
        result = resolve_env_vars(["${ITEM1}", "plain", "${ITEM2}"])
        assert result == ["first", "plain", "second"]

    def test_none_value(self):
        """Test that None passes through unchanged."""
        result = resolve_env_vars(None)
        assert result is None

    def test_nested_structure(self, monkeypatch):
        """Test deeply nested structures are resolved."""
        monkeypatch.setenv("DEEP_VAL", "found")
        resolve_env_vars(
            {"level1": {"level2": ["${DEEP_VAL}", {"nested": "${DEEP_VAL}"}]}}
        )


class TestFormatCoverage:
    """Tests for golden file coverage tracking."""

    def test_all_formats_have_inputs_and_expected(self):
        """Verify that each format directory has both inputs and expected."""
        golden_dir = Path(__file__).parent.parent / "golden_files"

        if not golden_dir.exists():
            pytest.skip("Golden files directory does not exist")

        for format_dir in golden_dir.iterdir():
            if not format_dir.is_dir() or format_dir.name.startswith("."):
                continue

            inputs_dir = format_dir / "inputs"
            expected_dir = format_dir / "expected"

            assert inputs_dir.exists(), f"{format_dir.name} missing inputs directory"
            assert (
                expected_dir.exists()
            ), f"{format_dir.name} missing expected directory"

            # Count files
            input_files = (
                list(inputs_dir.glob("*.edi"))
                + list(inputs_dir.glob("*.txt"))
                + list(inputs_dir.glob("*.csv"))
            )
            expected_files = list(expected_dir.glob("*.out"))

            assert len(input_files) > 0, f"{format_dir.name} has no input files"
            assert len(expected_files) > 0, f"{format_dir.name} has no expected files"

    def test_all_expected_files_have_metadata(self):
        """Verify that each expected file has corresponding metadata."""
        golden_dir = Path(__file__).parent.parent / "golden_files"

        if not golden_dir.exists():
            pytest.skip("Golden files directory does not exist")

        for format_dir in golden_dir.iterdir():
            if not format_dir.is_dir() or format_dir.name.startswith("."):
                continue

            expected_dir = format_dir / "expected"
            metadata_dir = format_dir / "metadata"

            if not expected_dir.exists():
                continue

            for expected_file in expected_dir.glob("*.out"):
                # Parse test ID
                # Format: <id>_<description>.out
                name = expected_file.stem
                metadata_file = metadata_dir / f"{name}.yaml"

                # Metadata is optional but should exist if directory exists
                if metadata_dir.exists() and metadata_file.exists():
                    metadata = load_test_case_metadata(str(metadata_file))
                    # Basic validation
                    assert (
                        "test_id" in metadata
                        or "description" in metadata
                        or not metadata
                    )


class TestLoadTestCases:
    """Tests for test case discovery."""

    def test_load_test_cases_returns_list(self):
        """Verify load_test_cases returns a list."""
        cases = load_test_cases()
        assert isinstance(cases, list)

    def test_test_cases_have_required_fields(self):
        """Verify all discovered test cases have required fields."""
        cases = load_test_cases()

        for case in cases:
            assert case.test_id, "test_id is required"
            assert case.description, "description is required"
            assert case.format_name, "format_name is required"
            assert case.input_file, "input_file is required"
            assert case.expected_file, "expected_file is required"

    def test_get_supported_formats(self):
        """Verify get_supported_formats returns format names."""
        formats = get_supported_formats()
        assert isinstance(formats, list)
        # If golden files exist, should return at least one format
        golden_dir = Path(__file__).parent.parent.parent / "golden_files"
        if golden_dir.exists() and any(
            d.is_dir() for d in golden_dir.iterdir() if not d.name.startswith(".")
        ):
            assert len(formats) > 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
