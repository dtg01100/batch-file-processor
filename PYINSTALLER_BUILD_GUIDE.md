# PyInstaller Build Guide

This project supports building executables for both Linux and Windows using PyInstaller. This guide covers all available build methods.

## Quick Start

### Build for Your Current Platform
```bash
chmod +x build_local.sh
./build_local.sh
```

### Build Windows Executable from Linux/macOS

**Using Docker (Recommended):**
```bash
chmod +x build_windows_docker.sh
./build_windows_docker.sh
```

**Using Wine:**
```bash
chmod +x build_windows_wine.sh
./build_windows_wine.sh
```

## Build Methods

### 1. Local Build (`build_local.sh`)

**Best for:** Development and testing on your current platform

**Supported platforms:** Linux, macOS, Windows

**Requirements:**
- Python 3.7+
- Virtual environment (optional but recommended)

**Usage:**
```bash
./build_local.sh              # Build + run self-test
./build_local.sh --build-only # Build only, skip self-test
```

**Output:**
- Executable: `./dist/Batch File Sender/Batch File Sender` (Linux/macOS) or `Batch File Sender.exe` (Windows)

### 2. Docker Build - Windows (`build_windows_docker.sh`)

**Best for:** Cross-platform Windows builds on Linux/macOS

**Requirements:**
- Docker installed and running
- Internet connection (to pull Docker image on first run)

**Container used:** `docker.io/batonogov/pyinstaller-windows:v4.0.1` (includes PyInstaller, Wine, and all dependencies)

**Usage:**
```bash
./build_windows_docker.sh              # Build + run self-test
./build_windows_docker.sh --build-only # Build only, skip self-test
```

**Output:**
- Executable: `./dist/Batch File Sender/Batch File Sender.exe`

**How it works:**
1. Pulls the batonogov PyInstaller Windows Docker image (cached after first pull)
2. Mounts your project directory into the container
3. Runs PyInstaller to build the Windows executable
4. Optionally runs the self-test using Wine inside the container

### 3. Wine Build - Windows (`build_windows_wine.sh`)

**Best for:** Windows builds on Linux when Docker is not available

**Requirements:**
- Wine installed (`wine` and `wine64`)
- Python installed in Wine (configured in `winpython.sh`)
- `winpython.sh` wrapper script in the project root

**Usage:**
```bash
./build_windows_wine.sh              # Build + run self-test
./build_windows_wine.sh --build-only # Build only, skip self-test
```

**Output:**
- Executable: `./dist/Batch File Sender/Batch File Sender.exe`

**How it works:**
1. Uses the `winpython.sh` wrapper to execute Python in Wine
2. Installs PyInstaller dependencies in Wine
3. Runs PyInstaller in Wine to generate the Windows executable
4. Optionally runs the self-test using the Wine Python environment

## Build Configuration

All builds use `main_interface.spec`, which contains:

- **Hidden imports:** All dynamically loaded modules (convert_to_*, *_backend, interface modules)
- **Qt data:** Platform plugins and binary files for PyQt6
- **Entry point:** `main_interface.py`

The spec file automatically:
- Includes Windows PyQt6 ICU DLLs (when available)
- Collects Qt plugins and libraries
- Adds database migration scripts
- Configures console output for self-test functionality

## Environment Setup

### Using Virtual Environment (Recommended)

```bash
# Create virtual environment
python -m venv .venv

# Activate it
source .venv/bin/activate  # Linux/macOS
# OR
.venv\Scripts\activate     # Windows

# Install dependencies
pip install PyQt6==6.10.2 -r requirements.txt
```

### Using Conda

```bash
conda create -n batch-file-processor python=3.11
conda activate batch-file-processor
pip install PyQt6==6.10.2 -r requirements.txt
```

## Troubleshooting

### "Docker not found" error
- Install Docker: https://docs.docker.com/get-docker/
- Or use `./build_windows_wine.sh` instead

### "Wine not found" error  
- Install Wine:
  - Ubuntu: `sudo apt install wine wine32 wine64`
  - macOS: `brew install wine-stable`
- Or use `./build_windows_docker.sh` instead

### Import errors during build
- Ensure all requirements are installed: `pip install -r requirements.txt`
- Check that hidden imports in `main_interface.spec` match your actual modules

### PyQt6 not found in Docker
- The batonogov Docker image includes PyQt6
- If building a custom Docker image, ensure PyQt6 is installed

### "Executable not found" after build
- Check the build output for errors
- Verify the spec file exists and is valid
- Try building with `--build-only` first to focus on build errors

## Development Workflow

1. **During development:** Use `./build_local.sh` for faster iteration
2. **Before release:** Build all formats:
   ```bash
   ./build_local.sh --build-only      # Linux/macOS native
   ./build_windows_docker.sh           # Windows native
   ```
3. **Verify:** Test each executable before distribution

## Advanced Usage

### Building for a Specific Platform

**On Linux, build for Windows using Docker:**
```bash
./build_windows_docker.sh --build-only
# Then manually test via Wine or on Windows
```

**On Windows, build native executable:**
```bash
./build_local.sh
```

### Custom PyInstaller Options

To pass additional PyInstaller arguments, edit the spec file or use the `--pyinstaller-args` parameter (if implemented in the build script).

### Building with Custom Dependencies

If you add new dependencies:
1. Update `requirements.txt`
2. Run the build scripts - they automatically install all requirements

## CI/CD Integration

For automated builds:

**Linux to Windows (Docker):**
```bash
#!/bin/bash
set -e
./build_windows_docker.sh --build-only
# Upload ./dist/ artifacts
```

**Native Platform Build:**
```bash
#!/bin/bash
set -e
./build_local.sh --build-only
# Upload ./dist/ artifacts
```

## Testing the Build

All build scripts include optional self-testing:

```bash
# With self-test (default)
./build_local.sh
./build_windows_docker.sh
./build_windows_wine.sh

# Without self-test (faster)
./build_local.sh --build-only
./build_windows_docker.sh --build-only
./build_windows_wine.sh --build-only
```

The self-test validates:
- All imports work correctly
- Database initialization
- Core functionality across platforms
