#!/usr/bin/env python3
"""Tests and manual checks for the Windows bundle layout."""

import sys
from pathlib import Path

import pytest

from build_wine_local import (
    REQUIRED_WINDOWS_BUNDLE_PATHS,
    WINDOWS_BUNDLE_NAME,
    WINDOWS_DIST_DIRNAME,
    format_bundle_validation_errors,
    get_windows_bundle_dir,
    validate_windows_bundle,
)

PROJECT_ROOT = Path(__file__).resolve().parents[1]


def _create_minimal_windows_bundle(root: Path) -> Path:
    bundle_dir = root / WINDOWS_BUNDLE_NAME
    for relative_path in REQUIRED_WINDOWS_BUNDLE_PATHS:
        target = bundle_dir / relative_path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(b"test")
    return bundle_dir


@pytest.mark.unit
def test_validate_windows_bundle_accepts_expected_layout(tmp_path):
    bundle_dir = _create_minimal_windows_bundle(tmp_path)
    assert validate_windows_bundle(bundle_dir) == []


@pytest.mark.unit
def test_validate_windows_bundle_flags_missing_qtwidgets_runtime(tmp_path):
    bundle_dir = _create_minimal_windows_bundle(tmp_path)
    (bundle_dir / "_internal" / "PyQt5" / "QtWidgets.pyd").unlink()

    issues = validate_windows_bundle(bundle_dir)

    assert any("PyQt5/QtWidgets.pyd" in issue for issue in issues)


@pytest.mark.unit
def test_validate_windows_bundle_flags_linux_shared_objects(tmp_path):
    bundle_dir = _create_minimal_windows_bundle(tmp_path)
    linux_artifact = bundle_dir / "_internal" / "libQt6Widgets.so.6"
    linux_artifact.parent.mkdir(parents=True, exist_ok=True)
    linux_artifact.write_bytes(b"linux")

    issues = validate_windows_bundle(bundle_dir)

    assert any("libQt6Widgets.so.6" in issue for issue in issues)


@pytest.mark.unit
def test_default_windows_bundle_dir_uses_dist_windows():
    assert get_windows_bundle_dir(PROJECT_ROOT / WINDOWS_DIST_DIRNAME) == (
        PROJECT_ROOT / WINDOWS_DIST_DIRNAME / WINDOWS_BUNDLE_NAME
    )


def main(argv: list[str] | None = None) -> int:
    """Run a manual validation of the built Windows bundle."""
    argv = argv or sys.argv[1:]
    bundle_dir = (
        Path(argv[0])
        if argv
        else get_windows_bundle_dir(PROJECT_ROOT / WINDOWS_DIST_DIRNAME)
    )
    issues = validate_windows_bundle(bundle_dir)

    print("=" * 60)
    print("Windows Executable Bundle Validation")
    print("=" * 60)
    print(f"Bundle: {bundle_dir}")

    if issues:
        print("❌ Bundle validation failed")
        print(format_bundle_validation_errors(issues))
        return 1

    print("✅ Bundle validation passed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
