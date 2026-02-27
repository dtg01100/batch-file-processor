# Windows Executable Self-Test Results

## Test Date
$(date)

## Test Environment
- Docker container with Wine on Ubuntu 22.04
- Xvfb for virtual display
- Windows executable built via PyInstaller

## Test Methodology
The self-test performs the following checks:
1. Verifies the executable file exists and has expected size
2. Checks for critical Qt6 DLLs (Qt6Core.dll, Qt6Gui.dll, Qt6Widgets.dll, etc.)
3. Verifies Python extension modules are present (.pyd files)
4. Checks for optional but recommended ICU DLLs

## Test Results

### ✓ Passed
- Executable file present: 8.16 MB
- _internal directory structure correct
- All critical Qt6 DLLs present:
  - Qt6Core.dll
  - Qt6Gui.dll
  - Qt6Widgets.dll
  - Qt6Network.dll
  - Qt6PrintSupport.dll
  - Qt6Svg.dll
  - Qt6Xml.dll
- Python modules present:
  - PyQt6/QtCore.pyd
  - PyQt6/QtGui.pyd
  - PyQt6/QtWidgets.pyd
  - lxml/etree.cp311-win_amd64.pyd
  - PIL/_imaging.cp311-win_amd64.pyd

### ⚠ Warnings
- **ICU DLLs missing:**
  - icuuc.dll (Unicode Common library)
  - icuin.dll (Unicode Internationalization library)
  - icudt.dll (Unicode Data library)

### Impact
The missing ICU DLLs will cause the application to fail on Windows with errors like:
```
ImportError: DLL load failed while importing QtCore: Module not found.
```

## Root Cause
When building Windows executables on Linux using PyInstaller with Wine, the ICU DLLs 
from PyQt6 are not automatically included because they are Windows-specific binaries 
that are not present in the Linux PyQt6 installation (which uses .so files instead).

## Recommendation
To fix this issue, the PyInstaller spec file should be updated to:
1. Download the Windows ICU DLLs from the PyQt6 Windows wheel
2. Include them explicitly in the binaries list
3. Or build the executable on a Windows system where these DLLs are available

## Test Command
```bash
# Build the Docker image
docker build -t batch-file-sender-wine -f Dockerfile.wine .

# Run the self-test
docker run --rm batch-file-sender-wine
```

## Files Created
- `Dockerfile.wine` - Docker configuration for Wine-based testing
- `test_windows_exe.py` - Standalone self-test script
- `.wine-build/dist/Batch File Sender/` - Windows executable and dependencies
