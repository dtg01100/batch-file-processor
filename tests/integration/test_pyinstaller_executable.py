"""PyInstaller executable integration tests for Batch File Sender.

These tests build the actual PyInstaller Linux executable from the spec file
and verify the real artifact works correctly via --self-test and --help.
"""

import os
import subprocess
import sys
from pathlib import Path

import pytest

pytestmark = [
    pytest.mark.integration,
    pytest.mark.pyinstaller,
    pytest.mark.slow,
    pytest.mark.timeout(900),
]

# Project root is the top-level repo directory
PROJECT_ROOT = Path(__file__).resolve().parents[2]
EXECUTABLE_PATH = PROJECT_ROOT / "dist" / "Batch File Sender" / "Batch File Sender"


@pytest.fixture(scope="session")
def built_executable(tmp_path_factory):
    """Build the PyInstaller executable once per session and cache it.

    Skips if PyInstaller is not installed.
    Does NOT clean up dist/build directories so they can be inspected on failure.
    """
    try:
        import PyInstaller  # noqa: F401
    except ImportError:
        pytest.skip("PyInstaller is not installed")

    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "PyInstaller",
            "main_interface.spec",
            "--clean",
            "--noconfirm",
        ],
        capture_output=True,
        text=True,
        cwd=str(PROJECT_ROOT),
    )

    assert result.returncode == 0, (
        f"PyInstaller build failed (returncode={result.returncode}).\n"
        f"--- stdout ---\n{result.stdout}\n"
        f"--- stderr ---\n{result.stderr}"
    )
    assert EXECUTABLE_PATH.exists(), (
        f"Build succeeded but executable not found at {EXECUTABLE_PATH}"
    )

    return EXECUTABLE_PATH


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


def test_executable_exists_and_is_executable(built_executable):
    """The built artifact exists, is a regular file, and has execute permission."""
    exe = Path(built_executable)

    assert exe.exists(), f"Executable does not exist: {exe}"
    assert exe.is_file(), f"Executable path is not a regular file: {exe}"
    assert os.access(exe, os.X_OK), f"Executable lacks execute permission: {exe}"


def test_self_test_passes(built_executable, tmp_path):
    """Running --self-test on the real executable succeeds without UPX corruption."""
    result = subprocess.run(
        [str(built_executable), "--self-test"],
        capture_output=True,
        text=True,
        cwd=str(tmp_path),
        timeout=120,
    )

    assert result.returncode == 0, (
        f"--self-test exited with returncode {result.returncode}.\n"
        f"--- stdout ---\n{result.stdout}\n"
        f"--- stderr ---\n{result.stderr}"
    )
    assert "Self-test passed" in result.stdout, (
        f"Expected 'Self-test passed' in stdout.\n--- stdout ---\n{result.stdout}"
    )
    assert "Failed to extract" not in result.stderr, (
        f"UPX corruption signature found in stderr.\n--- stderr ---\n{result.stderr}"
    )


def test_self_test_output_completeness(built_executable, tmp_path):
    """--self-test output contains all expected section headers and key module checks."""
    result = subprocess.run(
        [str(built_executable), "--self-test"],
        capture_output=True,
        text=True,
        cwd=str(tmp_path),
        timeout=120,
    )

    expected_sections = [
        "Checking module imports",
        "Checking configuration directories",
        "Checking appdirs functionality",
        "Checking file system access",
    ]

    for section in expected_sections:
        assert section in result.stdout, (
            f"Missing expected section header '{section}' in stdout.\n"
            f"--- stdout ---\n{result.stdout}"
        )

    # Verify the modules that are most likely to be missing from the bundle
    # are explicitly confirmed present by the self-test output.
    required_module_checks = [
        "[OK] archive",
        "[OK] archive.edi_tweaks",
        "[OK] dispatch.converters.convert_to_csv",
        "[OK] backend.copy_backend",
        "[OK] backend.ftp_backend",
        "[OK] backend.email_backend",
        "[OK] PyQt5.sip",
    ]

    for check in required_module_checks:
        assert check in result.stdout, (
            f"Expected '{check}' in self-test output — module may be missing from bundle.\n"
            f"--- stdout ---\n{result.stdout}"
        )


def test_help_flag(built_executable, tmp_path):
    """Running --help exits 0 and advertises --self-test and --automatic."""
    result = subprocess.run(
        [str(built_executable), "--help"],
        capture_output=True,
        text=True,
        cwd=str(tmp_path),
        timeout=120,
    )

    assert result.returncode == 0, (
        f"--help exited with returncode {result.returncode}.\n"
        f"--- stdout ---\n{result.stdout}\n"
        f"--- stderr ---\n{result.stderr}"
    )
    assert "--self-test" in result.stdout, (
        f"--self-test not found in --help output.\n--- stdout ---\n{result.stdout}"
    )
    assert "--automatic" in result.stdout, (
        f"--automatic not found in --help output.\n--- stdout ---\n{result.stdout}"
    )


def test_gui_self_test_with_offscreen(built_executable, tmp_path, monkeypatch):
    """Running --gui-test with QT_QPA_PLATFORM=offscreen verifies Qt bundle.

    This tests that the PyInstaller bundle correctly includes all Qt widgets
    and that the application can initialize the full GUI stack without a display.
    """
    import subprocess

    env = os.environ.copy()
    env["QT_QPA_PLATFORM"] = "offscreen"

    result = subprocess.run(
        [str(built_executable), "--gui-test"],
        capture_output=True,
        text=True,
        cwd=str(tmp_path),
        env=env,
        timeout=60,
    )

    assert result.returncode == 0, (
        f"--gui-test exited with returncode {result.returncode}.\n"
        f"--- stdout ---\n{result.stdout}\n"
        f"--- stderr ---\n{result.stderr}"
    )

    # Verify GUI components were created
    gui_checks = [
        "QApplication created",
        "QMainWindow created",
        "Database initialized",
        "FolderManager initialized",
        "Main window built",
        "Window displayed",
        "GUI self-test passed",
    ]

    for check in gui_checks:
        assert check in result.stdout, (
            f"Expected '{check}' in --gui-test output.\n--- stdout ---\n{result.stdout}"
        )
