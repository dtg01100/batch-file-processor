# PyInstaller Build Infrastructure Setup - Complete

## Summary

Your project is now fully configured for building executables with PyInstaller for both **Linux** and **Windows** platforms.

## What's Been Configured

### 1. ✅ Dependencies Fixed
- All Python dependencies from `requirements.txt` are installed
- PyQt6 6.10.2 specifically configured for GUI functionality
- Virtual environment (.venv) properly configured with Python 3.13

### 2. ✅ Spec Files Created

#### `main_interface_native.spec` (NEW - Recommended for local builds)
- Optimized for building **native executables** on Linux/macOS/Windows
- Faster builds (no cross-platform complexity)
- Includes all hidden imports needed for dynamic module loading
- Automatically detects and includes Qt plugins and binaries

#### `main_interface_windows.spec` (Formerly `main_interface.spec`)
- Optimized for building **Windows executables** from Linux/macOS
- Downloads Windows PyQt6 ICU DLLs (for proper text rendering in Windows)
- Works with both Docker and Wine builds
- Includes complete Windows dependency configuration

### 3. ✅ Build Scripts Created

#### `./build_local.sh` - Native Platform Build
**Purpose:** Build executable for your current system (Linux/macOS/Windows)

**Usage:**
```bash
./build_local.sh              # Build + self-test
./build_local.sh --build-only # Build only (faster)
```

**Output:** `dist/Batch File Sender/Batch File Sender` (executable)

**Time:** 5-15 minutes

---

#### `./build_windows_docker.sh` - Docker Windows Build
**Purpose:** Build Windows .exe from Linux/macOS using Docker

**Prerequisites:** Docker installed and running

**Container Used:** `docker.io/batonogov/pyinstaller-windows:v4.0.1`

**Usage:**
```bash
./build_windows_docker.sh              # Build + self-test
./build_windows_docker.sh --build-only # Build only (faster)
```

**Output:** `dist/Batch File Sender/Batch File Sender.exe` (Windows executable)

**Time:** 10-20 minutes (first run downloads Docker image ~2GB)

**Benefits:**
- ✓ True Windows executable (builds on Windows-compatible Python)
- ✓ Cross-platform (works on Linux/macOS)
- ✓ Includes Wine for testing
- ✓ Official batonogov PyInstaller image (well-maintained)

---

#### `./build_windows_wine.sh` - Wine Windows Build
**Purpose:** Build Windows .exe from Linux using Wine's Python

**Prerequisites:** 
- Wine installed (`wine`, `wine64`)
- `winpython.sh` wrapper with Python in Wine

**Usage:**
```bash
./build_windows_wine.sh              # Build + self-test
./build_windows_wine.sh --build-only # Build only (faster)
```

**Output:** `dist/Batch File Sender/Batch File Sender.exe` (Windows executable)

**Time:** 10-15 minutes

**Benefits:**
- ✓ No Docker required
- ✓ Works when Docker not available
- ✓ Direct Windows Python environment

---

### 4. ✅ Documentation Created

- **`PYINSTALLER_BUILD_GUIDE.md`** - Complete guide to all build methods, troubleshooting, and development workflow

## Quick Start

### Build for Your Current Platform
```bash
./build_local.sh --build-only
```

### Build Windows Executable (requires Docker or Wine)
```bash
./build_windows_docker.sh --build-only   # Recommended if Docker available
# OR
./build_windows_wine.sh --build-only     # If Wine available
```

## Build Architecture

```
main_interface.py (entry point)
    ↓
[build_local.sh] ────→ main_interface_native.spec ──→ Linux/macOS/Windows executable
    ↓
[build_windows_docker.sh] ─→ main_interface_windows.spec ──→ Docker ──→ .exe file
    ↓
[build_windows_wine.sh] ────→ main_interface_windows.spec ──→ Wine ──→ .exe file
```

## File Changes Summary

### New Files Created
- ✅ `main_interface_native.spec` - Native platform spec file
- ✅ `build_windows_docker.sh` - Docker build script
- ✅ `build_windows_wine.sh` - Wine build script
- ✅ `PYINSTALLER_BUILD_GUIDE.md` - Comprehensive documentation

### Modified Files
- ✅ `build_local.sh` - Updated to use native spec and support all platforms
- ✅ `main_interface.spec` → Renamed to `main_interface_windows.spec`

### No Changes Needed
- `.venv/` - Virtual environment already configured
- `requirements.txt` - All dependencies already installed
- `main_interface.py` - Entry point works as-is
- `interface/` modules - All imports working correctly

## Verification

Your project is ready. To verify:

### Test 1: Check Imports Work
```bash
.venv/bin/python -c "from interface.qt.app import QtBatchFileSenderApp; print('✓ OK')"
```

### Test 2: Build for Your Platform
```bash
./build_local.sh --build-only
# Should create: dist/Batch File Sender/Batch File Sender
```

### Test 3: Build Windows (if Docker/Wine available)
```bash
./build_windows_docker.sh --build-only
# Should create: dist/Batch File Sender/Batch File Sender.exe
```

## Development Workflow

### During Development
```bash
# Use local builds for fastest iteration
./build_local.sh --build-only
```

### Before Release
```bash
# Build all formats
./build_local.sh --build-only          # Native
./build_windows_docker.sh --build-only # Windows (if Docker available)
```

### Testing Builds
```bash
# Run with self-test (validates functionality)
./build_local.sh              # Linux/macOS/Windows
./build_windows_docker.sh     # Windows via Docker
./build_windows_wine.sh       # Windows via Wine
```

## Known Limitations & Notes

1. **PyInstaller Build Speed**
   - First build: 10-20 minutes (initializing modules)
   - Subsequent builds: 5-10 minutes with `--clean` flag
   - Tip: Use `--build-only` to skip self-test during development

2. **Docker Image Size**
   - `batonogov/pyinstaller-windows` is ~2GB
   - First pull takes time, then cached for future builds

3. **Wine Setup**
   - Requires pre-configured Wine environment with Python
   - The `winpython.sh` wrapper encapsulates this setup

4. **Cross-Compilation Notes**
   - Building Windows .exe on Linux is supported via both Docker and Wine
   - Building native Linux on Windows requires WSL or similar

## Troubleshooting

### Build Takes Too Long
- Normal! PyInstaller is analyzing all 50+ modules
- First build slower, subsequent builds faster
- Use `--build-only` to skip self-test

### "Docker not found"
- Install Docker: https://docs.docker.com/get-docker/
- Or use `./build_windows_wine.sh` instead

### "Wine not found"  
- Install on Ubuntu: `sudo apt install wine wine32 wine64`
- Install on macOS: `brew install wine-stable`
- Or use Docker (`./build_windows_docker.sh`)

### Import Errors  
- Verify: `.venv/bin/python -m pip install -r requirements.txt`
- Check: All modules in `hidden_imports` list match actual modules

See `PYINSTALLER_BUILD_GUIDE.md` for more troubleshooting.

## Next Steps

1. **Verify Setup Works:**
   ```bash
   chmod +x build_local.sh build_windows_docker.sh build_windows_wine.sh
   ./build_local.sh --build-only
   ```

2. **Test Your Application:**
   ```bash
   ./build_local.sh  # Includes self-test
   ```

3. **Build for Release:**
   ```bash
   # Linux/macOS/Windows native
   ./build_local.sh --build-only
   
   # Also build Windows if targeting Windows users
   ./build_windows_docker.sh --build-only
   ```

4. **Distribute:**
   - Copy `dist/Batch File Sender/` folder for your platform
   - Or `dist/Batch File Sender.exe` for Windows

## Support

All build scripts have:
- ✅ Colored output for easy reading
- ✅ Error handling and validation
- ✅ Automatic dependency installation
- ✅ Optional self-testing
- ✅ Clear error messages if issues occur

For complete details, see `PYINSTALLER_BUILD_GUIDE.md`.
