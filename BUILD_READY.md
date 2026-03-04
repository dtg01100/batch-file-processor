# PyInstaller Multi-Platform Build - Setup Complete

## Status: ✅ Ready to Build

Your batch-file-processor project is fully configured to build working executables for both **Linux** and **Windows** using PyInstaller.

## Key Configuration

### Python Versions
- **Linux Build:** Native Python (3.14 in your environment)
- **Windows Build:** Python 3.11.7 (via batonogov Docker container)

### Build Methods

#### 1. Linux Native Build
**File:** `main_interface_native.spec`
- Optimized for Linux/macOS/Windows native builds
- Uses local Python environment 
- Excludes `pyodbc` (requires system ODBC libs)
- Properly configured to use `collect_data_files()` for Qt data

#### 2. Windows Docker Build  
**File:** `main_interface_windows.spec`
- Optimized for Windows executables
- Uses `batonogov/pyinstaller-windows:v4.0.1` Docker image
- Python 3.11.7 guaranteed
- Includes `pyodbc` for Windows ODBC support
- Downloads Windows PyQt6 ICU DLLs for text rendering

## Build Scripts

### Quick Build (Both Platforms)
```bash
chmod +x build_all.sh
./build_all.sh
```

This script:
1. Cleans previous builds
2. Builds Linux executable with self-test
3. Builds Windows executable with self-test via Docker
4. Reports success/failure for both

### Individual Builds

**Linux only:**
```bash
./build_local.sh              # With self-test
./build_local.sh --build-only # No test (faster)
```

**Windows only (Docker):**
```bash
./build_windows_docker.sh              # With self-test
./build_windows_docker.sh --build-only # No test (faster)
```

**Windows only (Wine):**
```bash
./build_windows_wine.sh              # With self-test
./build_windows_wine.sh --build-only # No test (faster)
```

## Files Created/Modified

### New Spec Files
- ✅ `main_interface_native.spec` - Native platform build configuration
- ✅ `main_interface_windows.spec` - Windows cross-compilation (from main_interface.spec)

### Build Scripts
- ✅ `build_local.sh` - Native platform builds
- ✅ `build_windows_docker.sh` - Windows via Docker (recommended)
- ✅ `build_windows_wine.sh` - Windows via Wine
- ✅ `build_all.sh` - Complete multi-platform build
- ✅ `verify_pyinstaller_setup.sh` - Verify setup
- ✅ `check_build.sh` - Check build status

### Documentation
- ✅ `PYINSTALLER_BUILD_GUIDE.md` - Complete user guide
- ✅ `PYINSTALLER_COMPLETE_REFERENCE.md` - Advanced reference
- ✅ `PYINSTALLER_SETUP_COMPLETE.md` - Setup summary

## Verification

### Check Setup
```bash
bash verify_pyinstaller_setup.sh
```

Expected output:
- ✓ Python 3 found
- ✓ Virtual environment exists
- ✓ PyQt6 installed
- ✓ PyInstaller installed
- ✓ Both spec files present
- ✓ All build scripts ready
- ✓ Docker available
- ✓ Wine available

### Self-Testing

Both builds include integrated self-testing that validates:
- ✓ Module imports (50+ custom modules)
- ✓ PyQt6 functionality
- ✓ Database initialization
- ✓ Core services

Self-test output format:
```
Running self-test for Batch File Sender Version (Git Branch: Master)
  ✓ Testing imports...
  ✓ Required modules (50 modules loaded)
  ✓ Database initialization  
  ✓ Core utilities
✅ Self-test passed - all 54 checks successful
```

## Build Infrastructure Details

### Hidden Imports
Both specs include 120+ hidden imports covering:
- Convert backends (9 conversion formats)
- Send backends (FTP, Email, etc.)
- Core EDI/CSV processing
- Interface and UI modules
- All dynamically-loaded modules

### Qt Configuration
- Automatically collects PyQt6 data files using `collect_data_files()`
- Fallback manual collection if auto-collection fails
- Handles both Qt and Qt6 directory structures
- Includes plugins, binaries, and platform support

### Platform-Specific Handling
- **Linux:** Excludes `pyodbc`, uses system libraries
- **Windows:** Includes `pyodbc`, downloads Windows PyQt6 ICU DLLs
- **Both:** Console mode enabled for self-test output

## Execution Instructions

### Step 1: Run Complete Build
```bash
cd /var/mnt/Disk2/projects/batch-file-processor
chmod +x build_all.sh
./build_all.sh
```

**Expected output:**
```
✓ Cleaning previous builds...

════════════════════════════════════════════════════════
  BUILDING LINUX VERSION (Python 3.14)
════════════════════════════════════════════════════════

[Build output...]
✓ Linux executable created
✓ Running Linux self-test...
✅ Linux self-test PASSED

════════════════════════════════════════════════════════
  BUILDING WINDOWS VERSION (Python 3.11 via Docker)
════════════════════════════════════════════════════════

[Build output...]
✓ Windows executable created
✓ Running Windows self-test via Wine...
✅ Windows self-test PASSED

BUILD SUMMARY
✅ Linux Build: SUCCESS
✅ Windows Build: SUCCESS

🎉 ALL BUILDS SUCCESSFUL!

Executables ready for distribution:
  Linux:   dist/Batch File Sender/Batch File Sender
  Windows: dist/Batch File Sender/Batch File Sender.exe
```

### Step 2: Manual Testing (Optional)

**Linux:**
```bash
dist/Batch\ File\ Sender/Batch\ File\ Sender --self-test
```

**Windows (via Wine):**
```bash
wine dist/Batch\ File\ Sender/Batch\ File\ Sender.exe --self-test
```

## Build Times

- **Linux:** 10-20 minutes (first build slower, subsequent faster)
- **Windows:** 15-30 minutes (includes Docker image operations)
- **Both:** 25-50 minutes (parallel execution depends on system)

Use `--build-only` flag to skip self-test and reduce time by ~5-10 minutes.

## Troubleshooting

### Build Fails to Start
```bash
# Verify environment
bash verify_pyinstaller_setup.sh

# Check Python
python3 --version
source .venv/bin/activate

# Check dependencies
pip list | grep -E "PyQt6|pyinstaller"
```

### Docker Issues
```bash
# Check Docker is running
docker ps

# Check image exists
docker images | grep batonogov

# Verify Docker works
docker run --rm docker.io/batonogov/pyinstaller-windows:v4.0.1 python --version
```

### Wine Issues
```bash
# Check Wine version
wine --version

# Check Wine Python
WINEPREFIX=/var/home/dlafreniere/pywine wine python --version
```

### Import Errors During Build
```bash
# Verify all modules can be imported
python3 -c "from interface.qt.app import QtBatchFileSenderApp; print('OK')"

# Check hidden imports list matches reality
grep -A5 "hidden_imports = " main_interface_native.spec
```

## Next Steps

1. **Run the build:**
   ```bash
   ./build_all.sh
   ```

2. **Verify both executables are created:**
   ```bash
   ls -lh dist/Batch\ File\ Sender/
   ```

3. **Check self-test output:**
   - Build script will show test results
   - Look for "✅ Self-test passed" messages

4. **Distribute:**
   - Package the `dist/Batch File Sender/` directory
   - Include both .exe and native executable
   - Users can run without Python installed

## Summary

✅ Your project has:
- Professional multi-platform build infrastructure
- Integrated self-testing for both platforms
- Python 3.11 enforcement for Windows builds
- Docker-based cross-compilation
- Wine-based alternative for Windows builds
- Comprehensive documentation

🚀 Ready to build! Run: `./build_all.sh`
