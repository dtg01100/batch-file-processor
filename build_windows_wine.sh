#!/usr/bin/env bash
# Build Windows executable using Wine with Python 3.11
#
# Prerequisites:
#   - Wine installed
#   - Python 3.11 installed in Wine prefix (run with --setup first)
#
# Usage:
#   ./build_windows_wine.sh              # Build and run self-test
#   ./build_windows_wine.sh --build-only # Build only, skip tests
#   ./build_windows_wine.sh --setup      # Install Python 3.11 in Wine prefix
#   ./build_windows_wine.sh --gui-test   # Also run GUI self-test

set -e

# Colors for output
YELLOW='\033[1;33m'
GREEN='\033[0;32m'
RED='\033[0;31m'
BLUE='\033[0;34m'
NC='\033[0m'

BUILD_ONLY=0
SETUP_MODE=0
GUI_TEST=0

for arg in "$@"; do
    case "$arg" in
        --build-only) BUILD_ONLY=1 ;;
        --setup) SETUP_MODE=1 ;;
        --gui-test) GUI_TEST=1 ;;
    esac
done

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$PROJECT_ROOT"

# Wine prefix configuration (relative to project directory)
WINEPREFIX="${WINEPREFIX:-$PROJECT_ROOT/.wine}"
PYTHON_EXE="C:\\Program Files\\Python311\\python.exe"
ICU_URL="https://github.com/unicode-org/icu/releases/download/release-76-1/icu4c-76_1-Win64-MSVC2022.zip"
ICU_ZIP="/tmp/icu.zip"

# Function to run wine commands with correct prefix
run_wine() {
    WINEPREFIX="$WINEPREFIX" wine "$@"
}

# Function to run Python in Wine
run_python() {
    run_wine "$PYTHON_EXE" "$@"
}

# Setup mode: Install Python 3.11 in Wine prefix
if [ $SETUP_MODE -eq 1 ]; then
    echo -e "${YELLOW}=====================================${NC}"
    echo -e "${YELLOW}  Setting up Wine Python 3.11       ${NC}"
    echo -e "${YELLOW}=====================================${NC}"
    
    # Check if Python is already installed
    if run_python --version &>/dev/null; then
        echo -e "${GREEN}Python 3.11 already installed:${NC}"
        run_python --version
        exit 0
    fi
    
    # Download Python 3.11 installer
    PYTHON_INSTALLER="/tmp/python-3.11.9-amd64.exe"
    if [[ ! -f "$PYTHON_INSTALLER" ]]; then
        echo -e "${BLUE}Downloading Python 3.11.9 installer...${NC}"
        wget -q "https://www.python.org/ftp/python/3.11.9/python-3.11.9-amd64.exe" -O "$PYTHON_INSTALLER"
    fi
    
    # Install Python in Wine
    echo -e "${BLUE}Installing Python 3.11.9 in Wine...${NC}"
    run_wine "$PYTHON_INSTALLER" /quiet InstallAllUsers=1 PrependPath=1 Include_test=0
    
    # Verify installation
    if run_python --version; then
        echo -e "${GREEN}Python 3.11 installed successfully!${NC}"
    else
        echo -e "${RED}Failed to install Python 3.11${NC}"
        exit 1
    fi
    
    # Install dependencies
    echo -e "${BLUE}Installing pip and dependencies...${NC}"
    run_python -m pip install --upgrade pip wheel setuptools
    run_python -m pip install PyQt6==6.10.2
    run_python -m pip install -r requirements.txt
    run_python -m pip install pyinstaller
    
    echo -e "${GREEN}Setup complete!${NC}"
    exit 0
fi

echo -e "${YELLOW}=====================================${NC}"
echo -e "${YELLOW}  Building Windows .exe via Wine    ${NC}"
echo -e "${YELLOW}=====================================${NC}"

# Check if Wine is available
if ! command -v wine &> /dev/null; then
    echo -e "${RED}ERROR: Wine not found. Please install Wine to build Windows executables.${NC}"
    exit 1
fi

echo -e "${BLUE}Wine version: $(wine --version)${NC}"
echo -e "${BLUE}Wine prefix: $WINEPREFIX${NC}"

# Check if Python is installed in Wine
if ! run_python --version &>/dev/null; then
    echo -e "${RED}ERROR: Python 3.11 not found in Wine prefix.${NC}"
    echo -e "${YELLOW}Run with --setup to install Python 3.11 first:${NC}"
    echo "  ./build_windows_wine.sh --setup"
    exit 1
fi

echo -e "${BLUE}Python: $(run_python --version 2>&1 | head -1)${NC}"

# Clean previous builds
echo -e "${YELLOW}Cleaning previous builds...${NC}"
rm -rf build/main_interface_windows dist/Batch\ File\ Sender

# Build the executable with PyInstaller
echo -e "${YELLOW}Building Windows executable with PyInstaller...${NC}"
run_python -m PyInstaller main_interface_windows.spec

if [ $? -ne 0 ]; then
    echo -e "${RED}Build failed!${NC}"
    exit 1
fi

# Download and install ICU DLLs (required by Qt6)
echo -e "${YELLOW}Adding ICU DLLs for Qt6...${NC}"
QT_BIN_DIR="./dist/Batch File Sender/_internal/PyQt6/Qt6/bin"

if [[ ! -f "$ICU_ZIP" ]]; then
    echo -e "${BLUE}Downloading ICU DLLs...${NC}"
    wget -q "$ICU_URL" -O "$ICU_ZIP" || {
        echo -e "${RED}Failed to download ICU DLLs${NC}"
        exit 1
    }
fi

# Extract and copy ICU DLLs
rm -rf /tmp/icu_extract
mkdir -p /tmp/icu_extract
unzip -q "$ICU_ZIP" -d /tmp/icu_extract

if [[ -d /tmp/icu_extract/bin64 ]]; then
    cp /tmp/icu_extract/bin64/icu*.dll "$QT_BIN_DIR/"
    # Create unversioned copies (Qt looks for both)
    cp "$QT_BIN_DIR/icudt76.dll" "$QT_BIN_DIR/icudt.dll"
    cp "$QT_BIN_DIR/icuin76.dll" "$QT_BIN_DIR/icui18n.dll"
    cp "$QT_BIN_DIR/icuuc76.dll" "$QT_BIN_DIR/icuuc.dll"
    echo -e "${GREEN}ICU DLLs installed${NC}"
else
    echo -e "${RED}Failed to extract ICU DLLs${NC}"
    exit 1
fi

echo -e "${GREEN}Build complete!${NC}"
echo -e "${GREEN}Executable: ./dist/Batch File Sender/Batch File Sender.exe${NC}"

if [ "$BUILD_ONLY" -eq 1 ]; then
    echo ""
    echo -e "${BLUE}Build-only mode: skipping tests${NC}"
    exit 0
fi

# Run self-test via Wine
echo ""
echo -e "${YELLOW}=====================================${NC}"
echo -e "${YELLOW}  Running self-test via Wine        ${NC}"
echo -e "${YELLOW}=====================================${NC}"

EXEC_PATH="./dist/Batch File Sender/Batch File Sender.exe"

if [[ ! -f "$EXEC_PATH" ]]; then
    echo -e "${RED}ERROR: Executable not found at $EXEC_PATH${NC}"
    exit 1
fi

# Run command-line self-test
echo -e "${BLUE}Running: $EXEC_PATH --self-test${NC}"
DISPLAY="${DISPLAY:-:0}" run_wine "$EXEC_PATH" --self-test

if [ $? -eq 0 ]; then
    echo -e "${GREEN}Self-test passed!${NC}"
else
    echo -e "${RED}Self-test failed!${NC}"
    exit 1
fi

# Optionally run GUI test
if [ "$GUI_TEST" -eq 1 ]; then
    echo ""
    echo -e "${YELLOW}=====================================${NC}"
    echo -e "${YELLOW}  Running GUI self-test via Wine    ${NC}"
    echo -e "${YELLOW}=====================================${NC}"
    
    DISPLAY="${DISPLAY:-:0}" timeout 15s run_wine "$EXEC_PATH" --gui-test
    
    if [ $? -eq 0 ]; then
        echo -e "${GREEN}GUI self-test passed!${NC}"
    else
        echo -e "${RED}GUI self-test failed!${NC}"
        exit 1
    fi
fi

echo ""
echo -e "${GREEN}=====================================${NC}"
echo -e "${GREEN}  BUILD SUCCESSFUL                   ${NC}"
echo -e "${GREEN}=====================================${NC}"
echo ""
echo "Executable: dist/Batch File Sender/Batch File Sender.exe"
echo ""
echo "To test manually with Wine:"
echo "  wine \"dist/Batch File Sender/Batch File Sender.exe\""
echo ""
echo "To distribute, copy the entire 'dist/Batch File Sender' folder."
