#!/usr/bin/env bash
# Local Windows executable build using PyInstaller
# This script builds the Windows executable using PyInstaller on the current system.
# 
# For actual Windows .exe files, run this on Windows or use ./buildwin.sh on a machine
# with Docker access to batch-file-processor.
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

# Check for Python
if ! command -v python &> /dev/null && ! command -v python3 &> /dev/null; then
    echo -e "${RED}ERROR: Python not found${NC}"
    exit 1
fi

PYTHON_CMD="python"
if ! command -v python &> /dev/null; then
    PYTHON_CMD="python3"
fi

echo -e "${BLUE}Using Python: $($PYTHON_CMD --version)${NC}"

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
$PYTHON_CMD -m PyInstaller --clean main_interface.spec

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
    # On Linux, might be in different location or have different name
    if [[ -f "./dist/main_interface" ]]; then
        EXEC_PATH="./dist/main_interface"
    fi
fi

if [[ ! -f "$EXEC_PATH" ]] && [[ ! -x "$EXEC_PATH" ]]; then
    echo -e "${RED}ERROR: Executable not found at $EXEC_PATH${NC}"
    echo "Available files in dist/:"
    find ./dist -type f | head -10
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
