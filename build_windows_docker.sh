#!/usr/bin/env bash
# Build Windows executable using batonogov/pyinstaller-windows Docker container
# This script builds a .exe file for Windows by using the official PyInstaller
# Docker container maintained by batonogov.
#
# This is the recommended method for building Windows executables on Linux/macOS.
#
# Usage:
#   ./build_windows_docker.sh              # Build and run self-test
#   ./build_windows_docker.sh --build-only # Build only, skip self-test

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
echo -e "${YELLOW}  Building Windows .exe via Docker  ${NC}"
echo -e "${YELLOW}=====================================${NC}"

# Check if Docker is available
if ! command -v docker &> /dev/null; then
    echo -e "${RED}ERROR: Docker not found. Please install Docker to use this build script.${NC}"
    echo ""
    echo "Alternatives:"
    echo "  1. Use ./build_windows_wine.sh (requires Wine)"
    echo "  2. Use ./build_local.sh (for native platform)"
    exit 1
fi

echo -e "${BLUE}Docker version: $(docker --version)${NC}"

# Pull the batonogov PyInstaller Windows container if not present
DOCKER_IMAGE="docker.io/batonogov/pyinstaller-windows:v4.0.1"
echo -e "${BLUE}Checking Docker image: $DOCKER_IMAGE${NC}"
if ! docker image inspect "$DOCKER_IMAGE" &> /dev/null; then
    echo -e "${YELLOW}Pulling $DOCKER_IMAGE...${NC}"
    docker pull "$DOCKER_IMAGE"
fi

# Build the Windows executable
echo -e "${YELLOW}Building Windows executable with PyInstaller...${NC}"
docker run --rm \
    -v "$(pwd):/src" \
    "$DOCKER_IMAGE" \
    "pyinstaller --clean -y --dist dist_windows main_interface_windows.spec"

if [ $? -ne 0 ]; then
    echo -e "${RED}Build failed!${NC}"
    exit 1
fi

# Download and copy ICU DLLs (required by Qt6)
echo -e "${YELLOW}Adding ICU DLLs (required by Qt6)...${NC}"
ICU_URL="https://github.com/unicode-org/icu/releases/download/release-76-1/icu4c-76_1-Win64-MSVC2022.zip"
ICU_ZIP="/tmp/icu.zip"
ICU_EXTRACT_DIR="/tmp/icu_extract"

if [ ! -f "$ICU_ZIP" ]; then
    wget -q "$ICU_URL" -O "$ICU_ZIP" || echo -e "${YELLOW}Warning: Could not download ICU, executable may not run${NC}"
fi

if [ -f "$ICU_ZIP" ]; then
    rm -rf "$ICU_EXTRACT_DIR"
    mkdir -p "$ICU_EXTRACT_DIR"
    unzip -q "$ICU_ZIP" -d "$ICU_EXTRACT_DIR"
    
    # Copy ICU DLLs to the executable directory
    EXEC_DIR="./dist_windows/Batch File Sender"
    if [ -d "$ICU_EXTRACT_DIR/bin64" ]; then
        cp "$ICU_EXTRACT_DIR/bin64/"*.dll "$EXEC_DIR/_internal/PyQt6/Qt6/bin/" 2>/dev/null || true
        echo -e "${GREEN}ICU DLLs copied successfully${NC}"
    fi
fi

echo -e "${GREEN}Build complete!${NC}"
echo -e "${GREEN}Executable: ./dist_windows/Batch File Sender/Batch File Sender.exe${NC}"

if [ "$BUILD_ONLY" -eq 1 ]; then
    echo ""
    echo -e "${BLUE}Build-only mode: skipping self-test${NC}"
    exit 0
fi

# Run self-test via Wine (included in the container)
echo ""
echo -e "${YELLOW}=====================================${NC}"
echo -e "${YELLOW}  Running self-test via Wine        ${NC}"
echo -e "${YELLOW}=====================================${NC}"

EXEC_PATH="./dist_windows/Batch File Sender/Batch File Sender.exe"

if [[ ! -f "$EXEC_PATH" ]]; then
    echo -e "${RED}ERROR: Executable not found at $EXEC_PATH${NC}"
    echo "Available files in dist_windows/:"
    find ./dist_windows -type f 2>/dev/null | head -10
    exit 1
fi

# Run the executable via Wine inside the Docker container
echo -e "${BLUE}Running self-test...${NC}"
docker run --rm \
    -v "$(pwd):/src" \
    "$DOCKER_IMAGE" \
    "wine '/src/dist_windows/Batch File Sender/Batch File Sender.exe' --self-test"

if [ $? -eq 0 ]; then
    echo -e "${GREEN}Self-test passed!${NC}"
else
    echo -e "${RED}Self-test failed!${NC}"
    exit 1
fi
