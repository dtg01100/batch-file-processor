"""Tests that folder configurations saved to the database are correctly
mapped to their respective folder processing pipelines.

Covers:
- DB row → DispatchOrchestrator uses the right converter for each folder
- Multi-folder isolation: folder A config doesn't bleed into folder B
- Null/missing DB fields get proper defaults before reaching converters
- Tweak EDI config from DB activates the tweaker (not the converter)
- process_edi=True in DB triggers conversion (the DB→convert_edi mapping)
"""

import csv
import io

import pytest

pytestmark = [pytest.mark.integration]

from backend.database import sqlite_wrapper
from core.database import schema
from dispatch.orchestrator import DispatchConfig, DispatchOrchestrator
from dispatch.pipeline.converter import EDIConverterStep
from dispatch.pipeline.tweaker import EDITweakerStep

# =============================================================================
# Shared EDI content + helpers
# =============================================================================

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
SAMPLE_EDI = "\n".join([_HEADER, _DETAIL]) + "\n"


class CaptureBackend:
    """Capture every file the backend receives."""

    def __init__(self):
        self.received: list[tuple[str, bytes]] = []

    def send(self, params: dict, settings: dict, filename: str) -> bool:
        try:
            self.received.append((filename, open(filename, "rb").read()))
        except Exception:
            self.received.append((filename, b""))
        return True

    def first_csv_rows(self) -> list[list[str]]:
        assert self.received
        text = (
            self.received[0][1]
            .decode("utf-8-sig", errors="replace")
            .replace("\r\n", "\n")
        )
        return list(csv.reader(io.StringIO(text)))


@pytest.fixture
def temp_db(tmp_path):
    db = sqlite_wrapper.Database.connect(str(tmp_path / "folders.db"))
    schema.ensure_schema(db)
    return db


def _make_edi_dir(tmp_path, name="in"):
    d = tmp_path / name
    d.mkdir(exist_ok=True)
    (d / "invoice.edi").write_text(SAMPLE_EDI, encoding="utf-8")
    return d


def _run_folder_from_db(db, folder_id: int, extra_settings: dict = None) -> tuple:
    """Load a folder from the DB and run it through the orchestrator."""
    loaded = dict(db["folders"].find_one(id=folder_id))
    backend = CaptureBackend()
    cfg = DispatchConfig(
        backends={"copy": backend},
        converter_step=EDIConverterStep(),
        tweaker_step=EDITweakerStep(),
        settings=extra_settings or {},
        upc_dict={"_mock": []},  # Non-empty dict prevents UPC lookup from AS400
    )
    orch = DispatchOrchestrator(cfg)
    result = orch.process_folder(loaded, run_log=[], processed_files=None)
    return result, backend


# =============================================================================
# Tests: process_edi in DB triggers the right conversion
# =============================================================================


class TestProcessEDIMappingFromDB:
    """Verify that process_edi stored in DB maps to actual conversion."""

    def test_process_edi_true_triggers_csv_conversion(self, temp_db, tmp_path):
        indir = _make_edi_dir(tmp_path)
        fid = temp_db["folders"].insert(
            {
                "folder_name": str(indir),
                "alias": "csv-folder",
                "folder_is_active": True,
                "process_edi": True,
                "convert_to_format": "csv",
                "tweak_edi": False,
                "process_backend_copy": True,
                "copy_to_directory": "/tmp",
            }
        )
        result, backend = _run_folder_from_db(temp_db, fid)

        assert result.success
        assert result.files_processed == 1
        # The file delivered to the backend should be a converted CSV
        assert backend.received
        assert backend.received[0][0].endswith(
            ".csv"
        ), f"Expected .csv output, got: {backend.received[0][0]}"

    def test_process_edi_false_sends_original(self, temp_db, tmp_path):
        indir = _make_edi_dir(tmp_path)
        fid = temp_db["folders"].insert(
            {
                "folder_name": str(indir),
                "alias": "passthrough-folder",
                "folder_is_active": True,
                "process_edi": False,
                "tweak_edi": False,
                "process_backend_copy": True,
                "copy_to_directory": "/tmp",
            }
        )
        result, backend = _run_folder_from_db(temp_db, fid)

        assert result.success
        assert result.files_processed == 1
        # Original EDI file should be delivered unchanged
        assert backend.received
        content = backend.received[0][1].decode("utf-8", errors="replace")
        assert content.startswith("A"), "Original EDI should start with A record"

    def test_process_edi_csv_output_has_correct_columns(self, temp_db, tmp_path):
        indir = _make_edi_dir(tmp_path)
        fid = temp_db["folders"].insert(
            {
                "folder_name": str(indir),
                "alias": "csv-columns",
                "folder_is_active": True,
                "process_edi": True,
                "convert_to_format": "csv",
                "include_headers": True,
                "process_backend_copy": True,
                "copy_to_directory": "/tmp",
            }
        )
        result, backend = _run_folder_from_db(temp_db, fid)

        assert result.success
        rows = backend.first_csv_rows()
        header = rows[0]
        assert "UPC" in header
        detail = rows[1]
        upc_col = header.index("UPC")
        assert detail[upc_col] == "01234567890"

    def test_process_edi_with_simplified_csv_format(self, temp_db, tmp_path):
        indir = _make_edi_dir(tmp_path)
        fid = temp_db["folders"].insert(
            {
                "folder_name": str(indir),
                "alias": "simp-csv",
                "folder_is_active": True,
                "process_edi": True,
                "convert_to_format": "simplified_csv",
                "include_headers": True,
                "process_backend_copy": True,
                "copy_to_directory": "/tmp",
            }
        )
        result, backend = _run_folder_from_db(temp_db, fid)

        assert result.success
        assert backend.received[0][0].endswith(".csv")

    def test_process_edi_with_yellowdog_csv_format(self, temp_db, tmp_path):
        indir = _make_edi_dir(tmp_path)
        fid = temp_db["folders"].insert(
            {
                "folder_name": str(indir),
                "alias": "yellowdog",
                "folder_is_active": True,
                "process_edi": True,
                "convert_to_format": "yellowdog_csv",
                "process_backend_copy": True,
                "copy_to_directory": "/tmp",
            }
        )
        result, backend = _run_folder_from_db(temp_db, fid)

        assert result.success
        assert backend.received[0][0].endswith(".csv")


# =============================================================================
# Tests: tweak_edi config from DB activates the tweaker
# =============================================================================


class TestTweakEDIMappingFromDB:
    """Verify that convert_to_format='tweaks' in DB maps to actual EDI tweaking.

    NOTE: tweak_edi is deprecated; migration v44→v45 converts `tweak_edi=1`
    rows to `convert_to_format='tweaks'`.  Tests here always use the
    post-migration representation.
    """

    def test_tweak_edi_true_applies_date_offset(self, temp_db, tmp_path):
        indir = _make_edi_dir(tmp_path)
        fid = temp_db["folders"].insert(
            {
                "folder_name": str(indir),
                "alias": "tweak-folder",
                "folder_is_active": True,
                "process_edi": True,
                "convert_to_format": "tweaks",
                "invoice_date_offset": 1,  # shift Jan 01 → Jan 02
                "invoice_date_custom_format": False,
                "invoice_date_custom_format_string": "",
                "split_prepaid_sales_tax_crec": False,
                "process_backend_copy": True,
                "copy_to_directory": "/tmp",
            }
        )
        as400_settings = {
            "as400_username": "u",
            "as400_password": "p",
            "as400_address": "h",
        }
        result, backend = _run_folder_from_db(temp_db, fid, as400_settings)

        assert result.success
        assert result.files_processed == 1
        content = backend.received[0][1].decode("utf-8", errors="replace")
        # Original date 010125 should be shifted to 010225
        assert "010225" in content, f"Expected offset date in output; got:\n{content}"

    def test_tweak_edi_does_not_convert_to_csv(self, temp_db, tmp_path):
        indir = _make_edi_dir(tmp_path)
        fid = temp_db["folders"].insert(
            {
                "folder_name": str(indir),
                "alias": "tweak-noconvert",
                "folder_is_active": True,
                "process_edi": True,
                "convert_to_format": "tweaks",
                "invoice_date_custom_format": False,
                "invoice_date_custom_format_string": "",
                "split_prepaid_sales_tax_crec": False,
                "process_backend_copy": True,
                "copy_to_directory": "/tmp",
            }
        )
        as400_settings = {
            "as400_username": "u",
            "as400_password": "p",
            "as400_address": "h",
        }
        result, backend = _run_folder_from_db(temp_db, fid, as400_settings)

        assert result.success
        # Tweaked output is still EDI-like (not CSV)
        content = backend.received[0][1].decode("utf-8", errors="replace")
        assert not content.startswith("UPC,"), "Tweak should not produce a CSV header"

    def test_legacy_tweak_flag_matches_migrated_tweaks_output(self, temp_db, tmp_path):
        """Legacy tweak_edi rows and migrated tweaks-format rows produce same output.

        This guards upgrade compatibility: after migration clears tweak_edi and
        stores convert_to_format='tweaks', externally visible file content should
        remain unchanged.
        """
        indir_legacy = _make_edi_dir(tmp_path, "legacy")
        indir_migrated = _make_edi_dir(tmp_path, "migrated")

        # Legacy representation used by old DB rows.
        legacy_id = temp_db["folders"].insert(
            {
                "folder_name": str(indir_legacy),
                "alias": "legacy-tweak",
                "folder_is_active": True,
                "process_edi": False,
                "tweak_edi": True,
                "invoice_date_offset": 1,
                "invoice_date_custom_format": False,
                "invoice_date_custom_format_string": "",
                "split_prepaid_sales_tax_crec": False,
                "process_backend_copy": True,
                "copy_to_directory": "/tmp",
            }
        )

        # Post-migration representation expected in newer DBs.
        migrated_id = temp_db["folders"].insert(
            {
                "folder_name": str(indir_migrated),
                "alias": "migrated-tweaks",
                "folder_is_active": True,
                "process_edi": True,
                "tweak_edi": False,
                "convert_to_format": "tweaks",
                "invoice_date_offset": 1,
                "invoice_date_custom_format": False,
                "invoice_date_custom_format_string": "",
                "split_prepaid_sales_tax_crec": False,
                "process_backend_copy": True,
                "copy_to_directory": "/tmp",
            }
        )

        as400_settings = {
            "as400_username": "u",
            "as400_password": "p",
            "as400_address": "h",
        }

        legacy_result, legacy_backend = _run_folder_from_db(
            temp_db, legacy_id, as400_settings
        )
        migrated_result, migrated_backend = _run_folder_from_db(
            temp_db, migrated_id, as400_settings
        )

        assert legacy_result.success
        assert migrated_result.success
        assert legacy_backend.received
        assert migrated_backend.received

        legacy_content = legacy_backend.received[0][1].decode("utf-8", errors="replace")
        migrated_content = migrated_backend.received[0][1].decode(
            "utf-8", errors="replace"
        )

        # Equivalent external output for old/new profile representations.
        assert legacy_content == migrated_content
        assert "010225" in legacy_content  # offset applied in both cases
        assert not legacy_content.startswith("UPC,")


# =============================================================================
# Tests: multi-folder isolation
# =============================================================================


class TestMultiFolderIsolation:
    """Verify that different folder configs are applied independently."""

    def test_two_folders_use_their_own_formats(self, temp_db, tmp_path):
        """Folder A converts to CSV; folder B passes through. Neither bleeds config."""
        dir_a = _make_edi_dir(tmp_path, "a")
        dir_b = _make_edi_dir(tmp_path, "b")

        fid_a = temp_db["folders"].insert(
            {
                "folder_name": str(dir_a),
                "alias": "folder-a",
                "folder_is_active": True,
                "process_edi": True,
                "convert_to_format": "csv",
                "include_headers": True,
                "process_backend_copy": True,
                "copy_to_directory": "/tmp",
            }
        )
        fid_b = temp_db["folders"].insert(
            {
                "folder_name": str(dir_b),
                "alias": "folder-b",
                "folder_is_active": True,
                "process_edi": False,
                "tweak_edi": False,
                "process_backend_copy": True,
                "copy_to_directory": "/tmp",
            }
        )

        # Run each folder through the orchestrator
        result_a, backend_a = _run_folder_from_db(temp_db, fid_a)
        result_b, backend_b = _run_folder_from_db(temp_db, fid_b)

        assert result_a.success and result_b.success

        # A should be CSV; B should be raw EDI
        assert backend_a.received[0][0].endswith(".csv"), "Folder A should produce CSV"
        content_b = backend_b.received[0][1].decode("utf-8", errors="replace")
        assert content_b.startswith("A"), "Folder B should deliver original EDI"

    def test_two_folders_different_formats(self, temp_db, tmp_path):
        """Folder A → csv, Folder B → yellowdog_csv. Each uses its own format."""
        dir_a = _make_edi_dir(tmp_path, "fa")
        dir_b = _make_edi_dir(tmp_path, "fb")

        fid_a = temp_db["folders"].insert(
            {
                "folder_name": str(dir_a),
                "alias": "fmt-a",
                "folder_is_active": True,
                "process_edi": True,
                "convert_to_format": "csv",
                "process_backend_copy": True,
                "copy_to_directory": "/tmp",
            }
        )
        fid_b = temp_db["folders"].insert(
            {
                "folder_name": str(dir_b),
                "alias": "fmt-b",
                "folder_is_active": True,
                "process_edi": True,
                "convert_to_format": "yellowdog_csv",
                "process_backend_copy": True,
                "copy_to_directory": "/tmp",
            }
        )

        result_a, backend_a = _run_folder_from_db(temp_db, fid_a)
        result_b, backend_b = _run_folder_from_db(temp_db, fid_b)

        assert result_a.success and result_b.success
        assert backend_a.received[0][0].endswith(".csv")
        assert backend_b.received[0][0].endswith(".csv")

        # CSV has "Qty. Shipped"; YellowDog CSV has different columns -- just verify
        # both produced non-empty output with at least one data row
        rows_a = backend_a.first_csv_rows()
        rows_b = backend_b.first_csv_rows()
        assert len(rows_a) >= 1
        assert len(rows_b) >= 1

    def test_convert_folder_next_to_tweak_folder(self, temp_db, tmp_path):
        """Convert folder and tweak folder coexist without interfering."""
        dir_conv = _make_edi_dir(tmp_path, "conv")
        dir_tweak = _make_edi_dir(tmp_path, "tweak")

        fid_conv = temp_db["folders"].insert(
            {
                "folder_name": str(dir_conv),
                "alias": "conv-folder",
                "folder_is_active": True,
                "process_edi": True,
                "convert_to_format": "csv",
                "process_backend_copy": True,
                "copy_to_directory": "/tmp",
            }
        )
        fid_tweak = temp_db["folders"].insert(
            {
                "folder_name": str(dir_tweak),
                "alias": "tweak-folder",
                "folder_is_active": True,
                "process_edi": True,
                "convert_to_format": "tweaks",
                "invoice_date_offset": 2,
                "invoice_date_custom_format": False,
                "invoice_date_custom_format_string": "",
                "split_prepaid_sales_tax_crec": False,
                "process_backend_copy": True,
                "copy_to_directory": "/tmp",
            }
        )

        result_conv, backend_conv = _run_folder_from_db(temp_db, fid_conv)
        as400 = {
            "as400_username": "u",
            "as400_password": "p",
            "as400_address": "h",
        }
        result_tweak, backend_tweak = _run_folder_from_db(temp_db, fid_tweak, as400)

        assert result_conv.success and result_tweak.success

        # Convert folder → CSV
        assert backend_conv.received[0][0].endswith(".csv")

        # Tweak folder → EDI with date shifted
        content_tweak = backend_tweak.received[0][1].decode("utf-8", errors="replace")
        assert "010125" not in content_tweak, "Date should have been offset"


# =============================================================================
# Tests: NULL/missing DB fields get defaults
# =============================================================================


class TestNullFieldDefaultsFromDB:
    """Verify that NULL fields in the DB get proper defaults before conversion."""

    def test_null_upc_target_length_defaults_to_11(self, temp_db, tmp_path):
        indir = _make_edi_dir(tmp_path)
        # upc_target_length not set → NULL in DB
        fid = temp_db["folders"].insert(
            {
                "folder_name": str(indir),
                "alias": "null-upc-len",
                "folder_is_active": True,
                "process_edi": True,
                "convert_to_format": "csv",
                "process_backend_copy": True,
                "copy_to_directory": "/tmp",
                # upc_target_length deliberately omitted
            }
        )
        result, backend = _run_folder_from_db(temp_db, fid)

        # Should succeed (not crash with TypeError: int(None))
        assert result.success
        assert result.files_processed == 1

    def test_null_a_record_padding_length_defaults_to_6(self, temp_db, tmp_path):
        indir = _make_edi_dir(tmp_path)
        fid = temp_db["folders"].insert(
            {
                "folder_name": str(indir),
                "alias": "null-padding",
                "folder_is_active": True,
                "process_edi": True,
                "convert_to_format": "csv",
                "process_backend_copy": True,
                "copy_to_directory": "/tmp",
                # a_record_padding_length deliberately omitted
            }
        )
        result, backend = _run_folder_from_db(temp_db, fid)

        assert result.success

    def test_null_invoice_date_offset_defaults_to_zero(self, temp_db, tmp_path):
        indir = _make_edi_dir(tmp_path)
        fid = temp_db["folders"].insert(
            {
                "folder_name": str(indir),
                "alias": "null-date-offset",
                "folder_is_active": True,
                "process_edi": False,
                "tweak_edi": True,
                "invoice_date_custom_format": False,
                "invoice_date_custom_format_string": "",
                "split_prepaid_sales_tax_crec": False,
                "process_backend_copy": True,
                "copy_to_directory": "/tmp",
                # invoice_date_offset deliberately omitted
            }
        )
        as400 = {
            "as400_username": "u",
            "as400_password": "p",
            "as400_address": "h",
        }
        result, backend = _run_folder_from_db(temp_db, fid, as400)

        assert result.success
        # With offset=0, date should be unchanged
        content = backend.received[0][1].decode("utf-8", errors="replace")
        assert "010125" in content, "Date should be unchanged with zero offset"

    def test_minimal_folder_row_converts_without_crashing(self, temp_db, tmp_path):
        """The absolute minimum DB row (just folder_name and process_edi) must not crash."""
        indir = _make_edi_dir(tmp_path)
        fid = temp_db["folders"].insert(
            {
                "folder_name": str(indir),
                "alias": "minimal",
                "folder_is_active": True,
                "process_edi": True,
                "convert_to_format": "csv",
                "process_backend_copy": True,
                "copy_to_directory": "/tmp",
            }
        )
        result, _ = _run_folder_from_db(temp_db, fid)

        # Must not raise; success means conversion completed
        assert result.success
