"""Focused tests for PyQt6 packaging in the PyInstaller spec."""

import ast
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[2]
SPEC_FILE = PROJECT_ROOT / "main_interface.spec"


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


@pytest.mark.unit
def test_spec_relies_on_upstream_pyinstaller_runtime_handling():
    """The spec should not register a local PyQt6 runtime hook workaround."""
    runtime_hooks = _get_analysis_keyword("runtime_hooks")

    assert not (PROJECT_ROOT / "hooks" / "pyi_rth_pyqt6_qt_bin.py").exists()
    assert runtime_hooks is None


@pytest.mark.unit
def test_spec_collects_pyqt6_runtime_with_pyinstaller_helpers():
    """The spec should still collect the bundled Qt runtime explicitly."""
    with open(SPEC_FILE, encoding="utf-8") as spec_file:
        spec_source = spec_file.read()

    assert 'collect_data_files("PyQt6", subdir="Qt6")' in spec_source
    assert 'collect_dynamic_libs("PyQt6")' in spec_source
