import os
import platform
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
        print(f"  \u2713 {label}")

    def fail(label, reason=""):
        nonlocal failed
        failed += 1
        extra = f" -- {reason}" if reason else ""
        print(f"  \u2717 {label}{extra}")

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
    print("[1/5] Standard-library imports")
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
    print("[1b/5] Third-party (non-Qt) imports")
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
    print("[1c/5] Required GUI modules (Qt -- failures will cause test to fail)")
    qt_modules = [
        "PyQt6.QtCore",
        "PyQt6.QtWidgets",
        "PyQt6.QtGui",
        "PyQt6.QtPrintSupport",
        "PyQt6.QtSvg",
        "PyQt6.QtXml",
        "PyQt6.QtNetwork",
    ]
    for mod_name in qt_modules:
        try:
            __import__(mod_name)
            ok(mod_name)
        except Exception as exc:
            fail(mod_name, str(exc))
    
    # Check for sip which is required by PyQt6 but imported differently
    try:
        import PyQt6.sip
        ok("PyQt6.sip")
    except ImportError as exc:
        fail("PyQt6.sip", str(exc))
    print()

    # ----------------------------------------- 1d. Application module imports
    print("[1d/5] Application module imports")
    app_modules = [
        "interface.database.database_obj",
        "interface.operations.folder_manager",
        "interface.ports",
        "interface.services.reporting_service",
        "batch_log_sender",
        "print_run_log",
        "utils",
        "backup_increment",
        # Core business logic modules
        "core.edi.edi_parser",
        "core.edi.edi_splitter",
        "core.edi.inv_fetcher",
        "core.edi.po_fetcher",
        "dispatch",
        "dispatch.orchestrator",
        "dispatch.send_manager",
        "backend.ftp_client",
        "backend.smtp_client",
        "edi_tweaks",
        "record_error",
        "folders_database_migrator",
        "mover",
        "clear_old_files",
        "rclick_menu",
        "mtc_edi_validator",
    ]
    for mod_name in app_modules:
        try:
            __import__(mod_name)
            ok(mod_name)
        except Exception as exc:
            fail(mod_name, str(exc))
    print()

    # ---------------------------------------- 2. Configuration directories
    print("[2/5] Configuration directories")
    try:
        import appdirs as _appdirs

        config_dir = _appdirs.user_data_dir(appname)
        os.makedirs(config_dir, exist_ok=True)
        if os.path.isdir(config_dir):
            ok(f"config dir exists: {config_dir}")
        else:
            fail(f"config dir missing after makedirs: {config_dir}")
    except Exception as exc:
        fail(f"config directory creation", str(exc))
    print()

    # ---------------------------------------- 3. appdirs functionality
    print("[3/5] appdirs functionality")
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
    print("[4/5] File system access")
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
    print("[5/5] Local module availability (__file__ attribute)")
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
