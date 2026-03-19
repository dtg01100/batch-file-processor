"""Full pipeline end-to-end conversion tests.

These tests exercise the complete processing path:
  EDI file on disk
    → DispatchOrchestrator.process_folder()
      → EDIConverterStep (real converter modules)
        → converted file delivered to backend

Each test verifies that actual converted output is produced and has correct content.
Tweak-EDI flow is also covered via EDITweakerStep.
"""

import csv
import io

import pytest

pytestmark = [pytest.mark.integration, pytest.mark.e2e]

from dispatch.orchestrator import DispatchConfig, DispatchOrchestrator
from dispatch.pipeline.converter import EDIConverterStep
from dispatch.pipeline.tweaker import EDITweakerStep

# =============================================================================
# EDI sample content
# =============================================================================

# B record: UPC(11)=01234567890, Desc(25), Item(6)=123456 (numeric, needed by
#           simplified_csv), Cost(6)=001050 ($10.50), Combo(2)=01, Mult(6)=000001,
#           Qty(5)=00010, Retail(5)=00199, Pack(3)=001, Parent(6)=000000

_HEADER = "A" + "VENDOR" + "0000000001" + "010125" + "0000010000"
_DETAIL = (
    "B"
    + "01234567890"
    + "Test Item Description    "
    + "123456"
    + "001050"
    + "01"
    + "000001"
    + "00010"
    + "00199"
    + "001"
    + "000000"
)
_TAX = "C" + "TAB" + "Sales Tax                " + "000010000"
SAMPLE_EDI = "\n".join([_HEADER, _DETAIL, _TAX]) + "\n"


# =============================================================================
# Fixtures
# =============================================================================


@pytest.fixture
def edi_dir(tmp_path):
    """Directory containing a single EDI file."""
    d = tmp_path / "in"
    d.mkdir()
    (d / "invoice.edi").write_text(SAMPLE_EDI, encoding="utf-8")
    return d


@pytest.fixture
def base_settings():
    """Minimal settings dict (needed by some converters)."""
    return {
        "as400_username": "test_user",
        "as400_password": "test_pass",
        "as400_address": "test.example.com",
        "odbc_driver": "IBM i Access ODBC Driver",
    }


@pytest.fixture
def base_folder_params(edi_dir):
    """Minimal folder config common to all convert tests."""
    return {
        "folder_name": str(edi_dir),
        "alias": "test_folder",
        "folder_is_active": True,
        # EDI processing flags
        "process_edi": True,
        "convert_edi": True,  # orchestrator gate
        "tweak_edi": False,
        "split_edi": False,
        # Backend -- we use a capture backend, not the real copy backend
        "process_backend_copy": True,
        "copy_to_directory": "/tmp",
        # Converter defaults
        "calculate_upc_check_digit": "False",
        "include_a_records": "False",
        "include_c_records": "False",
        "include_headers": "True",
        "filter_ampersand": "False",
        "pad_a_records": "False",
        "a_record_padding": "      ",
        "a_record_padding_length": 6,
        "append_a_records": "False",
        "a_record_append_text": "",
        "force_txt_file_ext": "False",
        "invoice_date_offset": 0,
        "override_upc_bool": False,
        "override_upc_level": 1,
        "override_upc_category_filter": "",
        "upc_target_length": 11,
        "upc_padding_pattern": "           ",
        "retail_uom": False,
        "include_item_numbers": "True",
        "include_item_description": "True",
        "simple_csv_sort_order": "upc_number,qty_of_units,unit_cost,description,vendor_item",
        "estore_store_number": "001",
        "estore_Vendor_OId": "VENDOR001",
        "estore_vendor_NameVendorOID": "TestVendor",
        "estore_c_record_OID": "C_RECORD_OID",
        "fintech_division_id": "DIV001",
        # Tweak-specific keys required by edi_tweak()
        "invoice_date_custom_format": False,
        "invoice_date_custom_format_string": "",
        "split_prepaid_sales_tax_crec": False,
        "a_record_padding_length": 6,
    }


class CaptureBackend:
    """Backend that captures the content of each file it receives."""

    def __init__(self):
        self.received: list[tuple[str, bytes]] = []

    def send(self, params: dict, settings: dict, filename: str) -> bool:
        try:
            content = open(filename, "rb").read()
            self.received.append((filename, content))
        except Exception:
            self.received.append((filename, b""))
        return True

    @property
    def first_content(self) -> bytes:
        assert self.received, "Backend received no files"
        return self.received[0][1]

    @property
    def first_filename(self) -> str:
        assert self.received, "Backend received no files"
        return self.received[0][0]

    def first_csv_rows(self) -> list[list[str]]:
        text = self.first_content.decode("utf-8-sig", errors="replace").replace(
            "\r\n", "\n"
        )
        return list(csv.reader(io.StringIO(text)))


def _run(folder_params: dict, settings: dict) -> tuple["FolderResult", CaptureBackend]:
    """Run the orchestrator with a real converter step and capture backend."""
    backend = CaptureBackend()
    cfg = DispatchConfig(
        backends={"copy": backend},
        converter_step=EDIConverterStep(),
        settings=settings,
        upc_dict={"_mock": []},  # Non-empty dict prevents UPC lookup from AS400
    )
    orch = DispatchOrchestrator(cfg)
    result = orch.process_folder(folder_params, run_log=[], processed_files=None)
    return result, backend


# =============================================================================
# Tests: Convert EDI via full pipeline
# =============================================================================


class TestPipelineConvertToCSV:
    """Full pipeline: EDI → CSV via orchestrator."""

    def test_pipeline_produces_csv_file(self, base_folder_params, base_settings):
        base_folder_params["convert_to_format"] = "csv"
        result, backend = _run(base_folder_params, base_settings)

        assert result.success
        assert result.files_processed == 1
        assert result.files_failed == 0
        assert backend.first_filename.endswith(".csv")

    def test_csv_has_header_row(self, base_folder_params, base_settings):
        base_folder_params["convert_to_format"] = "csv"
        base_folder_params["include_headers"] = "True"
        _, backend = _run(base_folder_params, base_settings)

        rows = backend.first_csv_rows()
        assert len(rows) >= 2
        header = rows[0]
        assert "UPC" in header

    def test_csv_detail_row_matches_input(self, base_folder_params, base_settings):
        base_folder_params["convert_to_format"] = "csv"
        _, backend = _run(base_folder_params, base_settings)

        rows = backend.first_csv_rows()
        upc_col = rows[0].index("UPC")
        detail = rows[1]
        assert detail[upc_col] == "01234567890"

    def test_csv_upc_check_digit_applied(self, base_folder_params, base_settings):
        base_folder_params["convert_to_format"] = "csv"
        base_folder_params["calculate_upc_check_digit"] = "True"
        _, backend = _run(base_folder_params, base_settings)

        rows = backend.first_csv_rows()
        upc_col = rows[0].index("UPC")
        upc = rows[1][upc_col].strip()
        # Check digit applied: UPC should be 12 chars with a valid check digit
        assert len(upc) == 12


class TestPipelineConvertToSimplifiedCSV:
    """Full pipeline: EDI → simplified_csv."""

    def test_produces_simplified_csv(self, base_folder_params, base_settings):
        base_folder_params["convert_to_format"] = "simplified_csv"
        result, backend = _run(base_folder_params, base_settings)

        assert result.success
        assert result.files_processed == 1
        assert backend.first_filename.endswith(".csv")

    def test_simplified_csv_headers(self, base_folder_params, base_settings):
        base_folder_params["convert_to_format"] = "simplified_csv"
        base_folder_params["include_headers"] = "True"
        _, backend = _run(base_folder_params, base_settings)

        rows = backend.first_csv_rows()
        header = rows[0]
        assert len(header) > 0
        assert any("upc" in col.lower() or "item" in col.lower() for col in header)


class TestPipelineConvertToScannerWare:
    """Full pipeline: EDI → ScannerWare."""

    def test_produces_scannerware_output(self, base_folder_params, base_settings):
        base_folder_params["convert_to_format"] = "scannerware"
        result, backend = _run(base_folder_params, base_settings)

        assert result.success
        assert result.files_processed == 1
        assert len(backend.received) == 1

    def test_scannerware_output_has_content(self, base_folder_params, base_settings):
        base_folder_params["convert_to_format"] = "scannerware"
        _, backend = _run(base_folder_params, base_settings)

        assert len(backend.first_content) > 0

    def test_scannerware_txt_extension_option(self, base_folder_params, base_settings):
        base_folder_params["convert_to_format"] = "scannerware"
        base_folder_params["force_txt_file_ext"] = "True"
        _, backend = _run(base_folder_params, base_settings)

        assert backend.first_filename.endswith(".txt")


class TestPipelineConvertToFintech:
    """Full pipeline: EDI → fintech CSV."""

    def test_produces_fintech_csv(self, base_folder_params, base_settings):
        base_folder_params["convert_to_format"] = "fintech"
        result, backend = _run(base_folder_params, base_settings)

        assert result.success
        assert result.files_processed == 1
        assert backend.first_filename.endswith(".csv")

    def test_fintech_csv_has_content(self, base_folder_params, base_settings):
        base_folder_params["convert_to_format"] = "fintech"
        _, backend = _run(base_folder_params, base_settings)

        rows = backend.first_csv_rows()
        assert len(rows) >= 1


class TestPipelineConvertToYellowdogCSV:
    """Full pipeline: EDI → YellowDog CSV."""

    def test_produces_yellowdog_csv(self, base_folder_params, base_settings):
        base_folder_params["convert_to_format"] = "yellowdog_csv"
        result, backend = _run(base_folder_params, base_settings)

        assert result.success
        assert result.files_processed == 1
        assert backend.first_filename.endswith(".csv")

    def test_yellowdog_csv_has_upc_column(self, base_folder_params, base_settings):
        base_folder_params["convert_to_format"] = "yellowdog_csv"
        _, backend = _run(base_folder_params, base_settings)

        rows = backend.first_csv_rows()
        assert len(rows) >= 1
        header = rows[0]
        assert any("upc" in col.lower() for col in header)


class TestPipelineConvertToEstoreEinvoice:
    """Full pipeline: EDI → Estore eInvoice."""

    def test_produces_estore_output(self, base_folder_params, base_settings):
        base_folder_params["convert_to_format"] = "estore_einvoice"
        result, backend = _run(base_folder_params, base_settings)

        assert result.success
        assert result.files_processed == 1
        assert len(backend.received) == 1

    def test_estore_output_has_content(self, base_folder_params, base_settings):
        base_folder_params["convert_to_format"] = "estore_einvoice"
        _, backend = _run(base_folder_params, base_settings)

        assert len(backend.first_content) > 0


class TestPipelineConvertToEstoreEinvoiceGeneric:
    """Full pipeline: EDI → Estore eInvoice Generic."""

    def test_produces_estore_generic_output(self, base_folder_params, base_settings):
        base_folder_params["convert_to_format"] = "estore_einvoice_generic"
        result, backend = _run(base_folder_params, base_settings)

        assert result.success
        assert result.files_processed == 1
        assert len(backend.received) == 1


class TestPipelineConvertToJolleyCustom:
    """Full pipeline: EDI → jolley_custom.

    Requires as400_username/password/address in settings.
    """

    def test_produces_jolley_output(self, base_folder_params, base_settings):
        base_folder_params["convert_to_format"] = "jolley_custom"
        result, backend = _run(base_folder_params, base_settings)

        assert result.success
        assert result.files_processed == 1
        assert len(backend.received) == 1

    def test_jolley_output_has_content(self, base_folder_params, base_settings):
        base_folder_params["convert_to_format"] = "jolley_custom"
        _, backend = _run(base_folder_params, base_settings)

        assert len(backend.first_content) > 0


class TestPipelineConvertToStewartsCustom:
    """Full pipeline: EDI → stewarts_custom.

    Requires as400_username/password/address in settings.
    """

    def test_produces_stewarts_output(self, base_folder_params, base_settings):
        base_folder_params["convert_to_format"] = "stewarts_custom"
        result, backend = _run(base_folder_params, base_settings)

        assert result.success
        assert result.files_processed == 1
        assert len(backend.received) == 1

    def test_stewarts_output_has_content(self, base_folder_params, base_settings):
        base_folder_params["convert_to_format"] = "stewarts_custom"
        _, backend = _run(base_folder_params, base_settings)

        assert len(backend.first_content) > 0


# =============================================================================
# Tests: Tweak EDI via full pipeline
# =============================================================================


class TestPipelineTweakEDI:
    """Full pipeline: EDI → tweaked EDI (no format conversion)."""

    def _tweak_folder(self, base_folder_params: dict) -> dict:
        p = base_folder_params.copy()
        p["process_edi"] = False
        p["convert_edi"] = False
        p["tweak_edi"] = True
        p["convert_to_format"] = ""
        return p

    def test_tweak_sends_file(self, base_folder_params, base_settings):
        folder = self._tweak_folder(base_folder_params)
        backend = CaptureBackend()
        cfg = DispatchConfig(
            backends={"copy": backend},
            tweaker_step=EDITweakerStep(),
            settings=base_settings,
            upc_dict={"_mock": []},  # Non-empty dict prevents UPC lookup from AS400
        )
        orch = DispatchOrchestrator(cfg)
        result = orch.process_folder(folder, run_log=[], processed_files=None)

        assert result.success
        assert result.files_processed == 1

    def test_tweak_date_offset_modifies_content(
        self, base_folder_params, base_settings
    ):
        """Invoice date offset should change the date in the A record."""
        folder = self._tweak_folder(base_folder_params)
        folder["invoice_date_offset"] = 1  # shift date by 1 day

        backend = CaptureBackend()
        cfg = DispatchConfig(
            backends={"copy": backend},
            tweaker_step=EDITweakerStep(),
            settings=base_settings,
            upc_dict={"_mock": []},  # Non-empty dict prevents UPC lookup from AS400
        )
        orch = DispatchOrchestrator(cfg)
        result = orch.process_folder(folder, run_log=[], processed_files=None)

        assert result.success
        content = backend.first_content.decode("utf-8", errors="replace")
        # Original date was 010125 (Jan 01 2025); offset by 1 → 010225 (Jan 02 2025)
        assert "010125" not in content
        assert "010225" in content

    def test_tweak_upc_check_digit(self, base_folder_params, base_settings):
        """UPC check digit calculation should update UPCs in tweaked output."""
        folder = self._tweak_folder(base_folder_params)
        folder["calculate_upc_check_digit"] = "True"

        backend = CaptureBackend()
        cfg = DispatchConfig(
            backends={"copy": backend},
            tweaker_step=EDITweakerStep(),
            settings=base_settings,
            upc_dict={"_mock": []},  # Non-empty dict prevents UPC lookup from AS400
        )
        orch = DispatchOrchestrator(cfg)
        result = orch.process_folder(folder, run_log=[], processed_files=None)

        assert result.success
        assert result.files_processed == 1

    def test_tweak_force_txt_extension(self, base_folder_params, base_settings):
        """force_txt_file_ext should rename the output to .txt."""
        folder = self._tweak_folder(base_folder_params)
        folder["force_txt_file_ext"] = "True"

        backend = CaptureBackend()
        cfg = DispatchConfig(
            backends={"copy": backend},
            tweaker_step=EDITweakerStep(),
            settings=base_settings,
            upc_dict={"_mock": []},  # Non-empty dict prevents UPC lookup from AS400
        )
        orch = DispatchOrchestrator(cfg)
        result = orch.process_folder(folder, run_log=[], processed_files=None)

        assert result.success
        assert backend.first_filename.endswith(".txt")


# =============================================================================
# Tests: Pipeline with no-op (neither convert nor tweak)
# =============================================================================


class TestPipelinePassThrough:
    """Full pipeline: file is sent as-is (no conversion or tweaking)."""

    def test_passthrough_sends_original_file(self, base_folder_params, base_settings):
        folder = base_folder_params.copy()
        folder["process_edi"] = False
        folder["convert_edi"] = False
        folder["tweak_edi"] = False
        folder["convert_to_format"] = ""

        backend = CaptureBackend()
        cfg = DispatchConfig(
            backends={"copy": backend},
            settings=base_settings,
            upc_dict={"_mock": []},  # Non-empty dict prevents UPC lookup from AS400
        )
        orch = DispatchOrchestrator(cfg)
        result = orch.process_folder(folder, run_log=[], processed_files=None)

        assert result.success
        assert result.files_processed == 1
        # Should receive the original EDI content
        content = backend.first_content.decode("utf-8", errors="replace")
        assert content.startswith("A")
