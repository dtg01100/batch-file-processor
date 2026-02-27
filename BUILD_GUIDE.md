# Windows Build Guide

This document explains how to build Windows executables for the Batch File Sender application.

## Quick Start

### Local Build (Linux/macOS/WSL)
```bash
chmod +x build_local.sh
./build_local.sh
```

This builds a native executable for your current platform and runs the comprehensive self-test (67 checks).

### Windows Build via Docker
```bash
# From the host system (not from within devcontainer)
HOST_PATH=/path/to/batch-file-processor ./buildwin.sh
```

## Build Scripts Overview

### 1. `build_local.sh` - Local Platform Build
- **Location**: `/workspaces/batch-file-processor/build_local.sh`
- **Purpose**: Build executable for the current system using local PyInstaller
- **Usage**:
  ```bash
  ./build_local.sh              # Build + run self-test
  ./build_local.sh --build-only # Build only, skip self-test
  ```
- **Output**: `./dist/Batch File Sender/Batch File Sender` (executable)
- **Best for**: Development and testing on Linux, macOS, or WSL

### 2. `buildwin.sh` - Docker Windows Build
- **Location**: `/workspaces/batch-file-processor/buildwin.sh`
- **Purpose**: Build real Windows .exe using Docker (Wine + PyInstaller)
- **Container**: `batonogov/pyinstaller-windows:v4.0.1`
- **Host Docker Socket Required**: Yes, paths must be translated
- **Usage**:
  ```bash
  # From host (outside devcontainer):
  ./buildwin.sh
  
  # From devcontainer, must specify HOST_PATH:
  HOST_PATH=/home/user/batch-file-processor ./buildwin.sh
  ```
- **Output**: `./dist/Batch File Sender/Batch File Sender.exe` (Windows executable)

### 3. `buildwin_test.sh` - Docker Windows Build + Test
- **Location**: `/workspaces/batch-file-processor/buildwin_test.sh`
- **Purpose**: Build Windows executable and run self-test via Wine
- **Usage**:
  ```bash
  # From host (outside devcontainer):
  ./buildwin_test.sh              # Build + test
  ./buildwin_test.sh --build-only # Build only
  
  # From devcontainer, must specify HOST_PATH:
  HOST_PATH=/home/user/batch-file-processor ./buildwin_test.sh
  ```
- **Output**: `./dist/Batch File Sender/Batch File Sender.exe` (Windows executable)

## Path Translation Issue (Devcontainer)

### The Problem
When building from within a VS Code devcontainer:
1. Your workspace is mounted at `/workspaces/batch-file-processor` (container path)
2. Docker daemon runs on the **host**, not in the container
3. The host filesystem doesn't have `/workspaces/` - it has a different path
4. Docker needs the actual **host path** to mount the volume

### The Solution
Set the `HOST_PATH` environment variable to your actual workspace location on the host:

```bash
# Example 1: GitHub Codespaces or typical devcontainer setup
HOST_PATH=/home/user/batch-file-processor ./buildwin.sh

# Example 2: WSL setup
HOST_PATH=/mnt/c/Users/YourName/batch-file-processor ./buildwin.sh

# Example 3: macOS Docker Desktop
HOST_PATH=/Users/YourName/batch-file-processor ./buildwin.sh
```

### How to Find Your Host Path
1. **Codespaces/Remote SSH**: Ask your system administrator or check `.devcontainer.json`
2. **Local WSL**: Check Windows file explorer path (e.g., `C:\Users\...`) and convert to WSL path
3. **Native macOS/Linux**: Path is the same as container path

Check your devcontainer configuration:
```bash
cat /workspaces/batch-file-processor/.devcontainer.json | grep -A1 workspaceMount
```

## Build Configuration

### Spec File: `main_interface.spec`
- **PyInstaller configuration** that specifies:
  - Main entry point: `main_interface.py`
  - Hidden imports: All PyQt6 modules, business logic modules
  - Data files: Qt plugins, resources, hooks
  - Output: Windows/Linux executable with all dependencies bundled

### Hook Files: `hooks/`
Custom PyInstaller hooks for proper bundling:
- `hook-PyQt6.py` - Core Qt dependencies
- `hook-PyQt6.QtCore.py` - Qt Core module
- `hook-PyQt6.QtGui.py` - Qt GUI + platform plugins
- `hook-PyQt6.QtWidgets.py` - Qt Widgets
- `hook-interface.qt.py` - Application Qt modules

## Self-Test Checks (67 Total)

The built executable runs 67 comprehensive checks:

1. **Standard Library Modules** (8 checks)
   - argparse, datetime, multiprocessing, os, platform, sys, time, traceback

2. **Third-Party Modules** (10 checks)
   - PyQt6.*, appdirs, PIL, lxml, pyodbc

3. **Application Modules** (45 checks)
   - All conversion backends (11)
   - Dispatch system (3)
   - Backend systems (3)
   - Core EDI logic (7)
   - Interface modules (8)
   - Utility modules (4+)

4. **Configuration & File System** (4 checks)
   - Config directories
   - appdirs functionality
   - File system access
   - Local module availability

## Troubleshooting

### Error: "Cannot mount /workspaces in Docker"
**Cause**: Running from devcontainer without HOST_PATH
```bash
# Solution: Set HOST_PATH
HOST_PATH=/actual/path/on/host ./buildwin.sh
```

### Error: "Spec file not found"
**Cause**: Volume mount not working properly
```bash
# Solution: Verify:
1. HOST_PATH is set correctly
2. Files exist at that location
3. You have read permission on the directory
```

### Build succeeds but self-test fails
**Cause**: Missing dependencies or modules
```bash
# Solution: Check build output for warnings
# Re-run: ./buildwin_test.sh 2>&1 | tee build.log
# Review warning messages about missing modules
```

### Wine errors when running tested executable
**Cause**: Wine environment configuration
**Solution**: Check Docker container logs
```bash
docker logs <container_id>
```

## Verification Checklist

After building:

- [ ] Executable file exists at expected location
- [ ] File is executable (`chmod +x` if needed)
- [ ] Self-test runs successfully
- [ ] All 67 checks show ✓ (checkmark)
- [ ] No Python errors in output

## Development Workflow

1. **Make code changes** to Python files
2. **Run local build** to test quickly:
   ```bash
   ./build_local.sh
   ```
3. **After code freeze**, build Windows version:
   ```bash
   HOST_PATH=/path/to/source ./buildwin_test.sh
   ```
4. **Test Windows executable** to ensure no platform-specific issues

## CI/CD Integration

For automated builds, add to your CI/CD pipeline:

```yaml
# Example: GitHub Actions
- name: Build Windows Executable
  run: |
    chmod +x buildwin_test.sh
    HOST_PATH=${{ github.workspace }} ./buildwin_test.sh
```

## Files Modified
- `main_interface.spec` - PyInstaller configuration with 60+ hidden imports
- `buildwin.sh` - Docker Windows build script with path translation
- `buildwin_test.sh` - Docker build + test script with path translation
- `build_local.sh` - Local platform build script
- `build_executable.sh` - Smart build dispatcher
- `hooks/` - Custom PyInstaller hooks for Qt bundling

## Related Documentation
- [Qt Bundle Fixes](./QT_BUNDLE_FIXES.md) - Details of Qt dependency bundling
- [PyInstaller Documentation](https://pyinstaller.org/)
- [batonogov/pyinstaller-windows](https://github.com/batonogov/docker-pyinstaller)
