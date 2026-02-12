# Building Windows Executable

This document describes how to build the Windows executable for the Batch File Processor application.

Note: For compatibility with older hosts (for example, Windows Server 2012 R2), prefer building on a Windows VM that matches the target OS or validate any cross-compiled binaries on an actual Windows Server 2012 R2 machine; the repository's batonogov devcontainer and other Linux-based devcontainers are Linux-only and cannot reliably produce native Win2012R2 binaries.

## Prerequisites

- Python 3.11 or higher
- All dependencies from `requirements.txt`
- PyInstaller

## Build Methods

### Method 1: Build on Windows (Recommended)

This is the most straightforward method if you have access to a Windows machine.

#### Steps:

1. **Install Python 3.11+**
   - Download from [python.org](https://www.python.org/downloads/)
   - Make sure to check "Add Python to PATH" during installation

2. **Clone the repository**
   ```cmd
   git clone <repository-url>
   cd batch-file-processor
   ```

3. **Install dependencies**
   ```cmd
   python -m pip install --upgrade pip
   pip install -r requirements.txt
   pip install pyinstaller
   ```

4. **Build the executable**
   ```cmd
   pyinstaller main_interface.spec
   ```

5. **Find the executable**
   - The executable will be in the `dist` folder
   - File name: `Batch File Sender.exe`

### Method 2: Using GitHub Actions (Automated)

The repository includes a GitHub Actions workflow that automatically builds the Windows executable.

#### Trigger the build:

1. **On push to main/develop branch**
   - The workflow runs automatically
   - Download the artifact from the Actions tab

2. **On tag creation**
   - Create a tag: `git tag v1.0.0`
   - Push the tag: `git push origin v1.0.0`
   - The workflow creates a GitHub Release with the executable

3. **Manual trigger**
   - Go to Actions tab in GitHub
   - Select "Build Windows Executable" workflow
   - Click "Run workflow"

#### Download the artifact:

1. Go to the Actions tab in GitHub
2. Click on the latest successful workflow run
3. Download the `batch-file-sender-windows` artifact
4. Extract the ZIP file to get the executable

### Method 3: Using Docker/Podman (Linux/Mac)

This method uses a Docker container with Windows cross-compilation support.

#### Prerequisites:
- Docker or Podman installed
- The `buildwin.sh` script (included in repository)

#### Steps:

1. **Using Podman (original script)**
   ```bash
   bash buildwin.sh
   ```

2. **Using Docker (if Podman not available)**
   ```bash
   docker run --rm --volume "$(pwd):/src/" docker.io/batonogov/pyinstaller-windows:v4.0.1 pyinstaller main_interface.spec
   ```

3. **Find the executable**
   - The executable will be in the `dist` folder
   - File name: `Batch File Sender.exe`

**Note:** This method may not work in all environments (e.g., devcontainers, some CI/CD systems) due to Docker-in-Docker limitations.

### Method 4: Using Wine (Linux)

This method uses Wine to run Windows Python and PyInstaller on Linux.

#### Prerequisites:
- Wine installed
- Windows Python installed via Wine

#### Steps:

1. **Install Wine**
   ```bash
   sudo apt-get update
   sudo apt-get install -y wine wine64
   ```

2. **Install Windows Python via Wine**
   ```bash
   # Download Python installer for Windows
   wget https://www.python.org/ftp/python/3.11.0/python-3.11.0-amd64.exe
   
   # Install Python via Wine
   wine python-3.11.0-amd64.exe /quiet InstallAllUsers=1 PrependPath=1
   ```

3. **Install dependencies via Wine**
   ```bash
   wine python -m pip install --upgrade pip
   wine python -m pip install -r requirements.txt
   wine python -m pip install pyinstaller
   ```

4. **Build the executable**
   ```bash
   wine python -m PyInstaller main_interface.spec
   ```

5. **Find the executable**
   - The executable will be in the `dist` folder
   - File name: `Batch File Sender.exe`

## Build Configuration

The build is configured via the `main_interface.spec` file, which includes:

- **Entry point**: `main_interface.py`
- **Hidden imports**: All dynamically loaded modules (convert backends, send backends, etc.)
- **Hooks**: Custom PyInstaller hooks in the `hooks/` directory
- **Output**: Single executable file named "Batch File Sender.exe"
- **Console**: Enabled (set to `True` in spec file)

### Key Configuration Options

In `main_interface.spec`:

```python
exe = EXE(
    ...
    name='Batch File Sender',  # Output filename
    console=True,              # Show console window
    upx=True,                  # Compress with UPX
    ...
)
```

## Troubleshooting

### Missing DLL errors

If the executable fails to run due to missing DLLs:

1. Install the [Visual C++ Redistributable](https://aka.ms/vs/17/release/vc_redist.x64.exe)
2. Ensure all dependencies are properly included in the spec file

### Import errors

If modules are not found at runtime:

1. Add the module to the `hidden_imports` list in `main_interface.spec`
2. Create a custom hook in the `hooks/` directory if needed
3. Rebuild the executable

### Size optimization

To reduce the executable size:

1. Remove unused dependencies from `requirements.txt`
2. Set `upx=True` in the spec file (already enabled)
3. Use `--exclude-module` for unnecessary modules

### Testing the build

Before distributing:

1. Test on a clean Windows machine without Python installed
2. Verify all features work correctly
3. Check that database connections work
4. Test file operations and conversions

## Distribution

The built executable is standalone and can be distributed as-is. Users do not need Python installed.

### Requirements for end users:

- Windows 10 or later (64-bit)
- Visual C++ Redistributable (usually already installed)
- ODBC drivers if database connectivity is needed

### Recommended distribution method:

1. Create a ZIP file containing:
   - `Batch File Sender.exe`
   - `README.md` (user documentation)
   - Any required configuration files
   - Sample data (if applicable)

2. Or create an installer using tools like:
   - Inno Setup
   - NSIS
   - WiX Toolset

## Continuous Integration

The GitHub Actions workflow (`.github/workflows/build-windows.yml`) automatically:

1. Builds the executable on every push to main/develop
2. Uploads the executable as an artifact
3. Creates a GitHub Release when a version tag is pushed

To create a release:

```bash
git tag -a v1.0.0 -m "Release version 1.0.0"
git push origin v1.0.0
```

## Support

For build issues:

1. Check the GitHub Actions logs for automated builds
2. Verify all dependencies are installed
3. Ensure Python version matches (3.11+)
4. Check the PyInstaller documentation: https://pyinstaller.org/

## Version Information

- Python: 3.11+
- PyInstaller: 6.18.0+
- Target Platform: Windows 10+ (64-bit)
