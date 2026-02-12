BUILD: Windows Server 2012 R2 VM - Build Instructions

Purpose

These instructions describe how to produce a Windows-native executable compatible with Windows Server 2012 R2. The build must be performed on a Windows VM that matches (or is validated against) the target OS.

Prerequisites

- A Windows Server 2012 R2 VM (Hyper-V, VMware, VirtualBox) with Administrator access and latest updates applied.
- Install a Windows-compatible Python version used by the project (prefer Python 3.7 or 3.8 if higher versions are not supported on 2012 R2). Install for all users and add to PATH.
- Install Microsoft Visual C++ Build Tools (or the full Visual Studio C++ toolchain) so native extensions can be built, and install the appropriate Visual C++ Redistributable on the VM and any target machines.
- Install Git and 7-Zip (optional) for packaging and inspection.

High-level options

- Recommended: Build natively on a Windows Server 2012 R2 VM (ensures API/CRT compatibility).
- Alternative: Cross-compile from Linux using mingw-w64 or use Wine/pyinstaller on a Linux host — cross-compiled binaries MUST be validated on a real Win2012R2 VM.

Steps (native Windows VM)

1. Prepare VM
   - Ensure all Windows Updates are applied and the Visual C++ Redistributable appropriate for your toolchain is installed.

2. Clone repository
   - Open an elevated PowerShell or CMD and run:
     git clone <repo-url> && cd batch-file-processor

3. Create and activate a virtual environment
   - python -m venv venv
   - venv\Scripts\activate

4. Upgrade packaging tools
   - python -m pip install --upgrade pip wheel setuptools

5. Install project dependencies
   - pip install -r requirements.txt

6. Install PyInstaller (recommended for single-file exe)
   - pip install pyinstaller

7. Build the executable
   - Find the project entry point (common entry: main_interface.py). From repo root, run:
     pyinstaller --clean --noconfirm --onefile main_interface.py
   - If the project uses a different entry script, replace with that path.
   - If additional data files or hidden imports are required, add them via PyInstaller spec or --add-data / --hidden-import flags.

8. Retrieve the artifact and test
   - The produced exe will be in the dist\ directory (e.g., dist\main_interface.exe).
   - Test the exe on a clean Windows Server 2012 R2 VM to verify runtime compatibility.

Troubleshooting and notes

- C runtime issues: If the exe fails on the target with missing MSVCR*.dll, install the matching Visual C++ Redistributable on the target; consider compiling with an older toolchain compatible with 2012 R2.
- Native extensions: Ensure any compiled Python extensions are built on/for Win2012R2 or packaged as wheels built for that OS.
- Signing and installers: If required, perform code signing and installer creation on the Windows build host.
- CI: To reproduce builds in CI, use a Windows runner that matches the target OS (host kernel compatibility is required for Windows containers; native VM or runner is recommended).

References

- PyInstaller docs: https://pyinstaller.org/
- Visual C++ Redistributable: https://support.microsoft.com/

Created for task: task-1770933194-8586
