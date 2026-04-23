# Main Interface Launch Troubleshooting Guide

## Issue
When launching `main_interface.py`, you may encounter Qt-related errors about missing libraries or platform plugins.

## Common Errors and Solutions

### 1. ImportError: libEGL.so.1: cannot open shared object file

**Error:**
```
ImportError: libEGL.so.1: cannot open shared object file: No such file or directory
```

**Solution:**
Install the required Qt and OpenGL libraries:

```bash
sudo apt-get update
sudo apt-get install -y libegl1 libgl1 libglx0 libxcb-xinerama0 libxcb-cursor0
```

### 2. Could not load the Qt platform plugin "xcb"

**Error:**
```
qt.qpa.plugin: Could not load the Qt platform plugin "xcb" in "" even though it was found.
This application failed to start because no Qt platform plugin could be initialized.
```

**Solution:**
Install additional XCB libraries:

```bash
sudo apt-get install -y libxcb-keysyms1 libxcb-shape0 libxcb-sync1 libxcb-xfixes0 \
    libxcb-icccm4 libxcb-randr0 libxcb-render0 libxcb-xkb1 libxkbcommon-x11-0
```

### 3. No display available

**Error:**
```
qt.qpa.xcb: could not connect to display
```

**Solution:**
The application requires an X11 display. In the dev container, use the virtual display `:99`:

```bash
export DISPLAY=:99
python main_interface.py
```

Or use the helper script:
```bash
./launch_interface.sh
```

### 4. Running in headless/offscreen mode

For testing or when no display is available, run in offscreen mode:

```bash
QT_QPA_PLATFORM=offscreen python main_interface.py
```

Or use the helper script:
```bash
./launch_interface.sh --offscreen
```

### 5. Windows packaged executable: `DLL load failed while importing QtWidgets`

**Error:**
```text
ImportError: DLL load failed while importing QtWidgets: The specified module could not be found.
```

**What this usually means:**
- The workstation is missing the Microsoft Visual C++ runtime / UCRT that Qt5
  depends on.
- The executable was copied without the rest of the extracted bundle.
- Antivirus or deployment tooling removed DLLs from `_internal/PyQt5/Qt5/bin`.

**Checklist:**
1. Extract the full bundle and keep the entire `Batch File Sender` folder
   together. Do not copy only `Batch File Sender.exe`.
2. Confirm the workstation is **64-bit Windows**.
3. Install or repair the latest **Microsoft Visual C++ 2015-2022 Redistributable
   (x64)**:
   https://learn.microsoft.com/en-us/cpp/windows/latest-supported-vc-redist
4. Confirm these paths exist after extraction:
   - `_internal/PyQt5/Qt5/bin`
   - `_internal/PyQt5/Qt5/plugins/platforms/qwindows.dll`
5. If the error persists, check whether security software quarantined files
   under `_internal/PyQt5/Qt5/bin`.

**Build note:**
- Current Windows bundles are built with **PyInstaller 6.19.0**.

## Quick Start

### With GUI (using virtual display):
```bash
# Ensure X11 services are running
./start_x11.sh

# Launch the interface
./launch_interface.sh
```

### Without GUI (offscreen mode):
```bash
./launch_interface.sh --offscreen
```

### Manual launch:
```bash
# With display
DISPLAY=:99 python main_interface.py

# Offscreen
QT_QPA_PLATFORM=offscreen python main_interface.py
```

## Required System Packages

The following packages must be installed for the Qt application to run:

```bash
sudo apt-get install -y \
    libegl1 \
    libgl1 \
    libglx0 \
    libxcb-xinerama0 \
    libxcb-cursor0 \
    libxcb-keysyms1 \
    libxcb-shape0 \
    libxcb-sync1 \
    libxcb-xfixes0 \
    libxcb-icccm4 \
    libxcb-randr0 \
    libxcb-render0 \
    libxcb-xkb1 \
    libxkbcommon-x11-0
```

## Known Warnings (Non-Critical)

You may see these warnings - they are harmless:

1. **nvm configuration warning:**
   ```
   Your user's .npmrc file has a `globalconfig` and/or a `prefix` setting
   ```
   This is unrelated to the Python application.

2. **CSS box-shadow warnings:**
   ```
   Unknown property box-shadow
   ```
   These are Qt CSS warnings that don't affect functionality.

## Verification

To verify the application is running:
```bash
ps aux | grep main_interface.py
```

You should see the Python process running.

## Architecture Notes

- The application uses PyQt5 for the GUI
- In the dev container, Xvfb provides a virtual X11 display on `:99`
- The `start_x11.sh` script manages X11, VNC, and noVNC services for browser-based viewing
- Offscreen mode is useful for automated testing or headless environments
