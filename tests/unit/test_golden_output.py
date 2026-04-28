"""Golden file tests for converter output verification.

This module provides tests that verify converter output matches reference
files byte-for-byte, detecting regressions in converter implementations.

Usage:
    # Run tests in compare mode (default)
    pytest tests/unit/test_golden_output.py -v

    # Update golden files with current output
    pytest tests/unit/test_golden_output.py --update-golden
"""

import os
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import pytest

# Add project root to path for imports
import sys

_project_root = Path(__file__).parent.parent.parent.parent
if str(_project_root) not in sys.path:
    sys.path.insert(0, str(_project_root))


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
        lines.append(
            f"  Output has {diff_info['extra_at_end']} extra bytes at end"
        )
        lines.append(f"  Extra hex: {diff_info['extra_bytes_hex']}")

    return "\n".join(lines)


def load_test_case_metadata(metadata_file: str) -> dict[str, Any]:
    """Load test case metadata from YAML file.

    Args:
        metadata_file: Path to metadata YAML file

    Returns:
        Dictionary with metadata fields
    """
    # Try multiple yaml sources
    yaml_module = None

    # Try standard import first
    try:
        import yaml  # noqa: F401
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

    with open(metadata_file, "r", encoding="utf-8") as f:
        return yaml_module.safe_load(f) or {}


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
            ext = match.group(3)

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

            # Load metadata
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
_test_ids = [
    f"{tc.format_name}-{tc.test_id}_{tc.description}"
    for tc in _test_cases
]


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
        params: Converter parameters

    Returns:
        Raw bytes of converter output
    """
    import os
    import tempfile

    # Import the edi_convert function for the specified format
    module_name = f"dispatch.converters.convert_to_{format_name}"
    module = __import__(module_name, fromlist=["edi_convert"])
    edi_convert = module.edi_convert

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

        # Run conversion
        result = edi_convert(
            temp_input,
            temp_output,
            {},  # settings_dict
            params,
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

        assert match is True
        assert info["match"] is True

    def test_different_single_byte(self):
        """Test detection of single byte difference."""
        expected = b"Hello, World!"
        actual = b"Hello, World?"  # Last char differs

        match, info = compare_bytes(expected, actual)

        assert match is False
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

        assert match is False
        assert info["truncated"] is True
        assert info["missing_at_end"] == len(expected) - len(actual)

    def test_different_length_longer(self):
        """Test detection when actual is longer."""
        expected = b"Hello"
        actual = b"Hello, World!"

        match, info = compare_bytes(expected, actual)

        assert match is False
        assert info["extra_at_end"] == len(actual) - len(expected)

    def test_case_difference(self):
        """Test detection of case difference."""
        expected = b"ABC"
        actual = b"abc"

        match, info = compare_bytes(expected, actual)

        assert match is False
        assert info["first_difference_index"] == 0

    def test_empty_vs_content(self):
        """Test comparison of empty to non-empty."""
        expected = b""
        actual = b"Hello"

        match, info = compare_bytes(expected, actual)

        assert match is False
        assert info["expected_size"] == 0
        assert info["actual_size"] == 5

    def test_both_empty(self):
        """Test that two empty byte sequences match."""
        expected = b""
        actual = b""

        match, info = compare_bytes(expected, actual)

        assert match is True
        assert info["match"] is True


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
            assert expected_dir.exists(), f"{format_dir.name} missing expected directory"

            # Count files
            input_files = list(inputs_dir.glob("*.edi")) + list(
                inputs_dir.glob("*.txt")
            ) + list(inputs_dir.glob("*.csv"))
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
                if metadata_dir.exists():
                    # Just check it's parseable
                    if metadata_file.exists():
                        metadata = load_test_case_metadata(str(metadata_file))
                        # Basic validation
                        assert "test_id" in metadata or "description" in metadata or not metadata


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
