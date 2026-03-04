#!/usr/bin/env bash
# Local executable build using PyInstaller
# This script builds executables for the current platform using PyInstaller.
# 
# Supports:
#   - Native Linux executables
#   - Native macOS executables  
#   - Windows executables (via Wine on Linux/macOS)
#
# Usage:
#   ./build_local.sh              # Build and run self-test
#   ./build_local.sh --build-only # Build only, skip self-test

set -e

# Colors for output
YELLOW='\033[1;33m'
GREEN='\033[0;32m'
RED='\033[0;31m'
BLUE='\033[0;34m'
NC='\033[0m'

BUILD_ONLY=0
for arg in "$@"; do
    case "$arg" in
        --build-only) BUILD_ONLY=1 ;;
    esac
done

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$PROJECT_ROOT"

echo -e "${YELLOW}=====================================${NC}"
echo -e "${YELLOW}  Building executable locally       ${NC}"
echo -e "${YELLOW}=====================================${NC}"

# Determine Python command
PYTHON_CMD="python"
if ! command -v python &> /dev/null; then
    if ! command -v python3 &> /dev/null; then
        echo -e "${RED}ERROR: Python not found${NC}"
        exit 1
    fi
    PYTHON_CMD="python3"
fi

echo -e "${BLUE}Using Python: $($PYTHON_CMD --version)${NC}"

# Use virtual environment if available
if [[ -f ".venv/bin/python" ]]; then
    echo -e "${BLUE}Using virtual environment: .venv${NC}"
    PYTHON_CMD=".venv/bin/python"
elif [[ -f ".venv/Scripts/python.exe" ]]; then
    # Windows venv
    PYTHON_CMD=".venv/Scripts/python.exe"
fi

# Check/install PyInstaller
echo -e "${BLUE}Checking PyInstaller...${NC}"
if ! $PYTHON_CMD -m pip show pyinstaller &> /dev/null; then
    echo -e "${YELLOW}Installing PyInstaller...${NC}"
    $PYTHON_CMD -m pip install --upgrade pip wheel setuptools
    $PYTHON_CMD -m pip install pyinstaller
fi

# Install project requirements
echo -e "${BLUE}Installing project dependencies...${NC}"
$PYTHON_CMD -m pip install PyQt6==6.10.2 -r requirements.txt

# Build the executable
echo -e "${YELLOW}Building executable with PyInstaller...${NC}"
$PYTHON_CMD -m PyInstaller --clean main_interface_native.spec

if [ $? -ne 0 ]; then
    echo -e "${RED}Build failed!${NC}"
    exit 1
fi

echo -e "${GREEN}Build complete!${NC}"
echo -e "${GREEN}Executable: ./dist/Batch File Sender/${NC}"

if [ "$BUILD_ONLY" -eq 1 ]; then
    echo ""
    echo -e "${BLUE}Build-only mode: skipping self-test${NC}"
    exit 0
fi

# Run self-test
echo ""
echo -e "${YELLOW}=====================================${NC}"
echo -e "${YELLOW}  Running self-test                 ${NC}"
echo -e "${YELLOW}=====================================${NC}"

EXEC_PATH="./dist/Batch File Sender/Batch File Sender"

if [[ ! -f "$EXEC_PATH" ]] && [[ ! -x "$EXEC_PATH" ]]; then
    # On different platforms, might be in different locations or have different names
    if [[ -f "./dist/main_interface" ]]; then
        EXEC_PATH="./dist/main_interface"
    elif [[ -f "./dist/Batch File Sender.exe" ]]; then
        EXEC_PATH="./dist/Batch File Sender.exe"
    fi
fi

if [[ ! -f "$EXEC_PATH" ]] && [[ ! -x "$EXEC_PATH" ]]; then
    echo -e "${RED}ERROR: Executable not found at $EXEC_PATH${NC}"
    echo "Available files in dist/:"
    find ./dist -type f 2>/dev/null | head -10
    exit 1
fi

# Run the executable with self-test
"$EXEC_PATH" --self-test

if [ $? -eq 0 ]; then
    echo -e "${GREEN}Self-test passed!${NC}"
else
    echo -e "${RED}Self-test failed!${NC}"
    exit 1
fi