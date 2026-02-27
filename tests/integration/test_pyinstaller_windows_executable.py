"""PyInstaller Windows executable integration tests for Batch File Sender.

These tests build the Windows .exe via the batonogov/pyinstaller-windows
Docker image (which uses Wine + Windows Python inside Ubuntu) and verify
the real artifact works correctly via --self-test and --help under Wine.
"""

import os
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

# Project root is the top-level repo directory
PROJECT_ROOT = Path(__file__).resolve().parents[2]
EXECUTABLE_REL = Path("dist") / "Batch File Sender" / "Batch File Sender.exe"
EXECUTABLE_PATH = PROJECT_ROOT / EXECUTABLE_REL
IMAGE = "docker.io/batonogov/pyinstaller-windows:v4.0.1"


def _detect_docker_command():
    """Determine the working docker command, possibly with sudo.

    Returns the command prefix as a list, e.g. ["docker"] or ["sudo", "docker"].
    Raises pytest.skip if Docker is not available at all.
    """
    if not shutil.which("docker"):
        pytest.skip("docker command not found on PATH")

    # Try without sudo first
    result = subprocess.run(
        ["docker", "info"],
        capture_output=True,
        timeout=30,
    )
    if result.returncode == 0:
        return ["docker"]

    # Try with sudo
    result = subprocess.run(
        ["sudo", "docker", "info"],
        capture_output=True,
        timeout=30,
    )
    if result.returncode == 0:
        return ["sudo", "docker"]

    pytest.skip("Docker daemon is not reachable (tried both docker and sudo docker)")


@pytest.fixture(scope="session")
def docker_cmd():
    """Session-scoped fixture that returns the docker command prefix."""
    return _detect_docker_command()


@pytest.fixture(scope="session")
def windows_executable(docker_cmd):
    """Build the Windows .exe once per session via Docker + PyInstaller.

    Uses the default entrypoint of the pyinstaller-windows image with
    SPECFILE env var, then returns the path to the built .exe.

    Does NOT clean dist/build directories so they can be inspected on failure.
    """
    build_cmd = docker_cmd + [
        "run", "--rm",
        "--volume", f"{PROJECT_ROOT}:/src/",
        "--env", "SPECFILE=./main_interface.spec",
        IMAGE,
    ]

    result = subprocess.run(
        build_cmd,
        capture_output=True,
        text=True,
        cwd=str(PROJECT_ROOT),
        timeout=600,
    )

    assert result.returncode == 0, (
        f"Windows PyInstaller build failed (returncode={result.returncode}).\n"
        f"--- stdout (last 2000 chars) ---\n{result.stdout[-2000:]}\n"
        f"--- stderr (last 2000 chars) ---\n{result.stderr[-2000:]}"
    )

    assert EXECUTABLE_PATH.exists(), (
        f"Build succeeded but .exe not found at {EXECUTABLE_PATH}"
    )

    return EXECUTABLE_PATH


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


@pytest.mark.pyinstaller
@pytest.mark.slow
class TestWindowsExecutable:
    """Tests for the Windows .exe built via Docker."""

    def test_windows_executable_exists(self, windows_executable):
        """The built .exe exists and is larger than 1 MB."""
        exe = Path(windows_executable)
        assert exe.exists(), f"Executable does not exist: {exe}"
        assert exe.is_file(), f"Executable path is not a regular file: {exe}"

        size_mb = exe.stat().st_size / (1024 * 1024)
        assert size_mb > 1, (
            f"Executable is suspiciously small: {size_mb:.2f} MB"
        )

    def test_windows_self_test_via_wine(self, windows_executable, docker_cmd):
        """Running --self-test on the .exe via Wine succeeds."""
        wine_cmd = (
            "wine '/src/dist/Batch File Sender/Batch File Sender.exe' --self-test"
        )

        run_cmd = docker_cmd + [
            "run", "--rm",
            "--volume", f"{PROJECT_ROOT}:/src/",
            IMAGE,
            wine_cmd,
        ]

        result = subprocess.run(
            run_cmd,
            capture_output=True,
            text=True,
            cwd=str(PROJECT_ROOT),
            timeout=120,
        )

        assert result.returncode == 0, (
            f"--self-test via Wine exited with returncode {result.returncode}.\n"
            f"--- stdout ---\n{result.stdout}\n"
            f"--- stderr ---\n{result.stderr}"
        )
        assert "Self-test passed" in result.stdout, (
            f"Expected 'Self-test passed' in stdout.\n"
            f"--- stdout ---\n{result.stdout}"
        )

    def test_windows_help_flag_via_wine(self, windows_executable, docker_cmd):
        """Running --help on the .exe via Wine shows expected flags."""
        wine_cmd = (
            "wine '/src/dist/Batch File Sender/Batch File Sender.exe' --help"
        )

        run_cmd = docker_cmd + [
            "run", "--rm",
            "--volume", f"{PROJECT_ROOT}:/src/",
            IMAGE,
            wine_cmd,
        ]

        result = subprocess.run(
            run_cmd,
            capture_output=True,
            text=True,
            cwd=str(PROJECT_ROOT),
            timeout=120,
        )

        assert result.returncode == 0, (
            f"--help via Wine exited with returncode {result.returncode}.\n"
            f"--- stdout ---\n{result.stdout}\n"
            f"--- stderr ---\n{result.stderr}"
        )
        assert "--self-test" in result.stdout, (
            f"--self-test not found in --help output.\n"
            f"--- stdout ---\n{result.stdout}"
        )
        assert "--automatic" in result.stdout, (
            f"--automatic not found in --help output.\n"
            f"--- stdout ---\n{result.stdout}"
        )
