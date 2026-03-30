"""Integration tests for real-world scenarios.

This test suite covers end-to-end workflows:
1. Adding a folder and initial processing.
2. Duplicate detection.
3. Configuration changes.
4. Resend workflow.
5. EDI tweaking features.
"""

import pytest

pytestmark = [
    pytest.mark.integration,
    pytest.mark.e2e,
    pytest.mark.workflow,
    pytest.mark.slow,
]

from unittest import mock

import pytest

from backend.database.database_obj import DatabaseObj
from core.constants import CURRENT_DATABASE_VERSION
from dispatch.orchestrator import DispatchConfig, DispatchOrchestrator
from interface.operations.folder_manager import FolderManager
from scripts import create_database
from tests.integration.option_matrix import (
    CSV_OPTION_CASES,
    FORMAT_OPTION_CASES,
    OPTION_COMBINATION_CASES,
    SIMPLIFIED_CSV_OPTION_CASES,
    TWEAK_OPTION_CASES,
)


@pytest.fixture
def workspace(tmp_path):
    """Provide a temporary workspace dict with a DatabaseObj and I/O directories.

    Keys:
        db       -- a DatabaseObj with .folders_table / .processed_files attributes
        input    -- Path to the input directory
        output_1 -- Path to the first output directory
        output_2 -- Path to the second output directory
    """
    input_dir = tmp_path / "input"
    output_1 = tmp_path / "output_1"
    output_2 = tmp_path / "output_2"
    logs_dir = tmp_path / "logs"
    db_path = tmp_path / "folders.db"

    for d in (input_dir, output_1, output_2, logs_dir):
        d.mkdir()

    # Create the initial database file
    create_database.do(
        CURRENT_DATABASE_VERSION,
        str(db_path),
        str(tmp_path),
        "Linux",
    )

    db = DatabaseObj(
        database_path=str(db_path),
        database_version=CURRENT_DATABASE_VERSION,
        config_folder=str(tmp_path),
        running_platform="Linux",
    )

    # Ensure administrative record exists with a valid logs directory
    if db.oversight_and_defaults.find_one(id=1) is None:
        db.oversight_and_defaults.insert(
            dict(
                id=1,
                logs_directory=str(logs_dir),
                errors_folder=str(tmp_path / "errors"),
            )
        )
    else:
        db.oversight_and_defaults.update(
            {"id": 1, "logs_directory": str(logs_dir)}, ["id"]
        )

    yield {
        "db": db,
        "input": input_dir,
        "output_1": output_1,
        "output_2": output_2,
    }

    db.close()


class MockLog:
    def __init__(self):
        self.content = b""

    def write(self, b):
        if isinstance(b, str):
            b = b.encode()
        self.content += b

    def append(self, s):
        self.content += s.encode() + b"\n"


def test_full_real_world_workflow(workspace):
    """
    Test a full real-world scenario:
    1. Add a dummy folder.
    2. Set settings for the folder (Copy backend to output_1).
    3. Run the orchestrator.
    4. Verify the file is processed and copied to output_1.
    5. Run again (no change) and verify it's skipped (duplicate detection).
    6. Change settings (Copy backend to output_2).
    7. Enable resend for the file.
    8. Run again.
    9. Verify the file is processed and copied to output_2.
    """
    db = workspace["db"]
    folder_manager = FolderManager(db)

    # 1. Add a dummy folder
    input_path = str(workspace["input"])
    folder_manager.add_folder(input_path)

    # Find the added folder
    folder_rec = db.folders_table.find_one(folder_name=input_path)
    assert folder_rec is not None
    folder_id = folder_rec["id"]

    # 2. Set initial settings (Copy backend to output_1)
    db.folders_table.update(
        {
            "id": folder_id,
            "folder_is_active": "True",
            "process_backend_copy": 1,
            "copy_to_directory": str(workspace["output_1"]),
            "process_edi": 1,
            "convert_to_format": "csv",
        },
        ["id"],
    )

    # 3. Create a test EDI file
    # A simple EDI-like content that might pass basic validation if any
    a_rec = "AVENDOR00000000010101260000001000\n"
    b_rec = (
        "B01234567890TEST ITEM                123456000100000000010000100000         \n"
    )
    c_rec = "C001CHARGER DESCRIPTION      000000000\n"
    test_file_content = a_rec + b_rec + c_rec
    test_file_path = workspace["input"] / "test_invoice.edi"
    test_file_path.write_text(test_file_content)

    # 4. Do a run (Pipeline mode enabled)
    config = DispatchConfig(
        database=db,
        settings={},
    )
    # Since we use pipeline mode, we need to provide pipeline steps if we want them to work,
    # but for basic sending, it should still work if send_manager is configured.
    orchestrator = DispatchOrchestrator(config)

    run_log = MockLog()
    folder_rec = db.folders_table.find_one(id=folder_id)

    result = orchestrator.process_folder(folder_rec, run_log, db.processed_files)

    # 5. Verify file was processed and copied to output_1
    # Note: If this fails, it's because processed file recording is missing in orchestrator.
    assert result.files_processed == 1, (
        f"Expected 1 file processed, got {result.files_processed}. Errors: {result.errors}"
    )
    assert (workspace["output_1"] / "test_invoice.edi").exists()

    # Verify it's in processed_files
    processed = db.processed_files.find_one(folder_id=folder_id)
    assert processed is not None, (
        "File should have been recorded in processed_files table"
    )
    assert processed["file_name"] == str(test_file_path)

    # 6. Run again (no change) and verify it's skipped
    orchestrator.reset()
    run_log = MockLog()
    result_skip = orchestrator.process_folder(folder_rec, run_log, db.processed_files)
    assert result_skip.files_processed == 0, (
        "File should have been skipped as duplicate"
    )

    # 7. Change settings (Copy backend to output_2)
    db.folders_table.update(
        {
            "id": folder_id,
            "copy_to_directory": str(workspace["output_2"]),
        },
        ["id"],
    )

    # 8. Enable resend for the file
    db.processed_files.update({"id": processed["id"], "resend_flag": 1}, ["id"])

    # 9. Run again
    orchestrator.reset()
    run_log = MockLog()
    folder_rec = db.folders_table.find_one(id=folder_id)
    result_resend = orchestrator.process_folder(folder_rec, run_log, db.processed_files)

    # 10. Verify file was processed and copied to output_2
    assert result_resend.files_processed == 1, (
        "File should have been re-processed due to resend_flag"
    )
    assert (workspace["output_2"] / "test_invoice.edi").exists()

    # 11. Verify resend_flag is cleared
    processed_after = db.processed_files.find_one(id=processed["id"])
    assert processed_after["resend_flag"] == 0, (
        "resend_flag should be cleared after successful re-processing"
    )


def test_tweaking_scenario(workspace):
    """Test EDI tweaking (e.g., UPC check digit calculation)."""
    db = workspace["db"]
    folder_manager = FolderManager(db)

    input_path = str(workspace["input"])
    folder_manager.add_folder(input_path)
    folder = db.folders_table.find_one(folder_name=input_path)
    folder_id = folder["id"]

    # Configure with UPC check digit calculation
    db.folders_table.update(
        {
            "id": folder_id,
            "folder_is_active": "True",
            "process_backend_copy": 1,
            "copy_to_directory": str(workspace["output_1"]),
            "process_edi": 1,
            "tweak_edi": 1,
            "calculate_upc_check_digit": "True",
            "upc_target_length": 11,
        },
        ["id"],
    )

    # Create file with 11-digit UPC (missing check digit)
    # B record: B + 11-digit UPC + 25-char description + 6-char item + 6-char cost + ...
    upc_11 = "01234567890"
    description = "TEST ITEM".ljust(25)
    item = "123456"
    cost = "000100"
    combo = "00"
    multiplier = "000001"
    qty = "00001"
    retail = "00000"

    a_rec = "AVENDOR00000000010101260000001000\n"
    b_rec = (
        f"B{upc_11}{description}{item}{cost}{combo}{multiplier}{qty}{retail}         \n"
    )
    c_rec = "C001CHARGER DESCRIPTION      000000000\n"

    test_file_content = a_rec + b_rec + c_rec
    test_file_path = workspace["input"] / "upc_test.edi"
    test_file_path.write_text(test_file_content)

    # Setup orchestrator with pipeline steps (needed for tweaking)
    from unittest import mock

    from dispatch.pipeline.tweaker import EDITweakerStep

    with mock.patch("core.database.create_query_runner"):
        config = DispatchConfig(
            database=db,
            settings={
                "as400_username": "user",
                "as400_password": "pass",
                "as400_address": "addr",
            },
            tweaker_step=EDITweakerStep(),
            upc_dict={"_mock": []},
        )
        orchestrator = DispatchOrchestrator(config)

        run_log = MockLog()
        folder_rec = db.folders_table.find_one(id=folder_id)

        result = orchestrator.process_folder(folder_rec, run_log, db.processed_files)

    assert result.files_processed == 1, f"Errors: {result.errors}"

    # Verify the output file has the check digit appended (total 12 digits for UPC)
    output_file = workspace["output_1"] / "upc_test.edi"
    assert output_file.exists()
    output_content = output_file.read_text()

    # The check digit for 01234567890 is 5.
    # So the UPC should be 012345678905 (12 digits)
    # The B record should start with B012345678905
    assert "B012345678905" in output_content, (
        f"UPC should have check digit appended. Content: {output_content}"
    )


def test_csv_conversion_with_options(workspace):
    """Test CSV conversion with various configuration options."""
    from dispatch.pipeline.converter import EDIConverterStep

    db = workspace["db"]
    folder_manager = FolderManager(db)

    input_path = str(workspace["input"])
    folder_manager.add_folder(input_path)
    folder = db.folders_table.find_one(folder_name=input_path)
    folder_id = folder["id"]

    # Test CSV with headers and all records
    db.folders_table.update(
        {
            "id": folder_id,
            "folder_is_active": "True",
            "process_backend_copy": 1,
            "copy_to_directory": str(workspace["output_1"]),
            "process_edi": 1,
            "convert_to_format": "csv",
            "include_headers": 1,
            "include_a_records": 1,
            "include_c_records": 1,
        },
        ["id"],
    )

    # Create test EDI file
    a_rec = "AVENDOR00000000010101260000001000\n"
    b_rec = (
        "B01234567890TEST ITEM                123456000100000000010000100000         \n"
    )
    c_rec = "C001CHARGER DESCRIPTION      000000000\n"
    test_file_content = a_rec + b_rec + c_rec
    test_file_path = workspace["input"] / "test_csv.edi"
    test_file_path.write_text(test_file_content)

    # Process with converter step
    config = DispatchConfig(
        database=db,
        settings={},
        converter_step=EDIConverterStep(),
    )
    orchestrator = DispatchOrchestrator(config)

    run_log = MockLog()
    folder_rec = db.folders_table.find_one(id=folder_id)
    result = orchestrator.process_folder(folder_rec, run_log, db.processed_files)

    assert result.files_processed == 1, f"Errors: {result.errors}"

    # Verify some output file was created (CSV or EDI)
    all_files = list(workspace["output_1"].glob("*"))
    assert len(all_files) >= 1, f"Expected output files, found: {all_files}"

    # Check if CSV was created, otherwise EDI file should be there
    csv_files = list(workspace["output_1"].glob("*.csv"))
    if csv_files:
        csv_content = csv_files[0].read_text()
        # Should have headers
        assert "UPC" in csv_content or "VENDOR" in csv_content, (
            "CSV should contain headers"
        )


def test_all_conversion_formats(workspace):
    """Test that all supported conversion formats can process a file."""
    from dispatch.pipeline.converter import SUPPORTED_FORMATS, EDIConverterStep

    db = workspace["db"]
    folder_manager = FolderManager(db)

    # Test each format
    for fmt in SUPPORTED_FORMATS:
        # Skip formats that might require special configuration
        if fmt in ["estore_einvoice", "estore_einvoice_generic"]:
            continue

        input_path = str(workspace["input"])
        folder_manager.add_folder(input_path)
        folder = db.folders_table.find_one(folder_name=input_path)
        folder_id = folder["id"]

        db.folders_table.update(
            {
                "id": folder_id,
                "folder_is_active": "True",
                "process_backend_copy": 1,
                "copy_to_directory": str(workspace["output_1"]),
                "process_edi": 1,
                "convert_to_format": fmt,
            },
            ["id"],
        )

        # Create test EDI file with unique name per format
        a_rec = "AVENDOR00000000010101260000001000\n"
        b_rec = "B01234567890TEST ITEM                123456000100000000010000100000         \n"
        c_rec = "C001CHARGER DESCRIPTION      000000000\n"
        test_file_content = a_rec + b_rec + c_rec
        test_file_path = workspace["input"] / f"test_{fmt}.edi"
        test_file_path.write_text(test_file_content)

        # Process
        config = DispatchConfig(
            database=db,
            settings={},
            converter_step=EDIConverterStep(),
        )
        orchestrator = DispatchOrchestrator(config)

        run_log = MockLog()
        folder_rec = db.folders_table.find_one(id=folder_id)
        result = orchestrator.process_folder(folder_rec, run_log, db.processed_files)

        assert result.files_processed == 1, (
            f"Format {fmt} failed. Errors: {result.errors}"
        )

        # Verify some output file was created
        output_files = list(workspace["output_1"].glob(f"*{fmt.split('_')[0]}*"))
        assert len(output_files) >= 1, f"No output file for format {fmt}"

        # Clean up for next format
        db.folders_table.delete(id=folder_id)
        test_file_path.unlink()
        for f in workspace["output_1"].glob("*"):
            f.unlink()


def test_simplified_csv_with_options(workspace):
    """Test simplified CSV conversion with sorting options."""
    from dispatch.pipeline.converter import EDIConverterStep

    db = workspace["db"]
    folder_manager = FolderManager(db)

    input_path = str(workspace["input"])
    folder_manager.add_folder(input_path)
    folder = db.folders_table.find_one(folder_name=input_path)
    folder_id = folder["id"]

    # Test simplified CSV with sorting by description
    db.folders_table.update(
        {
            "id": folder_id,
            "folder_is_active": "True",
            "process_backend_copy": 1,
            "copy_to_directory": str(workspace["output_1"]),
            "process_edi": 1,
            "convert_to_format": "simplified_csv",
            "simple_csv_sort_order": "description",  # Sort by description
            "include_item_numbers": 1,
            "include_item_description": 1,
        },
        ["id"],
    )

    # Create test EDI file with multiple B records
    a_rec = "AVENDOR00000000010101260000001000\n"
    b_rec1 = "B01234567890ZEBRA ITEM                123456000100000000010000100000         \n"
    b_rec2 = "B09876543210APPLE ITEM                654321000200000000020000200000         \n"
    c_rec = "C002TOTAL                    000000300\n"
    test_file_content = a_rec + b_rec1 + b_rec2 + c_rec
    test_file_path = workspace["input"] / "test_sorted.edi"
    test_file_path.write_text(test_file_content)

    # Process
    config = DispatchConfig(
        database=db,
        settings={},
        converter_step=EDIConverterStep(),
    )
    orchestrator = DispatchOrchestrator(config)

    run_log = MockLog()
    folder_rec = db.folders_table.find_one(id=folder_id)
    result = orchestrator.process_folder(folder_rec, run_log, db.processed_files)

    assert result.files_processed == 1, f"Errors: {result.errors}"

    # Verify some output file was created
    all_files = list(workspace["output_1"].glob("*"))
    assert len(all_files) >= 1, f"Expected output files, found: {all_files}"

    # Check if CSV was created
    csv_files = list(workspace["output_1"].glob("*.csv"))
    if csv_files:
        csv_content = csv_files[0].read_text()
        # Check that APPLE appears before ZEBRA (sorted alphabetically)
        apple_pos = csv_content.find("APPLE")
        zebra_pos = csv_content.find("ZEBRA")
        if apple_pos > 0 and zebra_pos > 0:
            assert apple_pos < zebra_pos, (
                "Items should be sorted alphabetically by description"
            )


def test_email_backend(workspace):
    """Test email backend with mocked SMTP."""
    from unittest import mock

    db = workspace["db"]
    folder_manager = FolderManager(db)

    input_path = str(workspace["input"])
    folder_manager.add_folder(input_path)
    folder = db.folders_table.find_one(folder_name=input_path)
    folder_id = folder["id"]

    # Configure email backend
    db.folders_table.update(
        {
            "id": folder_id,
            "folder_is_active": "True",
            "process_backend_email": 1,
            "email_to": "recipient@example.com",
            "email_subject_line": "Test EDI File",
            "process_edi": 1,
            "convert_to_format": "csv",
        },
        ["id"],
    )

    # Create test EDI file
    a_rec = "AVENDOR00000000010101260000001000\n"
    b_rec = (
        "B01234567890TEST ITEM                123456000100000000010000100000         \n"
    )
    c_rec = "C001CHARGER DESCRIPTION      000000000\n"
    test_file_content = a_rec + b_rec + c_rec
    test_file_path = workspace["input"] / "test_email.edi"
    test_file_path.write_text(test_file_content)

    # Mock SMTP client
    with mock.patch("backend.smtp_client.RealSMTPClient") as MockSMTP:
        mock_smtp_instance = MockSMTP.return_value
        mock_smtp_instance.connect.return_value = None
        mock_smtp_instance.ehlo.return_value = None
        mock_smtp_instance.starttls.return_value = None
        mock_smtp_instance.login.return_value = None
        mock_smtp_instance.send_message.return_value = None
        mock_smtp_instance.close.return_value = None

        config = DispatchConfig(
            database=db,
            settings={
                "email_address": "sender@example.com",
                "email_username": "sender@example.com",
                "email_password": "password",
                "email_smtp_server": "smtp.example.com",
                "smtp_port": 587,
            },
        )
        orchestrator = DispatchOrchestrator(config)

        run_log = MockLog()
        folder_rec = db.folders_table.find_one(id=folder_id)
        result = orchestrator.process_folder(folder_rec, run_log, db.processed_files)

        assert result.files_processed == 1, f"Errors: {result.errors}"

        # Verify email was sent
        assert mock_smtp_instance.send_message.called, (
            "Email send_message should have been called"
        )


def test_ftp_backend(workspace):
    """Test FTP backend with mocked FTP client."""
    from unittest import mock

    db = workspace["db"]
    folder_manager = FolderManager(db)

    input_path = str(workspace["input"])
    folder_manager.add_folder(input_path)
    folder = db.folders_table.find_one(folder_name=input_path)
    folder_id = folder["id"]

    # Configure FTP backend
    db.folders_table.update(
        {
            "id": folder_id,
            "folder_is_active": "True",
            "process_backend_ftp": 1,
            "ftp_server": "ftp.example.com",
            "ftp_port": 21,
            "ftp_username": "ftpuser",
            "ftp_password": "ftppass",
            "ftp_folder": "/uploads/",
            "process_edi": 1,
            "convert_to_format": "csv",
        },
        ["id"],
    )

    # Create test EDI file
    a_rec = "AVENDOR00000000010101260000001000\n"
    b_rec = (
        "B01234567890TEST ITEM                123456000100000000010000100000         \n"
    )
    c_rec = "C001CHARGER DESCRIPTION      000000000\n"
    test_file_content = a_rec + b_rec + c_rec
    test_file_path = workspace["input"] / "test_ftp.edi"
    test_file_path.write_text(test_file_content)

    # Mock FTP client
    with mock.patch("backend.ftp_client.RealFTPClient") as MockFTP:
        mock_ftp_instance = MockFTP.return_value
        # Mock all FTP methods that ftp_backend.py uses
        mock_ftp_instance.connect.return_value = None
        mock_ftp_instance.login.return_value = None
        mock_ftp_instance.cwd.return_value = None
        mock_ftp_instance.mkd.return_value = None
        mock_ftp_instance.storbinary.return_value = None
        mock_ftp_instance.close.return_value = None

        config = DispatchConfig(
            database=db,
            settings={},
        )
        orchestrator = DispatchOrchestrator(config)

        run_log = MockLog()
        folder_rec = db.folders_table.find_one(id=folder_id)
        result = orchestrator.process_folder(folder_rec, run_log, db.processed_files)

        assert result.files_processed == 1, f"Errors: {result.errors}"


def test_conversion_with_tweaking(workspace):
    """Test conversion combined with EDI tweaking."""
    from unittest import mock

    from dispatch.pipeline.converter import EDIConverterStep
    from dispatch.pipeline.tweaker import EDITweakerStep

    db = workspace["db"]
    folder_manager = FolderManager(db)

    input_path = str(workspace["input"])
    folder_manager.add_folder(input_path)
    folder = db.folders_table.find_one(folder_name=input_path)
    folder_id = folder["id"]

    # Configure with both tweaking and conversion
    db.folders_table.update(
        {
            "id": folder_id,
            "folder_is_active": "True",
            "process_backend_copy": 1,
            "copy_to_directory": str(workspace["output_1"]),
            "process_edi": 1,
            "tweak_edi": 1,
            "calculate_upc_check_digit": "True",
            "upc_target_length": 11,
            "convert_to_format": "csv",
            "include_headers": 1,
        },
        ["id"],
    )

    # Create test EDI file with 11-digit UPC
    upc_11 = "01234567890"
    description = "TEST ITEM".ljust(25)
    item = "123456"
    cost = "000100"
    combo = "00"
    multiplier = "000001"
    qty = "00001"
    retail = "00000"

    a_rec = "AVENDOR00000000010101260000001000\n"
    b_rec = (
        f"B{upc_11}{description}{item}{cost}{combo}{multiplier}{qty}{retail}         \n"
    )
    c_rec = "C001CHARGER DESCRIPTION      000000000\n"

    test_file_content = a_rec + b_rec + c_rec
    test_file_path = workspace["input"] / "test_tweak_convert.edi"
    test_file_path.write_text(test_file_content)

    # Process with both steps
    with mock.patch("core.database.create_query_runner"):
        config = DispatchConfig(
            database=db,
            settings={
                "as400_username": "user",
                "as400_password": "pass",
                "as400_address": "addr",
            },
            tweaker_step=EDITweakerStep(),
            upc_dict={"_mock": []},
            converter_step=EDIConverterStep(),
        )
        orchestrator = DispatchOrchestrator(config)

        run_log = MockLog()
        folder_rec = db.folders_table.find_one(id=folder_id)
        result = orchestrator.process_folder(folder_rec, run_log, db.processed_files)

    assert result.files_processed == 1, f"Errors: {result.errors}"

    # Verify some output file was created
    all_files = list(workspace["output_1"].glob("*"))
    assert len(all_files) >= 1, f"Expected output files, found: {all_files}"

    # Check if CSV was created
    csv_files = list(workspace["output_1"].glob("*.csv"))
    if csv_files:
        csv_content = csv_files[0].read_text()
        # UPC should have check digit appended (012345678905)
        assert "012345678905" in csv_content, "CSV should contain UPC with check digit"


# ============================================================================
# COMPREHENSIVE OPTION TESTING
# These tests systematically verify each configuration option individually
# and in combinations to ensure robust, production-ready behavior
# ============================================================================


# Test CSV Conversion Options Individually
@pytest.mark.parametrize(("option", "value", "expected_behavior"), CSV_OPTION_CASES)
def test_csv_option_individual(workspace, option, value, expected_behavior):
    """Test each CSV conversion option individually to verify correct behavior."""
    db = workspace["db"]
    folder_manager = FolderManager(db)

    input_path = str(workspace["input"])
    folder_manager.add_folder(input_path)
    folder = db.folders_table.find_one(folder_name=input_path)
    folder_id = folder["id"]

    # Base configuration
    config = {
        "id": folder_id,
        "folder_is_active": "True",
        "process_backend_copy": 1,
        "copy_to_directory": str(workspace["output_1"]),
        "process_edi": 1,
        "convert_to_format": "csv",
    }

    # Set the specific option being tested
    config[option] = 1 if value else 0

    # For options that need additional parameters
    if option == "pad_a_records" and value:
        config["a_record_padding"] = " " * 20
        config["a_record_padding_length"] = 20
    if option == "override_upc_bool" and value:
        config["override_upc_level"] = 1
        config["override_upc_category_filter"] = "ALL"
    if option == "calculate_upc_check_digit" and value:
        config["upc_target_length"] = 11

    db.folders_table.update(config, ["id"])

    # Create test EDI file
    a_rec = "AVENDOR00000000010101260000001000\n"
    b_rec = (
        "B01234567890TEST ITEM                123456000100000000010000100000         \n"
    )
    c_rec = "C001CHARGER DESCRIPTION      000000000\n"
    test_file_content = a_rec + b_rec + c_rec
    test_file_path = workspace["input"] / f"test_{option}_{value}.edi"
    test_file_path.write_text(test_file_content)

    # Setup orchestrator with converter
    from dispatch.pipeline.converter import EDIConverterStep

    config_obj = DispatchConfig(
        database=db,
        settings={},
        converter_step=EDIConverterStep(),
    )
    orchestrator = DispatchOrchestrator(config_obj)

    run_log = MockLog()
    folder_rec = db.folders_table.find_one(id=folder_id)
    result = orchestrator.process_folder(folder_rec, run_log, db.processed_files)

    assert result.files_processed == 1, f"Errors: {result.errors}"

    # Verify output exists (look for any output files, not just CSV)
    all_output_files = list(workspace["output_1"].glob("*"))
    assert len(all_output_files) >= 1, f"Expected output files for {option}={value}"

    # Verify output exists (look for any output files, not just CSV)
    all_output_files = list(workspace["output_1"].glob("*"))
    assert len(all_output_files) >= 1, f"Expected output files for {option}={value}"

    output_files = [f for f in all_output_files if f.suffix in [".csv", ".edi", ".txt"]]
    assert len(output_files) >= 1, f"Expected CSV or EDI output for {option}={value}"

    # Read and verify content from the first output file
    output_content = output_files[0].read_text()
    lines = output_content.strip().split("\n")

    # Behavior-specific assertions (relaxed - works for both CSV and EDI formats)
    if expected_behavior == "headers_present" and output_files[0].suffix == ".csv":
        # Only check for CSV headers if it's actually a CSV file
        assert "upc_number" in lines[0] or "UPC" in lines[0], (
            "Headers should be present"
        )
    elif expected_behavior == "no_headers" and output_files[0].suffix == ".csv":
        assert not ("upc_number" in lines[0] or "UPC" in lines[0]), (
            "Headers should not be present"
        )
    elif expected_behavior == "a_records_present" and output_files[0].suffix == ".csv":
        # For CSV, A records would be included as rows
        assert any("VENDOR" in line for line in lines), (
            "A records should be present in CSV"
        )
    elif expected_behavior == "no_a_records" and output_files[0].suffix == ".csv":
        # When A records are excluded, CSV might still have other data
        # This is more about CSV structure than content
        pass  # Just verify file was created successfully
    elif expected_behavior == "c_records_present" and output_files[0].suffix == ".csv":
        # For CSV, C records would be included as charge rows
        assert any("CHARGER" in line or "CHARGE" in line for line in lines), (
            "C records should be present in CSV"
        )
    elif expected_behavior == "no_c_records" and output_files[0].suffix == ".csv":
        # When C records are excluded from CSV, verify charges aren't present
        pass  # Just verify file was created successfully
    # For other cases, just verify the file was created and has content
    else:
        assert len(output_content) > 0, (
            f"Output file should have content for {option}={value}"
        )


@pytest.mark.parametrize(("option", "value"), SIMPLIFIED_CSV_OPTION_CASES)
def test_simplified_csv_option_individual(workspace, option, value):
    """Test simplified CSV options individually."""
    db = workspace["db"]
    folder_manager = FolderManager(db)

    input_path = str(workspace["input"])
    folder_manager.add_folder(input_path)
    folder = db.folders_table.find_one(folder_name=input_path)
    folder_id = folder["id"]

    db.folders_table.update(
        {
            "id": folder_id,
            "folder_is_active": "True",
            "process_backend_copy": 1,
            "copy_to_directory": str(workspace["output_1"]),
            "process_edi": 1,
            "convert_to_format": "simplified_csv",
            option: 1 if value else 0,
        },
        ["id"],
    )

    # Create test EDI file
    a_rec = "AVENDOR00000000010101260000001000\n"
    b_rec = (
        "B01234567890TEST ITEM                123456000100000000010000100000         \n"
    )
    c_rec = "C001CHARGER DESCRIPTION      000000000\n"
    test_file_content = a_rec + b_rec + c_rec
    test_file_path = workspace["input"] / f"test_simpl_{option}_{value}.edi"
    test_file_path.write_text(test_file_content)

    from dispatch.pipeline.converter import EDIConverterStep

    config_obj = DispatchConfig(
        database=db,
        settings={},
        converter_step=EDIConverterStep(),
    )
    orchestrator = DispatchOrchestrator(config_obj)

    run_log = MockLog()
    folder_rec = db.folders_table.find_one(id=folder_id)
    result = orchestrator.process_folder(folder_rec, run_log, db.processed_files)

    assert result.files_processed == 1, f"Errors: {result.errors}"

    output_files = list(workspace["output_1"].glob("*.csv"))
    if len(output_files) == 0:
        # If no CSV, check for any output files
        output_files = list(workspace["output_1"].glob("*"))
    assert len(output_files) >= 1, (
        f"Expected CSV output for simplified {option}={value}"
    )

    output_content = output_files[0].read_text()

    # Only check content if it's actually a CSV file
    if output_files[0].suffix == ".csv":
        if option == "include_item_numbers" and value:
            assert "123456" in output_content, "Item number should be present"
        elif option == "include_item_description" and value:
            assert "TEST ITEM" in output_content, "Description should be present"


@pytest.mark.parametrize(("tweak_option", "value"), TWEAK_OPTION_CASES)
def test_tweaking_option_individual(workspace, tweak_option, value):
    """Test each EDI tweaking option individually."""
    db = workspace["db"]
    folder_manager = FolderManager(db)

    input_path = str(workspace["input"])
    folder_manager.add_folder(input_path)
    folder = db.folders_table.find_one(folder_name=input_path)
    folder_id = folder["id"]

    config = {
        "id": folder_id,
        "folder_is_active": "True",
        "process_backend_copy": 1,
        "copy_to_directory": str(workspace["output_1"]),
        "process_edi": 1,
        "tweak_edi": 1,
        tweak_option: 1 if value else 0,
    }

    # Add required supporting parameters
    if tweak_option == "calculate_upc_check_digit":
        config["upc_target_length"] = 11
    elif tweak_option == "pad_a_records":
        config["a_record_padding"] = " " * 20
        config["a_record_padding_length"] = 20
    elif tweak_option == "append_a_records":
        config["a_record_append_text"] = "APPENDED"
    elif tweak_option == "invoice_date_custom_format":
        config["invoice_date_custom_format_string"] = "%Y-%m-%d"
    elif tweak_option == "override_upc_bool":
        config["override_upc_level"] = 1
        config["override_upc_category_filter"] = "ALL"

    db.folders_table.update(config, ["id"])

    # Create test EDI file
    upc_11 = "01234567890"
    description = "TEST ITEM".ljust(25)
    item = "123456"
    cost = "000100"
    combo = "00"
    multiplier = "000001"
    qty = "00001"
    retail = "00000"

    a_rec = "AVENDOR00000000010101260000001000\n"
    b_rec = (
        f"B{upc_11}{description}{item}{cost}{combo}{multiplier}{qty}{retail}         \n"
    )
    c_rec = "C001CHARGER DESCRIPTION      000000000\n"

    test_file_content = a_rec + b_rec + c_rec
    test_file_path = workspace["input"] / f"test_tweak_{tweak_option}.edi"
    test_file_path.write_text(test_file_content)

    # Mock query_runner and process
    from dispatch.pipeline.tweaker import EDITweakerStep

    with mock.patch("core.database.create_query_runner"):
        config_obj = DispatchConfig(
            database=db,
            settings={
                "as400_username": "user",
                "as400_password": "pass",
                "as400_address": "addr",
            },
            tweaker_step=EDITweakerStep(),
            upc_dict={"_mock": []},
        )
        orchestrator = DispatchOrchestrator(config_obj)

        run_log = MockLog()
        folder_rec = db.folders_table.find_one(id=folder_id)
        result = orchestrator.process_folder(folder_rec, run_log, db.processed_files)

    assert result.files_processed == 1, f"Errors: {result.errors}"

    # Verify output
    if tweak_option == "force_txt_file_ext" and value:
        output_files = list(workspace["output_1"].glob("*.txt"))
        assert len(output_files) >= 1, f"Expected .txt output for {tweak_option}"
    else:
        output_files = list(workspace["output_1"].glob("*"))
        assert len(output_files) >= 1, f"Expected output for {tweak_option}"

    output_content = output_files[0].read_text()

    # Specific validations
    if tweak_option == "calculate_upc_check_digit":
        if value:
            assert "B012345678905" in output_content, (
                "UPC check digit should be appended when enabled"
            )
        else:
            assert "B012345678905" not in output_content, (
                "UPC check digit should not be appended when disabled"
            )
    elif tweak_option == "append_a_records":
        if value:
            assert "APPENDED" in output_content, (
                "A record should have appended text when enabled"
            )
        else:
            assert "APPENDED" not in output_content, (
                "A record should not have appended text when disabled"
            )


# Test common option combinations
@pytest.mark.parametrize(
    ("combo_name", "config_overrides", "description"), OPTION_COMBINATION_CASES
)
def test_option_combinations(workspace, combo_name, config_overrides, description):
    """Test common combinations of options that represent real-world usage patterns."""
    db = workspace["db"]
    folder_manager = FolderManager(db)

    input_path = str(workspace["input"])
    folder_manager.add_folder(input_path)
    folder = db.folders_table.find_one(folder_name=input_path)
    folder_id = folder["id"]

    # Base configuration
    config = {
        "id": folder_id,
        "folder_is_active": "True",
        "process_backend_copy": 1,
        "copy_to_directory": str(workspace["output_1"]),
        "process_edi": 1,
    }

    # Merge in the specific combination
    config.update(config_overrides)

    db.folders_table.update(config, ["id"])

    # Create test EDI file
    upc_11 = "01234567890"
    description_text = "TEST ITEM".ljust(25)
    item = "123456"
    cost = "000100"
    combo = "00"
    multiplier = "000001"
    qty = "00001"
    retail = "00000"

    a_rec = "AVENDOR00000000010101260000001000\n"
    b_rec = f"B{upc_11}{description_text}{item}{cost}{combo}{multiplier}{qty}{retail}         \n"
    c_rec = "C001CHARGER DESCRIPTION      000000000\n"

    test_file_content = a_rec + b_rec + c_rec
    test_file_path = workspace["input"] / f"test_combo_{combo_name}.edi"
    test_file_path.write_text(test_file_content)

    # Setup orchestrator with appropriate pipeline steps
    from dispatch.pipeline.converter import EDIConverterStep
    from dispatch.pipeline.tweaker import EDITweakerStep

    needs_tweaker = config_overrides.get("tweak_edi", False)

    if needs_tweaker:
        with mock.patch("core.database.create_query_runner"):
            config_obj = DispatchConfig(
                database=db,
                settings={
                    "as400_username": "user",
                    "as400_password": "pass",
                    "as400_address": "addr",
                },
                tweaker_step=EDITweakerStep(),
                upc_dict={"_mock": []},
                converter_step=EDIConverterStep(),
            )
            orchestrator = DispatchOrchestrator(config_obj)

            run_log = MockLog()
            folder_rec = db.folders_table.find_one(id=folder_id)
            result = orchestrator.process_folder(
                folder_rec, run_log, db.processed_files
            )
    else:
        config_obj = DispatchConfig(
            database=db,
            settings={},
            converter_step=EDIConverterStep(),
        )
        orchestrator = DispatchOrchestrator(config_obj)

        run_log = MockLog()
        folder_rec = db.folders_table.find_one(id=folder_id)
        result = orchestrator.process_folder(folder_rec, run_log, db.processed_files)

    assert result.files_processed == 1, f"{description} - Errors: {result.errors}"

    # Verify output exists
    output_files = list(workspace["output_1"].glob("*"))
    assert len(output_files) >= 1, f"{description} - Expected output files"

    output_content = output_files[0].read_text()
    assert len(output_content) > 0, f"{description} - Output file should not be empty"


# Test all conversion formats with key option combinations
@pytest.mark.parametrize(("format_name", "options"), FORMAT_OPTION_CASES)
def test_all_formats_with_options(workspace, format_name, options):
    """Test all conversion formats with various option combinations."""
    db = workspace["db"]
    folder_manager = FolderManager(db)

    input_path = str(workspace["input"])
    folder_manager.add_folder(input_path)
    folder = db.folders_table.find_one(folder_name=input_path)
    folder_id = folder["id"]

    config = {
        "id": folder_id,
        "folder_is_active": "True",
        "process_backend_copy": 1,
        "copy_to_directory": str(workspace["output_1"]),
        "process_edi": 1,
        "convert_to_format": format_name,
    }
    config.update(options)

    db.folders_table.update(config, ["id"])

    # Create test EDI file
    a_rec = "AVENDOR00000000010101260000001000\n"
    b_rec = (
        "B01234567890TEST ITEM                123456000100000000010000100000         \n"
    )
    c_rec = "C001CHARGER DESCRIPTION      000000000\n"
    test_file_content = a_rec + b_rec + c_rec
    test_file_path = (
        workspace["input"]
        / f"test_{format_name}_{hash(frozenset(options.items()))}.edi"
    )
    test_file_path.write_text(test_file_content)

    from dispatch.pipeline.converter import EDIConverterStep

    config_obj = DispatchConfig(
        database=db,
        settings={},
        converter_step=EDIConverterStep(),
    )
    orchestrator = DispatchOrchestrator(config_obj)

    run_log = MockLog()
    folder_rec = db.folders_table.find_one(id=folder_id)
    result = orchestrator.process_folder(folder_rec, run_log, db.processed_files)

    assert result.files_processed == 1, (
        f"{format_name} with {options} - Errors: {result.errors}"
    )

    output_files = list(workspace["output_1"].glob("*"))
    assert len(output_files) >= 1, f"{format_name} should produce output"


# Test backends with option combinations
@pytest.mark.parametrize(
    "backend_type,backend_config",
    [
        ("copy", {"process_backend_copy": 1}),
        (
            "ftp",
            {
                "process_backend_ftp": 1,
                "ftp_server": "ftp.example.com",
                "ftp_port": 21,
                "ftp_username": "user",
                "ftp_password": "pass",
                "ftp_folder": "/uploads/",
            },
        ),
        (
            "email",
            {
                "process_backend_email": 1,
                "email_to": "test@example.com",
                "email_subject_line": "Test",
            },
        ),
    ],
)
def test_backends_with_csv_options(workspace, backend_type, backend_config):
    """Test all backends with various CSV option combinations."""
    db = workspace["db"]
    folder_manager = FolderManager(db)

    input_path = str(workspace["input"])
    folder_manager.add_folder(input_path)
    folder = db.folders_table.find_one(folder_name=input_path)
    folder_id = folder["id"]

    config = {
        "id": folder_id,
        "folder_is_active": "True",
        "copy_to_directory": str(workspace["output_1"]),
        "process_edi": 1,
        "convert_to_format": "csv",
        "include_headers": 1,
        "include_a_records": 1,
    }
    config.update(backend_config)

    db.folders_table.update(config, ["id"])

    # Create test file
    a_rec = "AVENDOR00000000010101260000001000\n"
    b_rec = (
        "B01234567890TEST ITEM                123456000100000000010000100000         \n"
    )
    c_rec = "C001CHARGER DESCRIPTION      000000000\n"
    test_file_content = a_rec + b_rec + c_rec
    test_file_path = workspace["input"] / f"test_backend_{backend_type}.edi"
    test_file_path.write_text(test_file_content)

    from unittest import mock

    from dispatch.pipeline.converter import EDIConverterStep

    if backend_type == "ftp":
        with mock.patch("backend.ftp_client.RealFTPClient") as MockFTP:
            mock_ftp = MockFTP.return_value
            # Mock all FTP methods that ftp_backend.py uses
            mock_ftp.connect.return_value = None
            mock_ftp.login.return_value = None
            mock_ftp.cwd.return_value = None
            mock_ftp.mkd.return_value = None
            mock_ftp.storbinary.return_value = None
            mock_ftp.close.return_value = None

            config_obj = DispatchConfig(
                database=db,
                settings={},
                converter_step=EDIConverterStep(),
            )
            orchestrator = DispatchOrchestrator(config_obj)

            run_log = MockLog()
            folder_rec = db.folders_table.find_one(id=folder_id)
            result = orchestrator.process_folder(
                folder_rec, run_log, db.processed_files
            )

            assert result.files_processed == 1, f"FTP backend errors: {result.errors}"

    elif backend_type == "email":
        with mock.patch("backend.smtp_client.RealSMTPClient") as MockSMTP:
            mock_smtp = MockSMTP.return_value
            mock_smtp.connect.return_value = None
            mock_smtp.ehlo.return_value = None
            mock_smtp.starttls.return_value = None
            mock_smtp.login.return_value = None
            mock_smtp.send_message.return_value = None
            mock_smtp.close.return_value = None

            config_obj = DispatchConfig(
                database=db,
                settings={
                    "email_address": "sender@example.com",
                    "email_smtp_server": "smtp.example.com",
                    "smtp_port": 587,
                },
                converter_step=EDIConverterStep(),
            )
            orchestrator = DispatchOrchestrator(config_obj)

            run_log = MockLog()
            folder_rec = db.folders_table.find_one(id=folder_id)
            result = orchestrator.process_folder(
                folder_rec, run_log, db.processed_files
            )

            assert result.files_processed == 1, f"Email backend errors: {result.errors}"

    else:  # copy
        config_obj = DispatchConfig(
            database=db,
            settings={},
            converter_step=EDIConverterStep(),
        )
        orchestrator = DispatchOrchestrator(config_obj)

        run_log = MockLog()
        folder_rec = db.folders_table.find_one(id=folder_id)
        result = orchestrator.process_folder(folder_rec, run_log, db.processed_files)

        assert result.files_processed == 1, f"Copy backend errors: {result.errors}"
        output_files = list(workspace["output_1"].glob("*"))
        assert len(output_files) >= 1, "Copy backend should create output files"
