"""Standalone self-test with no Qt dependencies.

Returns 0 if all required checks pass, 1 otherwise.
"""

import contextlib
import hashlib
import os
import shutil
import sys
import tempfile

# -------------------------------------------------------------------------- section 1: stdlib imports


def _check_stdlib_modules() -> tuple[int, int]:
    """Check all required standard-library modules are importable."""
    passed = failed = 0
    stdlib_modules = [
        "argparse",
        "datetime",
        "multiprocessing",
        "os",
        "platform",
        "sys",
        "time",
        "traceback",
    ]
    for mod_name in stdlib_modules:
        try:
            __import__(mod_name)
            passed += 1
            print(f"  ✓ {mod_name}")
        except Exception as exc:
            failed += 1
            print(f"  ✗ {mod_name} -- {exc}")
    return passed, failed


# -------------------------------------------------------------------------- section 1b: third-party imports


def _check_third_party_modules() -> tuple[int, int]:
    """Check third-party (non-Qt) dependencies."""
    passed = failed = 0
    third_party_modules = [
        "appdirs",
        "lxml",
        "lxml.etree",
    ]
    for mod_name in third_party_modules:
        try:
            __import__(mod_name)
            passed += 1
            print(f"  ✓ {mod_name}")
        except Exception as exc:
            failed += 1
            print(f"  ✗ {mod_name} -- {exc}")
    return passed, failed


# -------------------------------------------------------------------------- section 1c: Qt imports


def _check_qt_modules() -> tuple[int, int]:
    """Check all required PyQt5 modules."""
    passed = failed = 0
    qt_modules = [
        "PyQt5.QtCore",
        "PyQt5.QtWidgets",
        "PyQt5.QtGui",
        "PyQt5.QtPrintSupport",
        "PyQt5.QtSvg",
        "PyQt5.QtXml",
        "PyQt5.QtNetwork",
    ]
    for mod_name in qt_modules:
        try:
            __import__(mod_name)
            passed += 1
            print(f"  ✓ {mod_name}")
        except Exception as exc:
            failed += 1
            print(f"  ✗ {mod_name} -- {exc}")

    try:
        __import__("PyQt5.sip")
        passed += 1
        print("  ✓ PyQt5.sip")
    except ImportError as exc:
        failed += 1
        print(f"  ✗ PyQt5.sip -- {exc}")

    return passed, failed


# -------------------------------------------------------------------------- section 1d: app module imports


def _check_app_modules() -> tuple[int, int]:
    """Check all application modules can be imported."""
    passed = failed = 0
    app_modules = [
        # Database and operations
        "backend.database.database_obj",
        "interface.operations.folder_manager",
        "interface.ports",
        "interface.services.reporting_service",
        # Qt application layer
        "interface.qt.app",
        "interface.qt.bootstrap",
        "interface.qt.diagnostics",
        "interface.qt.run_coordinator",
        "interface.qt.window_controller",
        "interface.qt.theme",
        # Qt dialogs
        "interface.qt.dialogs.base_dialog",
        "interface.qt.dialogs.edit_folders_dialog",
        "interface.qt.dialogs.edit_folders.data_extractor",
        "interface.qt.dialogs.edit_folders.layout_builder",
        "interface.qt.dialogs.edit_folders.column_builders",
        "interface.qt.dialogs.edit_folders.dynamic_edi_builder",
        "interface.qt.dialogs.edit_folders.event_handlers",
        "interface.qt.dialogs.edit_settings_dialog",
        "interface.qt.dialogs.maintenance_dialog",
        "interface.qt.dialogs.processed_files_dialog",
        "interface.qt.dialogs.resend_dialog",
        "interface.qt.dialogs.database_import_dialog",
        # Qt widgets and services
        "interface.qt.services.qt_services",
        "interface.qt.widgets.folder_list_widget",
        "interface.qt.widgets.search_widget",
        "interface.qt.widgets.extra_widgets",
        # Top-level scripts
        "batch_log_sender",
        "print_run_log",
        "utils",
        "backup_increment",
        # Core business logic
        "core.edi.edi_parser",
        "core.edi.edi_splitter",
        "core.edi.inv_fetcher",
        "core.edi.po_fetcher",
        "dispatch",
        "dispatch.orchestrator",
        "dispatch.send_manager",
        "backend.ftp_client",
        "backend.smtp_client",
        "record_error",
        "folders_database_migrator",
        "mover",
        "clear_old_files",
        # Converter entry points
        "convert_to_csv",
        "convert_to_fintech",
        "convert_to_simplified_csv",
        "convert_to_stewarts_custom",
        "convert_to_yellowdog_csv",
        "convert_to_estore_einvoice",
        "convert_to_estore_einvoice_generic",
        "convert_to_scannerware",
        "convert_to_scansheet_type_a",
        "convert_to_jolley_custom",
        # Backend entry points
        "copy_backend",
        "ftp_backend",
        "email_backend",
    ]
    for mod_name in app_modules:
        try:
            __import__(mod_name)
            passed += 1
            print(f"  ✓ {mod_name}")
        except Exception as exc:
            failed += 1
            print(f"  ✗ {mod_name} -- {exc}")
    return passed, failed


# -------------------------------------------------------------------------- section 2: config directories


def _check_config_directories() -> tuple[int, int]:
    """Verify configuration directory creation."""
    passed = failed = 0
    try:
        import appdirs as _appdirs

        config_dir = _appdirs.user_data_dir("Batch File Sender")
        os.makedirs(config_dir, exist_ok=True)
        if os.path.isdir(config_dir):
            passed += 1
            print(f"  ✓ config dir exists: {config_dir}")
        else:
            failed += 1
            print(f"  ✗ config dir missing after makedirs: {config_dir}")
    except Exception as exc:
        failed += 1
        print(f"  ✗ config directory creation -- {exc}")
    return passed, failed


# -------------------------------------------------------------------------- section 3: appdirs functionality


def _check_appdirs() -> tuple[int, int]:
    """Verify appdirs.user_data_dir returns a valid string."""
    passed = failed = 0
    try:
        import appdirs as _appdirs

        test_dir = _appdirs.user_data_dir("TestApp")
        if isinstance(test_dir, str) and len(test_dir) > 0:
            passed += 1
            print(f"  ✓ appdirs.user_data_dir('TestApp') = {test_dir}")
        else:
            failed += 1
            print("  ✗ appdirs.user_data_dir returned unexpected value")
    except Exception as exc:
        failed += 1
        print(f"  ✗ appdirs.user_data_dir -- {exc}")
    return passed, failed


# -------------------------------------------------------------------------- section 4: file system access


def _check_file_system() -> tuple[int, int]:
    """Verify read/write/cleanup of temp files."""
    passed = failed = 0
    try:
        tmpdir = tempfile.mkdtemp(prefix="selftest_")
        tmp_path = os.path.join(tmpdir, "test_file.txt")
        test_payload = "self-test-payload"
        with open(tmp_path, "w", encoding="utf-8") as fh:
            fh.write(test_payload)
        with open(tmp_path, encoding="utf-8") as fh:
            read_back = fh.read()
        if read_back == test_payload:
            passed += 1
            print(f"  ✓ write/read temp file in {tmpdir}")
        else:
            failed += 1
            print("  ✗ temp file content mismatch")
        os.remove(tmp_path)
        os.rmdir(tmpdir)
        passed += 1
        print("  ✓ temp file cleanup")
    except Exception as exc:
        failed += 1
        print(f"  ✗ file system access -- {exc}")
    return passed, failed


# -------------------------------------------------------------------------- section 5: module __file__ attributes


def _check_module_file_attrs() -> tuple[int, int]:
    """Verify local scripts expose __file__."""
    passed = failed = 0
    local_modules = [
        "batch_log_sender",
        "print_run_log",
        "utils",
        "backup_increment",
    ]
    for mod_name in local_modules:
        mod = sys.modules.get(mod_name)
        if mod is None:
            try:
                mod = __import__(mod_name)
            except Exception as exc:
                failed += 1
                print(f"  ✗ {mod_name} (import) -- {exc}")
                continue
        if hasattr(mod, "__file__") and mod.__file__:
            passed += 1
            print(f"  ✓ {mod_name}.__file__ = {mod.__file__}")
        else:
            failed += 1
            print(f"  ✗ {mod_name} has no __file__ attribute")
    return passed, failed


# -------------------------------------------------------------------------- section 6: constants


def _check_constants() -> tuple[int, int]:
    """Check CURRENT_DATABASE_VERSION == '50'."""
    passed = failed = 0
    try:
        from core.constants import CURRENT_DATABASE_VERSION

        if CURRENT_DATABASE_VERSION == "50":
            passed += 1
            print("  ✓ CURRENT_DATABASE_VERSION == '50'")
        else:
            failed += 1
            print(
                f"  ✗ CURRENT_DATABASE_VERSION -- expected '50', "
                f"got {CURRENT_DATABASE_VERSION!r}"
            )
    except Exception as exc:
        failed += 1
        print(f"  ✗ CURRENT_DATABASE_VERSION import -- {exc}")
    return passed, failed


# -------------------------------------------------------------------------- section 7: boolean utilities


def _check_bool_utils() -> tuple[int, int]:
    """Check boolean normalization utilities."""
    passed = failed = 0
    try:
        from core.utils.bool_utils import from_db_bool as _fdb
        from core.utils.bool_utils import normalize_bool as _nb
        from core.utils.bool_utils import to_db_bool as _tdb

        passed += 1
        print("  ✓ core.utils.bool_utils imported")
    except Exception as exc:
        failed += 1
        print(f"  ✗ core.utils.bool_utils import -- {exc}")
        return passed, failed

    # normalize_bool: booleans pass through
    for val, expected in [(True, True), (False, False)]:
        try:
            result = _nb(val)
            if result is expected:
                passed += 1
                print(f"  ✓ normalize_bool({val}) == {expected}")
            else:
                failed += 1
                print(f"  ✗ normalize_bool({val}) -- got {result!r}")
        except Exception as exc:
            failed += 1
            print(f"  ✗ normalize_bool({val}) -- {exc}")

    # normalize_bool: string inputs
    for val, expected in [
        ("true", True),
        ("false", False),
        ("yes", True),
        ("no", False),
        ("1", True),
        ("0", False),
        ("", False),
    ]:
        try:
            result = _nb(val)
            if result is expected:
                passed += 1
                print(f"  ✓ normalize_bool({val!r}) == {expected}")
            else:
                failed += 1
                print(
                    f"  ✗ normalize_bool({val!r}) -- expected {expected}, got {result!r}"
                )
        except Exception as exc:
            failed += 1
            print(f"  ✗ normalize_bool({val!r}) -- {exc}")

    # normalize_bool: int/None inputs
    for val, expected in [(1, True), (0, False), (None, False)]:
        try:
            result = _nb(val)
            if result is expected:
                passed += 1
                print(f"  ✓ normalize_bool({val!r}) == {expected}")
            else:
                failed += 1
                print(
                    f"  ✗ normalize_bool({val!r}) -- expected {expected}, got {result!r}"
                )
        except Exception as exc:
            failed += 1
            print(f"  ✗ normalize_bool({val!r}) -- {exc}")

    # to_db_bool
    for val, expected in [(True, 1), (False, 0)]:
        try:
            result = _tdb(val)
            if result == expected:
                passed += 1
                print(f"  ✓ to_db_bool({val}) == {expected}")
            else:
                failed += 1
                print(f"  ✗ to_db_bool({val}) -- got {result!r}")
        except Exception as exc:
            failed += 1
            print(f"  ✗ to_db_bool({val}) -- {exc}")

    # from_db_bool
    for val, expected in [(1, True), (0, False)]:
        try:
            result = _fdb(val)
            if result is expected:
                passed += 1
                print(f"  ✓ from_db_bool({val}) == {expected}")
            else:
                failed += 1
                print(f"  ✗ from_db_bool({val}) -- got {result!r}")
        except Exception as exc:
            failed += 1
            print(f"  ✗ from_db_bool({val}) -- {exc}")

    # Round-trip: to_db_bool -> from_db_bool
    try:
        for original in [True, False]:
            rt = _fdb(_tdb(original))
            if rt is original:
                passed += 1
                print(f"  ✓ round-trip to_db_bool/from_db_bool({original}) == {original}")
            else:
                failed += 1
                print(
                    f"  ✗ round-trip to_db_bool/from_db_bool({original}) -- got {rt!r}"
                )
    except Exception as exc:
        failed += 1
        print(f"  ✗ round-trip to_db_bool/from_db_bool -- {exc}")

    # Cross-check: utils.normalize_bool agrees with core version
    try:
        import core.utils as _utils

        same = all(
            _utils.normalize_bool(v) == _nb(v)
            for v in [
                True, False, "true", "false", "yes", "no", "1", "0", "", 1, 0, None
            ]
        )
        if same:
            passed += 1
            print(
                "  ✓ utils.normalize_bool agrees with "
                "core.utils.bool_utils.normalize_bool"
            )
        else:
            failed += 1
            print(
                "  ✗ utils.normalize_bool vs core version -- results differ for some inputs"
            )
    except Exception as exc:
        failed += 1
        print(f"  ✗ utils.normalize_bool cross-check -- {exc}")

    return passed, failed


# -------------------------------------------------------------------------- section 8: date utilities


def _check_date_utils() -> tuple[int, int]:
    """Check date conversion utilities."""
    passed = failed = 0
    try:
        from datetime import datetime as _dt

        from core.utils.date_utils import dactime_from_datetime as _dfd
        from core.utils.date_utils import dactime_from_invtime as _dacfi
        from core.utils.date_utils import datetime_from_dactime as _dfd2
        from core.utils.date_utils import datetime_from_invtime as _dfi

        passed += 1
        print("  ✓ core.utils.date_utils imported")
    except Exception as exc:
        failed += 1
        print(f"  ✗ core.utils.date_utils import -- {exc}")
        return passed, failed

    # dactime_from_datetime: 2024-01-01 -> "1240101"
    try:
        result = _dfd(_dt(2024, 1, 1))
        if result == "1240101":
            passed += 1
            print("  ✓ dactime_from_datetime(2024-01-01) == '1240101'")
        else:
            failed += 1
            print(f"  ✗ dactime_from_datetime(2024-01-01) -- got {result!r}")
    except Exception as exc:
        failed += 1
        print(f"  ✗ dactime_from_datetime(2024-01-01) -- {exc}")

    # datetime_from_dactime: 1240101 -> datetime(2024, 1, 1)
    try:
        result = _dfd2(1240101)
        expected = _dt(2024, 1, 1)
        if result == expected:
            passed += 1
            print("  ✓ datetime_from_dactime(1240101) == datetime(2024, 1, 1)")
        else:
            failed += 1
            print(f"  ✗ datetime_from_dactime(1240101) -- got {result!r}")
    except Exception as exc:
        failed += 1
        print(f"  ✗ datetime_from_dactime(1240101) -- {exc}")

    # Round-trip dactime_from_datetime -> datetime_from_dactime
    try:
        for test_dt in [_dt(2024, 1, 1), _dt(2023, 12, 31), _dt(2000, 6, 15)]:
            dactime_str = _dfd(test_dt)
            recovered = _dfd2(int(dactime_str))
            if recovered == test_dt:
                passed += 1
                print(f"  ✓ dactime round-trip {test_dt.date()}")
            else:
                failed += 1
                print(
                    f"  ✗ dactime round-trip {test_dt.date()} -- got {recovered!r}"
                )
    except Exception as exc:
        failed += 1
        print(f"  ✗ dactime round-trip -- {exc}")

    # datetime_from_invtime: "010124" -> datetime(2024, 1, 1)
    try:
        result = _dfi("010124")
        expected = _dt(2024, 1, 1)
        if result == expected:
            passed += 1
            print("  ✓ datetime_from_invtime('010124') == datetime(2024, 1, 1)")
        else:
            failed += 1
            print(f"  ✗ datetime_from_invtime('010124') -- got {result!r}")
    except Exception as exc:
        failed += 1
        print(f"  ✗ datetime_from_invtime('010124') -- {exc}")

    # dactime_from_invtime round-trip: "010124" -> "1240101"
    try:
        result = _dacfi("010124")
        if result == "1240101":
            passed += 1
            print("  ✓ dactime_from_invtime('010124') == '1240101'")
        else:
            failed += 1
            print(f"  ✗ dactime_from_invtime('010124') -- got {result!r}")
    except Exception as exc:
        failed += 1
        print(f"  ✗ dactime_from_invtime('010124') -- {exc}")

    return passed, failed


# -------------------------------------------------------------------------- section 9: UPC utilities


def _check_upc_utils() -> tuple[int, int]:
    """Check UPC calculation and validation utilities."""
    passed = failed = 0
    try:
        from core.edi.upc_utils import calc_check_digit as _ccd
        from core.edi.upc_utils import convert_upce_to_upca as _upce2upca
        from core.edi.upc_utils import pad_upc as _pupc
        from core.edi.upc_utils import validate_upc as _vupc

        passed += 1
        print("  ✓ core.edi.upc_utils imported")
    except Exception as exc:
        failed += 1
        print(f"  ✗ core.edi.upc_utils import -- {exc}")
        return passed, failed

    test_cases = [
        ("calc_check_digit", "04180000026", _ccd, 5),
        ("calc_check_digit", "07462100060", _ccd, 2),
    ]
    for name, upc, func, expected in test_cases:
        try:
            result = func(upc)
            if result == expected:
                passed += 1
                print(f"  ✓ {name}({upc!r}) == {expected}")
            else:
                failed += 1
                print(f"  ✗ {name}({upc!r}) -- got {result!r}")
        except Exception as exc:
            failed += 1
            print(f"  ✗ {name}({upc!r}) -- {exc}")

    # convert_upce_to_upca
    try:
        result = _upce2upca("04182635")
        if result == "041800000265":
            passed += 1
            print("  ✓ convert_upce_to_upca('04182635') == '041800000265'")
        else:
            failed += 1
            print(f"  ✗ convert_upce_to_upca('04182635') -- got {result!r}")
    except Exception as exc:
        failed += 1
        print(f"  ✗ convert_upce_to_upca('04182635') -- {exc}")

    try:
        result = _upce2upca("123")
        if result == "":
            passed += 1
            print("  ✓ convert_upce_to_upca('123') == '' (invalid length)")
        else:
            failed += 1
            print(f"  ✗ convert_upce_to_upca('123') -- expected '', got {result!r}")
    except Exception as exc:
        failed += 1
        print(f"  ✗ convert_upce_to_upca('123') -- {exc}")

    # validate_upc
    try:
        result = _vupc("041800000265")
        if result is True:
            passed += 1
            print("  ✓ validate_upc('041800000265') == True")
        else:
            failed += 1
            print(f"  ✗ validate_upc('041800000265') -- got {result!r}")
    except Exception as exc:
        failed += 1
        print(f"  ✗ validate_upc('041800000265') -- {exc}")

    try:
        result = _vupc("041800000260")
        if result is False:
            passed += 1
            print("  ✓ validate_upc('041800000260') == False (bad check digit)")
        else:
            failed += 1
            print(f"  ✗ validate_upc('041800000260') -- expected False, got {result!r}")
    except Exception as exc:
        failed += 1
        print(f"  ✗ validate_upc('041800000260') -- {exc}")

    try:
        result = _vupc("abc")
        if result is False:
            passed += 1
            print("  ✓ validate_upc('abc') == False (non-numeric)")
        else:
            failed += 1
            print(f"  ✗ validate_upc('abc') -- expected False, got {result!r}")
    except Exception as exc:
        failed += 1
        print(f"  ✗ validate_upc('abc') -- {exc}")

    # pad_upc
    for upc_str, length, expected in [
        ("12345", 10, "     12345"),
        ("123456789", 5, "12345"),
        ("12345", 5, "12345"),
    ]:
        try:
            result = _pupc(upc_str, length)
            if result == expected:
                passed += 1
                note = " (truncate)" if len(upc_str) > length else ""
                print(f"  ✓ pad_upc({upc_str!r}, {length}) == {expected!r}{note}")
            else:
                failed += 1
                print(f"  ✗ pad_upc({upc_str!r}, {length}) -- got {result!r}")
        except Exception as exc:
            failed += 1
            print(f"  ✗ pad_upc({upc_str!r}, {length}) -- {exc}")

    return passed, failed


# -------------------------------------------------------------------------- section 10: EDI parser


def _check_edi_parser() -> tuple[int, int]:
    """Check EDI record parsing and building."""
    passed = failed = 0
    try:
        from core.edi.edi_parser import ARecord
        from core.edi.edi_parser import build_a_record as _bar
        from core.edi.edi_parser import build_b_record as _bbr
        from core.edi.edi_parser import build_c_record as _bcr
        from core.edi.edi_parser import capture_records as _cr
        from core.edi.edi_parser import parse_a_record as _par

        passed += 1
        print("  ✓ core.edi.edi_parser imported")
    except Exception as exc:
        failed += 1
        print(f"  ✗ core.edi.edi_parser import -- {exc}")
        return passed, failed

    # capture_records: empty/whitespace
    for content, label in [("", "None"), ("   \n", "None (whitespace)")]:
        try:
            result = _cr(content)
            if result is None:
                passed += 1
                print(f"  ✓ capture_records({content!r}) == {label}")
            else:
                failed += 1
                print(f"  ✗ capture_records({content!r}) -- expected None, got {result!r}")
        except Exception as exc:
            failed += 1
            print(f"  ✗ capture_records({content!r}) -- {exc}")

    # A-record construction
    _a_line = "A" + "VEND01" + "INV0012345" + "010124" + "0000000100" + "\n"
    for field, value in [
        ("record_type", "A"),
        ("cust_vendor", "VEND01"),
        ("invoice_number", "INV0012345"),
        ("invoice_date", "010124"),
        ("invoice_total", "0000000100"),
    ]:
        try:
            result = _cr(_a_line)
            if result is not None and result[field] == value:
                passed += 1
                print(f"  ✓ capture_records(A-record): {field} == {value!r}")
            else:
                failed += 1
                print(
                    f"  ✗ capture_records(A-record): {field} -- got {result!r}"
                )
        except Exception as exc:
            failed += 1
            print(f"  ✗ capture_records(A-record): {field} -- {exc}")

    # parse_a_record -> ARecord
    try:
        rec = _par(_a_line)
        if isinstance(rec, ARecord):
            passed += 1
            print("  ✓ parse_a_record returns ARecord instance")
        else:
            failed += 1
            print(f"  ✗ parse_a_record -- expected ARecord, got {type(rec)!r}")
    except Exception as exc:
        failed += 1
        print(f"  ✗ parse_a_record instance check -- {exc}")

    try:
        rec = _par(_a_line)
        if rec.cust_vendor == "VEND01" and rec.invoice_number == "INV0012345":
            passed += 1
            print("  ✓ parse_a_record fields correct")
        else:
            failed += 1
            print(
                f"  ✗ parse_a_record fields -- cust_vendor={rec.cust_vendor!r}, "
                f"invoice_number={rec.invoice_number!r}"
            )
    except Exception as exc:
        failed += 1
        print(f"  ✗ parse_a_record fields -- {exc}")

    try:
        raised = False
        try:
            _par("BSOMELINE\n")
        except ValueError:
            raised = True
        if raised:
            passed += 1
            print("  ✓ parse_a_record raises ValueError on non-A line")
        else:
            failed += 1
            print("  ✗ parse_a_record ValueError -- no exception raised on B-record input")
    except Exception as exc:
        failed += 1
        print(f"  ✗ parse_a_record ValueError -- {exc}")

    # B-record
    _b_line = (
        "B"
        + "00012345678"
        + "Item Description         "
        + "000001"
        + "000100"
        + "01"
        + "000001"
        + "00010"
        + "01000"
        + "   "
        + "      "
        + "\n"
    )
    for field, value in [("record_type", "B"), ("upc_number", "00012345678")]:
        try:
            result = _cr(_b_line)
            if result is not None and result[field] == value:
                passed += 1
                print(f"  ✓ capture_records(B-record): {field} == {value!r}")
            else:
                failed += 1
                print(f"  ✗ capture_records(B-record): {field} -- got {result!r}")
        except Exception as exc:
            failed += 1
            print(f"  ✗ capture_records(B-record): {field} -- {exc}")

    # C-record
    _c_line = (
        "C" + "TAX" + "Sales Tax                " + "000001000" + "\n"
    )
    for field, value in [
        ("record_type", "C"),
        ("charge_type", "TAX"),
    ]:
        try:
            result = _cr(_c_line)
            if result is not None and result[field] == value:
                passed += 1
                print(f"  ✓ capture_records(C-record): {field} == {value!r}")
            else:
                failed += 1
                print(f"  ✗ capture_records(C-record): {field} -- got {result!r}")
        except Exception as exc:
            failed += 1
            print(f"  ✗ capture_records(C-record): {field} -- {exc}")

    # build + capture round-trips
    for build_fn, built, checks in [
        (_bar, None, [("cust_vendor", "VEND01"), ("invoice_number", "INV0012345"), ("invoice_date", "010124"), ("invoice_total", "0000000100")]),
        (
            _bbr,
            dict(upc_number="00012345678", description="Item Description         ", vendor_item="000001", unit_cost="000100", combo_code="01", unit_multiplier="000001", qty_of_units="00010", suggested_retail_price="01000", price_multi_pack="   ", parent_item_number="      "),
            [("upc_number", "00012345678"), ("vendor_item", "000001")],
        ),
        (_bcr, ("TAX", "Sales Tax                ", "000001000"), [("record_type", "C"), ("charge_type", "TAX"), ("amount", "000001000")]),
    ]:
        try:
            if build_fn == _bar:
                built_line = _bar("VEND01", "INV0012345", "010124", "0000000100")
                parsed = _cr(built_line)
            elif build_fn == _bbr:
                built_line = _bbr(**built)
                parsed = _cr(built_line)
            else:
                built_line = _bcr(*built)
                parsed = _cr(built_line)

            for field, expected in checks:
                if parsed is not None and parsed[field] == expected:
                    passed += 1
                    print(f"  ✓ {build_fn.__name__} + capture_records round-trip: {field}")
                else:
                    failed += 1
                    print(f"  ✗ {build_fn.__name__} round-trip: {field} -- got {parsed!r}")
        except Exception as exc:
            failed += 1
            print(f"  ✗ {build_fn.__name__} round-trip -- {exc}")

    return passed, failed


# -------------------------------------------------------------------------- section 11: hash utilities


def _check_hash_utils() -> tuple[int, int]:
    """Check file hash generation and matching utilities."""
    passed = failed = 0
    try:
        from dispatch.hash_utils import build_hash_dictionaries as _bhd
        from dispatch.hash_utils import check_file_against_processed as _cfap
        from dispatch.hash_utils import generate_file_hash as _gfh
        from dispatch.hash_utils import generate_match_lists as _gml

        passed += 1
        print("  ✓ dispatch.hash_utils imported")
    except Exception as exc:
        failed += 1
        print(f"  ✗ dispatch.hash_utils import -- {exc}")
        return passed, failed

    try:
        _hash_tmpdir = tempfile.mkdtemp(prefix="selftest_hash_")
        _hash_file = os.path.join(_hash_tmpdir, "hash_test.txt")
        _hash_content = b"hello world"
        with open(_hash_file, "wb") as _fh:
            _fh.write(_hash_content)
        expected_hash = hashlib.md5(_hash_content).hexdigest()
        result = _gfh(_hash_file)
        if result == expected_hash:
            passed += 1
            print(f"  ✓ generate_file_hash matches expected MD5 ({expected_hash[:8]}...)")
        else:
            failed += 1
            print(f"  ✗ generate_file_hash -- expected {expected_hash!r}, got {result!r}")
        os.remove(_hash_file)
        os.rmdir(_hash_tmpdir)
    except Exception as exc:
        failed += 1
        print(f"  ✗ generate_file_hash -- {exc}")

    # generate_match_lists
    try:
        _records = [
            {"file_name": "file_a.edi", "file_checksum": "aaaa", "resend_flag": False},
            {"file_name": "file_b.edi", "file_checksum": "bbbb", "resend_flag": True},
            {"file_name": "file_c.edi", "file_checksum": "cccc", "resend_flag": False},
        ]
        hash_list, name_list, resend_set = _gml(_records)
        if ("file_a.edi", "aaaa") in hash_list:
            passed += 1
            print("  ✓ generate_match_lists: hash_list contains expected tuple")
        else:
            failed += 1
            print(f"  ✗ generate_match_lists: hash_list -- got {hash_list!r}")
        if ("bbbb", "file_b.edi") in name_list:
            passed += 1
            print("  ✓ generate_match_lists: name_list contains expected tuple")
        else:
            failed += 1
            print(f"  ✗ generate_match_lists: name_list -- got {name_list!r}")
        if resend_set == {"bbbb"}:
            passed += 1
            print("  ✓ generate_match_lists: resend_set == {'bbbb'}")
        else:
            failed += 1
            print(f"  ✗ generate_match_lists: resend_set -- got {resend_set!r}")
    except Exception as exc:
        failed += 1
        print(f"  ✗ generate_match_lists -- {exc}")

    # build_hash_dictionaries
    try:
        _records2 = [
            {"file_name": "file_x.edi", "file_checksum": "xxxx", "resend_flag": False},
            {"file_name": "file_y.edi", "file_checksum": "yyyy", "resend_flag": True},
        ]
        hash_dict, name_dict, resend_set2 = _bhd(_records2)
        if hash_dict.get("file_x.edi") == "xxxx":
            passed += 1
            print("  ✓ build_hash_dictionaries: hash_dict['file_x.edi'] == 'xxxx'")
        else:
            failed += 1
            print(f"  ✗ build_hash_dictionaries: hash_dict -- got {hash_dict!r}")
        if name_dict.get("yyyy") == "file_y.edi":
            passed += 1
            print("  ✓ build_hash_dictionaries: name_dict['yyyy'] == 'file_y.edi'")
        else:
            failed += 1
            print(f"  ✗ build_hash_dictionaries: name_dict -- got {name_dict!r}")
        if resend_set2 == {"yyyy"}:
            passed += 1
            print("  ✓ build_hash_dictionaries: resend_set == {'yyyy'}")
        else:
            failed += 1
            print(f"  ✗ build_hash_dictionaries: resend_set -- got {resend_set2!r}")
    except Exception as exc:
        failed += 1
        print(f"  ✗ build_hash_dictionaries -- {exc}")

    # check_file_against_processed
    scenarios = [
        ("new file", {"existingchecksum": "old_file.edi"}, set(), False, True),
        ("already processed", {"existingchecksum": "old_file.edi"}, set(), True, False),
        ("resend", {"resendchecksum": "resend_file.edi"}, {"resendchecksum"}, True, True),
    ]
    for name, name_dict, resend_set, exp_match, exp_send in scenarios:
        try:
            checksum = next(iter(name_dict.keys()))
            fname = name_dict[checksum]
            match, should_send = _cfap(fname, checksum, name_dict, resend_set)
            if match is exp_match and should_send is exp_send:
                passed += 1
                print(f"  ✓ check_file_against_processed: {name} -> ({exp_match}, {exp_send})")
            else:
                failed += 1
                print(
                    f"  ✗ check_file_against_processed: {name} -- "
                    f"expected ({exp_match}, {exp_send}), got ({match}, {should_send})"
                )
        except Exception as exc:
            failed += 1
            print(f"  ✗ check_file_against_processed: {name} -- {exc}")

    return passed, failed


# -------------------------------------------------------------------------- section 12: feature flags


def _check_feature_flags() -> tuple[int, int]:
    """Check feature flag get/set functionality."""
    passed = failed = 0
    try:
        from dispatch.feature_flags import get_debug_mode as _gdm
        from dispatch.feature_flags import get_feature_flags as _gff
        from dispatch.feature_flags import set_feature_flag as _sff

        passed += 1
        print("  ✓ dispatch.feature_flags imported")
    except Exception as exc:
        failed += 1
        print(f"  ✗ dispatch.feature_flags import -- {exc}")
        return passed, failed

    # Default value
    try:
        os.environ.pop("DISPATCH_DEBUG_MODE", None)
        result = _gdm()
        if result is False:
            passed += 1
            print("  ✓ get_debug_mode() == False (default)")
        else:
            failed += 1
            print(f"  ✗ get_debug_mode() -- expected False, got {result!r}")
    except Exception as exc:
        failed += 1
        print(f"  ✗ get_debug_mode() -- {exc}")

    # get_feature_flags dict shape
    try:
        flags = _gff()
        required_keys = {"debug_mode"}
        if isinstance(flags, dict) and required_keys <= set(flags.keys()):
            passed += 1
            print(f"  ✓ get_feature_flags() returns dict with keys {required_keys}")
        else:
            failed += 1
            print(f"  ✗ get_feature_flags() -- got {flags!r}")
    except Exception as exc:
        failed += 1
        print(f"  ✗ get_feature_flags() -- {exc}")

    try:
        flags = _gff()
        if flags["debug_mode"] is False:
            passed += 1
            print("  ✓ get_feature_flags() default values correct")
        else:
            failed += 1
            print(f"  ✗ get_feature_flags() default values -- got {flags!r}")
    except Exception as exc:
        failed += 1
        print(f"  ✗ get_feature_flags() default values -- {exc}")

    # set_feature_flag + read back + restore
    try:
        _sff("debug_mode", value=True)
        result = _gdm()
        _sff("debug_mode", value=False)  # restore immediately
        if result is True:
            passed += 1
            print("  ✓ set_feature_flag('debug_mode', True) -> get_debug_mode() == True")
        else:
            failed += 1
            print(f"  ✗ set_feature_flag('debug_mode', True) -- got {result!r}")
    except Exception as exc:
        with contextlib.suppress(ValueError, KeyError):
            _sff("debug_mode", value=False)
        failed += 1
        print(f"  ✗ set_feature_flag('debug_mode', True) -- {exc}")

    # set_feature_flag with unknown name raises ValueError
    try:
        raised = False
        try:
            _sff("nonexistent_flag", value=True)
        except ValueError:
            raised = True
        if raised:
            passed += 1
            print("  ✓ set_feature_flag unknown name raises ValueError")
        else:
            failed += 1
            print("  ✗ set_feature_flag unknown name -- no ValueError raised")
    except Exception as exc:
        failed += 1
        print(f"  ✗ set_feature_flag unknown name -- {exc}")

    return passed, failed


# -------------------------------------------------------------------------- section 13: send manager


def _check_send_manager() -> tuple[int, int]:
    """Check SendManager and MockBackend functionality."""
    passed = failed = 0
    try:
        from dispatch.send_manager import MockBackend as _MB
        from dispatch.send_manager import SendManager as _SM

        passed += 1
        print("  ✓ dispatch.send_manager imported (SendManager, MockBackend)")
    except Exception as exc:
        failed += 1
        print(f"  ✗ dispatch.send_manager import -- {exc}")
        return passed, failed

    # SendManager instantiation
    try:
        sm = _SM()
        if (
            hasattr(sm, "backends")
            and hasattr(sm, "results")
            and hasattr(sm, "errors")
        ):
            passed += 1
            print("  ✓ SendManager() has .backends, .results, .errors")
        else:
            failed += 1
            print(f"  ✗ SendManager() attributes -- missing attrs on {sm!r}")
    except Exception as exc:
        failed += 1
        print(f"  ✗ SendManager() instantiation -- {exc}")

    try:
        sm = _SM()
        if sm.backends == {} and sm.results == {} and sm.errors == {}:
            passed += 1
            print("  ✓ SendManager() backends/results/errors are empty dicts")
        else:
            failed += 1
            print(f"  ✗ SendManager() initial state -- backends={sm.backends!r}")
    except Exception as exc:
        failed += 1
        print(f"  ✗ SendManager() initial state -- {exc}")

    # get_enabled_backends
    try:
        sm = _SM()
        enabled = sm.get_enabled_backends(
            {"process_backend_copy": True, "process_backend_ftp": False}
        )
        if "copy" in enabled and "ftp" not in enabled:
            passed += 1
            print("  ✓ get_enabled_backends: copy=True,ftp=False -> {'copy'}")
        else:
            failed += 1
            print(f"  ✗ get_enabled_backends -- got {enabled!r}")
    except Exception as exc:
        failed += 1
        print(f"  ✗ get_enabled_backends -- {exc}")

    try:
        sm = _SM()
        enabled = sm.get_enabled_backends({})
        if enabled == set():
            passed += 1
            print("  ✓ get_enabled_backends({}) == set()")
        else:
            failed += 1
            print(f"  ✗ get_enabled_backends({{}}) -- got {enabled!r}")
    except Exception as exc:
        failed += 1
        print(f"  ✗ get_enabled_backends({{}}) -- {exc}")

    # validate_backend_config
    try:
        sm = _SM()
        errors = sm.validate_backend_config({"process_backend_copy": True})
        if errors and any("Copy Backend" in e for e in errors):
            passed += 1
            print(
                "  ✓ validate_backend_config: copy without directory -> "
                "error mentioning 'Copy Backend'"
            )
        else:
            failed += 1
            print(f"  ✗ validate_backend_config: copy without directory -- got {errors!r}")
    except Exception as exc:
        failed += 1
        print(f"  ✗ validate_backend_config: copy without directory -- {exc}")

    try:
        sm = _SM()
        errors = sm.validate_backend_config({})
        if errors == []:
            passed += 1
            print("  ✓ validate_backend_config({}) == []")
        else:
            failed += 1
            print(f"  ✗ validate_backend_config({{}}) -- got {errors!r}")
    except Exception as exc:
        failed += 1
        print(f"  ✗ validate_backend_config({{}}) -- {exc}")

    # MockBackend
    try:
        mb = _MB(should_succeed=True)
        if mb.send_calls == []:
            passed += 1
            print("  ✓ MockBackend(should_succeed=True): send_calls starts empty")
        else:
            failed += 1
            print(f"  ✗ MockBackend send_calls initial -- got {mb.send_calls!r}")
    except Exception as exc:
        failed += 1
        print(f"  ✗ MockBackend(should_succeed=True) -- {exc}")

    try:
        mb = _MB(should_succeed=True)
        mb.send({"p": 1}, {"s": 2}, "/tmp/test.edi")
        if len(mb.send_calls) == 1:
            passed += 1
            print("  ✓ MockBackend.send() records call (should_succeed=True)")
        else:
            failed += 1
            print(f"  ✗ MockBackend.send() call recording -- send_calls={mb.send_calls!r}")
    except Exception as exc:
        failed += 1
        print(f"  ✗ MockBackend.send() (should_succeed=True) -- {exc}")

    try:
        mb_fail = _MB(should_succeed=False)
        raised = False
        try:
            mb_fail.send({}, {}, "/tmp/test.edi")
        except RuntimeError:
            raised = True
        if raised:
            passed += 1
            print("  ✓ MockBackend(should_succeed=False).send() raises RuntimeError")
        else:
            failed += 1
            print("  ✗ MockBackend failure -- no RuntimeError raised")
    except Exception as exc:
        failed += 1
        print(f"  ✗ MockBackend(should_succeed=False) -- {exc}")

    try:
        mb_fail = _MB(should_succeed=False)
        val_errors = mb_fail.validate({})
        if val_errors and isinstance(val_errors, list):
            passed += 1
            print(
                "  ✓ MockBackend(should_succeed=False).validate() returns "
                "non-empty error list"
            )
        else:
            failed += 1
            print(
                f"  ✗ MockBackend(should_succeed=False).validate() -- "
                f"got {val_errors!r}"
            )
    except Exception as exc:
        failed += 1
        print(f"  ✗ MockBackend(should_succeed=False).validate() -- {exc}")

    # send_all with MockBackend
    try:
        mb = _MB(should_succeed=True)
        _hash_tmpdir2 = tempfile.mkdtemp(prefix="selftest_sm_")
        _test_file = os.path.join(_hash_tmpdir2, "invoice.edi")
        with open(_test_file, "w") as _fh:
            _fh.write("AVEND01INV0012345010124000000010\n")
        sm = _SM(backends={"mock": mb})
        results = sm.send_all({"mock"}, _test_file, {}, {})
        if results.get("mock") is True:
            passed += 1
            print("  ✓ send_all with MockBackend -> results['mock'] == True")
        else:
            failed += 1
            print(f"  ✗ send_all with MockBackend -- got {results!r}")
        if len(mb.send_calls) == 1:
            passed += 1
            print("  ✓ send_all with MockBackend -> MockBackend.send_calls has 1 entry")
        else:
            failed += 1
            print(f"  ✗ send_all MockBackend call count -- send_calls={mb.send_calls!r}")
        os.remove(_test_file)
        os.rmdir(_hash_tmpdir2)
    except Exception as exc:
        failed += 1
        print(f"  ✗ send_all with MockBackend -- {exc}")

    return passed, failed


# -------------------------------------------------------------------------- section 14: orchestrator dataclasses


def _check_orchestrator() -> tuple[int, int]:
    """Check DispatchConfig, FolderResult, FileResult, ProcessingContext, and DispatchOrchestrator."""
    passed = failed = 0
    try:
        from dispatch.orchestrator import DispatchConfig as _DC
        from dispatch.orchestrator import DispatchOrchestrator as _DO
        from dispatch.orchestrator import FileResult as _FiR
        from dispatch.orchestrator import ProcessingContext as _PC
        from dispatch.results import FolderResult as _FR

        passed += 1
        print("  ✓ dispatch.orchestrator imported")
    except Exception as exc:
        failed += 1
        print(f"  ✗ dispatch.orchestrator import -- {exc}")
        return passed, failed

    # DispatchConfig defaults
    try:
        config = _DC()
        if (
            config.backends == {}
            and config.settings == {}
            and config.version == "1.0.0"
        ):
            passed += 1
            print(
                "  ✓ DispatchConfig() defaults: backends={}, settings={}, version='1.0.0'"
            )
        else:
            failed += 1
            print(
                f"  ✗ DispatchConfig() defaults -- "
                f"backends={config.backends!r}, version={config.version!r}"
            )
    except Exception as exc:
        failed += 1
        print(f"  ✗ DispatchConfig() defaults -- {exc}")

    # FolderResult defaults
    try:
        fr = _FR(folder_name="test", alias="Test")
        if (
            fr.files_processed == 0
            and fr.files_failed == 0
            and fr.errors == []
            and fr.success is True
        ):
            passed += 1
            print(
                "  ✓ FolderResult defaults: files_processed=0, files_failed=0, "
                "errors=[], success=True"
            )
        else:
            failed += 1
            print(
                f"  ✗ FolderResult defaults -- processed={fr.files_processed}, "
                f"failed={fr.files_failed}, success={fr.success}"
            )
    except Exception as exc:
        failed += 1
        print(f"  ✗ FolderResult defaults -- {exc}")

    # FileResult defaults
    try:
        fir = _FiR(file_name="test.edi", checksum="abc123")
        if (
            fir.sent is False
            and fir.validated is True
            and fir.converted is False
            and fir.errors == []
        ):
            passed += 1
            print(
                "  ✓ FileResult defaults: sent=False, validated=True, "
                "converted=False, errors=[]"
            )
        else:
            failed += 1
            print(
                f"  ✗ FileResult defaults -- sent={fir.sent}, "
                f"validated={fir.validated}, converted={fir.converted}"
            )
    except Exception as exc:
        failed += 1
        print(f"  ✗ FileResult defaults -- {exc}")

    # ProcessingContext defaults
    try:
        pc = _PC(folder={}, effective_folder={}, settings={}, upc_dict={})
        if pc.temp_dirs == [] and pc.temp_files == []:
            passed += 1
            print("  ✓ ProcessingContext defaults: temp_dirs=[], temp_files=[]")
        else:
            failed += 1
            print(
                f"  ✗ ProcessingContext defaults -- temp_dirs={pc.temp_dirs!r}, "
                f"temp_files={pc.temp_files!r}"
            )
    except Exception as exc:
        failed += 1
        print(f"  ✗ ProcessingContext defaults -- {exc}")

    # DispatchOrchestrator instantiation
    try:
        config = _DC()
        orch = _DO(config)
        if (
            hasattr(orch, "validator")
            and hasattr(orch, "send_manager")
            and hasattr(orch, "error_handler")
        ):
            passed += 1
            print("  ✓ DispatchOrchestrator has .validator, .send_manager, .error_handler")
        else:
            failed += 1
            print("  ✗ DispatchOrchestrator attributes -- missing attrs")
    except Exception as exc:
        failed += 1
        print(f"  ✗ DispatchOrchestrator instantiation -- {exc}")

    try:
        config = _DC()
        orch = _DO(config)
        if orch.processed_count == 0 and orch.error_count == 0:
            passed += 1
            print(
                "  ✓ DispatchOrchestrator initial counts: processed_count=0, "
                "error_count=0"
            )
        else:
            failed += 1
            print(
                f"  ✗ DispatchOrchestrator initial counts -- "
                f"processed={orch.processed_count}, errors={orch.error_count}"
            )
    except Exception as exc:
        failed += 1
        print(f"  ✗ DispatchOrchestrator initial counts -- {exc}")

    # get_summary()
    try:
        config = _DC()
        orch = _DO(config)
        summary = orch.get_summary()
        if summary == "0 processed, 0 errors":
            passed += 1
            print("  ✓ DispatchOrchestrator.get_summary() == '0 processed, 0 errors'")
        else:
            failed += 1
            print(f"  ✗ DispatchOrchestrator.get_summary() -- got {summary!r}")
    except Exception as exc:
        failed += 1
        print(f"  ✗ DispatchOrchestrator.get_summary() -- {exc}")

    # reset()
    try:
        config = _DC()
        orch = _DO(config)
        orch.processed_count = 5
        orch.error_count = 3
        orch.reset()
        if orch.processed_count == 0 and orch.error_count == 0:
            passed += 1
            print("  ✓ DispatchOrchestrator.reset() resets counts to 0")
        else:
            failed += 1
            print(
                f"  ✗ DispatchOrchestrator.reset() -- "
                f"processed={orch.processed_count}, errors={orch.error_count}"
            )
    except Exception as exc:
        failed += 1
        print(f"  ✗ DispatchOrchestrator.reset() -- {exc}")

    # End-to-end orchestrator test
    try:
        from dispatch.send_manager import MockBackend as _MB

        _e2e_tmpdir = tempfile.mkdtemp(prefix="selftest_e2e_")
        _edi_file = os.path.join(_e2e_tmpdir, "test_invoice.edi")
        _edi_content = (
            "A"
            + "VEND01"
            + "INV0012345"
            + "010124"
            + "0000000010"
            + "\n"
            + "B"
            + "00012345678"
            + "Item Description         "
            + "000001"
            + "000100"
            + "01"
            + "000001"
            + "00010"
            + "01000"
            + "   "
            + "      "
            + "\n"
        )
        with open(_edi_file, "w", encoding="utf-8") as _fh:
            _fh.write(_edi_content)

        _mock_backend = _MB(should_succeed=True)
        _e2e_config = _DC(backends={"mock": _mock_backend})
        _orch = _DO(_e2e_config)

        _folder = {
            "folder_name": _e2e_tmpdir,
            "alias": "E2E Test",
        }
        _result = _orch.process_folder(_folder, run_log=[])

        if _result.files_processed == 1:
            passed += 1
            print("  ✓ end-to-end orchestrator: files_processed == 1")
        else:
            failed += 1
            print(
                f"  ✗ end-to-end orchestrator: files_processed -- "
                f"expected 1, got {_result.files_processed} (errors: {_result.errors})"
            )

        if len(_mock_backend.send_calls) == 1:
            passed += 1
            print(
                "  ✓ end-to-end orchestrator: MockBackend.send_calls has 1 entry"
            )
        else:
            failed += 1
            print(
                f"  ✗ end-to-end orchestrator: MockBackend.send_calls -- "
                f"expected 1, got {len(_mock_backend.send_calls)}"
            )

        shutil.rmtree(_e2e_tmpdir, ignore_errors=True)

    except Exception as exc:
        failed += 1
        print(f"  ✗ end-to-end orchestrator test -- {exc}")

    return passed, failed


# -------------------------------------------------------------------------- main


def run_self_test(
    appname: str = "Batch File Sender", version: str = "(Git Branch: Master)"
) -> int:
    """Run all self-test sections. Returns 0 if all pass, 1 otherwise."""
    sections = [
        ("[1/14] Standard-library imports", _check_stdlib_modules),
        ("[1b/14] Third-party (non-Qt) imports", _check_third_party_modules),
        ("[1c/14] Required GUI modules (Qt -- failures will cause test to fail)", _check_qt_modules),
        ("[1d/14] Application module imports", _check_app_modules),
        ("[2/14] Configuration directories", _check_config_directories),
        ("[3/14] appdirs functionality", _check_appdirs),
        ("[4/14] File system access", _check_file_system),
        ("[5/14] Local module availability (__file__ attribute)", _check_module_file_attrs),
        ("[6/14] Constants", _check_constants),
        ("[7/14] Boolean utilities", _check_bool_utils),
        ("[8/14] Date utilities", _check_date_utils),
        ("[9/14] UPC utilities", _check_upc_utils),
        ("[10/14] EDI parser", _check_edi_parser),
        ("[11/14] Hash utilities", _check_hash_utils),
        ("[12/14] Feature flags", _check_feature_flags),
        ("[13/14] Send manager", _check_send_manager),
        ("[14/14] Orchestrator dataclasses and basic orchestration", _check_orchestrator),
    ]

    total_passed = total_failed = 0

    for label, fn in sections:
        print(f"\n{label}")
        passed, failed = fn()
        total_passed += passed
        total_failed += failed
        print()

    total = total_passed + total_failed
    print("=" * 60)
    print(f"Results: {total_passed}/{total} checks passed, {total_failed} failed")
    if total_failed == 0:
        print("STATUS: ALL REQUIRED CHECKS PASSED")
    else:
        print("STATUS: SOME REQUIRED CHECKS FAILED")
    print("=" * 60)

    return 0 if total_failed == 0 else 1


if __name__ == "__main__":
    sys.exit(run_self_test())
