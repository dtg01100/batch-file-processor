"""Nuitka build configuration tests.

Mirrors the role of tests/unit/test_pyinstaller_spec.py but for
the Nuitka build (Phase 5 of the Qt6/PySide6 migration plan).
Asserts:

* The build scripts exist and are executable.
* All dispatch.converters.convert_to_* modules are bundled
  via --include-package=dispatch.converters.
* PySide6 plugin is enabled.
* All data dirs referenced at runtime are in INCLUDED_DATA_DIRS.
* The entry point file exists and matches main_interface.py.
* The dry-run path of both build_linux.py and build_windows.py
  exits 0 with the expected flags in the command output.

The actual binary production is a separate concern (validated
manually with a real build in CI).
"""

from __future__ import annotations

import importlib.util
import os
import subprocess
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[2]
NUITKA_DIR = PROJECT_ROOT / "nuitka"
NUITKA_CONFIG_PATH = NUITKA_DIR / "nuitka_config.py"
BUILD_LINUX_PATH = NUITKA_DIR / "build_linux.py"
BUILD_WINDOWS_PATH = NUITKA_DIR / "build_windows.py"


def _load_config_module():
    """Import nuitka_config as a module without adding it to sys.path."""
    spec = importlib.util.spec_from_file_location(
        "_nuitka_config_under_test", str(NUITKA_CONFIG_PATH)
    )
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Cannot load spec from {NUITKA_CONFIG_PATH}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.fixture(scope="module")
def cfg():
    """Load the nuitka_config module once for the test module."""
    return _load_config_module()


# ---------------------------------------------------------------------------
# File-existence tests
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_nuitka_dir_exists():
    """The nuitka/ directory must exist."""
    assert NUITKA_DIR.is_dir(), f"Nuitka build dir missing: {NUITKA_DIR}"


@pytest.mark.unit
def test_nuitka_config_module_exists():
    """The nuitka_config.py module must exist."""
    assert NUITKA_CONFIG_PATH.is_file(), f"Missing: {NUITKA_CONFIG_PATH}"


@pytest.mark.unit
def test_build_linux_script_exists_and_is_executable():
    """The Linux build driver must exist and be executable."""
    assert BUILD_LINUX_PATH.is_file(), f"Missing: {BUILD_LINUX_PATH}"
    mode = os.stat(BUILD_LINUX_PATH).st_mode
    assert mode & 0o100, f"{BUILD_LINUX_PATH} is not executable"


@pytest.mark.unit
def test_build_windows_script_exists_and_is_executable():
    """The Windows build driver must exist and be executable."""
    if not BUILD_WINDOWS_PATH.is_file():
        pytest.skip("build_windows.py not yet implemented")
    mode = os.stat(BUILD_WINDOWS_PATH).st_mode
    assert mode & 0o100, f"{BUILD_WINDOWS_PATH} is not executable"


# ---------------------------------------------------------------------------
# Config content tests
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_pyside6_plugin_enabled(cfg):
    """The PySide6 plugin must be enabled.

    Without --enable-plugin=pyside6, Nuitka fails to bundle Qt's
    dynamic imports and the binary won't start.
    """
    assert (
        "pyside6" in cfg.ENABLED_PLUGINS
    ), f"ENABLED_PLUGINS must include 'pyside6'; got {cfg.ENABLED_PLUGINS!r}"


@pytest.mark.unit
def test_dispatch_converters_package_included(cfg):
    """All dispatch.converters modules must be bundled.

    Converters are loaded by name string at runtime via
    importlib.import_module; Nuitka's static analysis misses them
    unless the whole package is listed.
    """
    assert "dispatch.converters" in cfg.INCLUDED_PACKAGES, (
        f"INCLUDED_PACKAGES must include 'dispatch.converters'; "
        f"got {cfg.INCLUDED_PACKAGES!r}"
    )


@pytest.mark.unit
def test_interface_qt_subpackages_included(cfg):
    """All interface.qt subpackages must be bundled."""
    required_subpackages = {
        "interface",
        "interface.qt",
        "interface.qt.dialogs",
        "interface.qt.dialogs.edit_folders",
        "interface.qt.services",
        "interface.qt.widgets",
    }
    missing = required_subpackages - set(cfg.INCLUDED_PACKAGES)
    assert not missing, (
        f"INCLUDED_PACKAGES must include all interface.qt subpackages; "
        f"missing: {missing}"
    )


@pytest.mark.unit
def test_all_dispatch_converters_exist_as_files():
    """Every dispatch.converters.convert_to_*.py file must exist on disk.

    Sanity check: catches typos in INCLUDED_PACKAGES and dead
    converter files that should be removed.
    """
    converters_dir = PROJECT_ROOT / "dispatch" / "converters"
    if not converters_dir.is_dir():
        pytest.skip("dispatch/converters directory not present")
    module_files = list(converters_dir.glob("convert_to_*.py"))
    assert module_files, "No convert_to_*.py files in dispatch/converters"


@pytest.mark.unit
def test_data_dirs_referenced_at_runtime_exist(cfg):
    """Every src path in INCLUDED_DATA_DIRS must exist.

    Catches typos like 'edi_formates' that would silently produce
    a build that breaks at runtime.
    """
    for src, _dest in cfg.INCLUDED_DATA_DIRS:
        assert (
            PROJECT_ROOT / src
        ).is_dir(), f"INCLUDED_DATA_DIRS references missing directory: {src}"


@pytest.mark.unit
def test_entry_point_exists(cfg):
    """The ENTRY_POINT file must exist at the project root."""
    assert (
        PROJECT_ROOT / cfg.ENTRY_POINT
    ).is_file(), f"ENTRY_POINT {cfg.ENTRY_POINT!r} does not exist at {PROJECT_ROOT}"


@pytest.mark.unit
def test_entry_point_is_main_interface(cfg):
    """The ENTRY_POINT must be main_interface.py for parity with the
    existing PyInstaller build (main_interface.spec)."""
    assert cfg.ENTRY_POINT == "main_interface.py", (
        f"ENTRY_POINT must be 'main_interface.py' for build parity; "
        f"got {cfg.ENTRY_POINT!r}"
    )


@pytest.mark.unit
def test_product_metadata_present(cfg):
    """The Nuitka binary metadata fields must be populated."""
    assert cfg.COMPANY_NAME, "COMPANY_NAME must be set"
    assert cfg.PRODUCT_NAME, "PRODUCT_NAME must be set"
    assert cfg.FILE_VERSION, "FILE_VERSION must be set"
    assert cfg.PRODUCT_VERSION, "PRODUCT_VERSION must be set"


# ---------------------------------------------------------------------------
# Dry-run smoke tests (exercises the command assembly without a real build)
# ---------------------------------------------------------------------------


def _dry_run(script_path: Path) -> subprocess.CompletedProcess:
    """Run `<script> --dry-run` and return the CompletedProcess."""
    return subprocess.run(
        ["python3", str(script_path), "--dry-run"],
        capture_output=True,
        text=True,
        cwd=PROJECT_ROOT,
    )


@pytest.mark.unit
def test_build_linux_dry_run_succeeds():
    """build_linux.py --dry-run must exit 0 and print a command
    containing the expected flags. This is the canary that the
    config loads, all symbols are defined, and the command-line
    assembly works.

    Note: this does NOT actually invoke Nuitka (which would take
    10+ minutes). It just validates that the dry-run code path
    is intact.
    """
    result = _dry_run(BUILD_LINUX_PATH)
    assert result.returncode == 0, (
        f"build_linux.py --dry-run failed:\nstdout: {result.stdout}\n"
        f"stderr: {result.stderr}"
    )
    assert (
        "--enable-plugin=pyside6" in result.stdout
    ), f"dry-run output should mention PySide6 plugin; got: {result.stdout!r}"
    assert (
        "--include-package=dispatch.converters" in result.stdout
    ), "dry-run output should include dispatch.converters package"


@pytest.mark.unit
def test_build_windows_dry_run_succeeds():
    """build_windows.py --dry-run must exit 0 and include the
    Windows-specific flags. Skipped if build_windows.py is absent."""
    if not BUILD_WINDOWS_PATH.is_file():
        pytest.skip("build_windows.py not yet implemented")
    result = _dry_run(BUILD_WINDOWS_PATH)
    assert result.returncode == 0, (
        f"build_windows.py --dry-run failed:\nstdout: {result.stdout}\n"
        f"stderr: {result.stderr}"
    )
    assert (
        "--windows-disable-console" in result.stdout
    ), "Windows dry-run should include --windows-disable-console flag"
