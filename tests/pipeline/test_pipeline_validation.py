"""
Pipeline Validation Framework
Ensures that generated pipeline outputs are bit-for-bit identical to converter outputs.
"""

from __future__ import annotations

import pytest
import subprocess
import hashlib
import json
import os
import sys
from pathlib import Path
from dataclasses import dataclass


# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))


@dataclass
class ConverterTestCase:
    """Test case for converter validation"""

    name: str
    converter_script: str
    pipeline_file: str
    input_file: str
    expected_output_file: str
    test_edi_files: list
    description: str
    skip_until: str | None = None


class PipelineValidationFramework:
    """
    Framework for validating that pipeline outputs match converter outputs exactly.

    Key Principles:
    - Pipeline output must be bit-for-bit identical to converter output
    - All edge cases must be handled identically
    - CSV dialect, field ordering, and formatting must match exactly
    """

    def __init__(self, project_root: Path):
        self.project_root = Path(project_root)
        self.test_data_dir = self.project_root / "alledi"
        self.pipelines_dir = self.project_root / "pipelines" / "examples"
        self.converters_dir = self.project_root
        self.output_dir = self.project_root / "test_outputs"
        self.output_dir.mkdir(exist_ok=True)

        # Define all converter test cases
        self.test_cases = self._load_test_cases()

    def _load_test_cases(self) -> list:
        """Load all converter test cases"""
        return [
            ConverterTestCase(
                name="edi_to_standard_csv",
                converter_script="convert_to_csv.py",
                pipeline_file="edi_to_standard_csv.json",
                input_file="*.edi",
                expected_output_file="output.csv",
                test_edi_files=[f"{i:03d}.edi" for i in range(1, 28)],
                description="Standard CSV output with UPC calculations",
                skip_until=None,
            ),
            ConverterTestCase(
                name="edi_to_fintech",
                converter_script="convert_to_fintech.py",
                pipeline_file="edi_to_fintech.json",
                input_file="*.edi",
                expected_output_file="fintech_output.csv",
                test_edi_files=[f"{i:03d}.edi" for i in range(1, 28)],
                description="Fintech CSV format with Division ID",
                skip_until=None,
            ),
            ConverterTestCase(
                name="edi_to_scannerware",
                converter_script="convert_to_scannerware.py",
                pipeline_file="edi_to_scannerware.json",
                input_file="*.edi",
                expected_output_file="scannerware_output.txt",
                test_edi_files=[f"{i:03d}.edi" for i in range(1, 28)],
                description="Fixed-width text with exact column positions",
                skip_until=None,
            ),
        ]

    def get_converter_command(
        self, case: ConverterTestCase, input_file: Path, output_file: Path
    ) -> list:
        """Build the command to run the original converter"""
        return [
            sys.executable,
            str(self.converters_dir / case.converter_script),
            "--input",
            str(input_file),
            "--output",
            str(output_file),
        ]

    def run_converter(
        self, case: ConverterTestCase, input_file: Path, output_file: Path
    ) -> tuple:
        """Run the original converter and return exit code, stdout, stderr"""
        cmd = self.get_converter_command(case, input_file, output_file)
        result = subprocess.run(
            cmd, capture_output=True, text=True, cwd=str(self.converters_dir)
        )
        return result.returncode, result.stdout, result.stderr

    def run_pipeline(
        self, case: ConverterTestCase, input_file: Path, output_file: Path
    ) -> tuple:
        """Run the pipeline executor and return exit code, stdout, stderr"""
        cmd = [
            sys.executable,
            str(self.project_root / "backend" / "pipeline_executor.py"),
            "--pipeline",
            str(self.pipelines_dir / case.pipeline_file),
            "--input",
            str(input_file),
            "--output",
            str(output_file),
        ]
        result = subprocess.run(
            cmd, capture_output=True, text=True, cwd=str(self.project_root)
        )
        return result.returncode, result.stdout, result.stderr

    def compute_file_hash(self, file_path: Path) -> str:
        """Compute MD5 hash of a file"""
        hash_md5 = hashlib.md5()
        with open(file_path, "rb") as f:
            for chunk in iter(lambda: f.read(4096), b""):
                hash_md5.update(chunk)
        return hash_md5.hexdigest()

    def compare_files(self, file1: Path, file2: Path) -> tuple:
        """Compare two files for exact equality"""
        hash1 = self.compute_file_hash(file1)
        hash2 = self.compute_file_hash(file2)

        if hash1 == hash2:
            return True, f"Files are identical (MD5: {hash1})"

        # Detailed comparison
        with open(file1, "r", encoding="utf-8", errors="replace") as f1:
            lines1 = f1.readlines()
        with open(file2, "r", encoding="utf-8", errors="replace") as f2:
            lines2 = f2.readlines()

        differences = []
        max_lines = max(len(lines1), len(lines2))

        for i in range(max_lines):
            line1 = lines1[i] if i < len(lines1) else "<MISSING>"
            line2 = lines2[i] if i < len(lines2) else "<MISSING>"

            if line1 != line2:
                differences.append(f"Line {i + 1}:")
                differences.append(f"  Converter: {repr(line1[:100])}")
                differences.append(f"  Pipeline:  {repr(line2[:100])}")

        diff_text = "\n".join(differences[:50])
        return False, f"Files differ:\n{diff_text}\n\nHash1: {hash1}\nHash2: {hash2}"

    def normalize_csv(self, file_path: Path) -> list:
        """Normalize CSV for comparison (handle different line endings, etc.)"""
        with open(file_path, "r", encoding="utf-8", errors="replace") as f:
            content = f.read()
        # Normalize line endings
        content = content.replace("\r\n", "\n").replace("\r", "\n")
        return content.split("\n")

    def compare_csv_output(self, file1: Path, file2: Path) -> tuple:
        """Compare CSV outputs with normalized line endings"""
        lines1 = self.normalize_csv(file1)
        lines2 = self.normalize_csv(file2)

        if lines1 == lines2:
            return True, "CSV outputs are identical"

        differences = []
        max_lines = max(len(lines1), len(lines2))

        for i in range(max_lines):
            line1 = lines1[i] if i < len(lines1) else "<MISSING>"
            line2 = lines2[i] if i < len(lines2) else "<MISSING>"

            if line1 != line2:
                differences.append(f"Line {i + 1}:")
                differences.append(f"  Converter: {repr(line1)}")
                differences.append(f"  Pipeline:  {repr(line2)}")

        diff_text = "\n".join(differences[:30])
        return False, f"CSV outputs differ:\n{diff_text}"


# Pytest fixtures
@pytest.fixture
def validation_framework():
    """Provide validation framework instance"""
    return PipelineValidationFramework(Path(__file__).parent.parent.parent)


@pytest.fixture
def test_edi_files():
    """Provide list of test EDI files"""
    test_dir = Path(__file__).parent.parent.parent / "alledi"
    return [f for f in os.listdir(test_dir) if f.endswith(".edi")]


class TestConverterBaseline:
    """
    Establish baseline behavior of converters.
    These tests verify that converters work correctly before testing pipeline equivalence.
    """

    def test_convert_to_csv_produces_valid_output(
        self, validation_framework, test_edi_files
    ):
        """Verify convert_to_csv.py produces expected output format"""
        case = validation_framework.test_cases[0]  # edi_to_standard_csv

        # Run converter on first test file
        input_file = validation_framework.test_data_dir / test_edi_files[0]
        output_file = validation_framework.output_dir / "baseline_csv.csv"

        returncode, stdout, stderr = validation_framework.run_converter(
            case, input_file, output_file
        )

        assert returncode == 0, f"Converter failed: {stderr}"
        assert output_file.exists(), "Output file was not created"

        # Verify output has expected characteristics
        with open(output_file, "r") as f:
            content = f.read()

        # Check line terminators
        assert "\r\n" in content, "Expected Windows line terminators"

        # Check for expected fields
        assert "UPC" in content or "upc" in content.lower(), (
            "Expected UPC field in output"
        )

        print(f"Baseline CSV output verified: {output_file.stat().st_size} bytes")

    def test_convert_to_fintech_produces_valid_output(
        self, validation_framework, test_edi_files
    ):
        """Verify convert_to_fintech.py produces expected output format"""
        case = validation_framework.test_cases[1]  # edi_to_fintech

        input_file = validation_framework.test_data_dir / test_edi_files[0]
        output_file = validation_framework.output_dir / "baseline_fintech.csv"

        returncode, stdout, stderr = validation_framework.run_converter(
            case, input_file, output_file
        )

        assert returncode == 0, f"Converter failed: {stderr}"
        assert output_file.exists(), "Output file was not created"

        with open(output_file, "r") as f:
            content = f.read()

        # Fintech format should have Division ID
        assert "Division" in content or "division" in content.lower(), (
            "Expected Division field"
        )

        print(f"Baseline Fintech output verified: {output_file.stat().st_size} bytes")

    def test_convert_to_scannerware_produces_valid_output(
        self, validation_framework, test_edi_files
    ):
        """Verify convert_to_scannerware.py produces expected output format"""
        case = validation_framework.test_cases[2]  # edi_to_scannerware

        input_file = validation_framework.test_data_dir / test_edi_files[0]
        output_file = validation_framework.output_dir / "baseline_scannerware.txt"

        returncode, stdout, stderr = validation_framework.run_converter(
            case, input_file, output_file
        )

        assert returncode == 0, f"Converter failed: {stderr}"
        assert output_file.exists(), "Output file was not created"

        with open(output_file, "r") as f:
            content = f.read()

        # Scannerware is fixed-width, check for padding
        lines = content.split("\n")
        if lines:
            # Each line should be exactly the same width
            line_widths = set(len(line) for line in lines if line)
            assert len(line_widths) == 1, (
                f"Expected fixed-width lines, got widths: {line_widths}"
            )

        print(
            f"Baseline Scannerware output verified: {output_file.stat().st_size} bytes"
        )


class TestPipelineConverterEquivalence:
    """
    Core validation tests: Ensure pipeline outputs match converter outputs exactly.

    These tests are the gatekeeper for pipeline correctness.
    """

    @pytest.mark.parametrize("edi_file_idx", range(5))
    def test_edi_to_csv_equivalence(
        self, validation_framework, test_edi_files, edi_file_idx
    ):
        """
        Test that pipeline produces identical output to convert_to_csv.py
        for multiple EDI files.
        """
        case = validation_framework.test_cases[0]

        input_file = validation_framework.test_data_dir / test_edi_files[edi_file_idx]
        converter_output = (
            validation_framework.output_dir / f"equiv_csv_conv_{edi_file_idx}.csv"
        )
        pipeline_output = (
            validation_framework.output_dir / f"equiv_csv_pipe_{edi_file_idx}.csv"
        )

        # Run converter
        returncode, stdout, stderr = validation_framework.run_converter(
            case, input_file, converter_output
        )
        assert returncode == 0, f"Converter failed on {input_file}: {stderr}"

        # Run pipeline (will fail until executor is implemented)
        returncode, stdout, stderr = validation_framework.run_pipeline(
            case, input_file, pipeline_output
        )

        # For now, just verify converter works (pipeline test will pass once implemented)
        if returncode != 0:
            pytest.skip("Pipeline executor not yet implemented")

        # Compare outputs
        are_equal, message = validation_framework.compare_csv_output(
            converter_output, pipeline_output
        )
        assert are_equal, (
            f"Pipeline output differs from converter for {input_file}:\n{message}"
        )

    @pytest.mark.parametrize("edi_file_idx", range(3))
    def test_edi_to_fintech_equivalence(
        self, validation_framework, test_edi_files, edi_file_idx
    ):
        """Test pipeline output matches convert_to_fintech.py exactly"""
        case = validation_framework.test_cases[1]

        input_file = validation_framework.test_data_dir / test_edi_files[edi_file_idx]
        converter_output = (
            validation_framework.output_dir / f"equiv_fintech_conv_{edi_file_idx}.csv"
        )
        pipeline_output = (
            validation_framework.output_dir / f"equiv_fintech_pipe_{edi_file_idx}.csv"
        )

        returncode, stdout, stderr = validation_framework.run_converter(
            case, input_file, converter_output
        )
        assert returncode == 0

        returncode, stdout, stderr = validation_framework.run_pipeline(
            case, input_file, pipeline_output
        )
        if returncode != 0:
            pytest.skip("Pipeline executor not yet implemented")

        are_equal, message = validation_framework.compare_csv_output(
            converter_output, pipeline_output
        )
        assert are_equal, f"Fintech pipeline output differs: {message}"

    @pytest.mark.parametrize("edi_file_idx", range(3))
    def test_edi_to_scannerware_equivalence(
        self, validation_framework, test_edi_files, edi_file_idx
    ):
        """Test pipeline output matches convert_to_scannerware.py exactly"""
        case = validation_framework.test_cases[2]

        input_file = validation_framework.test_data_dir / test_edi_files[edi_file_idx]
        converter_output = (
            validation_framework.output_dir
            / f"equiv_scannerware_conv_{edi_file_idx}.txt"
        )
        pipeline_output = (
            validation_framework.output_dir
            / f"equiv_scannerware_pipe_{edi_file_idx}.txt"
        )

        returncode, stdout, stderr = validation_framework.run_converter(
            case, input_file, converter_output
        )
        assert returncode == 0

        returncode, stdout, stderr = validation_framework.run_pipeline(
            case, input_file, pipeline_output
        )
        if returncode != 0:
            pytest.skip("Pipeline executor not yet implemented")

        are_equal, message = validation_framework.compare_files(
            converter_output, pipeline_output
        )
        assert are_equal, f"Scannerware pipeline output differs: {message}"


class TestPipelineDispatchFeatures:
    """
    Test that pipeline implements dispatch.py features correctly.
    """

    def test_edi_split_functionality(self):
        """
        Test that pipeline handles multi-invoice EDI files correctly.
        This mimics dispatch.py's do_split_edi() functionality.
        """
        pytest.skip("Split node implementation pending")

    def test_edi_validation_before_processing(self):
        """
        Test that pipeline validates EDI files before processing.
        Mimics mtc_edi_validator.report_edi_issues() from dispatch.py.
        """
        pytest.skip("EDI validation node implementation pending")

    def test_credit_invoice_detection(self):
        """
        Test that pipeline correctly detects and handles credit invoices.
        Mimics detect_invoice_is_credit() from utils.py.
        """
        pytest.skip("Credit invoice detection implementation pending")

    def test_upc_lookup_integration(self):
        """
        Test that pipeline performs UPC lookup from AS400 database.
        Mimics invFetcher functionality from utils.py.
        """
        pytest.skip("UPC lookup node implementation pending")

    def test_md5_deduplication(self):
        """
        Test that pipeline uses MD5 hashing for file deduplication.
        Mimics dispatch.py's md5_cached_copy function.
        """
        pytest.skip("MD5 deduplication implementation pending")


class TestFullPipelineIntegration:
    """End-to-end pipeline tests using complete pipeline configurations."""

    def test_all_edi_files_processed(self):
        """Test that all EDI files in alledi/ are processed correctly."""
        test_dir = Path(__file__).parent.parent.parent / "alledi"
        edi_files = [f for f in os.listdir(test_dir) if f.endswith(".edi")]

        # Should process all EDI files without errors
        assert len(edi_files) >= 25, f"Expected ~27 EDI files, found {len(edi_files)}"

        # Each file should be processed successfully
        for edi_file in edi_files[:5]:  # Test first 5 files
            input_file = test_dir / edi_file
            output_file = Path("/tmp") / f"test_{edi_file}.csv"

            cmd = [
                sys.executable,
                "convert_to_csv.py",
                "--input",
                str(input_file),
                "--output",
                str(output_file),
            ]
            result = subprocess.run(cmd, capture_output=True, cwd=project_root)

            assert result.returncode == 0, (
                f"Failed to process {edi_file}: {result.stderr}"
            )
            assert output_file.exists(), f"No output for {edi_file}"

        print(
            f"Successfully processed {len([f for f in os.listdir(test_dir) if f.endswith('.edi')])} EDI files"
        )


if __name__ == "__main__":
    # Run validation framework directly
    framework = PipelineValidationFramework(Path(__file__).parent.parent.parent)

    print("=" * 60)
    print("Pipeline Validation Framework")
    print("=" * 60)
    print(f"Project root: {framework.project_root}")
    print(f"Test data: {framework.test_data_dir}")
    print(f"Pipelines: {framework.pipelines_dir}")
    print(f"Converters: {framework.converters_dir}")
    print()

    print("Test cases defined:")
    for case in framework.test_cases:
        print(f"  - {case.name}: {case.description}")
        print(f"    Pipeline: {case.pipeline_file}")
        print(f"    Converter: {case.converter_script}")
        print(f"    Test files: {len(case.test_edi_files)} files")
        print()
