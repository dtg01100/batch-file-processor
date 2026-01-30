"""
Parity Verification Tests for Convert Plugins.

This test file provides pytest-based tests that:
- Load stored baselines from tests/convert_backends/baselines/
- Run current implementation with same inputs/settings
- Assert output matches baseline exactly
- Provide clear failure messages showing differences

These tests ensure that changes to convert plugins do not unintentionally
modify output formats, preserving backward compatibility.

Usage:
    # Run all parity tests
    pytest tests/convert_backends/test_parity_verification.py -v

    # Run tests for specific plugin
    pytest tests/convert_backends/test_parity_verification.py -v -k csv

    # Run tests with detailed diff on failure
    pytest tests/convert_backends/test_parity_verification.py -v --tb=long

Requirements:
    - Baselines must be captured first using capture_master_baselines.py
    - Tests will skip if baselines don't exist
    - Tests focus on non-DB-dependent plugins by default
"""

import os
import sys
from pathlib import Path

import pytest

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from tests.convert_backends.baseline_manager import BaselineManager, SettingsCombination


# ============================================================================
# FIXTURES
# ============================================================================

@pytest.fixture(scope="module")
def baseline_manager():
    """Provide a BaselineManager instance for the test module."""
    return BaselineManager(project_root=str(project_root))


@pytest.fixture
def settings_dict():
    """Return default settings dictionary for converters."""
    return {
        "as400_username": "test_user",
        "as400_password": "test_pass",
        "as400_address": "localhost",
        "odbc_driver": "mock_driver",
    }


@pytest.fixture
def upc_lookup():
    """Return default UPC lookup for testing."""
    return {
        561234: ("1001", "012345678901", "012345678902"),
        987654: ("1002", "098765432101", "098765432102"),
    }


# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

def run_parity_test(manager, plugin_id, edi_file, settings_combo):
    """Run a single parity test and return detailed failure message if any.

    Args:
        manager: BaselineManager instance
        plugin_id: Plugin ID to test
        edi_file: EDI test file name
        settings_combo: SettingsCombination to use

    Returns:
        Tuple of (success: bool, message: str)
    """
    result = manager.compare_against_baseline(plugin_id, edi_file, settings_combo)

    if result.error:
        return False, f"Error: {result.error}"

    if not result.matches:
        # Build detailed failure message
        lines = [
            f"Baseline mismatch for {plugin_id}/{edi_file} ({settings_combo.name})",
            f"Settings hash: {result.settings_hash}",
            f"Baseline path: {result.baseline_path}",
            f"Current output: {result.current_path}",
            "",
            f"Differences ({len(result.differences)}):",
        ]

        for i, diff in enumerate(result.differences[:20], 1):
            lines.append(f"  {i}. {diff}")

        if len(result.differences) > 20:
            lines.append(f"  ... and {len(result.differences) - 20} more differences")

        return False, "\n".join(lines)

    return True, "OK"


def pytest_generate_tests(metafunc):
    """Generate test parameters dynamically based on available baselines.

    This hook generates test cases for all plugins/EDI/settings combinations
    that have baselines captured.
    """
    if "plugin_id" in metafunc.fixturenames and "edi_file" in metafunc.fixturenames:
        manager = BaselineManager(project_root=str(project_root))

        params = []
        ids = []

        for plugin_id in manager.NON_DB_PLUGINS:
            if plugin_id not in manager.SETTINGS_COMBINATIONS:
                continue

            # Use appropriate test files for each plugin
            test_files = manager._get_test_files_for_plugin(plugin_id)

            for settings_combo in manager.SETTINGS_COMBINATIONS[plugin_id]:
                for edi_file in test_files:
                    # Check if baseline exists
                    settings_hash = manager._compute_settings_hash(settings_combo.parameters)
                    baseline_path = manager._get_baseline_path(plugin_id, edi_file, settings_hash)

                    if baseline_path.exists():
                        param_id = f"{plugin_id}_{edi_file.replace('.', '_')}_{settings_combo.name}"
                        params.append((plugin_id, edi_file, settings_combo))
                        ids.append(param_id)

        if params:
            metafunc.parametrize("plugin_id,edi_file,settings_combo", params, ids=ids)


# ============================================================================
# PARITY VERIFICATION TESTS
# ============================================================================

@pytest.mark.convert_backend
@pytest.mark.parity
class TestConvertPluginParity:
    """Parity tests ensuring convert plugin outputs match baselines."""

    def test_parity(self, plugin_id, edi_file, settings_combo, baseline_manager):
        """Test that current output matches stored baseline.

        This test runs the converter with the same inputs and settings
        that were used to capture the baseline, and asserts that the
        output is identical.
        """
        success, message = run_parity_test(
            baseline_manager, plugin_id, edi_file, settings_combo
        )
        assert success, message


# ============================================================================
# PLUGIN-SPECIFIC PARITY TESTS (Explicit)
# ============================================================================

@pytest.mark.convert_backend
@pytest.mark.parity
class TestConvertToCSVParity:
    """Parity tests for convert_to_csv plugin."""

    CSV_SETTINGS = [
        SettingsCombination("default", {}),
        SettingsCombination("with_headers", {"include_headers": "True"}),
        SettingsCombination("with_a_records", {"include_a_records": "True"}),
        SettingsCombination("with_c_records", {"include_c_records": "True"}),
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
    ]

    EDI_FILES = [
        "basic_edi.txt",
        "complex_edi.txt",
        "edge_cases_edi.txt",
        "empty_edi.txt",
        "malformed_edi.txt",
    ]

    @pytest.mark.parametrize("edi_file", EDI_FILES)
    @pytest.mark.parametrize("settings_combo", CSV_SETTINGS, ids=[s.name for s in CSV_SETTINGS])
    def test_csv_parity(self, baseline_manager, edi_file, settings_combo):
        """Test CSV converter parity for various settings."""
        # Skip if baseline doesn't exist
        settings_hash = baseline_manager._compute_settings_hash(settings_combo.parameters)
        baseline_path = baseline_manager._get_baseline_path("csv", edi_file, settings_hash)

        if not baseline_path.exists():
            pytest.skip(f"Baseline not found: {baseline_path}")

        success, message = run_parity_test(
            baseline_manager, "csv", edi_file, settings_combo
        )
        assert success, message


@pytest.mark.convert_backend
@pytest.mark.parity
class TestConvertToScannerwareParity:
    """Parity tests for convert_to_scannerware plugin."""

    SCANNERWARE_SETTINGS = [
        SettingsCombination("default", {}),
        SettingsCombination("with_padding", {"pad_a_records": "True", "a_record_padding": "999999"}),
        SettingsCombination("with_append", {"append_a_records": "True", "a_record_append_text": "TEST"}),
        SettingsCombination("with_date_offset", {"invoice_date_offset": 5}),
        SettingsCombination("force_txt_ext", {"force_txt_file_ext": "True"}),
    ]

    EDI_FILES = [
        "basic_edi.txt",
        "complex_edi.txt",
        "edge_cases_edi.txt",
        "empty_edi.txt",
        "malformed_edi.txt",
    ]

    @pytest.mark.parametrize("edi_file", EDI_FILES)
    @pytest.mark.parametrize("settings_combo", SCANNERWARE_SETTINGS, ids=[s.name for s in SCANNERWARE_SETTINGS])
    def test_scannerware_parity(self, baseline_manager, edi_file, settings_combo):
        """Test Scannerware converter parity for various settings."""
        # Skip if baseline doesn't exist
        settings_hash = baseline_manager._compute_settings_hash(settings_combo.parameters)
        baseline_path = baseline_manager._get_baseline_path("scannerware", edi_file, settings_hash)

        if not baseline_path.exists():
            pytest.skip(f"Baseline not found: {baseline_path}")

        success, message = run_parity_test(
            baseline_manager, "scannerware", edi_file, settings_combo
        )
        assert success, message


@pytest.mark.convert_backend
@pytest.mark.parity
class TestConvertToSimplifiedCSVParity:
    """Parity tests for convert_to_simplified_csv plugin."""

    SIMPLIFIED_SETTINGS = [
        SettingsCombination("default", {}),
        SettingsCombination("with_headers", {"include_headers": "True"}),
        SettingsCombination("with_item_numbers", {"include_item_numbers": "True"}),
        SettingsCombination("with_description", {"include_item_description": "True"}),
        SettingsCombination("retail_uom", {"retail_uom": True}),
    ]

    EDI_FILES = [
        "basic_edi.txt",
        "complex_edi.txt",
        "edge_cases_edi.txt",
        "empty_edi.txt",
        "malformed_edi.txt",
    ]

    @pytest.mark.parametrize("edi_file", EDI_FILES)
    @pytest.mark.parametrize("settings_combo", SIMPLIFIED_SETTINGS, ids=[s.name for s in SIMPLIFIED_SETTINGS])
    def test_simplified_csv_parity(self, baseline_manager, edi_file, settings_combo):
        """Test Simplified CSV converter parity for various settings."""
        # Skip if baseline doesn't exist
        settings_hash = baseline_manager._compute_settings_hash(settings_combo.parameters)
        baseline_path = baseline_manager._get_baseline_path("simplified_csv", edi_file, settings_hash)

        if not baseline_path.exists():
            pytest.skip(f"Baseline not found: {baseline_path}")

        success, message = run_parity_test(
            baseline_manager, "simplified_csv", edi_file, settings_combo
        )
        assert success, message


@pytest.mark.convert_backend
@pytest.mark.parity
class TestConvertToEstoreEinvoiceParity:
    """Parity tests for convert_to_estore_einvoice plugin."""

    ESTORE_SETTINGS = [
        SettingsCombination(
            "default",
            {
                "estore_store_number": "12345",
                "estore_Vendor_OId": "67890",
                "estore_vendor_NameVendorOID": "TestVendor",
            },
        ),
    ]

    EDI_FILES = [
        "basic_edi.txt",
        "complex_edi.txt",
        "edge_cases_edi.txt",
        "empty_edi.txt",
        "malformed_edi.txt",
    ]

    @pytest.mark.parametrize("edi_file", EDI_FILES)
    @pytest.mark.parametrize("settings_combo", ESTORE_SETTINGS, ids=[s.name for s in ESTORE_SETTINGS])
    def test_estore_einvoice_parity(self, baseline_manager, edi_file, settings_combo):
        """Test eStore eInvoice converter parity."""
        # Skip if baseline doesn't exist
        settings_hash = baseline_manager._compute_settings_hash(settings_combo.parameters)
        baseline_path = baseline_manager._get_baseline_path("estore_einvoice", edi_file, settings_hash)

        if not baseline_path.exists():
            pytest.skip(f"Baseline not found: {baseline_path}")

        success, message = run_parity_test(
            baseline_manager, "estore_einvoice", edi_file, settings_combo
        )
        assert success, message


@pytest.mark.convert_backend
@pytest.mark.parity
class TestEdiTweaksParity:
    """Parity tests for edi_tweaks EDI preprocessor.

    edi_tweaks is an EDI-to-EDI preprocessor (not a convert plugin).
    It modifies EDI files with various transformations:
    - A-record padding and appending
    - Date formatting and offset
    - UPC calculation and override
    - Retail UOM conversion

    Note: edi_tweaks only works with EDI files that have numeric invoice numbers
    (it parses invoice numbers as integers for database lookups).
    """

    EDI_TWEAKS_SETTINGS = [
        SettingsCombination("default", {}),
        SettingsCombination(
            "with_padding",
            {"pad_a_records": "True", "a_record_padding": "XXXXXX", "a_record_padding_length": 6},
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
            {"invoice_date_custom_format": True, "invoice_date_custom_format_string": "%Y-%m-%d"},
        ),
        SettingsCombination(
            "with_upc_calc",
            {"calculate_upc_check_digit": "True"},
        ),
        SettingsCombination(
            "with_upc_override",
            {"override_upc_bool": True, "override_upc_level": 1, "override_upc_category_filter": "ALL"},
        ),
        SettingsCombination(
            "with_retail_uom",
            {"retail_uom": True},
        ),
        SettingsCombination(
            "force_txt_ext",
            {"force_txt_file_ext": "True"},
        ),
    ]

    # edi_tweaks only works with numeric invoice numbers (fintech_edi.txt)
    EDI_FILES = [
        "empty_edi.txt",
        "fintech_edi.txt",
    ]

    @pytest.mark.parametrize("edi_file", EDI_FILES)
    @pytest.mark.parametrize("settings_combo", EDI_TWEAKS_SETTINGS, ids=[s.name for s in EDI_TWEAKS_SETTINGS])
    def test_edi_tweaks_parity(self, baseline_manager, edi_file, settings_combo):
        """Test edi_tweaks EDI preprocessor parity."""
        # Skip if baseline doesn't exist
        settings_hash = baseline_manager._compute_settings_hash(settings_combo.parameters)
        baseline_path = baseline_manager._get_baseline_path("edi_tweaks", edi_file, settings_hash)

        if not baseline_path.exists():
            pytest.skip(f"Baseline not found: {baseline_path}")

        success, message = run_parity_test(
            baseline_manager, "edi_tweaks", edi_file, settings_combo
        )
        assert success, message


# ============================================================================
# BASELINE AVAILABILITY TESTS
# ============================================================================

@pytest.mark.convert_backend
@pytest.mark.parity
class TestBaselineAvailability:
    """Tests to verify baselines are available for testing."""

    def test_baselines_directory_exists(self, baseline_manager):
        """Verify the baselines directory exists."""
        assert baseline_manager.baselines_dir.exists(), \
            f"Baselines directory does not exist: {baseline_manager.baselines_dir}"

    def test_non_db_plugins_have_baselines(self, baseline_manager):
        """Verify non-DB plugins have at least some baselines captured."""
        missing_baselines = []

        for plugin_id in BaselineManager.NON_DB_PLUGINS:
            if plugin_id not in baseline_manager.SETTINGS_COMBINATIONS:
                continue

            has_baseline = False
            for settings_combo in baseline_manager.SETTINGS_COMBINATIONS[plugin_id]:
                for edi_file in baseline_manager.TEST_EDI_FILES:
                    settings_hash = baseline_manager._compute_settings_hash(settings_combo.parameters)
                    baseline_path = baseline_manager._get_baseline_path(plugin_id, edi_file, settings_hash)

                    if baseline_path.exists():
                        has_baseline = True
                        break
                if has_baseline:
                    break

            if not has_baseline:
                missing_baselines.append(plugin_id)

        if missing_baselines:
            pytest.skip(
                f"No baselines found for plugins: {', '.join(missing_baselines)}. "
                f"Run: python tests/convert_backends/capture_master_baselines.py"
            )

    def test_list_available_baselines(self, baseline_manager):
        """List all available baselines (informational test)."""
        baselines = baseline_manager.list_baselines()

        total_baselines = 0
        for plugin_id, baseline_list in baselines.items():
            if baseline_list:
                total_baselines += len(baseline_list)
                print(f"\n{plugin_id}: {len(baseline_list)} baselines")

        print(f"\nTotal baselines available: {total_baselines}")

        # This test always passes - it's informational
        assert True


# ============================================================================
# REGENERATION HELPERS
# ============================================================================

@pytest.mark.convert_backend
@pytest.mark.parity
@pytest.mark.skip(reason="Only run manually to regenerate baselines")
class TestRegenerateBaselines:
    """Helper tests to regenerate baselines (not run in CI).

    These tests are skipped by default and should only be run manually
    when you need to regenerate baselines after intentional changes.

    To regenerate baselines:
        pytest tests/convert_backends/test_parity_verification.py::TestRegenerateBaselines -v --run-regenerate
    """

    def test_regenerate_csv_baselines(self, baseline_manager):
        """Regenerate CSV baselines from current implementation."""
        results = baseline_manager.capture_all_baselines(plugins=["csv"], source="regenerated")
        total = sum(len(paths) for paths in results.values())
        print(f"\nRegenerated {total} CSV baselines")
        assert total > 0, "No baselines were regenerated"

    def test_regenerate_scannerware_baselines(self, baseline_manager):
        """Regenerate Scannerware baselines from current implementation."""
        results = baseline_manager.capture_all_baselines(plugins=["scannerware"], source="regenerated")
        total = sum(len(paths) for paths in results.values())
        print(f"\nRegenerated {total} Scannerware baselines")
        assert total > 0, "No baselines were regenerated"

    def test_regenerate_simplified_csv_baselines(self, baseline_manager):
        """Regenerate Simplified CSV baselines from current implementation."""
        results = baseline_manager.capture_all_baselines(plugins=["simplified_csv"], source="regenerated")
        total = sum(len(paths) for paths in results.values())
        print(f"\nRegenerated {total} Simplified CSV baselines")
        assert total > 0, "No baselines were regenerated"

    def test_regenerate_all_non_db_baselines(self, baseline_manager):
        """Regenerate all non-DB plugin baselines."""
        results = baseline_manager.capture_all_baselines(source="regenerated")
        total = sum(len(paths) for paths in results.values())
        print(f"\nRegenerated {total} total baselines")
        assert total > 0, "No baselines were regenerated"


# ============================================================================
# UTILITY TESTS
# ============================================================================

@pytest.mark.convert_backend
@pytest.mark.parity
class TestParityUtilities:
    """Utility tests for the parity verification system."""

    def test_settings_hash_consistency(self, baseline_manager):
        """Verify settings hash is consistent for same parameters."""
        params = {"include_headers": "True", "test_param": 123}

        hash1 = baseline_manager._compute_settings_hash(params)
        hash2 = baseline_manager._compute_settings_hash(params)

        assert hash1 == hash2, "Settings hash should be consistent"

    def test_settings_hash_uniqueness(self, baseline_manager):
        """Verify different parameters produce different hashes."""
        params1 = {"include_headers": "True"}
        params2 = {"include_headers": "False"}

        hash1 = baseline_manager._compute_settings_hash(params1)
        hash2 = baseline_manager._compute_settings_hash(params2)

        assert hash1 != hash2, "Different parameters should produce different hashes"

    def test_baseline_path_generation(self, baseline_manager):
        """Verify baseline paths are generated correctly."""
        plugin_id = "csv"
        edi_file = "basic_edi.txt"
        settings_hash = "abc12345"

        path = baseline_manager._get_baseline_path(plugin_id, edi_file, settings_hash)

        expected_suffix = f"baselines/csv/basic_edi_{settings_hash}.csv"
        assert str(path).endswith(expected_suffix), f"Path should end with {expected_suffix}"

    def test_all_test_edi_files_exist(self, baseline_manager):
        """Verify all test EDI files exist."""
        missing_files = []

        for edi_file in baseline_manager.TEST_EDI_FILES:
            edi_path = baseline_manager.test_data_dir / edi_file
            if not edi_path.exists():
                missing_files.append(str(edi_path))

        assert not missing_files, f"Missing test EDI files: {missing_files}"
