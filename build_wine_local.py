#!/usr/bin/env python3
"""
Windows executable build script using Wine on Linux.
This builds the Windows executable using Python 3.11 for Windows through Wine.
"""

import os
import sys
import subprocess
import shutil
import urllib.request
import zipfile
import time
from pathlib import Path

# Configuration
PYTHON_VERSION = "3.11.9"
PYTHON_URL = f"https://www.python.org/ftp/python/{PYTHON_VERSION}/python-{PYTHON_VERSION}-embed-amd64.zip"
PYINSTALLER_VERSION = "6.11.0"
BUILD_DIR = Path(__file__).parent.absolute() / "build_wine"
DIST_DIR = Path(__file__).parent.absolute() / "dist_windows"
PYINSTALLER_LOG = BUILD_DIR / "pyinstaller_wine.log"
WINE_PREFIX = Path(
    os.environ.get("BFP_WINEPREFIX", str(BUILD_DIR / "wineprefix"))
).expanduser().resolve()


def ensure_wine_prefix() -> None:
    """Ensure Wine prefix directory exists and show location used for build."""
    WINE_PREFIX.mkdir(parents=True, exist_ok=True)
    print(f"Using WINEPREFIX: {WINE_PREFIX}")

def run_wine(cmd, cwd=None, check=True, timeout=None):
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
    with zipfile.ZipFile(python_zip, 'r') as zip_ref:
        zip_ref.extractall(python_dir)

    # Enable site-packages by modifying python311._pth
    pth_file = python_dir / "python311._pth"
    if pth_file.exists():
        content = pth_file.read_text()
        content = content.replace("#import site", "import site")
        pth_file.write_text(content)

    print("Python setup complete.")
    return python_dir

def install_pip(python_dir):
    """Install pip in the embeddable Python."""
    print("Installing pip...")

    pip_exe = python_dir / "Scripts" / "pip.exe"

    if pip_exe.exists():
        print("Pip already installed.")
        return

    get_pip = BUILD_DIR / "get-pip.py"
    if not get_pip.exists():
        print("Downloading get-pip.py...")
        urllib.request.urlretrieve(
            "https://bootstrap.pypa.io/get-pip.py",
            get_pip
        )

    # Run get-pip.py through Wine
    python_exe = python_dir / "python.exe"
    run_wine(
        [str(python_exe), str(get_pip), "--no-warn-script-location"],
        timeout=600,
    )

    print("Pip installed.")

def install_dependencies(python_dir):
    """Install project dependencies."""
    print("Installing dependencies...")

    deps_marker = BUILD_DIR / ".deps_installed_py311.txt"
    force_reinstall = os.environ.get("FORCE_WINE_REINSTALL", "").strip() == "1"
    if deps_marker.exists() and not force_reinstall:
        print("Dependencies already installed (cached). Set FORCE_WINE_REINSTALL=1 to reinstall.")
        return

    python_exe = python_dir / "python.exe"
    pyinstaller_exe = python_dir / "Scripts" / "pyinstaller.exe"

    # Upgrade pip
    run_wine(
        [str(python_exe), "-m", "pip", "install", "--upgrade", "pip"],
        timeout=900,
    )

    # Install pyinstaller
    if pyinstaller_exe.exists():
        print("PyInstaller already installed.")
    else:
        run_wine(
            [str(python_exe), "-m", "pip", "install", f"pyinstaller=={PYINSTALLER_VERSION}"],
            timeout=900,
        )

    # Install project requirements
    req_file = Path(__file__).parent.absolute() / "requirements.txt"
    if req_file.exists():
        # Create a modified requirements file excluding problematic packages
        modified_req = BUILD_DIR / "requirements_modified.txt"
        with open(req_file, 'r', encoding='utf-8') as f:
            lines = f.readlines()

        # Filter out packages that may cause issues on Windows
        skip_packages = ['py3dns', 'pytest', 'pytest-qt', 'pytest-timeout']
        filtered_lines = []
        for line in lines:
            skip = False
            for pkg in skip_packages:
                if line.lower().startswith(pkg.lower()):
                    skip = True
                    break
            if not skip:
                filtered_lines.append(line)

        with open(modified_req, 'w', encoding='utf-8') as f:
            f.writelines(filtered_lines)

        run_wine(
            [str(python_exe), "-m", "pip", "install", "-r", str(modified_req)],
            timeout=1800,
        )

    deps_marker.write_text(f"python={PYTHON_VERSION}\npyinstaller={PYINSTALLER_VERSION}\n")

    print("Dependencies installed.")

def build_executable(python_dir):
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
            ["wine", str(python_exe), "-m", "PyInstaller",
             str(spec_file),
             "--clean",
             "--noconfirm",
             "--distpath", str(run_staging_dir)],
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
        tail_lines = PYINSTALLER_LOG.read_text(encoding="utf-8", errors="replace").splitlines()[-80:]
        if tail_lines:
            print("Last PyInstaller lines:")
            for line in tail_lines:
                print(line)
        return False

    staged_bundle = run_staging_dir / "Batch File Sender"
    if not staged_bundle.exists():
        print("Build failed: staged output not found.")
        return False

    final_bundle = DIST_DIR / "Batch File Sender"
    if final_bundle.exists():
        shutil.rmtree(final_bundle, ignore_errors=True)
    shutil.copytree(staged_bundle, final_bundle)

    print("Build completed!")
    return True

def verify_build():
    """Verify the build output."""
    exe_path = DIST_DIR / "Batch File Sender" / "Batch File Sender.exe"

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

def main():
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
            verify_build()
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