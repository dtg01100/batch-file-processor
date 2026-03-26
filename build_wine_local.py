#!/usr/bin/env python3
"""
Windows executable build script using Wine on Linux.
This builds the Windows executable using Python 3.11 for Windows through Wine.
"""

import hashlib
import os
import shutil
import subprocess
import sys
import time
import urllib.request
import zipfile
from pathlib import Path

# Configuration
WINDOWS_BUNDLE_NAME = "Batch File Sender"
WINDOWS_EXECUTABLE_NAME = f"{WINDOWS_BUNDLE_NAME}.exe"
WINDOWS_DIST_DIRNAME = "dist_windows"
WINDOWS_DEPLOYMENT_NOTES_NAME = "WINDOWS-DEPLOYMENT-NOTES.txt"
PYTHON_VERSION = "3.11.9"
PYTHON_URL = f"https://www.python.org/ftp/python/{PYTHON_VERSION}/python-{PYTHON_VERSION}-embed-amd64.zip"
PYINSTALLER_VERSION = "6.19.0"
BUILD_DIR = Path(__file__).parent.absolute() / "build_wine"
DIST_DIR = Path(__file__).parent.absolute() / WINDOWS_DIST_DIRNAME
PYINSTALLER_LOG = BUILD_DIR / "pyinstaller_wine.log"
DEPENDENCY_MARKER = BUILD_DIR / ".deps_installed_py311.txt"
WINDOWS_REQUIREMENTS_SKIP_PACKAGES = (
    "py3dns",
    "pytest",
    "pytest-qt",
    "pytest-timeout",
)
WINE_PREFIX = (
    Path(os.environ.get("BFP_WINEPREFIX", str(BUILD_DIR / "wineprefix")))
    .expanduser()
    .resolve()
)
REQUIRED_WINDOWS_BUNDLE_PATHS = (
    WINDOWS_EXECUTABLE_NAME,
    "_internal/PyQt5/QtCore.pyd",
    "_internal/PyQt5/QtGui.pyd",
    "_internal/PyQt5/QtWidgets.pyd",
    "_internal/PyQt5/Qt5/bin/Qt5Core.dll",
    "_internal/PyQt5/Qt5/bin/Qt5Gui.dll",
    "_internal/PyQt5/Qt5/bin/Qt5Widgets.dll",
    "_internal/PyQt5/Qt5/bin/Qt5Network.dll",
    "_internal/PyQt5/Qt5/bin/Qt5PrintSupport.dll",
    "_internal/PyQt5/Qt5/bin/Qt5Svg.dll",
    "_internal/PyQt5/Qt5/bin/Qt5Xml.dll",
    "_internal/PyQt5/plugins/platforms/qwindows.dll",
    "_internal/python311.dll",
    "_internal/VCRUNTIME140.dll",
)
FORBIDDEN_WINDOWS_BUNDLE_GLOBS = (
    "_internal/*.so",
    "_internal/**/*.so",
    "_internal/*.so.*",
    "_internal/**/*.so.*",
    "_internal/libQt5*.so*",
    "_internal/libpython*.so*",
)
FORBIDDEN_WINDOWS_BUNDLE_NAMES = {
    "python3",
    "python3.11",
    "libpython3.11.so.1.0",
}

WINDOWS_DEPLOYMENT_NOTES = f"""Batch File Sender Windows Deployment Notes
========================================

Bundle contents
---------------
- Keep the entire extracted '{WINDOWS_BUNDLE_NAME}' directory together.
- Do not copy only '{WINDOWS_EXECUTABLE_NAME}' by itself.
- Do not launch the executable from inside a zip file.

Workstation prerequisites
-------------------------
- 64-bit Windows is required.
- Install the latest Microsoft Visual C++ 2015-2022 Redistributable (x64):
  https://learn.microsoft.com/en-us/cpp/windows/latest-supported-vc-redist

Build details
-------------
- Windows bundle built with PyInstaller {PYINSTALLER_VERSION}
- Python {PYTHON_VERSION}
- PyQt5 5.15.10
"""


def ensure_wine_prefix() -> None:
    """Ensure Wine prefix directory exists and show location used for build."""
    WINE_PREFIX.mkdir(parents=True, exist_ok=True)
    print(f"Using WINEPREFIX: {WINE_PREFIX}")


def get_windows_bundle_dir(dist_dir: Path = DIST_DIR) -> Path:
    """Return the expected Windows bundle directory for a dist root."""
    return Path(dist_dir) / WINDOWS_BUNDLE_NAME


def write_windows_deployment_notes(bundle_dir: Path) -> Path:
    """Write Windows deployment guidance into the built bundle."""
    notes_path = Path(bundle_dir) / WINDOWS_DEPLOYMENT_NOTES_NAME
    notes_path.write_text(WINDOWS_DEPLOYMENT_NOTES, encoding="utf-8")
    return notes_path


def validate_windows_bundle(bundle_dir: Path) -> list[str]:
    """Return validation errors for a Windows PyInstaller bundle."""
    bundle_dir = Path(bundle_dir)
    issues = []

    if not bundle_dir.exists():
        return [f"Bundle directory not found: {bundle_dir}"]

    for relative_path in REQUIRED_WINDOWS_BUNDLE_PATHS:
        if not (bundle_dir / relative_path).exists():
            issues.append(f"Missing required Windows bundle file: {relative_path}")

    linux_artifacts = {
        path.relative_to(bundle_dir).as_posix()
        for pattern in FORBIDDEN_WINDOWS_BUNDLE_GLOBS
        for path in bundle_dir.glob(pattern)
    }
    linux_artifacts.update(
        path.relative_to(bundle_dir).as_posix()
        for path in bundle_dir.rglob("*")
        if path.name in FORBIDDEN_WINDOWS_BUNDLE_NAMES
    )

    for artifact in sorted(linux_artifacts):
        issues.append(f"Found Linux-only artifact in Windows bundle: {artifact}")

    return issues


def format_bundle_validation_errors(issues: list[str]) -> str:
    """Format bundle validation errors for console output."""
    return "\n".join(f"  - {issue}" for issue in issues)


def run_wine(cmd, cwd=None, *, check=True, timeout=None):
    """Run a command through Wine."""
    wine_cmd = ["wine"] + cmd
    env = os.environ.copy()
    env["WINEPREFIX"] = str(WINE_PREFIX)
    env["WINEDEBUG"] = "-all"  # Suppress wine debug output

    result = subprocess.run(
        wine_cmd,
        cwd=cwd,
        env=env,
        check=check,
        capture_output=True,
        text=True,
        timeout=timeout,
    )
    return result


def setup_python():
    """Download and set up Python for Windows (embeddable)."""
    print("Setting up Python 3.11 for Windows...")

    python_dir = BUILD_DIR / "python"
    python_zip = BUILD_DIR / "python.zip"

    if python_dir.exists():
        print("Python already downloaded.")
        return python_dir

    BUILD_DIR.mkdir(parents=True, exist_ok=True)

    # Download Python embeddable
    if not python_zip.exists():
        print(f"Downloading Python {PYTHON_VERSION}...")
        urllib.request.urlretrieve(PYTHON_URL, python_zip)

    # Extract Python
    print("Extracting Python...")
    with zipfile.ZipFile(python_zip, "r") as zip_ref:
        zip_ref.extractall(python_dir)

    # Enable site-packages by modifying python311._pth
    pth_file = python_dir / "python311._pth"
    if pth_file.exists():
        content = pth_file.read_text()
        content = content.replace("#import site", "import site")
        pth_file.write_text(content)

    print("Python setup complete.")
    return python_dir


def install_pip(python_dir) -> None:
    """Install pip in the embeddable Python."""
    print("Installing pip...")

    pip_exe = python_dir / "Scripts" / "pip.exe"

    if pip_exe.exists():
        print("Pip already installed.")
        return

    get_pip = BUILD_DIR / "get-pip.py"
    if not get_pip.exists():
        print("Downloading get-pip.py...")
        urllib.request.urlretrieve("https://bootstrap.pypa.io/get-pip.py", get_pip)

    # Run get-pip.py through Wine
    python_exe = python_dir / "python.exe"
    run_wine(
        [str(python_exe), str(get_pip), "--no-warn-script-location"],
        timeout=600,
    )

    print("Pip installed.")


def filter_windows_requirements(requirement_lines):
    """Filter requirements that are intentionally excluded from Wine installs."""
    filtered_lines = []
    for line in requirement_lines:
        normalized_line = line.strip().lower()
        if any(
            normalized_line.startswith(package.lower())
            for package in WINDOWS_REQUIREMENTS_SKIP_PACKAGES
        ):
            continue
        filtered_lines.append(line)
    return filtered_lines


def get_requirements_hash(req_file: Path) -> str:
    """Return a stable hash of the Windows requirements that will be installed."""
    if not req_file.exists():
        return "missing"

    filtered_requirements = "".join(
        filter_windows_requirements(
            req_file.read_text(encoding="utf-8").splitlines(keepends=True)
        )
    )
    return hashlib.sha256(filtered_requirements.encode("utf-8")).hexdigest()


def read_dependency_marker(marker_path: Path) -> dict[str, str]:
    """Parse the dependency cache marker into key/value metadata."""
    if not marker_path.exists():
        return {}

    metadata = {}
    for line in marker_path.read_text(encoding="utf-8").splitlines():
        if "=" not in line:
            continue
        key, value = line.split("=", 1)
        metadata[key.strip()] = value.strip()
    return metadata


def get_dependency_marker_metadata(req_file: Path) -> dict[str, str]:
    """Return the dependency metadata expected for the current build pin set."""
    return {
        "python": PYTHON_VERSION,
        "pyinstaller": PYINSTALLER_VERSION,
        "requirements_sha256": get_requirements_hash(req_file),
    }


def get_dependency_reinstall_reason(
    marker_path: Path, req_file: Path, *, force_reinstall: bool = False
) -> str | None:
    """Return why dependencies must be reinstalled, or None when cache is valid."""
    if force_reinstall:
        return "FORCE_WINE_REINSTALL=1 was set"

    cached_metadata = read_dependency_marker(marker_path)
    if not cached_metadata:
        return "dependency cache metadata is missing"

    expected_metadata = get_dependency_marker_metadata(req_file)
    for key, expected_value in expected_metadata.items():
        actual_value = cached_metadata.get(key)
        if actual_value != expected_value:
            return (
                f"{key} changed from {actual_value or '<missing>'} to {expected_value}"
            )

    return None


def install_dependencies(python_dir) -> None:
    """Install project dependencies."""
    print("Installing dependencies...")

    req_file = Path(__file__).parent.absolute() / "requirements.txt"
    force_reinstall = os.environ.get("FORCE_WINE_REINSTALL", "").strip() == "1"
    reinstall_reason = get_dependency_reinstall_reason(
        DEPENDENCY_MARKER, req_file, force_reinstall=force_reinstall
    )
    if reinstall_reason is None:
        print(
            "Dependencies already installed (cached). "
            "Set FORCE_WINE_REINSTALL=1 to reinstall."
        )
        return
    print(f"Refreshing Wine dependencies because {reinstall_reason}.")

    python_exe = python_dir / "python.exe"

    # Upgrade pip
    run_wine(
        [str(python_exe), "-m", "pip", "install", "--upgrade", "pip"],
        timeout=900,
    )

    # Reinstall PyInstaller so a pin change replaces any stale cached version.
    run_wine(
        [
            str(python_exe),
            "-m",
            "pip",
            "install",
            "--upgrade",
            "--force-reinstall",
            f"pyinstaller=={PYINSTALLER_VERSION}",
        ],
        timeout=900,
    )

    # Install project requirements
    if req_file.exists():
        # Create a modified requirements file excluding problematic packages
        modified_req = BUILD_DIR / "requirements_modified.txt"
        filtered_lines = filter_windows_requirements(
            req_file.read_text(encoding="utf-8").splitlines(keepends=True)
        )
        modified_req.write_text("".join(filtered_lines), encoding="utf-8")

        run_wine(
            [
                str(python_exe),
                "-m",
                "pip",
                "install",
                "--upgrade",
                "-r",
                str(modified_req),
            ],
            timeout=1800,
        )

    DEPENDENCY_MARKER.write_text(
        "".join(
            f"{key}={value}\n"
            for key, value in get_dependency_marker_metadata(req_file).items()
        ),
        encoding="utf-8",
    )

    print("Dependencies installed.")


def build_executable(python_dir) -> bool:
    """Build the Windows executable using PyInstaller."""
    print("Building Windows executable...")

    python_exe = python_dir / "python.exe"
    project_root = Path(__file__).parent.absolute()

    # Ensure no stale wine processes are holding file handles.
    env = os.environ.copy()
    env["WINEPREFIX"] = str(WINE_PREFIX)
    env["WINEDEBUG"] = "-all"
    wineserver = shutil.which("wineserver")
    if wineserver:
        subprocess.run([wineserver, "-k"], env=env, check=False)
        time.sleep(1)
    else:
        print("wineserver not found on PATH; continuing without explicit server reset.")

    DIST_DIR.mkdir(parents=True, exist_ok=True)

    # Build to staging directory first; this avoids wine-side delete/permission
    # issues when PyInstaller tries to clean pre-existing dist folders.
    run_staging_dir = BUILD_DIR / f"dist_windows_staging_{int(time.time())}"
    run_staging_dir.mkdir(parents=True, exist_ok=True)

    # Run PyInstaller
    spec_file = project_root / "main_interface.spec"

    BUILD_DIR.mkdir(parents=True, exist_ok=True)
    with open(PYINSTALLER_LOG, "w", encoding="utf-8", errors="replace") as log_file:
        result = subprocess.run(
            [
                "wine",
                str(python_exe),
                "-m",
                "PyInstaller",
                str(spec_file),
                "--clean",
                "--noconfirm",
                "--distpath",
                str(run_staging_dir),
            ],
            cwd=project_root,
            env=env,
            check=False,
            stdout=log_file,
            stderr=subprocess.STDOUT,
            text=True,
        )

    if result.returncode != 0:
        print("Build failed!")
        print(f"PyInstaller log: {PYINSTALLER_LOG}")
        tail_lines = PYINSTALLER_LOG.read_text(
            encoding="utf-8", errors="replace"
        ).splitlines()[-80:]
        if tail_lines:
            print("Last PyInstaller lines:")
            for line in tail_lines:
                print(line)
        return False

    staged_bundle = get_windows_bundle_dir(run_staging_dir)
    if not staged_bundle.exists():
        print("Build failed: staged output not found.")
        return False

    issues = validate_windows_bundle(staged_bundle)
    if issues:
        print("Build failed validation checks for a Windows bundle:")
        print(format_bundle_validation_errors(issues))
        return False

    final_bundle = get_windows_bundle_dir(DIST_DIR)
    if final_bundle.exists():
        shutil.rmtree(final_bundle, ignore_errors=True)
    shutil.copytree(staged_bundle, final_bundle)
    write_windows_deployment_notes(final_bundle)

    print("Build completed!")
    return True


def verify_build() -> bool:
    """Verify the build output."""
    bundle_dir = get_windows_bundle_dir(DIST_DIR)
    issues = validate_windows_bundle(bundle_dir)

    if issues:
        print("❌ Build completed but bundle validation failed")
        print(format_bundle_validation_errors(issues))
        if DIST_DIR.exists():
            print("\nContents of dist directory:")
            for item in DIST_DIR.rglob("*"):
                print(f"  {item.relative_to(DIST_DIR)}")
        return False

    exe_path = bundle_dir / WINDOWS_EXECUTABLE_NAME

    if exe_path.exists():
        size = exe_path.stat().st_size
        print("=" * 60)
        print("✅ Windows build completed successfully!")
        print("=" * 60)
        print(f"Executable location: {exe_path}")
        print(f"Executable size: {size:,} bytes ({size / 1024 / 1024:.2f} MB)")

        # List all files in the dist directory
        print("\nBuild artifacts:")
        for item in sorted(DIST_DIR.rglob("*")):
            rel_path = item.relative_to(DIST_DIR)
            if item.is_file():
                file_size = item.stat().st_size
                print(f"  {rel_path} ({file_size / 1024:.1f} KB)")

        return True
    else:
        print("❌ Build completed but executable not found")
        if DIST_DIR.exists():
            print("\nContents of dist directory:")
            for item in DIST_DIR.rglob("*"):
                print(f"  {item.relative_to(DIST_DIR)}")
        return False


def main() -> None:
    print("=" * 60)
    print("Building Windows Executable with Wine")
    print("=" * 60)
    print()

    try:
        ensure_wine_prefix()

        # Setup Python
        python_dir = setup_python()

        # Install pip
        install_pip(python_dir)

        # Install dependencies
        install_dependencies(python_dir)

        # Build executable
        if build_executable(python_dir):
            if not verify_build():
                sys.exit(1)
        else:
            print("Build failed!")
            sys.exit(1)

    except subprocess.CalledProcessError as e:
        print(f"❌ Command failed: {e}")
        if e.stdout:
            print("STDOUT:", e.stdout)
        if e.stderr:
            print("STDERR:", e.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        import traceback

        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
