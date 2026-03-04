# PyInstaller Build Scripts - Complete Reference

## Overview

This project is fully configured to build native executables for your current platform (Linux/macOS/Windows) and to cross-compile Windows executables from Linux/macOS.

## Build Methods

### 1. Native Platform Build (`./build_local.sh`)
**For:** Building executables that run on your current system

```bash
./build_local.sh              # Build + run self-test
./build_local.sh --build-only # Build only (faster)
```

**Outputs:**
- Linux: `dist/Batch File Sender/Batch File Sender`
- macOS: `dist/Batch File Sender/Batch File Sender`
- Windows: `dist/Batch File Sender/Batch File Sender.exe`

**Time:** 10-20 minutes (first build slower)

**Best For:** Development, testing, rapid iteration

---

### 2. Docker Windows Build (`./build_windows_docker.sh`)
**For:** Building Windows executables on Linux/macOS using Docker

```bash
./build_windows_docker.sh              # Build + run self-test
./build_windows_docker.sh --build-only # Build only (faster)
```

**Requirements:**
- Docker installed and running
- Internet connection (to pull ~2GB Docker image on first run)

**Container:** `docker.io/batonogov/pyinstaller-windows:v4.0.1`

**Output:** `dist/Batch File Sender/Batch File Sender.exe`

**Time:** 15-25 minutes (first run downloads image)

**Best For:**
- Cross-platform Windows builds from Linux/macOS
- CI/CD pipelines
- Reliable, reproducible builds

**How It Works:**
1. Pulls the official PyInstaller Windows Docker image (cached after first pull)
2. Mounts your source code into the container
3. Runs PyInstaller inside the container with Windows Python
4. Includes Wine for testing
5. Returns the built .exe to your host directory

---

### 3. Wine Windows Build (`./build_windows_wine.sh`)
**For:** Building Windows executables on Linux using Wine

```bash
./build_windows_wine.sh              # Build + run self-test
./build_windows_wine.sh --build-only # Build only (faster)
```

**Requirements:**
- Wine installed (`wine`, `wine64`)
- Python configured in Wine (via `winpython.sh`)

**Output:** `dist/Batch File Sender/Batch File Sender.exe`

**Time:** 12-20 minutes

**Best For:**
- When Docker is not available
- Direct Windows Python environment
- Smaller footprint than Docker

**How It Works:**
1. Uses the `winpython.sh` wrapper to access Wine's Python
2. Installs PyInstaller dependencies in Wine
3. Runs PyInstaller via Wine to generate .exe
4. Optionally runs tests using Wine

---

## Spec Files

### `main_interface_native.spec`
- **Use:** For building on your current platform (Linux/macOS/Windows)
- **Optimized:** For maximum compatibility on native platform
- **Excludes:** `pyodbc` (requires system ODBC libs on Linux)
- **Output:** Native binary for your OS

### `main_interface_windows.spec`
- **Use:** For Windows cross-compilation from Linux/macOS (Docker or Wine)
- **Optimized:** For Windows-specific features and libraries
- **Includes:** `pyodbc`, Windows PyQt6 ICU DLLs
- **Output:** Windows .exe file

---

## Self-Testing

All build scripts include **optional self-testing**:

```bash
# With self-test (validates all imports and core functionality)
./build_local.sh
./build_windows_docker.sh
./build_windows_wine.sh

# Without self-test (faster for development)
./build_local.sh --build-only
./build_windows_docker.sh --build-only
./build_windows_wine.sh --build-only
```

**Self-Test Runs:**
- Import validation for 50+ project modules
- PyQt6 imports (QtCore, QtWidgets, QtGui, etc.)
- Database initialization
- Core utilities

**Sample Output:**
```
Running self-test for Batch File Sender Version (Git Branch: Master)
  ✓ Testing imports...
  ✓ Required modules (50 modules loaded successfully)
  ✓ Database initialization
  ✓ Core utilities
✅ Self-test passed - all 54 checks successful
```

---

## Quick Start Checklist

### Prerequisites
```bash
# 1. Verify Python is available
python --version
# or
python3 --version

# 2. Verify virtual environment
ls -la .venv/
# Should show: bin/, lib/, pyvenv.cfg

# 3. Verify PyQt6 and dependencies
.venv/bin/python -c "from interface.qt.app import QtBatchFileSenderApp; print('✓')"
```

### Build Your Current Platform
```bash
# Method 1: Quick build (no testing)
./build_local.sh --build-only
# Output: dist/Batch File Sender/Batch File Sender

# Method 2: Full build with testing
./build_local.sh
# Includes self-test validation
```

### Build Windows (If Targeting Windows)
```bash
# Option A: Using Docker (recommended)
./build_windows_docker.sh --build-only
# Output: dist/Batch File Sender/Batch File Sender.exe

# Option B: Using Wine
./build_windows_wine.sh --build-only
# Output: dist/Batch File Sender/Batch File Sender.exe
```

---

## Directory Structure

```
batch-file-processor/
├── main_interface.py              # Entry point
├── main_interface_native.spec     # Spec for native builds
├── main_interface_windows.spec    # Spec for Windows builds
│
├── build_local.sh                 # Native platform build script
├── build_windows_docker.sh        # Docker Windows build script
├── build_windows_wine.sh          # Wine Windows build script
├── verify_pyinstaller_setup.sh    # Setup verification script
│
├── interface/                     # Qt GUI application
│   ├── qt/
│   │   ├── app.py               # Main app class with self-test
│   │   └── dialogs/
│   ├── database/
│   ├── operations/
│   ├── validation/
│   └── ...
│
├── core/                          # EDI/CSV processing
├── backend/                       # FTP, Email, etc.
├── dispatch/                      # File handling and orchestration
│
├── requirements.txt               # Python dependencies
├── .venv/                         # Virtual environment
│
└── dist/                          # Build output
    └── Batch File Sender/
        ├── Batch File Sender      # Linux/macOS executable
        ├── Batch File Sender.exe  # Windows executable
        └── _internal/             # Dependencies (auto-generated)
```

---

## Verification

### Verify Setup Is Complete
```bash
chmod +x verify_pyinstaller_setup.sh
./verify_pyinstaller_setup.sh

# Output shows:
# ✓ Python 3 found
# ✓ Virtual environment exists
# ✓ PyQt6 installed
# ✓ PyInstaller installed
# ✓ Spec files present
# ✓ Build scripts ready
# ✓ Docker available
# ✓ Wine available
```

### Test the Executable
```bash
# After building with native script:
./build_local.sh  # Includes self-test

# Or manual test:
dist/Batch\ File\ Sender/Batch\ File\ Sender --self-test

# For Windows executable via Wine:
wine dist/Batch\ File\ Sender/Batch\ File\ Sender.exe --self-test
```

---

## Advanced Usage

### Cross-Platform Complete Build
```bash
#!/bin/bash
# Build for all platforms

# Native build
echo "Building for current platform..."
./build_local.sh --build-only

# Windows build (if Docker available)
if command -v docker &> /dev/null; then
    echo "Building for Windows..."
    ./build_windows_docker.sh --build-only
fi

# You now have both:
# - Linux: dist/Batch File Sender/Batch File Sender
# - Windows: dist/Batch File Sender/Batch File Sender.exe
```

### CI/CD Integration
```yaml
# Example GitHub Actions workflow
- name: Build Linux
  run: ./build_local.sh --build-only

- name: Build Windows
  run: ./build_windows_docker.sh --build-only

- name: Upload artifacts
  uses: actions/upload-artifact@v2
  with:
    name: builds
    path: dist/
```

### Customizing Builds

**To add new modules:**
1. Add to `requirements.txt`
2. Add to `hidden_imports` list in spec file
3. Rebuild: `./build_local.sh --build-only`

**To add file resources:**
1. Add to `datas` list in spec file
2. Format: `('source_path', 'dest_path_in_bundle')`
3. Rebuild

---

## Troubleshooting

### Build Takes Too Long
**Normal!** First build analyzes 50+ modules - takes 10-20 minutes
- Subsequent builds are faster (uses cache)
- Use `--build-only` to skip self-test

### "Docker not found"
```bash
# Solution 1: Install Docker
https://docs.docker.com/get-docker/

# Solution 2: Use Wine instead
./build_windows_wine.sh
```

### "Wine not found"
```bash
# Ubuntu/Debian
sudo apt install wine wine32 wine64

# macOS
brew install wine-stable

# Or use Docker
./build_windows_docker.sh
```

### Build Fails with Import Errors
```bash
# Verify dependencies
.venv/bin/python -m pip install -r requirements.txt

# Check hidden imports match actual modules
grep -l "your_module" main_interface_*.spec

# Add missing modules to hidden_imports in spec file
```

### "libodbc.so.2: cannot open shared object file"
- Already fixed in `main_interface_native.spec` (excludes pyodbc on Linux)
- pyodbc is included in `main_interface_windows.spec` for Windows

### Self-Test Fails
```bash
# Run without packaging first
.venv/bin/python main_interface.py --self-test

# Debug specific module
.venv/bin/python -c "import interface.qt.app; print('OK')"
```

---

## Performance Tips

### Optimize Build Time
1. **Use `--build-only` during development:**
   ```bash
   ./build_local.sh --build-only  # ~5 minutes
   # vs
   ./build_local.sh                # ~15 minutes (includes test)
   ```

2. **Cache Docker images:**
   - First build: pulls 2GB Docker image (~5 min)
   - Subsequent builds: uses cached image (~1 min saved)

3. **Parallel builds:**
   ```bash
   # Build multiple formats simultaneously
   ./build_local.sh --build-only &
   ./build_windows_docker.sh --build-only &
   wait
   ```

### Optimize Distribution Size
- The bundled executable is ~8-15MB (includes PyQt6, all modules)
- Compress for distribution:
  ```bash
  cd dist
  zip -r Batch\ File\ Sender.zip Batch\ File\ Sender/
  ```

---

## Files Reference

| File | Purpose |
|------|---------|
| `main_interface.py` | Application entry point |
| `main_interface_native.spec` | PyInstaller spec for native builds |
| `main_interface_windows.spec` | PyInstaller spec for Windows builds |
| `build_local.sh` | Build script for native platform |
| `build_windows_docker.sh` | Build script using Docker |
| `build_windows_wine.sh` | Build script using Wine |
| `verify_pyinstaller_setup.sh` | Verification script |
| `requirements.txt` | Python dependencies |
| `.venv/` | Python virtual environment |

---

## Support Resources

- **PyInstaller Docs:** https://pyinstaller.readthedocs.io/
- **PyQt6 Docs:** https://www.riverbankcomputing.com/static/Docs/PyQt6/
- **batonogov Docker Image:** https://hub.docker.com/r/batonogov/pyinstaller-windows
- **Wine Docs:** https://wiki.winehq.org/

---

## Summary

✅ **Your project is fully configured to:**
- Build native executables for any platform (Linux/macOS/Windows)
- Cross-compile Windows executables from Linux/macOS (via Docker or Wine)
- Validate builds with integrated self-testing
- Distribute ready-to-run executables without Python installation
- Integrate with CI/CD pipelines

🚀 **Ready to build!**
```bash
./build_local.sh
# or
./build_windows_docker.sh
```
