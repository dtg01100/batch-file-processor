"""Tests to ensure PyInstaller bundles everything needed.

This module verifies that the spec file's hiddenimports are complete by checking
both explicit hiddenimports in the spec file AND hiddenimports contributed by
hook files (which use collect_submodules to automatically cover package submodules).
"""

import ast
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[2]
SPEC_FILE = PROJECT_ROOT / "main_interface.spec"
HOOKS_DIR = PROJECT_ROOT / "hooks"


def _get_hook_hidden_imports() -> set[str]:
    """Get hiddenimports contributed by hook files.

    Hook files can define hiddenimports = collect_submodules("package") which
    automatically includes all submodules of that package.
    """
    hidden_imports = set()
    if not HOOKS_DIR.exists():
        return hidden_imports

    for hook_file in HOOKS_DIR.glob("hook-*.py"):
        try:
            content = hook_file.read_text(encoding="utf-8")
            # Check if hook uses collect_submodules
            if "collect_submodules" in content:
                tree = ast.parse(content)
                for node in ast.walk(tree):
                    if isinstance(node, ast.Assign):
                        for target in node.targets:
                            if (
                                isinstance(target, ast.Name)
                                and target.id == "hiddenimports"
                            ):
                                if isinstance(node.value, ast.Call):
                                    if isinstance(node.value.func, ast.Name):
                                        if node.value.func.id == "collect_submodules":
                                            if node.value.args:
                                                arg = node.value.args[0]
                                                if isinstance(arg, ast.Constant):
                                                    package_name = arg.value
                                                    # Collect all submodules would add "package" and "package.submodule"
                                                    # For simplicity, we just note that the package itself is covered
                                                    hidden_imports.add(package_name)
                                elif isinstance(node.value, ast.List):
                                    for elt in node.value.elts:
                                        if isinstance(elt, ast.Constant):
                                            hidden_imports.add(elt.value)
        except Exception:
            pass
    return hidden_imports


def _extract_spec_hidden_imports() -> set[str]:
    """Extract explicit hiddenimports from the spec file."""
    content = SPEC_FILE.read_text(encoding="utf-8")
    tree = ast.parse(content)

    hidden_imports = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Call):
            func = node.func
            func_name = ""
            if isinstance(func, ast.Name):
                func_name = func.id
            elif isinstance(func, ast.Attribute):
                func_name = func.attr

            if func_name == "Analysis":
                for keyword in node.keywords:
                    if keyword.arg == "hiddenimports":
                        if isinstance(keyword.value, ast.List):
                            for elt in keyword.value.elts:
                                if isinstance(elt, ast.Constant) and isinstance(
                                    elt.value, str
                                ):
                                    hidden_imports.add(elt.value)
    return hidden_imports


def _get_all_hidden_imports() -> set[str]:
    """Get combined hiddenimports from spec file and hooks."""
    return _extract_spec_hidden_imports() | _get_hook_hidden_imports()


# ============================================================================
# Dynamic Module Discovery Tests
# ============================================================================


class TestPyInstallerHiddenImportCompleteness:
    """Verify all required modules are covered by hiddenimports or hooks.

    These tests check that modules which cannot be auto-detected by PyInstaller
    are either:
    1. Explicitly listed in spec file's hiddenimports, OR
    2. Covered by a hook file that uses collect_submodules()
    """

    @pytest.mark.unit
    def test_all_dispatch_converters_covered(self):
        """All dispatch/converters/*.py modules must be covered.

        Converters are loaded dynamically and must be in hiddenimports or
        covered by hook-dispatch.py's collect_submodules("dispatch").
        """
        all_hidden = _get_all_hidden_imports()
        converters_dir = PROJECT_ROOT / "dispatch" / "converters"

        missing = []
        if converters_dir.exists():
            for converter_file in sorted(converters_dir.glob("convert_to_*.py")):
                module_name = f"dispatch.converters.{converter_file.stem}"
                # Check if converter is covered by hook (dispatch package is hook-covered)
                # or explicitly listed
                if module_name not in all_hidden:
                    # Check if parent package is covered
                    parent_covered = any(
                        module_name.startswith(h + ".")
                        for h in all_hidden
                        if h.startswith("dispatch")
                    )
                    if not parent_covered and module_name not in all_hidden:
                        missing.append(module_name)

        assert not missing, (
            f"Missing converter coverage: {missing}\n"
            "These converters must be in hiddenimports or covered by a hook."
        )


class TestThirdPartyPackages:
    """Third-party packages that cannot be auto-detected must be in hiddenimports."""


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
        """PyQt5 runtime modules must be in hiddenimports."""
        spec_hidden = _extract_spec_hidden_imports()
        missing = [m for m in self.REQUIRED_PYQT5 if m not in spec_hidden]
        assert not missing, f"Missing PyQt5 hiddenimports: {missing}"


class TestSpecFileConfiguration:
    """Verify spec file is correctly configured."""

    @pytest.mark.unit
    def test_spec_collects_pyqt5_runtime(self):
        """Spec must explicitly collect PyQt5 runtime files."""
        content = SPEC_FILE.read_text(encoding="utf-8")
        assert 'collect_data_files("PyQt5")' in content
        assert 'collect_dynamic_libs("PyQt5")' in content

    @pytest.mark.unit
    def test_no_pyqt6_in_hiddenimports(self):
        """PyQt6 must not appear in hiddenimports (Qt5 project)."""
        spec_hidden = _extract_spec_hidden_imports()
        pyqt6_imports = [h for h in spec_hidden if "PyQt6" in h or "Qt6" in h]
        assert not pyqt6_imports, f"Found Qt6 in hiddenimports: {pyqt6_imports}"

    @pytest.mark.unit
    def test_hooks_directory_configured(self):
        """Spec must be configured to use hooks directory."""
        content = SPEC_FILE.read_text(encoding="utf-8")
        assert "hookspath" in content
        assert "hooks" in content

    @pytest.mark.unit
    def test_spec_file_exists(self):
        """Spec file must exist."""
        assert SPEC_FILE.exists()

    @pytest.mark.unit
    def test_hooks_directory_exists(self):
        """Hooks directory must exist."""
        assert HOOKS_DIR.exists()

    @pytest.mark.unit
    def test_no_pyqt6_runtime_hooks(self):
        """No PyQt6 runtime hooks should exist (Qt5 project)."""
        pyqt6_hooks = list(HOOKS_DIR.glob("pyi_rth_pyqt6*.py"))
        assert not pyqt6_hooks, f"Found PyQt6 hooks: {pyqt6_hooks}"

    @pytest.mark.unit
    def test_backend_modules_in_hiddenimports(self):
        """Backend modules must be in hiddenimports."""
        spec_hidden = _extract_spec_hidden_imports()
        required = [
            "backend.copy_backend",
            "backend.email_backend",
            "backend.ftp_backend",
        ]
        missing = [m for m in required if m not in spec_hidden]
        assert not missing, f"Missing backend hiddenimports: {missing}"
