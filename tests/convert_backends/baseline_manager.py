"""
Baseline Manager for Convert Plugin Outputs.

This module provides utilities for:
- Running convert plugins against test EDI files
- Generating expected outputs for specific settings combinations
- Storing and retrieving baselines
- Comparing current implementation outputs against stored baselines
- Generating detailed diff reports

Usage:
    from tests.convert_backends.baseline_manager import BaselineManager

    manager = BaselineManager()

    # Capture baselines for all plugins
    manager.capture_all_baselines()

    # Compare current implementation against baselines
    results = manager.compare_all()

    # Generate diff report
    report = manager.generate_diff_report(results)
"""

import csv
import hashlib
import json
import os
import subprocess
import tempfile
from dataclasses import asdict, dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Optional, Union


@dataclass
class BaselineResult:
    """Result of a baseline comparison."""

    plugin_id: str
    edi_file: str
    settings_hash: str
    baseline_path: Optional[str]
    current_path: str
    matches: bool
    differences: list[str] = field(default_factory=list)
    error: Optional[str] = None


@dataclass
class SettingsCombination:
    """A specific combination of settings for testing."""

    name: str
    parameters: dict[str, Any]


class BaselineManager:
    """Manager for capturing and comparing convert plugin baselines."""

    # Plugin mapping: plugin_id -> (module_name, class_name)
    PLUGINS = {
        "csv": ("convert_to_csv", "CsvConverter"),
        "scannerware": ("convert_to_scannerware", "ScannerWareConverter"),
        "simplified_csv": ("convert_to_simplified_csv", "SimplifiedCsvConverter"),
        "estore_einvoice": ("convert_to_estore_einvoice", "EstoreEinvoiceConverter"),
        "estore_einvoice_generic": (
            "convert_to_estore_einvoice_generic",
            "EstoreEinvoiceGenericConverter",
        ),
        "fintech": ("convert_to_fintech", "FintechConverter"),
        "scansheet_type_a": ("convert_to_scansheet_type_a", "ScansheetTypeAConverter"),
        "yellowdog_csv": ("convert_to_yellowdog_csv", "YellowdogConverter"),
        "jolley_custom": ("convert_to_jolley_custom", "JolleyCustomConverter"),
        "stewarts_custom": ("convert_to_stewarts_custom", "StewartsCustomConverter"),
        "edi_tweaks": ("convert_to_edi_tweaks", "EDITweaksConverter"),
    }

    # Test EDI files
    TEST_EDI_FILES = [
        "basic_edi.txt",
        "complex_edi.txt",
        "edge_cases_edi.txt",
        "empty_edi.txt",
        "fintech_edi.txt",
        "malformed_edi.txt",
    ]

    # Default parameters for each plugin
    DEFAULT_PARAMETERS: dict[str, dict[str, Any]] = {
        "csv": {
            "calculate_upc_check_digit": "False",
            "include_a_records": "True",
            "include_c_records": "True",
            "include_headers": "True",
            "filter_ampersand": "False",
            "pad_a_records": "False",
            "a_record_padding": "000000",
            "override_upc_bool": "False",
            "override_upc_level": 0,
            "override_upc_category_filter": "",
            "retail_uom": False,
        },
        "scannerware": {
            "a_record_padding": "000000",
            "append_a_records": "False",
            "a_record_append_text": "",
            "force_txt_file_ext": "False",
            "invoice_date_offset": 0,
            "pad_a_records": "False",
        },
        "simplified_csv": {
            "include_headers": "True",
            "filter_by_customer": "False",
            "customer_filter": "",
            "retail_uom": False,
            "include_item_numbers": "True",
            "include_item_description": "True",
            "simple_csv_sort_order": "description,vendor_item,unit_cost,qty_of_units",
        },
        "estore_einvoice": {
            "include_package_info": "True",
            "include_pricing": "True",
            "xml_format": "generic",
            "output_encoding": "UTF-8",
            "estore_store_number": "12345",
            "estore_Vendor_OId": "67890",
            "estore_vendor_NameVendorOID": "TestVendor",
            "estore_c_record_OID": "10025",
        },
        "estore_einvoice_generic": {
            "include_package_info": "True",
            "include_pricing": "True",
            "xml_format": "generic",
            "output_encoding": "UTF-8",
            "estore_store_number": "12345",
            "estore_Vendor_OId": "67890",
            "estore_vendor_NameVendorOID": "TestVendor",
            "estore_c_record_OID": "10025",
        },
        "fintech": {
            "include_headers": "True",
            "include_a_records": "True",
            "include_c_records": "True",
            "a_record_padding": "000000",
            "pad_a_records": "False",
            "fintech_division_id": "12345",
        },
        "scansheet_type_a": {
            "a_record_padding": "000000",
            "append_a_records": "False",
            "a_record_append_text": "",
            "include_headers": "True",
            "header_text": "Invoice Header",
            "include_invoice_totals": "True",
        },
        "yellowdog_csv": {
            "include_headers": "True",
            "delimiter": ",",
        },
        "jolley_custom": {
            "a_record_padding": "000000",
            "include_headers": "True",
            "customer_specific_field": "",
        },
        "stewarts_custom": {
            "a_record_padding": "000000",
            "include_headers": "True",
            "customer_specific_field": "",
        },
        "edi_tweaks": {
            "pad_a_records": "False",
            "a_record_padding": "      ",
            "a_record_padding_length": 6,
            "append_a_records": "False",
            "a_record_append_text": "",
            "invoice_date_custom_format": False,
            "invoice_date_custom_format_string": "%Y-%m-%d",
            "force_txt_file_ext": "False",
            "calculate_upc_check_digit": "False",
            "invoice_date_offset": 0,
            "retail_uom": False,
            "override_upc_bool": False,
            "override_upc_level": 1,
            "override_upc_category_filter": "ALL",
            "split_prepaid_sales_tax_crec": False,
        },
    }

    # Settings combinations for each plugin (overlays on defaults)
    SETTINGS_COMBINATIONS: dict[str, list[SettingsCombination]] = {
        "csv": [
            SettingsCombination("default", {}),
            SettingsCombination(
                "with_headers",
                {"include_headers": "True"},
            ),
            SettingsCombination(
                "with_a_records",
                {"include_a_records": "True"},
            ),
            SettingsCombination(
                "with_c_records",
                {"include_c_records": "True"},
            ),
            SettingsCombination(
                "all_flags",
                {
                    "include_headers": "True",
                    "include_a_records": "True",
                    "include_c_records": "True",
                    "calculate_upc_check_digit": "True",
                    "filter_ampersand": "True",
                },
            ),
        ],
        "scannerware": [
            SettingsCombination("default", {}),
            SettingsCombination(
                "with_padding",
                {"pad_a_records": "True", "a_record_padding": "999999"},
            ),
            SettingsCombination(
                "with_append",
                {"append_a_records": "True", "a_record_append_text": "TEST"},
            ),
            SettingsCombination(
                "with_date_offset",
                {"invoice_date_offset": 5},
            ),
            SettingsCombination(
                "force_txt_ext",
                {"force_txt_file_ext": "True"},
            ),
        ],
        "simplified_csv": [
            SettingsCombination("default", {}),
            SettingsCombination(
                "with_headers",
                {"include_headers": "True"},
            ),
            SettingsCombination(
                "with_item_numbers",
                {"include_item_numbers": "True"},
            ),
            SettingsCombination(
                "with_description",
                {"include_item_description": "True"},
            ),
            SettingsCombination(
                "retail_uom",
                {"retail_uom": True},
            ),
        ],
        "estore_einvoice": [
            SettingsCombination(
                "default",
                {
                    "estore_store_number": "12345",
                    "estore_Vendor_OId": "67890",
                    "estore_vendor_NameVendorOID": "TestVendor",
                },
            ),
        ],
        "estore_einvoice_generic": [
            SettingsCombination(
                "default",
                {
                    "estore_store_number": "12345",
                    "estore_Vendor_OId": "67890",
                    "estore_vendor_NameVendorOID": "TestVendor",
                    "estore_c_record_OID": "10025",
                },
            ),
        ],
        "fintech": [
            SettingsCombination(
                "default",
                {"fintech_division_id": "12345"},
            ),
            SettingsCombination(
                "with_headers",
                {"fintech_division_id": "12345", "include_headers": "True"},
            ),
        ],
        "scansheet_type_a": [
            SettingsCombination("default", {}),
            SettingsCombination(
                "with_headers",
                {"include_headers": "True"},
            ),
        ],
        "yellowdog_csv": [
            SettingsCombination("default", {}),
            SettingsCombination(
                "with_headers",
                {"include_headers": "True"},
            ),
            SettingsCombination(
                "pipe_delimited",
                {"delimiter": "|"},
            ),
        ],
        "jolley_custom": [
            SettingsCombination("default", {}),
        ],
        "stewarts_custom": [
            SettingsCombination("default", {}),
        ],
        "edi_tweaks": [
            SettingsCombination("default", {}),
            SettingsCombination(
                "with_padding",
                {
                    "pad_a_records": "True",
                    "a_record_padding": "XXXXXX",
                    "a_record_padding_length": 6,
                },
            ),
            SettingsCombination(
                "with_append",
                {"append_a_records": "True", "a_record_append_text": "_TEST"},
            ),
            SettingsCombination(
                "with_date_offset",
                {"invoice_date_offset": 5},
            ),
            SettingsCombination(
                "with_date_format",
                {
                    "invoice_date_custom_format": True,
                    "invoice_date_custom_format_string": "%Y-%m-%d",
                },
            ),
            SettingsCombination(
                "with_upc_calc",
                {"calculate_upc_check_digit": "True"},
            ),
            SettingsCombination(
                "with_upc_override",
                {
                    "override_upc_bool": True,
                    "override_upc_level": 1,
                    "override_upc_category_filter": "ALL",
                },
            ),
            SettingsCombination(
                "with_retail_uom",
                {"retail_uom": True},
            ),
            SettingsCombination(
                "force_txt_ext",
                {"force_txt_file_ext": "True"},
            ),
        ],
    }

    # Non-DB-dependent plugins (prioritized for baseline capture)
    # Note: edi_tweaks is EDI-to-EDI preprocessor (not a convert plugin)
    NON_DB_PLUGINS = [
        "csv",
        "scannerware",
        "simplified_csv",
        "estore_einvoice",
        "edi_tweaks",
    ]

    # edi_tweaks only works with EDI files that have numeric invoice numbers
    # (it tries to parse invoice numbers as integers for database lookups)
    EDI_TWEAKS_TEST_FILES = [
        "empty_edi.txt",
        "fintech_edi.txt",
    ]

    def __init__(
        self,
        baselines_dir: Optional[str] = None,
        test_data_dir: Optional[str] = None,
        project_root: Optional[str] = None,
    ):
        """Initialize the baseline manager.

        Args:
            baselines_dir: Directory to store baselines. Defaults to tests/convert_backends/baselines/
            test_data_dir: Directory containing test EDI files. Defaults to tests/convert_backends/data/
            project_root: Project root directory. Defaults to parent of tests/
        """
        if project_root is None:
            self.project_root = Path(__file__).parent.parent.parent
        else:
            self.project_root = Path(project_root)

        if baselines_dir is None:
            self.baselines_dir = (
                self.project_root / "tests" / "convert_backends" / "baselines"
            )
        else:
            self.baselines_dir = Path(baselines_dir)

        if test_data_dir is None:
            self.test_data_dir = (
                self.project_root / "tests" / "convert_backends" / "data"
            )
        else:
            self.test_data_dir = Path(test_data_dir)

        # Ensure baselines directory exists
        self.baselines_dir.mkdir(parents=True, exist_ok=True)

        # Default settings for converters
        self.default_settings = {
            "as400_username": "test_user",
            "as400_password": "test_pass",
            "as400_address": "localhost",
            "odbc_driver": "mock_driver",
        }

        # Default UPC lookup
        self.default_upc_lookup = {
            561234: ("1001", "012345678901", "012345678902"),
            987654: ("1002", "098765432101", "098765432102"),
        }

    def _compute_settings_hash(self, parameters: dict) -> str:
        """Compute a hash for the settings combination."""
        # Sort parameters for consistent hashing
        param_str = json.dumps(parameters, sort_keys=True)
        return hashlib.md5(param_str.encode()).hexdigest()[:8]

    def _get_baseline_path(
        self, plugin_id: str, edi_file: str, settings_hash: str
    ) -> Path:
        """Get the path for a baseline file."""
        plugin_dir = self.baselines_dir / plugin_id
        plugin_dir.mkdir(parents=True, exist_ok=True)

        edi_name = Path(edi_file).stem
        # edi_tweaks produces EDI output, others produce CSV
        extension = ".edi" if plugin_id == "edi_tweaks" else ".csv"
        return plugin_dir / f"{edi_name}_{settings_hash}{extension}"

    def _get_baseline_metadata_path(self, plugin_id: str) -> Path:
        """Get the path for baseline metadata file."""
        return self.baselines_dir / f"{plugin_id}_metadata.json"

    def _import_converter(self, plugin_id: str):
        """Import the converter module for a plugin."""
        import importlib
        import sys

        module_name, _ = self.PLUGINS[plugin_id]

        # Add project root to path if not already there
        project_root_str = str(self.project_root)
        if project_root_str not in sys.path:
            sys.path.insert(0, project_root_str)

        return importlib.import_module(module_name)

    def _run_converter(
        self,
        plugin_id: str,
        edi_file: str,
        parameters: dict,
        output_dir: Optional[str] = None,
    ) -> str:
        """Run a converter and return the output file path.

        Args:
            plugin_id: The plugin ID
            edi_file: Path to the EDI file
            parameters: Converter parameters
            output_dir: Optional output directory (uses temp dir if None)

        Returns:
            Path to the generated output file
        """
        converter_module = self._import_converter(plugin_id)

        # Determine output path
        if output_dir is None:
            output_dir = tempfile.mkdtemp()
        else:
            output_dir = str(output_dir)

        edi_name = Path(edi_file).stem
        settings_hash = self._compute_settings_hash(parameters)
        output_base = os.path.join(output_dir, f"{edi_name}_{settings_hash}")

        edi_path = self.test_data_dir / edi_file
        if not edi_path.exists():
            raise FileNotFoundError(f"EDI file not found: {edi_path}")

        # Instantiate the converter class and call convert()
        _, class_name = self.PLUGINS[plugin_id]
        converter_class = getattr(converter_module, class_name)
        converter = converter_class(
            str(edi_path),
            output_base,
            self.default_settings,
            parameters,
            self.default_upc_lookup,
        )
        result_path = converter.convert()

        return result_path

    def _get_full_parameters(self, plugin_id: str, combo_parameters: dict) -> dict:
        """Get full parameters by merging defaults with combination overrides.

        Args:
            plugin_id: The plugin ID
            combo_parameters: The settings combination parameters

        Returns:
            Complete parameters dict with defaults and overrides merged
        """
        # Start with defaults for this plugin
        full_params = self.DEFAULT_PARAMETERS.get(plugin_id, {}).copy()
        # Overlay the combination-specific parameters
        full_params.update(combo_parameters)
        return full_params

    def capture_baseline(
        self,
        plugin_id: str,
        edi_file: str,
        settings_combo: SettingsCombination,
        source: str = "current",
    ) -> Path:
        """Capture a baseline for a specific plugin/EDI/settings combination.

        Args:
            plugin_id: The plugin ID
            edi_file: Name of the EDI test file
            settings_combo: Settings combination to use
            source: Source of the baseline ('current' or 'master')

        Returns:
            Path to the saved baseline file
        """
        # Get full parameters with defaults
        full_parameters = self._get_full_parameters(
            plugin_id, settings_combo.parameters
        )
        settings_hash = self._compute_settings_hash(settings_combo.parameters)
        baseline_path = self._get_baseline_path(plugin_id, edi_file, settings_hash)

        # Run converter to generate output
        output_path = self._run_converter(plugin_id, edi_file, full_parameters)

        # Copy output to baseline location
        import shutil

        shutil.copy2(output_path, baseline_path)

        # Update metadata
        self._update_metadata(
            plugin_id, edi_file, settings_combo, settings_hash, source
        )

        return baseline_path

    def _update_metadata(
        self,
        plugin_id: str,
        edi_file: str,
        settings_combo: SettingsCombination,
        settings_hash: str,
        source: str,
    ):
        """Update metadata for a captured baseline."""
        metadata_path = self._get_baseline_metadata_path(plugin_id)

        if metadata_path.exists():
            with open(metadata_path, "r") as f:
                metadata = json.load(f)
        else:
            metadata = {"baselines": {}}

        key = f"{Path(edi_file).stem}_{settings_hash}"
        metadata["baselines"][key] = {
            "edi_file": edi_file,
            "settings_name": settings_combo.name,
            "settings": settings_combo.parameters,
            "settings_hash": settings_hash,
            "captured_at": datetime.now().isoformat(),
            "source": source,
        }

        with open(metadata_path, "w") as f:
            json.dump(metadata, f, indent=2)

    def _get_test_files_for_plugin(self, plugin_id: str) -> list[str]:
        """Get the list of test EDI files for a specific plugin.

        Args:
            plugin_id: The plugin ID

        Returns:
            List of test EDI file names
        """
        if plugin_id == "edi_tweaks":
            # edi_tweaks only works with numeric invoice numbers
            return self.EDI_TWEAKS_TEST_FILES
        return self.TEST_EDI_FILES

    def capture_all_baselines(
        self,
        plugins: Optional[list[str]] = None,
        source: str = "current",
    ) -> dict[str, list[Path]]:
        """Capture baselines for all specified plugins.

        Args:
            plugins: List of plugin IDs to capture. Defaults to non-DB plugins.
            source: Source of the baseline ('current' or 'master')

        Returns:
            Dictionary mapping plugin_id to list of captured baseline paths
        """
        if plugins is None:
            plugins = self.NON_DB_PLUGINS

        results = {}
        for plugin_id in plugins:
            if plugin_id not in self.SETTINGS_COMBINATIONS:
                continue

            results[plugin_id] = []
            test_files = self._get_test_files_for_plugin(plugin_id)
            for settings_combo in self.SETTINGS_COMBINATIONS[plugin_id]:
                for edi_file in test_files:
                    try:
                        baseline_path = self.capture_baseline(
                            plugin_id, edi_file, settings_combo, source
                        )
                        results[plugin_id].append(baseline_path)
                    except Exception as e:
                        print(
                            f"Error capturing baseline for {plugin_id}/{edi_file}: {e}"
                        )

        return results

    def compare_against_baseline(
        self,
        plugin_id: str,
        edi_file: str,
        settings_combo: SettingsCombination,
    ) -> BaselineResult:
        """Compare current implementation against stored baseline.

        Args:
            plugin_id: The plugin ID
            edi_file: Name of the EDI test file
            settings_combo: Settings combination to use

        Returns:
            BaselineResult with comparison details
        """
        settings_hash = self._compute_settings_hash(settings_combo.parameters)
        baseline_path = self._get_baseline_path(plugin_id, edi_file, settings_hash)

        # Check if baseline exists
        if not baseline_path.exists():
            return BaselineResult(
                plugin_id=plugin_id,
                edi_file=edi_file,
                settings_hash=settings_hash,
                baseline_path=None,
                current_path="",
                matches=False,
                error="Baseline does not exist",
            )

        try:
            # Get full parameters with defaults
            full_parameters = self._get_full_parameters(
                plugin_id, settings_combo.parameters
            )
            # Generate current output
            current_path = self._run_converter(plugin_id, edi_file, full_parameters)

            # Compare files
            differences = self._compare_files(baseline_path, current_path)

            return BaselineResult(
                plugin_id=plugin_id,
                edi_file=edi_file,
                settings_hash=settings_hash,
                baseline_path=str(baseline_path),
                current_path=current_path,
                matches=len(differences) == 0,
                differences=differences,
            )

        except Exception as e:
            return BaselineResult(
                plugin_id=plugin_id,
                edi_file=edi_file,
                settings_hash=settings_hash,
                baseline_path=str(baseline_path),
                current_path="",
                matches=False,
                error=str(e),
            )

    def _compare_files(self, baseline_path: Path, current_path: str) -> list[str]:
        """Compare two files and return list of differences."""
        differences = []

        try:
            with open(baseline_path, "r", encoding="utf-8") as f:
                baseline_content = f.read()
        except Exception as e:
            return [f"Error reading baseline: {e}"]

        try:
            with open(current_path, "r", encoding="utf-8") as f:
                current_content = f.read()
        except Exception as e:
            return [f"Error reading current output: {e}"]

        # Normalize line endings
        baseline_lines = baseline_content.replace("\r\n", "\n").split("\n")
        current_lines = current_content.replace("\r\n", "\n").split("\n")

        # Compare line by line
        max_lines = max(len(baseline_lines), len(current_lines))
        for i in range(max_lines):
            if i >= len(baseline_lines):
                differences.append(f"Line {i + 1}: Extra line in current output")
            elif i >= len(current_lines):
                differences.append(f"Line {i + 1}: Missing line in current output")
            elif baseline_lines[i] != current_lines[i]:
                # For CSV files, try to provide more detailed diff
                if str(baseline_path).endswith(".csv"):
                    diff = self._compare_csv_lines(
                        baseline_lines[i], current_lines[i], i + 1
                    )
                    differences.extend(diff)
                else:
                    # For EDI and other files, show line-level diff
                    differences.append(
                        f"Line {i + 1}: Content differs\n"
                        f"  Baseline: {repr(baseline_lines[i][:100])}\n"
                        f"  Current:  {repr(current_lines[i][:100])}"
                    )

        return differences

    def _compare_csv_lines(
        self, baseline_line: str, current_line: str, line_num: int
    ) -> list[str]:
        """Compare two CSV lines and return detailed differences."""
        differences = []

        try:
            baseline_cols = baseline_line.split(",")
            current_cols = current_line.split(",")
        except Exception:
            return [f"Line {line_num}: Content differs (could not parse as CSV)"]

        max_cols = max(len(baseline_cols), len(current_cols))
        for i in range(max_cols):
            if i >= len(baseline_cols):
                differences.append(
                    f"Line {line_num}, Col {i + 1}: Extra column in current"
                )
            elif i >= len(current_cols):
                differences.append(
                    f"Line {line_num}, Col {i + 1}: Missing column in current"
                )
            elif baseline_cols[i] != current_cols[i]:
                differences.append(
                    f"Line {line_num}, Col {i + 1}: Value differs\n"
                    f"  Baseline: '{baseline_cols[i]}'\n"
                    f"  Current:  '{current_cols[i]}'"
                )

        return differences

    def compare_all(
        self,
        plugins: Optional[list[str]] = None,
    ) -> list[BaselineResult]:
        """Compare current implementation against all stored baselines.

        Args:
            plugins: List of plugin IDs to compare. Defaults to non-DB plugins.

        Returns:
            List of BaselineResult for all comparisons
        """
        if plugins is None:
            plugins = self.NON_DB_PLUGINS

        results = []
        for plugin_id in plugins:
            if plugin_id not in self.SETTINGS_COMBINATIONS:
                continue

            test_files = self._get_test_files_for_plugin(plugin_id)
            for settings_combo in self.SETTINGS_COMBINATIONS[plugin_id]:
                for edi_file in test_files:
                    result = self.compare_against_baseline(
                        plugin_id, edi_file, settings_combo
                    )
                    results.append(result)

        return results

    def generate_diff_report(
        self,
        results: list[BaselineResult],
        output_path: Optional[str] = None,
    ) -> str:
        """Generate a detailed diff report.

        Args:
            results: List of BaselineResult from comparisons
            output_path: Optional path to save the report

        Returns:
            The report as a string
        """
        lines = [
            "=" * 80,
            "CONVERT PLUGIN BASELINE DIFF REPORT",
            f"Generated: {datetime.now().isoformat()}",
            "=" * 80,
            "",
        ]

        # Summary
        total = len(results)
        passed = sum(1 for r in results if r.matches)
        failed = total - passed
        errors = sum(1 for r in results if r.error is not None)

        lines.extend(
            [
                "SUMMARY",
                "-" * 40,
                f"Total comparisons: {total}",
                f"Passed: {passed}",
                f"Failed: {failed}",
                f"Errors: {errors}",
                "",
            ]
        )

        # Failed comparisons
        if failed > 0:
            lines.extend(
                [
                    "FAILED COMPARISONS",
                    "-" * 40,
                    "",
                ]
            )

            for result in results:
                if not result.matches and result.error is None:
                    lines.extend(
                        [
                            f"Plugin: {result.plugin_id}",
                            f"EDI File: {result.edi_file}",
                            f"Settings Hash: {result.settings_hash}",
                            f"Differences ({len(result.differences)}):",
                        ]
                    )
                    for diff in result.differences[
                        :10
                    ]:  # Limit to first 10 differences
                        lines.append(f"  - {diff}")
                    if len(result.differences) > 10:
                        lines.append(
                            f"  ... and {len(result.differences) - 10} more differences"
                        )
                    lines.append("")

        # Errors
        if errors > 0:
            lines.extend(
                [
                    "ERRORS",
                    "-" * 40,
                    "",
                ]
            )

            for result in results:
                if result.error:
                    lines.extend(
                        [
                            f"Plugin: {result.plugin_id}",
                            f"EDI File: {result.edi_file}",
                            f"Error: {result.error}",
                            "",
                        ]
                    )

        report = "\n".join(lines)

        if output_path:
            with open(output_path, "w") as f:
                f.write(report)

        return report

    def list_baselines(self) -> dict[str, list[dict]]:
        """List all captured baselines.

        Returns:
            Dictionary mapping plugin_id to list of baseline info dicts
        """
        baselines = {}

        for plugin_id in self.PLUGINS.keys():
            metadata_path = self._get_baseline_metadata_path(plugin_id)
            if metadata_path.exists():
                with open(metadata_path, "r") as f:
                    metadata = json.load(f)
                    baselines[plugin_id] = list(metadata.get("baselines", {}).values())
            else:
                baselines[plugin_id] = []

        return baselines

    def clear_baselines(self, plugin_id: Optional[str] = None):
        """Clear captured baselines.

        Args:
            plugin_id: Optional specific plugin to clear. If None, clears all.
        """
        import shutil

        if plugin_id:
            plugin_dir = self.baselines_dir / plugin_id
            metadata_path = self._get_baseline_metadata_path(plugin_id)

            if plugin_dir.exists():
                shutil.rmtree(plugin_dir)
            if metadata_path.exists():
                metadata_path.unlink()
        else:
            if self.baselines_dir.exists():
                shutil.rmtree(self.baselines_dir)
            self.baselines_dir.mkdir(parents=True, exist_ok=True)


class GitBaselineCapture:
    """Capture baselines from git master branch."""

    def __init__(self, project_root: Optional[str] = None):
        """Initialize git baseline capture.

        Args:
            project_root: Project root directory. Defaults to parent of tests/
        """
        if project_root is None:
            self.project_root = Path(__file__).parent.parent.parent
        else:
            self.project_root = Path(project_root)

        self.baseline_manager = BaselineManager(project_root=str(self.project_root))

    def get_current_branch(self) -> str:
        """Get the current git branch."""
        result = subprocess.run(
            ["git", "rev-parse", "--abbrev-ref", "HEAD"],
            cwd=self.project_root,
            capture_output=True,
            text=True,
            check=True,
        )
        return result.stdout.strip()

    def checkout_master(self):
        """Checkout the master branch."""
        subprocess.run(
            ["git", "checkout", "master"],
            cwd=self.project_root,
            check=True,
        )

    def checkout_branch(self, branch: str):
        """Checkout a specific branch."""
        subprocess.run(
            ["git", "checkout", branch],
            cwd=self.project_root,
            check=True,
        )

    def capture_from_master(
        self,
        plugins: Optional[list[str]] = None,
    ) -> dict[str, list[Path]]:
        """Capture baselines from git master branch.

        This method:
        1. Saves the current branch
        2. Checks out master
        3. Captures baselines
        4. Returns to the original branch

        Args:
            plugins: List of plugin IDs to capture. Defaults to non-DB plugins.

        Returns:
            Dictionary mapping plugin_id to list of captured baseline paths
        """
        original_branch = self.get_current_branch()

        try:
            print(f"Switching from {original_branch} to master...")
            self.checkout_master()

            print("Capturing baselines from master...")
            results = self.baseline_manager.capture_all_baselines(
                plugins=plugins, source="master"
            )

            return results

        finally:
            print(f"Returning to {original_branch}...")
            self.checkout_branch(original_branch)


def main():
    """CLI interface for baseline manager."""
    import argparse

    parser = argparse.ArgumentParser(description="Convert Plugin Baseline Manager")
    subparsers = parser.add_subparsers(dest="command", help="Commands")

    # Capture command
    capture_parser = subparsers.add_parser("capture", help="Capture baselines")
    capture_parser.add_argument(
        "--plugins",
        nargs="+",
        choices=list(BaselineManager.PLUGINS.keys()),
        help="Plugins to capture (default: non-DB plugins)",
    )
    capture_parser.add_argument(
        "--from-master",
        action="store_true",
        help="Capture from git master branch",
    )

    # Compare command
    compare_parser = subparsers.add_parser("compare", help="Compare against baselines")
    compare_parser.add_argument(
        "--plugins",
        nargs="+",
        choices=list(BaselineManager.PLUGINS.keys()),
        help="Plugins to compare (default: non-DB plugins)",
    )
    compare_parser.add_argument(
        "--output",
        "-o",
        help="Output file for diff report",
    )

    # List command
    subparsers.add_parser("list", help="List captured baselines")

    # Clear command
    clear_parser = subparsers.add_parser("clear", help="Clear baselines")
    clear_parser.add_argument(
        "--plugin",
        choices=list(BaselineManager.PLUGINS.keys()),
        help="Specific plugin to clear (default: all)",
    )

    args = parser.parse_args()

    if args.command == "capture":
        if args.from_master:
            git_capture = GitBaselineCapture()
            results = git_capture.capture_from_master(plugins=args.plugins)
        else:
            manager = BaselineManager()
            results = manager.capture_all_baselines(plugins=args.plugins)

        print(f"Captured {sum(len(v) for v in results.values())} baselines")

    elif args.command == "compare":
        manager = BaselineManager()
        results = manager.compare_all(plugins=args.plugins)
        report = manager.generate_diff_report(results, output_path=args.output)
        print(report)

        # Exit with error code if any failures
        failed = sum(1 for r in results if not r.matches)
        if failed > 0:
            exit(1)

    elif args.command == "list":
        manager = BaselineManager()
        baselines = manager.list_baselines()

        for plugin_id, baseline_list in baselines.items():
            if baseline_list:
                print(f"\n{plugin_id}: {len(baseline_list)} baselines")
                for baseline in baseline_list:
                    print(f"  - {baseline['edi_file']} ({baseline['settings_name']})")

    elif args.command == "clear":
        manager = BaselineManager()
        manager.clear_baselines(plugin_id=args.plugin)
        print("Baselines cleared")

    else:
        parser.print_help()


if __name__ == "__main__":
    main()
