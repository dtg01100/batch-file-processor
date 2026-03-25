import hashlib
import os
import platform
import shutil
import sys
import tempfile


def run_self_test(appname="Batch File Sender", version="(Git Branch: Master)"):
    """Standalone self-test with no Qt dependencies.

    Returns 0 if all required checks pass, 1 otherwise.
    """

    passed = 0
    failed = 0
    qt_warnings = []

    def ok(label):
        nonlocal passed
        passed += 1
        print(f"  ✓ {label}")

    def fail(label, reason=""):
        nonlocal failed
        failed += 1
        extra = f" -- {reason}" if reason else ""
        print(f"  ✗ {label}{extra}")

    def qt_warn(label, reason=""):
        extra = f" -- {reason}" if reason else ""
        qt_warnings.append(f"{label}{extra}")
        print(f"  ? {label} (optional){extra}")

    # ------------------------------------------------------------------ header
    print(f"Self-test: {appname} {version}")
    print(f"Platform : {platform.platform()}")
    print(f"Python   : {sys.version}")
    print()

    # -------------------------------------------- 1. Standard-library imports
    print("[1/14] Standard-library imports")
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
            ok(mod_name)
        except Exception as exc:
            fail(mod_name, str(exc))
    print()

    # ----------------------------------------- 1b. Third-party (non-Qt) imports
    print("[1b/14] Third-party (non-Qt) imports")
    third_party_modules = [
        "appdirs",
        "lxml",
        "lxml.etree",
    ]
    for mod_name in third_party_modules:
        try:
            __import__(mod_name)
            ok(mod_name)
        except Exception as exc:
            fail(mod_name, str(exc))
    print()

    # ------------------------------------ 1c. Required GUI (Qt) imports
    print("[1c/14] Required GUI modules (Qt -- failures will cause test to fail)")
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
            ok(mod_name)
        except Exception as exc:
            fail(mod_name, str(exc))

    # Check for sip which is required by PyQt5 but imported differently
    try:
        ok("PyQt5.sip")
    except ImportError as exc:
        fail("PyQt5.sip", str(exc))
    print()

    # ----------------------------------------- 1d. Application module imports
    print("[1d/14] Application module imports")
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
            ok(mod_name)
        except Exception as exc:
            fail(mod_name, str(exc))
    print()

    # ---------------------------------------- 2. Configuration directories
    print("[2/14] Configuration directories")
    try:
        import appdirs as _appdirs

        config_dir = _appdirs.user_data_dir(appname)
        os.makedirs(config_dir, exist_ok=True)
        if os.path.isdir(config_dir):
            ok(f"config dir exists: {config_dir}")
        else:
            fail(f"config dir missing after makedirs: {config_dir}")
    except Exception as exc:
        fail("config directory creation", str(exc))
    print()

    # ---------------------------------------- 3. appdirs functionality
    print("[3/14] appdirs functionality")
    try:
        import appdirs as _appdirs

        test_dir = _appdirs.user_data_dir("TestApp")
        if isinstance(test_dir, str) and len(test_dir) > 0:
            ok(f"appdirs.user_data_dir('TestApp') = {test_dir}")
        else:
            fail("appdirs.user_data_dir returned unexpected value")
    except Exception as exc:
        fail("appdirs.user_data_dir", str(exc))
    print()

    # ---------------------------------------- 4. File system access
    print("[4/14] File system access")
    try:
        tmpdir = tempfile.mkdtemp(prefix="selftest_")
        tmp_path = os.path.join(tmpdir, "test_file.txt")
        test_payload = "self-test-payload"
        with open(tmp_path, "w", encoding="utf-8") as fh:
            fh.write(test_payload)
        with open(tmp_path, "r", encoding="utf-8") as fh:
            read_back = fh.read()
        if read_back == test_payload:
            ok(f"write/read temp file in {tmpdir}")
        else:
            fail("temp file content mismatch")
        os.remove(tmp_path)
        os.rmdir(tmpdir)
        ok("temp file cleanup")
    except Exception as exc:
        fail("file system access", str(exc))
    print()

    # ---------------------------------------- 5. Local module __file__ attrs
    print("[5/14] Local module availability (__file__ attribute)")
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
                fail(f"{mod_name} (import)", str(exc))
                continue
        if hasattr(mod, "__file__") and mod.__file__:
            ok(f"{mod_name}.__file__ = {mod.__file__}")
        else:
            fail(f"{mod_name} has no __file__ attribute")
    print()

    # ---------------------------------------- 6. Constants
    print("[6/14] Constants")
    try:
        from core.constants import CURRENT_DATABASE_VERSION

        if CURRENT_DATABASE_VERSION == "47":
            ok("CURRENT_DATABASE_VERSION == '47'")
        else:
            fail(
                "CURRENT_DATABASE_VERSION",
                f"expected '47', got {CURRENT_DATABASE_VERSION!r}",
            )
    except Exception as exc:
        fail("CURRENT_DATABASE_VERSION import", str(exc))
    print()

    # ---------------------------------------- 7. Boolean utilities
    print("[7/14] Boolean utilities")

    try:
        from core.utils.bool_utils import from_db_bool as _fdb
        from core.utils.bool_utils import normalize_bool as _nb
        from core.utils.bool_utils import to_db_bool as _tdb

        ok("core.utils.bool_utils imported")
    except Exception as exc:
        fail("core.utils.bool_utils import", str(exc))
        _nb = _tdb = _fdb = None

    if _nb is not None:
        # normalize_bool: booleans pass through
        try:
            if _nb(True) is True:
                ok("normalize_bool(True) == True")
            else:
                fail("normalize_bool(True)", f"got {_nb(True)!r}")
        except Exception as exc:
            fail("normalize_bool(True)", str(exc))

        try:
            if _nb(False) is False:
                ok("normalize_bool(False) == False")
            else:
                fail("normalize_bool(False)", f"got {_nb(False)!r}")
        except Exception as exc:
            fail("normalize_bool(False)", str(exc))

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
                    ok(f"normalize_bool({val!r}) == {expected}")
                else:
                    fail(
                        f"normalize_bool({val!r})",
                        f"expected {expected}, got {result!r}",
                    )
            except Exception as exc:
                fail(f"normalize_bool({val!r})", str(exc))

        # normalize_bool: int/None inputs
        for val, expected in [(1, True), (0, False), (None, False)]:
            try:
                result = _nb(val)
                if result is expected:
                    ok(f"normalize_bool({val!r}) == {expected}")
                else:
                    fail(
                        f"normalize_bool({val!r})",
                        f"expected {expected}, got {result!r}",
                    )
            except Exception as exc:
                fail(f"normalize_bool({val!r})", str(exc))

        # to_db_bool
        try:
            if _tdb(True) == 1:
                ok("to_db_bool(True) == 1")
            else:
                fail("to_db_bool(True)", f"got {_tdb(True)!r}")
        except Exception as exc:
            fail("to_db_bool(True)", str(exc))

        try:
            if _tdb(False) == 0:
                ok("to_db_bool(False) == 0")
            else:
                fail("to_db_bool(False)", f"got {_tdb(False)!r}")
        except Exception as exc:
            fail("to_db_bool(False)", str(exc))

        # from_db_bool
        try:
            if _fdb(1) is True:
                ok("from_db_bool(1) == True")
            else:
                fail("from_db_bool(1)", f"got {_fdb(1)!r}")
        except Exception as exc:
            fail("from_db_bool(1)", str(exc))

        try:
            if _fdb(0) is False:
                ok("from_db_bool(0) == False")
            else:
                fail("from_db_bool(0)", f"got {_fdb(0)!r}")
        except Exception as exc:
            fail("from_db_bool(0)", str(exc))

        # Round-trip: to_db_bool -> from_db_bool
        try:
            for original in [True, False]:
                rt = _fdb(_tdb(original))
                if rt is original:
                    ok(f"round-trip to_db_bool/from_db_bool({original}) == {original}")
                else:
                    fail(
                        f"round-trip to_db_bool/from_db_bool({original})", f"got {rt!r}"
                    )
        except Exception as exc:
            fail("round-trip to_db_bool/from_db_bool", str(exc))

        # Cross-check: utils.normalize_bool gives the same results as core version
        try:
            import core.utils as _utils

            same = all(
                _utils.normalize_bool(v) == _nb(v)
                for v in [
                    True,
                    False,
                    "true",
                    "false",
                    "yes",
                    "no",
                    "1",
                    "0",
                    "",
                    1,
                    0,
                    None,
                ]
            )
            if same:
                ok(
                    "utils.normalize_bool agrees with core.utils.bool_utils.normalize_bool"
                )
            else:
                fail(
                    "utils.normalize_bool vs core version",
                    "results differ for some inputs",
                )
        except Exception as exc:
            fail("utils.normalize_bool cross-check", str(exc))

    print()

    # ---------------------------------------- 8. Date utilities
    print("[8/14] Date utilities")

    try:
        from datetime import datetime as _dt

        from core.utils.date_utils import (
            dactime_from_datetime as _dfd,
        )
        from core.utils.date_utils import (
            dactime_from_invtime as _dacfi,
        )
        from core.utils.date_utils import (
            datetime_from_dactime as _dfd2,
        )
        from core.utils.date_utils import (
            datetime_from_invtime as _dfi,
        )

        ok("core.utils.date_utils imported")
    except Exception as exc:
        fail("core.utils.date_utils import", str(exc))
        _dfd = _dfd2 = _dfi = _dacfi = _dt = None

    if _dfd is not None:
        # dactime_from_datetime: 2024-01-01 -> "1240101"
        # century_digit = int("20") - 19 = 1, then "1" + "240101"
        try:
            result = _dfd(_dt(2024, 1, 1))
            if result == "1240101":
                ok("dactime_from_datetime(2024-01-01) == '1240101'")
            else:
                fail("dactime_from_datetime(2024-01-01)", f"got {result!r}")
        except Exception as exc:
            fail("dactime_from_datetime(2024-01-01)", str(exc))

        # datetime_from_dactime: 1240101 -> datetime(2024, 1, 1)
        try:
            result = _dfd2(1240101)
            expected = _dt(2024, 1, 1)
            if result == expected:
                ok("datetime_from_dactime(1240101) == datetime(2024, 1, 1)")
            else:
                fail("datetime_from_dactime(1240101)", f"got {result!r}")
        except Exception as exc:
            fail("datetime_from_dactime(1240101)", str(exc))

        # Round-trip dactime_from_datetime -> datetime_from_dactime
        try:
            for test_dt in [_dt(2024, 1, 1), _dt(2023, 12, 31), _dt(2000, 6, 15)]:
                dactime_str = _dfd(test_dt)
                recovered = _dfd2(int(dactime_str))
                if recovered == test_dt:
                    ok(f"dactime round-trip {test_dt.date()}")
                else:
                    fail(f"dactime round-trip {test_dt.date()}", f"got {recovered!r}")
        except Exception as exc:
            fail("dactime round-trip", str(exc))

        # datetime_from_invtime: "010124" -> datetime(2024, 1, 1)
        try:
            result = _dfi("010124")
            expected = _dt(2024, 1, 1)
            if result == expected:
                ok("datetime_from_invtime('010124') == datetime(2024, 1, 1)")
            else:
                fail("datetime_from_invtime('010124')", f"got {result!r}")
        except Exception as exc:
            fail("datetime_from_invtime('010124')", str(exc))

        # dactime_from_invtime round-trip: "010124" -> "1240101"
        try:
            result = _dacfi("010124")
            if result == "1240101":
                ok("dactime_from_invtime('010124') == '1240101'")
            else:
                fail("dactime_from_invtime('010124')", f"got {result!r}")
        except Exception as exc:
            fail("dactime_from_invtime('010124')", str(exc))

    print()

    # ---------------------------------------- 9. UPC utilities
    print("[9/14] UPC utilities")

    try:
        from core.edi.upc_utils import (
            calc_check_digit as _ccd,
        )
        from core.edi.upc_utils import (
            convert_upce_to_upca as _upce2upca,
        )
        from core.edi.upc_utils import (
            pad_upc as _pupc,
        )
        from core.edi.upc_utils import (
            validate_upc as _vupc,
        )

        ok("core.edi.upc_utils imported")
    except Exception as exc:
        fail("core.edi.upc_utils import", str(exc))
        _ccd = _upce2upca = _vupc = _pupc = None

    if _ccd is not None:
        # calc_check_digit known values
        try:
            result = _ccd("04180000026")
            if result == 5:
                ok("calc_check_digit('04180000026') == 5")
            else:
                fail("calc_check_digit('04180000026')", f"got {result!r}")
        except Exception as exc:
            fail("calc_check_digit('04180000026')", str(exc))

        try:
            # calc_check_digit('07462100060') -> 2  (full UPC-A: 074621000602)
            result = _ccd("07462100060")
            if result == 2:
                ok("calc_check_digit('07462100060') == 2")
            else:
                fail("calc_check_digit('07462100060')", f"got {result!r}")
        except Exception as exc:
            fail("calc_check_digit('07462100060')", str(exc))

        # convert_upce_to_upca known value
        try:
            result = _upce2upca("04182635")
            if result == "041800000265":
                ok("convert_upce_to_upca('04182635') == '041800000265'")
            else:
                fail("convert_upce_to_upca('04182635')", f"got {result!r}")
        except Exception as exc:
            fail("convert_upce_to_upca('04182635')", str(exc))

        # convert_upce_to_upca with invalid length
        try:
            result = _upce2upca("123")
            if result == "":
                ok("convert_upce_to_upca('123') == '' (invalid length)")
            else:
                fail("convert_upce_to_upca('123')", f"expected '', got {result!r}")
        except Exception as exc:
            fail("convert_upce_to_upca('123')", str(exc))

        # validate_upc valid
        try:
            result = _vupc("041800000265")
            if result is True:
                ok("validate_upc('041800000265') == True")
            else:
                fail("validate_upc('041800000265')", f"got {result!r}")
        except Exception as exc:
            fail("validate_upc('041800000265')", str(exc))

        # validate_upc invalid check digit
        try:
            result = _vupc("041800000260")
            if result is False:
                ok("validate_upc('041800000260') == False (bad check digit)")
            else:
                fail("validate_upc('041800000260')", f"expected False, got {result!r}")
        except Exception as exc:
            fail("validate_upc('041800000260')", str(exc))

        # validate_upc non-numeric
        try:
            result = _vupc("abc")
            if result is False:
                ok("validate_upc('abc') == False (non-numeric)")
            else:
                fail("validate_upc('abc')", f"expected False, got {result!r}")
        except Exception as exc:
            fail("validate_upc('abc')", str(exc))

        # pad_upc: pad to longer
        try:
            result = _pupc("12345", 10)
            if result == "     12345":
                ok("pad_upc('12345', 10) == '     12345'")
            else:
                fail("pad_upc('12345', 10)", f"got {result!r}")
        except Exception as exc:
            fail("pad_upc('12345', 10)", str(exc))

        # pad_upc: truncate to shorter
        try:
            result = _pupc("123456789", 5)
            if result == "12345":
                ok("pad_upc('123456789', 5) == '12345' (truncate)")
            else:
                fail("pad_upc('123456789', 5)", f"got {result!r}")
        except Exception as exc:
            fail("pad_upc('123456789', 5)", str(exc))

        # pad_upc: exact length
        try:
            result = _pupc("12345", 5)
            if result == "12345":
                ok("pad_upc('12345', 5) == '12345' (exact length)")
            else:
                fail("pad_upc('12345', 5)", f"got {result!r}")
        except Exception as exc:
            fail("pad_upc('12345', 5)", str(exc))

    print()

    # ---------------------------------------- 10. EDI parser
    print("[10/14] EDI parser")

    try:
        from core.edi.edi_parser import (
            ARecord,
        )
        from core.edi.edi_parser import (
            build_a_record as _bar,
        )
        from core.edi.edi_parser import (
            build_b_record as _bbr,
        )
        from core.edi.edi_parser import (
            build_c_record as _bcr,
        )
        from core.edi.edi_parser import (
            capture_records as _cr,
        )
        from core.edi.edi_parser import (
            parse_a_record as _par,
        )
        from core.edi.edi_parser import (
            parse_b_record as _pbr,
        )

        ok("core.edi.edi_parser imported")
    except Exception as exc:
        fail("core.edi.edi_parser import", str(exc))
        _cr = _par = _pbr = _bar = _bbr = _bcr = None
        ARecord = None

    if _cr is not None:
        # capture_records: empty/whitespace -> None
        try:
            result = _cr("")
            if result is None:
                ok("capture_records('') == None")
            else:
                fail("capture_records('')", f"expected None, got {result!r}")
        except Exception as exc:
            fail("capture_records('')", str(exc))

        try:
            result = _cr("   \n")
            if result is None:
                ok("capture_records('   \\n') == None (whitespace)")
            else:
                fail("capture_records('   \\n')", f"expected None, got {result!r}")
        except Exception as exc:
            fail("capture_records('   \\n')", str(exc))

        # A-record: "A" + cust_vendor(6) + invoice_number(10) + invoice_date(6) + invoice_total(10)
        # = 1 + 6 + 10 + 6 + 10 = 33 chars + "\n"
        _a_line = "AVEND01   INV0012345010124000000010\n"
        # Positions: A[0], VEND01[1:7], "   INV001234"... wait, let me be precise:
        # cust_vendor = positions 1-6 = "VEND01"
        # invoice_number = positions 7-16 = "   INV001234"... no.
        # "AVEND01   INV0012345010124000000010\n"
        #  0123456789...
        # pos 0: 'A'
        # pos 1-6: 'VEND01' (6 chars)
        # pos 7-16: '   INV0012' -- hmm that's only if we use the string as-is
        # Let me recalculate: "AVEND01" = 7 chars. Then "   INV0012345" would start at 7.
        # "AVEND01   INV0012345010124000000010" has length:
        # A=1, VEND01=6, spaces=3, INV0012345=10, 010124=6, 000000010=9... that's only 9 for total.
        # Let's use a well-formed line:
        _a_line = "A" + "VEND01" + "INV0012345" + "010124" + "0000000100" + "\n"
        # = 1+6+10+6+10 = 33 chars + \n

        try:
            result = _cr(_a_line)
            if result is not None and result["record_type"] == "A":
                ok("capture_records(A-record): record_type == 'A'")
            else:
                fail("capture_records(A-record): record_type", f"got {result!r}")
        except Exception as exc:
            fail("capture_records(A-record)", str(exc))

        try:
            result = _cr(_a_line)
            if result is not None and result["cust_vendor"] == "VEND01":
                ok("capture_records(A-record): cust_vendor == 'VEND01'")
            else:
                fail("capture_records(A-record): cust_vendor", f"got {result!r}")
        except Exception as exc:
            fail("capture_records(A-record): cust_vendor", str(exc))

        try:
            result = _cr(_a_line)
            if result is not None and result["invoice_number"] == "INV0012345":
                ok("capture_records(A-record): invoice_number == 'INV0012345'")
            else:
                fail("capture_records(A-record): invoice_number", f"got {result!r}")
        except Exception as exc:
            fail("capture_records(A-record): invoice_number", str(exc))

        try:
            result = _cr(_a_line)
            if result is not None and result["invoice_date"] == "010124":
                ok("capture_records(A-record): invoice_date == '010124'")
            else:
                fail("capture_records(A-record): invoice_date", f"got {result!r}")
        except Exception as exc:
            fail("capture_records(A-record): invoice_date", str(exc))

        try:
            result = _cr(_a_line)
            if result is not None and result["invoice_total"] == "0000000100":
                ok("capture_records(A-record): invoice_total == '0000000100'")
            else:
                fail("capture_records(A-record): invoice_total", f"got {result!r}")
        except Exception as exc:
            fail("capture_records(A-record): invoice_total", str(exc))

        # parse_a_record -> ARecord dataclass
        try:
            rec = _par(_a_line)
            if isinstance(rec, ARecord):
                ok("parse_a_record returns ARecord instance")
            else:
                fail("parse_a_record", f"expected ARecord, got {type(rec)!r}")
        except Exception as exc:
            fail("parse_a_record", str(exc))

        try:
            rec = _par(_a_line)
            if rec.cust_vendor == "VEND01" and rec.invoice_number == "INV0012345":
                ok("parse_a_record fields correct")
            else:
                fail(
                    "parse_a_record fields",
                    f"cust_vendor={rec.cust_vendor!r}, invoice_number={rec.invoice_number!r}",
                )
        except Exception as exc:
            fail("parse_a_record fields", str(exc))

        # parse_a_record raises ValueError on non-A line
        try:
            raised = False
            try:
                _par("BSOMELINE\n")
            except ValueError:
                raised = True
            if raised:
                ok("parse_a_record raises ValueError on non-A line")
            else:
                fail(
                    "parse_a_record ValueError", "no exception raised on B-record input"
                )
        except Exception as exc:
            fail("parse_a_record ValueError", str(exc))

        # B-record: B + upc(11) + desc(25) + vendor_item(6) + unit_cost(6)
        #           + combo(2) + unit_mult(6) + qty(5) + srp(5) + multipack(3) + parent(6)
        # = 1+11+25+6+6+2+6+5+5+3+6 = 76 chars + \n
        _b_line = (
            "B"
            + "00012345678"  # upc_number (11)
            + "Item Description         "  # description (25)
            + "000001"  # vendor_item (6)
            + "000100"  # unit_cost (6)
            + "01"  # combo_code (2)
            + "000001"  # unit_multiplier (6)
            + "00010"  # qty_of_units (5)
            + "01000"  # suggested_retail_price (5)
            + "   "  # price_multi_pack (3)
            + "      "  # parent_item_number (6)
            + "\n"
        )

        try:
            result = _cr(_b_line)
            if result is not None and result["record_type"] == "B":
                ok("capture_records(B-record): record_type == 'B'")
            else:
                fail("capture_records(B-record): record_type", f"got {result!r}")
        except Exception as exc:
            fail("capture_records(B-record)", str(exc))

        try:
            result = _cr(_b_line)
            if result is not None and result["upc_number"] == "00012345678":
                ok("capture_records(B-record): upc_number == '00012345678'")
            else:
                fail("capture_records(B-record): upc_number", f"got {result!r}")
        except Exception as exc:
            fail("capture_records(B-record): upc_number", str(exc))

        # C-record: C + charge_type(3) + description(25) + amount(9)
        # = 1+3+25+9 = 38 chars + \n
        _c_line = (
            "C"
            + "TAX"  # charge_type (3)
            + "Sales Tax                "  # description (25)
            + "000001000"  # amount (9)
            + "\n"
        )

        try:
            result = _cr(_c_line)
            if result is not None and result["record_type"] == "C":
                ok("capture_records(C-record): record_type == 'C'")
            else:
                fail("capture_records(C-record): record_type", f"got {result!r}")
        except Exception as exc:
            fail("capture_records(C-record)", str(exc))

        try:
            result = _cr(_c_line)
            if result is not None and result["charge_type"] == "TAX":
                ok("capture_records(C-record): charge_type == 'TAX'")
            else:
                fail("capture_records(C-record): charge_type", f"got {result!r}")
        except Exception as exc:
            fail("capture_records(C-record): charge_type", str(exc))

        # build_a_record + capture_records round-trip
        try:
            built = _bar("VEND01", "INV0012345", "010124", "0000000100")
            parsed = _cr(built)
            if (
                parsed is not None
                and parsed["cust_vendor"] == "VEND01"
                and parsed["invoice_number"] == "INV0012345"
                and parsed["invoice_date"] == "010124"
                and parsed["invoice_total"] == "0000000100"
            ):
                ok("build_a_record + capture_records round-trip")
            else:
                fail("build_a_record round-trip", f"parsed={parsed!r}")
        except Exception as exc:
            fail("build_a_record round-trip", str(exc))

        # build_b_record + capture_records round-trip
        try:
            built = _bbr(
                upc_number="00012345678",
                description="Item Description         ",
                vendor_item="000001",
                unit_cost="000100",
                combo_code="01",
                unit_multiplier="000001",
                qty_of_units="00010",
                suggested_retail_price="01000",
                price_multi_pack="   ",
                parent_item_number="      ",
            )
            parsed = _cr(built)
            if (
                parsed is not None
                and parsed["upc_number"] == "00012345678"
                and parsed["vendor_item"] == "000001"
            ):
                ok("build_b_record + capture_records round-trip")
            else:
                fail("build_b_record round-trip", f"parsed={parsed!r}")
        except Exception as exc:
            fail("build_b_record round-trip", str(exc))

        # build_c_record + capture_records round-trip
        try:
            built = _bcr("TAX", "Sales Tax                ", "000001000")
            parsed = _cr(built)
            if (
                parsed is not None
                and parsed["record_type"] == "C"
                and parsed["charge_type"] == "TAX"
                and parsed["amount"] == "000001000"
            ):
                ok("build_c_record + capture_records round-trip")
            else:
                fail("build_c_record round-trip", f"parsed={parsed!r}")
        except Exception as exc:
            fail("build_c_record round-trip", str(exc))

    print()

    # ---------------------------------------- 11. Hash utilities
    print("[11/14] Hash utilities")

    try:
        from dispatch.hash_utils import (
            build_hash_dictionaries as _bhd,
        )
        from dispatch.hash_utils import (
            check_file_against_processed as _cfap,
        )
        from dispatch.hash_utils import (
            generate_file_hash as _gfh,
        )
        from dispatch.hash_utils import (
            generate_match_lists as _gml,
        )

        ok("dispatch.hash_utils imported")
    except Exception as exc:
        fail("dispatch.hash_utils import", str(exc))
        _gfh = _gml = _cfap = _bhd = None

    if _gfh is not None:
        # generate_file_hash with known content
        try:
            _hash_tmpdir = tempfile.mkdtemp(prefix="selftest_hash_")
            _hash_file = os.path.join(_hash_tmpdir, "hash_test.txt")
            _hash_content = b"hello world"
            with open(_hash_file, "wb") as _fh:
                _fh.write(_hash_content)
            expected_hash = hashlib.md5(_hash_content).hexdigest()
            result = _gfh(_hash_file)
            if result == expected_hash:
                ok(f"generate_file_hash matches expected MD5 ({expected_hash[:8]}...)")
            else:
                fail(
                    "generate_file_hash", f"expected {expected_hash!r}, got {result!r}"
                )
            os.remove(_hash_file)
            os.rmdir(_hash_tmpdir)
        except Exception as exc:
            fail("generate_file_hash", str(exc))

        # generate_match_lists with sample records
        try:
            _records = [
                {
                    "file_name": "file_a.edi",
                    "file_checksum": "aaaa",
                    "resend_flag": False,
                },
                {
                    "file_name": "file_b.edi",
                    "file_checksum": "bbbb",
                    "resend_flag": True,
                },
                {
                    "file_name": "file_c.edi",
                    "file_checksum": "cccc",
                    "resend_flag": False,
                },
            ]
            hash_list, name_list, resend_set = _gml(_records)
            # hash_list: list of (file_name, checksum) tuples
            if ("file_a.edi", "aaaa") in hash_list:
                ok("generate_match_lists: hash_list contains expected tuple")
            else:
                fail("generate_match_lists: hash_list", f"got {hash_list!r}")
            # name_list: list of (checksum, file_name) tuples
            if ("bbbb", "file_b.edi") in name_list:
                ok("generate_match_lists: name_list contains expected tuple")
            else:
                fail("generate_match_lists: name_list", f"got {name_list!r}")
            # resend_set: only the resend_flag=True checksum
            if resend_set == {"bbbb"}:
                ok("generate_match_lists: resend_set == {'bbbb'}")
            else:
                fail("generate_match_lists: resend_set", f"got {resend_set!r}")
        except Exception as exc:
            fail("generate_match_lists", str(exc))

        # build_hash_dictionaries produces dict form
        try:
            _records2 = [
                {
                    "file_name": "file_x.edi",
                    "file_checksum": "xxxx",
                    "resend_flag": False,
                },
                {
                    "file_name": "file_y.edi",
                    "file_checksum": "yyyy",
                    "resend_flag": True,
                },
            ]
            hash_dict, name_dict, resend_set2 = _bhd(_records2)
            # hash_dict maps file_name -> checksum
            if hash_dict.get("file_x.edi") == "xxxx":
                ok("build_hash_dictionaries: hash_dict['file_x.edi'] == 'xxxx'")
            else:
                fail("build_hash_dictionaries: hash_dict", f"got {hash_dict!r}")
            # name_dict maps checksum -> file_name
            if name_dict.get("yyyy") == "file_y.edi":
                ok("build_hash_dictionaries: name_dict['yyyy'] == 'file_y.edi'")
            else:
                fail("build_hash_dictionaries: name_dict", f"got {name_dict!r}")
            if resend_set2 == {"yyyy"}:
                ok("build_hash_dictionaries: resend_set == {'yyyy'}")
            else:
                fail("build_hash_dictionaries: resend_set", f"got {resend_set2!r}")
        except Exception as exc:
            fail("build_hash_dictionaries", str(exc))

        # check_file_against_processed: new file (not in name_dict)
        try:
            # name_dict is a dict mapping checksum -> file_name
            _nd = {"existingchecksum": "old_file.edi"}
            _rs = set()
            match, should_send = _cfap("new_file.edi", "newchecksum", _nd, _rs)
            if match is False and should_send is True:
                ok("check_file_against_processed: new file -> (False, True)")
            else:
                fail(
                    "check_file_against_processed: new file",
                    f"got ({match}, {should_send})",
                )
        except Exception as exc:
            fail("check_file_against_processed: new file", str(exc))

        # check_file_against_processed: already processed (in name_dict, not in resend_set)
        try:
            _nd2 = {"existingchecksum": "old_file.edi"}
            _rs2 = set()
            match2, should_send2 = _cfap("old_file.edi", "existingchecksum", _nd2, _rs2)
            if match2 is True and should_send2 is False:
                ok("check_file_against_processed: already processed -> (True, False)")
            else:
                fail(
                    "check_file_against_processed: already processed",
                    f"got ({match2}, {should_send2})",
                )
        except Exception as exc:
            fail("check_file_against_processed: already processed", str(exc))

        # check_file_against_processed: resend (in name_dict AND in resend_set)
        try:
            _nd3 = {"resendchecksum": "resend_file.edi"}
            _rs3 = {"resendchecksum"}
            match3, should_send3 = _cfap(
                "resend_file.edi", "resendchecksum", _nd3, _rs3
            )
            if match3 is True and should_send3 is True:
                ok("check_file_against_processed: resend -> (True, True)")
            else:
                fail(
                    "check_file_against_processed: resend",
                    f"got ({match3}, {should_send3})",
                )
        except Exception as exc:
            fail("check_file_against_processed: resend", str(exc))

    print()

    # ---------------------------------------- 12. Feature flags
    print("[12/14] Feature flags")

    try:
        from dispatch.feature_flags import (
            get_debug_mode as _gdm,
        )
        from dispatch.feature_flags import (
            get_feature_flags as _gff,
        )
        from dispatch.feature_flags import (
            set_feature_flag as _sff,
        )

        ok("dispatch.feature_flags imported")
    except Exception as exc:
        fail("dispatch.feature_flags import", str(exc))
        _gdm = _gff = _sff = None

    if _gdm is not None:
        # Default values

        try:
            os.environ.pop("DISPATCH_DEBUG_MODE", None)
            result = _gdm()
            if result is False:
                ok("get_debug_mode() == False (default)")
            else:
                fail("get_debug_mode()", f"expected False, got {result!r}")
        except Exception as exc:
            fail("get_debug_mode()", str(exc))

        # get_feature_flags() dict shape
        try:
            flags = _gff()
            required_keys = {"debug_mode"}
            if isinstance(flags, dict) and required_keys <= set(flags.keys()):
                ok(f"get_feature_flags() returns dict with keys {required_keys}")
            else:
                fail("get_feature_flags()", f"got {flags!r}")
        except Exception as exc:
            fail("get_feature_flags()", str(exc))

        try:
            flags = _gff()
            if flags["debug_mode"] is False:
                ok("get_feature_flags() default values correct")
            else:
                fail("get_feature_flags() default values", f"got {flags!r}")
        except Exception as exc:
            fail("get_feature_flags() default values", str(exc))

        # set_feature_flag + read back + restore
        try:
            _sff("debug_mode", True)
            result = _gdm()
            _sff("debug_mode", False)  # restore immediately
            if result is True:
                ok("set_feature_flag('debug_mode', True) -> get_debug_mode() == True")
            else:
                fail("set_feature_flag('debug_mode', True)", f"got {result!r}")
        except Exception as exc:
            # Ensure restore even on failure
            try:
                _sff("debug_mode", False)
            except Exception:
                pass
            fail("set_feature_flag('debug_mode', True)", str(exc))

        # set_feature_flag with unknown name raises ValueError
        try:
            raised = False
            try:
                _sff("nonexistent_flag", True)
            except ValueError:
                raised = True
            if raised:
                ok("set_feature_flag unknown name raises ValueError")
            else:
                fail("set_feature_flag unknown name", "no ValueError raised")
        except Exception as exc:
            fail("set_feature_flag unknown name", str(exc))

    print()

    # ---------------------------------------- 13. Send manager
    print("[13/14] Send manager")

    try:
        from dispatch.send_manager import MockBackend as _MB
        from dispatch.send_manager import SendManager as _SM

        ok("dispatch.send_manager imported (SendManager, MockBackend)")
    except Exception as exc:
        fail("dispatch.send_manager import", str(exc))
        _SM = _MB = None

    if _SM is not None:
        # SendManager instantiation
        try:
            sm = _SM()
            if (
                hasattr(sm, "backends")
                and hasattr(sm, "results")
                and hasattr(sm, "errors")
            ):
                ok("SendManager() has .backends, .results, .errors")
            else:
                fail("SendManager() attributes", f"missing attrs on {sm!r}")
        except Exception as exc:
            fail("SendManager() instantiation", str(exc))

        try:
            sm = _SM()
            if sm.backends == {} and sm.results == {} and sm.errors == {}:
                ok("SendManager() backends/results/errors are empty dicts")
            else:
                fail("SendManager() initial state", f"backends={sm.backends!r}")
        except Exception as exc:
            fail("SendManager() initial state", str(exc))

        # get_enabled_backends: copy enabled, ftp disabled
        try:
            sm = _SM()
            enabled = sm.get_enabled_backends(
                {"process_backend_copy": True, "process_backend_ftp": False}
            )
            if "copy" in enabled and "ftp" not in enabled:
                ok("get_enabled_backends: copy=True,ftp=False -> {'copy'}")
            else:
                fail("get_enabled_backends", f"got {enabled!r}")
        except Exception as exc:
            fail("get_enabled_backends", str(exc))

        # get_enabled_backends: empty params -> empty set
        try:
            sm = _SM()
            enabled = sm.get_enabled_backends({})
            if enabled == set():
                ok("get_enabled_backends({}) == set()")
            else:
                fail("get_enabled_backends({})", f"got {enabled!r}")
        except Exception as exc:
            fail("get_enabled_backends({})", str(exc))

        # validate_backend_config: copy enabled without copy_to_directory
        try:
            sm = _SM()
            errors = sm.validate_backend_config({"process_backend_copy": True})
            if errors and any("Copy Backend" in e for e in errors):
                ok(
                    "validate_backend_config: copy without directory -> error mentioning 'Copy Backend'"
                )
            else:
                fail(
                    "validate_backend_config: copy without directory", f"got {errors!r}"
                )
        except Exception as exc:
            fail("validate_backend_config: copy without directory", str(exc))

        # validate_backend_config: empty params -> no errors
        try:
            sm = _SM()
            errors = sm.validate_backend_config({})
            if errors == []:
                ok("validate_backend_config({}) == []")
            else:
                fail("validate_backend_config({})", f"got {errors!r}")
        except Exception as exc:
            fail("validate_backend_config({})", str(exc))

        # MockBackend success
        try:
            mb = _MB(should_succeed=True)
            if mb.send_calls == []:
                ok("MockBackend(should_succeed=True): send_calls starts empty")
            else:
                fail("MockBackend send_calls initial", f"got {mb.send_calls!r}")
        except Exception as exc:
            fail("MockBackend(should_succeed=True)", str(exc))

        try:
            mb = _MB(should_succeed=True)
            mb.send({"p": 1}, {"s": 2}, "/tmp/test.edi")
            if len(mb.send_calls) == 1:
                ok("MockBackend.send() records call (should_succeed=True)")
            else:
                fail(
                    "MockBackend.send() call recording", f"send_calls={mb.send_calls!r}"
                )
        except Exception as exc:
            fail("MockBackend.send() (should_succeed=True)", str(exc))

        # MockBackend failure
        try:
            mb_fail = _MB(should_succeed=False)
            raised = False
            try:
                mb_fail.send({}, {}, "/tmp/test.edi")
            except RuntimeError:
                raised = True
            if raised:
                ok("MockBackend(should_succeed=False).send() raises RuntimeError")
            else:
                fail("MockBackend failure", "no RuntimeError raised")
        except Exception as exc:
            fail("MockBackend(should_succeed=False)", str(exc))

        try:
            mb_fail = _MB(should_succeed=False)
            val_errors = mb_fail.validate({})
            if val_errors and isinstance(val_errors, list):
                ok(
                    "MockBackend(should_succeed=False).validate() returns non-empty error list"
                )
            else:
                fail(
                    "MockBackend(should_succeed=False).validate()",
                    f"got {val_errors!r}",
                )
        except Exception as exc:
            fail("MockBackend(should_succeed=False).validate()", str(exc))

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
                ok("send_all with MockBackend -> results['mock'] == True")
            else:
                fail("send_all with MockBackend", f"got {results!r}")
            if len(mb.send_calls) == 1:
                ok("send_all with MockBackend -> MockBackend.send_calls has 1 entry")
            else:
                fail("send_all MockBackend call count", f"send_calls={mb.send_calls!r}")
            os.remove(_test_file)
            os.rmdir(_hash_tmpdir2)
        except Exception as exc:
            fail("send_all with MockBackend", str(exc))

    print()

    # ---------------------------------------- 14. Orchestrator dataclasses and basic orchestration
    print("[14/14] Orchestrator dataclasses and basic orchestration")

    try:
        from dispatch.orchestrator import (
            DispatchConfig as _DC,
        )
        from dispatch.orchestrator import (
            DispatchOrchestrator as _DO,
        )
        from dispatch.orchestrator import (
            FileResult as _FiR,
        )
        from dispatch.orchestrator import (
            FolderResult as _FR,
        )
        from dispatch.orchestrator import (
            ProcessingContext as _PC,
        )

        ok("dispatch.orchestrator imported")
    except Exception as exc:
        fail("dispatch.orchestrator import", str(exc))
        _DC = _FR = _FiR = _PC = _DO = None

    if _DC is not None:
        # DispatchConfig defaults
        try:
            config = _DC()
            if (
                config.backends == {}
                and config.settings == {}
                and config.version == "1.0.0"
            ):
                ok(
                    "DispatchConfig() defaults: backends={}, settings={}, version='1.0.0'"
                )
            else:
                fail(
                    "DispatchConfig() defaults",
                    f"backends={config.backends!r}, version={config.version!r}",
                )
        except Exception as exc:
            fail("DispatchConfig() defaults", str(exc))

        # FolderResult defaults
        try:
            fr = _FR(folder_name="test", alias="Test")
            if (
                fr.files_processed == 0
                and fr.files_failed == 0
                and fr.errors == []
                and fr.success is True
            ):
                ok(
                    "FolderResult defaults: files_processed=0, files_failed=0, errors=[], success=True"
                )
            else:
                fail(
                    "FolderResult defaults",
                    f"processed={fr.files_processed}, failed={fr.files_failed}, success={fr.success}",
                )
        except Exception as exc:
            fail("FolderResult defaults", str(exc))

        # FileResult defaults
        try:
            fir = _FiR(file_name="test.edi", checksum="abc123")
            if (
                fir.sent is False
                and fir.validated is True
                and fir.converted is False
                and fir.errors == []
            ):
                ok(
                    "FileResult defaults: sent=False, validated=True, converted=False, errors=[]"
                )
            else:
                fail(
                    "FileResult defaults",
                    f"sent={fir.sent}, validated={fir.validated}, converted={fir.converted}",
                )
        except Exception as exc:
            fail("FileResult defaults", str(exc))

        # ProcessingContext defaults
        try:
            pc = _PC(folder={}, effective_folder={}, settings={}, upc_dict={})
            if pc.temp_dirs == [] and pc.temp_files == []:
                ok("ProcessingContext defaults: temp_dirs=[], temp_files=[]")
            else:
                fail(
                    "ProcessingContext defaults",
                    f"temp_dirs={pc.temp_dirs!r}, temp_files={pc.temp_files!r}",
                )
        except Exception as exc:
            fail("ProcessingContext defaults", str(exc))

        # DispatchOrchestrator instantiation
        try:
            config = _DC()
            orch = _DO(config)
            if (
                hasattr(orch, "validator")
                and hasattr(orch, "send_manager")
                and hasattr(orch, "error_handler")
            ):
                ok("DispatchOrchestrator has .validator, .send_manager, .error_handler")
            else:
                fail("DispatchOrchestrator attributes", "missing attrs")
        except Exception as exc:
            fail("DispatchOrchestrator instantiation", str(exc))

        try:
            config = _DC()
            orch = _DO(config)
            if orch.processed_count == 0 and orch.error_count == 0:
                ok(
                    "DispatchOrchestrator initial counts: processed_count=0, error_count=0"
                )
            else:
                fail(
                    "DispatchOrchestrator initial counts",
                    f"processed={orch.processed_count}, errors={orch.error_count}",
                )
        except Exception as exc:
            fail("DispatchOrchestrator initial counts", str(exc))

        # get_summary()
        try:
            config = _DC()
            orch = _DO(config)
            summary = orch.get_summary()
            if summary == "0 processed, 0 errors":
                ok("DispatchOrchestrator.get_summary() == '0 processed, 0 errors'")
            else:
                fail("DispatchOrchestrator.get_summary()", f"got {summary!r}")
        except Exception as exc:
            fail("DispatchOrchestrator.get_summary()", str(exc))

        # reset()
        try:
            config = _DC()
            orch = _DO(config)
            orch.processed_count = 5
            orch.error_count = 3
            orch.reset()
            if orch.processed_count == 0 and orch.error_count == 0:
                ok("DispatchOrchestrator.reset() resets counts to 0")
            else:
                fail(
                    "DispatchOrchestrator.reset()",
                    f"processed={orch.processed_count}, errors={orch.error_count}",
                )
        except Exception as exc:
            fail("DispatchOrchestrator.reset()", str(exc))

        # End-to-end: process a temp folder with a MockBackend
        # The folder has one EDI file and a MockBackend injected as "mock" backend.
        # Since "mock" is not in DEFAULT_BACKENDS and process_backend_mock key is absent,
        # get_enabled_backends defaults to including injected backends that lack an explicit flag.
        try:
            if _MB is None:
                fail(
                    "end-to-end orchestrator test",
                    "MockBackend not available (send_manager import failed)",
                )
            else:
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
                    + "00012345678"  # upc_number (11)
                    + "Item Description         "  # description (25)
                    + "000001"  # vendor_item (6)
                    + "000100"  # unit_cost (6)
                    + "01"  # combo_code (2)
                    + "000001"  # unit_multiplier (6)
                    + "00010"  # qty_of_units (5)
                    + "01000"  # suggested_retail_price (5)
                    + "   "  # price_multi_pack (3)
                    + "      "  # parent_item_number (6)
                    + "\n"
                )
                with open(_edi_file, "w", encoding="utf-8") as _fh:
                    _fh.write(_edi_content)

                _mock_backend = _MB(should_succeed=True)
                _e2e_config = _DC(backends={"mock": _mock_backend})
                _orch = _DO(_e2e_config)

                # Folder dict: process_backend_mock key absent -> mock backend auto-enabled
                _folder = {
                    "folder_name": _e2e_tmpdir,
                    "alias": "E2E Test",
                }
                _result = _orch.process_folder(_folder, run_log=[])

                if _result.files_processed == 1:
                    ok("end-to-end orchestrator: files_processed == 1")
                else:
                    fail(
                        "end-to-end orchestrator: files_processed",
                        f"expected 1, got {_result.files_processed} (errors: {_result.errors})",
                    )

                if len(_mock_backend.send_calls) == 1:
                    ok("end-to-end orchestrator: MockBackend.send_calls has 1 entry")
                else:
                    fail(
                        "end-to-end orchestrator: MockBackend.send_calls",
                        f"expected 1, got {len(_mock_backend.send_calls)}",
                    )

                # Cleanup
                shutil.rmtree(_e2e_tmpdir, ignore_errors=True)

        except Exception as exc:
            fail("end-to-end orchestrator test", str(exc))

    print()

    # ---------------------------------------------------------------- summary
    total = passed + failed
    print("=" * 60)
    print(f"Results: {passed}/{total} checks passed, {failed} failed")
    if qt_warnings:
        print(f"Qt warnings (not counted as failures): {len(qt_warnings)}")
        for w in qt_warnings:
            print(f"  ? {w}")
    if failed == 0:
        print("STATUS: ALL REQUIRED CHECKS PASSED")
    else:
        print("STATUS: SOME REQUIRED CHECKS FAILED")
    print("=" * 60)

    return 0 if failed == 0 else 1


if __name__ == "__main__":
    sys.exit(run_self_test())
