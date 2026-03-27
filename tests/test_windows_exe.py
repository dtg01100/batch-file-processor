#!/usr/bin/env python3
"""Tests and manual checks for the Windows single-file executable layout."""

import sys
from pathlib import Path

import pytest

from build_wine_local import (
    WINDOWS_DIST_DIRNAME,
    WINDOWS_EXECUTABLE_NAME,
    WINDOWS_MINIMUM_EXE_SIZE,
    format_bundle_validation_errors,
    get_windows_executable_path,
    validate_windows_bundle,
)

PROJECT_ROOT = Path(__file__).resolve().parents[1]


def _create_minimal_windows_exe(root: Path) -> Path:
    """Create a fake single-file exe that passes minimum size validation."""
    exe_path = root / WINDOWS_EXECUTABLE_NAME
    exe_path.write_bytes(b"MZ" + b"\x00" * WINDOWS_MINIMUM_EXE_SIZE)
    return exe_path


@pytest.mark.unit
def test_validate_windows_exe_accepts_expected_layout(tmp_path):
    exe_path = _create_minimal_windows_exe(tmp_path)
    assert validate_windows_bundle(exe_path) == []


@pytest.mark.unit
def test_validate_windows_exe_flags_missing_file(tmp_path):
    exe_path = tmp_path / WINDOWS_EXECUTABLE_NAME
    issues = validate_windows_bundle(exe_path)
    assert any("not found" in issue for issue in issues)


@pytest.mark.unit
def test_validate_windows_exe_flags_small_file(tmp_path):
    exe_path = tmp_path / WINDOWS_EXECUTABLE_NAME
    exe_path.write_bytes(b"MZ\x00\x00")  # Too small
    issues = validate_windows_bundle(exe_path)
    assert any("suspiciously small" in issue for issue in issues)


@pytest.mark.unit
def test_validate_windows_exe_flags_linux_shared_objects(tmp_path):
    exe_path = _create_minimal_windows_exe(tmp_path)
    linux_artifact = tmp_path / "libQt5Widgets.so.6"
    linux_artifact.write_bytes(b"linux")

    issues = validate_windows_bundle(exe_path)
    assert any("libQt5Widgets.so.6" in issue for issue in issues)


@pytest.mark.unit
def test_default_windows_exe_path_uses_dist_windows():
    assert get_windows_executable_path(PROJECT_ROOT / WINDOWS_DIST_DIRNAME) == (
        PROJECT_ROOT / WINDOWS_DIST_DIRNAME / WINDOWS_EXECUTABLE_NAME
    )


def main(argv: list[str] | None = None) -> int:
    """Run a manual validation of the built Windows executable."""
    argv = argv or sys.argv[1:]
    exe_path = (
        Path(argv[0])
        if argv
        else get_windows_executable_path(PROJECT_ROOT / WINDOWS_DIST_DIRNAME)
    )
    issues = validate_windows_bundle(exe_path)

    print("=" * 60)
    print("Windows Executable Validation")
    print("=" * 60)
    print(f"Executable: {exe_path}")

    if issues:
        print("❌ Validation failed")
        print(format_bundle_validation_errors(issues))
        return 1

    print("✅ Validation passed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
