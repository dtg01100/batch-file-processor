"""Consolidated tests for PyInstaller spec file completeness.

These tests verify that:
- The spec file is configured correctly
- All required modules are in hiddenimports
- PyQt5 (not PyQt6) is used
- Hook files are properly configured
"""

import ast
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[2]
SPEC_FILE = PROJECT_ROOT / "main_interface.spec"
HOOKS_DIR = PROJECT_ROOT / "hooks"
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


def _get_hook_hidden_imports() -> set[str]:
    hidden_imports = set()
    if not HOOKS_DIR.exists():
        return hidden_imports

    for hook_file in HOOKS_DIR.glob("hook-*.py"):
        try:
            content = hook_file.read_text(encoding="utf-8")
            if "collect_submodules" in content:
                tree = ast.parse(content)
                for node in ast.walk(tree):
                    if isinstance(node, ast.Assign):
                        for target in node.targets:
                            if (
                                isinstance(target, ast.Name)
                                and target.id == "hiddenimports"
                            ):
                                if isinstance(node.value, ast.List):
                                    for elt in node.value.elts:
                                        if isinstance(elt, ast.Constant):
                                            hidden_imports.add(elt.value)
        except Exception:
            pass
    return hidden_imports


def _get_all_hidden_imports() -> set[str]:
    return _extract_hidden_imports() | _get_hook_hidden_imports()


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


class TestSpecFileConfiguration:
    """Verify spec file is correctly configured."""

    @pytest.mark.unit
    def test_spec_file_exists(self):
        assert SPEC_FILE.exists(), f"Spec file {SPEC_FILE} should exist"

    @pytest.mark.unit
    def test_spec_uses_pyqt5_not_pyqt6(self):
        with open(SPEC_FILE, encoding="utf-8") as spec_file:
            spec_source = spec_file.read()

        assert "PyQt5" in spec_source, "Spec must use PyQt5"
        assert "PyQt6" not in spec_source, "Spec must not use PyQt6"

    @pytest.mark.unit
    def test_spec_collects_pyqt5_runtime_with_pyinstaller_helpers(self):
        with open(SPEC_FILE, encoding="utf-8") as spec_file:
            spec_source = spec_file.read()

        assert 'collect_data_files("PyQt5")' in spec_source
        assert 'collect_dynamic_libs("PyQt5")' in spec_source

    @pytest.mark.unit
    def test_spec_hooks_directory_configured(self):
        with open(SPEC_FILE, encoding="utf-8") as spec_file:
            content = spec_file.read()

        assert "hookspath" in content, "Spec file should configure hookspath"
        assert "hooks" in content, "Spec file should include hooks directory"

    @pytest.mark.unit
    def test_hooks_directory_exists(self):
        assert HOOKS_DIR.exists(), f"Hooks directory {HOOKS_DIR} should exist"

    @pytest.mark.unit
    def test_no_pyqt6_runtime_hooks(self):
        pyqt6_hooks = list(HOOKS_DIR.glob("pyi_rth_pyqt6*.py"))
        assert not pyqt6_hooks, f"Found PyQt6 hooks: {pyqt6_hooks}"


class TestPyQt5Runtime:
    """PyQt5 runtime modules must be in hiddenimports."""

    REQUIRED_PYQT5 = [
        "PyQt5.sip",
        "PyQt5.QtCore",
        "PyQt5.QtGui",
        "PyQt5.QtWidgets",
        "PyQt5.QtNetwork",
    ]

    @pytest.mark.unit
    def test_pyqt5_runtime_in_hiddenimports(self):
        spec_hidden = _extract_hidden_imports()
        missing = [m for m in self.REQUIRED_PYQT5 if m not in spec_hidden]
        assert not missing, f"Missing PyQt5 hiddenimports: {missing}"

    @pytest.mark.unit
    def test_no_pyqt6_in_hiddenimports(self):
        spec_hidden = _extract_hidden_imports()
        pyqt6_imports = [h for h in spec_hidden if "PyQt6" in h or "Qt6" in h]
        assert not pyqt6_imports, f"Found Qt6 in hiddenimports: {pyqt6_imports}"

    @pytest.mark.unit
    def test_no_pyi_rth_pyqt6_hook_exists(self):
        assert not (PROJECT_ROOT / "hooks" / "pyi_rth_pyqt6_qt_bin.py").exists()


class TestHiddenImports:
    """Verify all required modules are covered by hiddenimports or hooks."""

    @pytest.mark.unit
    def test_hiddenimports_includes_all_app_modules_requiring_bundling(self):
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
            "PyQt5.sip",
        ]

        missing = sorted(
            m for m in app_modules_requiring_bundling if m not in hidden_imports
        )
        assert not missing, (
            f"The following modules require explicit hiddenimports: {missing}"
        )

    @pytest.mark.unit
    def test_hiddenimports_includes_all_dispatch_converters(self):
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
    def test_hiddenimports_includes_all_backend_modules(self):
        hidden_imports = _extract_hidden_imports()

        backends = [
            "backend.copy_backend",
            "backend.email_backend",
            "backend.ftp_backend",
        ]

        missing = [b for b in backends if b not in hidden_imports]
        assert not missing, f"Missing backend hiddenimports: {missing}"

    @pytest.mark.unit
    def test_hiddenimports_includes_archive_module(self):
        hidden_imports = _extract_hidden_imports()
        assert "archive" in hidden_imports

    @pytest.mark.unit
    def test_all_dispatch_converters_covered(self):
        all_hidden = _get_all_hidden_imports()
        converters_dir = PROJECT_ROOT / "dispatch" / "converters"

        missing = []
        if converters_dir.exists():
            for converter_file in sorted(converters_dir.glob("convert_to_*.py")):
                module_name = f"dispatch.converters.{converter_file.stem}"
                if module_name not in all_hidden:
                    parent_covered = any(
                        module_name.startswith(h + ".")
                        for h in all_hidden
                        if h.startswith("dispatch")
                    )
                    if not parent_covered and module_name not in all_hidden:
                        missing.append(module_name)

        assert not missing, f"Missing converter coverage: {missing}"


class TestHookFiles:
    """Verify hook files are properly configured."""

    @pytest.mark.unit
    def test_hook_files_exist_for_packages(self):
        hook_files = list(HOOKS_DIR.glob("hook-*.py"))
        assert len(hook_files) > 0, "Hook files should exist for packages"

    @pytest.mark.unit
    def test_qt_hooks_use_collect_data_files_or_dynamic_libs(self):
        qt_hooks = ["hook-PyQt5.py", "hook-PyQt5.QtCore.py", "hook-PyQt5.QtGui.py"]
        for hook_name in qt_hooks:
            hook_file = HOOKS_DIR / hook_name
            if hook_file.exists():
                content = hook_file.read_text()
                assert (
                    "collect_data_files" in content or "collect_dynamic_libs" in content
                ), f"{hook_name} should use collect_data_files or collect_dynamic_libs"
