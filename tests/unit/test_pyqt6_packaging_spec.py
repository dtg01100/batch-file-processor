"""Focused tests for PyInstaller spec file completeness.

Ensures that all modules required by the application are listed in the
spec file's hiddenimports so they get bundled by PyInstaller.
"""

import ast
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[2]
SPEC_FILE = PROJECT_ROOT / "main_interface.spec"
DIAGNOSTICS_FILE = PROJECT_ROOT / "interface" / "qt" / "diagnostics.py"


def _get_analysis_keyword(keyword_name: str) -> ast.expr | None:
    with open(SPEC_FILE, encoding="utf-8") as spec_file:
        tree = ast.parse(spec_file.read())

    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue

        func = node.func
        func_name = ""
        if isinstance(func, ast.Name):
            func_name = func.id
        elif isinstance(func, ast.Attribute):
            func_name = func.attr

        if func_name != "Analysis":
            continue

        for keyword in node.keywords:
            if keyword.arg == keyword_name:
                return keyword.value

    return None


def _extract_hidden_imports() -> set[str]:
    hiddenimports_node = _get_analysis_keyword("hiddenimports")
    if hiddenimports_node is None or not isinstance(hiddenimports_node, ast.List):
        return set()

    imports = set()
    for elt in hiddenimports_node.elts:
        if isinstance(elt, ast.Constant) and isinstance(elt.value, str):
            imports.add(elt.value)
    return imports


def _extract_required_modules_from_diagnostics() -> set[str]:
    with open(DIAGNOSTICS_FILE, encoding="utf-8") as f:
        tree = ast.parse(f.read())

    required_modules = set()

    for node in ast.walk(tree):
        if isinstance(node, ast.Assign):
            for target in node.targets:
                if isinstance(target, ast.Name) and target.id == "required_modules":
                    if isinstance(node.value, ast.List):
                        for elt in node.value.elts:
                            if isinstance(elt, ast.Constant) and isinstance(
                                elt.value, str
                            ):
                                required_modules.add(elt.value)
                    break

    return required_modules


@pytest.mark.unit
def test_spec_uses_pyqt5_not_pyqt6():
    """The spec must use PyQt5, not PyQt6 (Qt6 is for development only)."""
    with open(SPEC_FILE, encoding="utf-8") as spec_file:
        spec_source = spec_file.read()

    assert "PyQt5" in spec_source, "Spec must use PyQt5"
    assert "PyQt6" not in spec_source, "Spec must not use PyQt6"


@pytest.mark.unit
def test_spec_collects_pyqt5_runtime_with_pyinstaller_helpers():
    """The spec must collect the bundled Qt5 runtime explicitly."""
    with open(SPEC_FILE, encoding="utf-8") as spec_file:
        spec_source = spec_file.read()

    assert 'collect_data_files("PyQt5")' in spec_source
    assert 'collect_dynamic_libs("PyQt5")' in spec_source


@pytest.mark.unit
def test_spec_hiddenimports_includes_all_app_modules_requiring_bundling():
    """Modules that PyInstaller cannot auto-detect must be listed in hiddenimports.

    This includes: app-level modules (interface.*, backend.*, core.*, dispatch.*),
    third-party packages (lxml, appdirs), and any module imported via
    importlib.import_module at runtime.
    Stdlib modules (os, sys, platform, etc.) are always available and do not
    need explicit hiddenimports.
    """
    hidden_imports = _extract_hidden_imports()

    app_modules_requiring_bundling = [
        "appdirs",
        "lxml",
        "lxml.etree",
        "backend.database.database_obj",
        "backend.ftp_client",
        "backend.smtp_client",
        "backend.copy_backend",
        "backend.ftp_backend",
        "backend.email_backend",
        "core.edi.edi_parser",
        "core.edi.edi_splitter",
        "core.edi.inv_fetcher",
        "core.edi.po_fetcher",
        "dispatch",
        "dispatch.orchestrator",
        "dispatch.send_manager",
        "interface.operations.folder_manager",
        "interface.ports",
        "interface.services.reporting_service",
        "interface.qt.app",
        "interface.qt.dialogs.edit_folders_dialog",
        "interface.qt.dialogs.edit_folders.data_extractor",
        "archive",
        "PyQt5.sip",
    ]

    missing = sorted(
        m for m in app_modules_requiring_bundling if m not in hidden_imports
    )
    assert not missing, (
        f"The following modules require explicit hiddenimports "
        f"(PyInstaller cannot auto-detect them):\n  {missing}"
    )


@pytest.mark.unit
def test_spec_hiddenimports_includes_all_dispatch_converters():
    """All dispatch converter modules must be listed in hiddenimports."""
    hidden_imports = _extract_hidden_imports()

    converters = [
        "dispatch.converters.convert_to_csv",
        "dispatch.converters.convert_to_fintech",
        "dispatch.converters.convert_to_simplified_csv",
        "dispatch.converters.convert_to_stewarts_custom",
        "dispatch.converters.convert_to_tweaks",
        "dispatch.converters.convert_to_yellowdog_csv",
        "dispatch.converters.convert_to_estore_einvoice",
        "dispatch.converters.convert_to_estore_einvoice_generic",
        "dispatch.converters.convert_to_scannerware",
        "dispatch.converters.convert_to_scansheet_type_a",
        "dispatch.converters.convert_to_jolley_custom",
    ]

    missing = [c for c in converters if c not in hidden_imports]
    assert not missing, f"Missing converter hiddenimports: {missing}"


@pytest.mark.unit
def test_spec_hiddenimports_includes_all_backend_modules():
    """All backend modules must be listed in hiddenimports."""
    hidden_imports = _extract_hidden_imports()

    backends = [
        "backend.copy_backend",
        "backend.email_backend",
        "backend.ftp_backend",
    ]

    missing = [b for b in backends if b not in hidden_imports]
    assert not missing, f"Missing backend hiddenimports: {missing}"


@pytest.mark.unit
def test_spec_hiddenimports_includes_archive_modules():
    """archive must be listed in hiddenimports."""
    hidden_imports = _extract_hidden_imports()

    assert "archive" in hidden_imports


@pytest.mark.unit
def test_spec_no_pyi_rth_pyqt6_hook_exists():
    """No PyQt6 runtime hook should exist in the hooks directory."""
    assert not (PROJECT_ROOT / "hooks" / "pyi_rth_pyqt6_qt_bin.py").exists()


@pytest.mark.unit
def test_spec_no_pyqt6_in_hiddenimports():
    """PyQt6 must not appear anywhere in hiddenimports."""
    hidden_imports = _extract_hidden_imports()

    pyqt6_imports = [h for h in hidden_imports if "PyQt6" in h or "Qt6" in h]
    assert not pyqt6_imports, f"PyQt6 must not be in hiddenimports: {pyqt6_imports}"
