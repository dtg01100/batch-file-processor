#!/bin/bash
# Complete build and test script for both Linux and Windows versions
# Linux: Uses native Python (3.14)
# Windows: Uses Docker with Python 3.11

set -e

# Get the directory where this script is located
PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$PROJECT_ROOT"

YELLOW='\033[1;33m'
GREEN='\033[0;32m'
RED='\033[0;31m'
BLUE='\033[0;34m'
NC='\033[0m'

echo -e "${BLUE}╔════════════════════════════════════════════════════════╗${NC}"
echo -e "${BLUE}║  Batch File Processor - Multi-Platform Build           ║${NC}"
echo -e "${BLUE}╚════════════════════════════════════════════════════════╝${NC}"
echo ""

# Clean previous builds
echo -e "${YELLOW}Cleaning previous builds...${NC}"
rm -rf build dist *.log

echo ""
echo -e "${YELLOW}════════════════════════════════════════════════════════${NC}"
echo -e "${YELLOW}  BUILDING LINUX VERSION (Python 3.14)${NC}"
echo -e "${YELLOW}════════════════════════════════════════════════════════${NC}"
echo ""

"${PROJECT_ROOT}/.venv/bin/python" -m PyInstaller --clean main_interface_native.spec

if [ -f "dist/Batch File Sender/Batch File Sender" ]; then
    echo -e "${GREEN}✓ Linux executable created${NC}"
    echo "  File: dist/Batch File Sender/Batch File Sender"
    ls -lh "dist/Batch File Sender/Batch File Sender"
    
    echo ""
    echo -e "${YELLOW}Running Linux self-test...${NC}"
    if "dist/Batch File Sender/Batch File Sender" --self-test; then
        echo -e "${GREEN}✅ Linux self-test PASSED${NC}"
        LINUX_PASS=1
    else
        echo -e "${RED}❌ Linux self-test FAILED${NC}"
        LINUX_PASS=0
    fi
else
    echo -e "${RED}✗ Linux executable not created${NC}"
    tail -50 build.log
    exit 1
fi

echo ""
echo -e "${YELLOW}════════════════════════════════════════════════════════${NC}"
echo -e "${YELLOW}  BUILDING WINDOWS VERSION (Python 3.11 via Docker)${NC}"
echo -e "${YELLOW}════════════════════════════════════════════════════════${NC}"
echo ""

# Build Windows using Docker
docker run --rm \
    -v "$(pwd):/src" \
    docker.io/batonogov/pyinstaller-windows:v4.0.1 \
    pyinstaller --clean main_interface_windows.spec

if [ -f "dist/Batch File Sender/Batch File Sender.exe" ]; then
    echo -e "${GREEN}✓ Windows executable created${NC}"
    echo "  File: dist/Batch File Sender/Batch File Sender.exe"
    ls -lh "dist/Batch File Sender/Batch File Sender.exe"
    
    echo ""
    echo -e "${YELLOW}Running Windows self-test via Wine...${NC}"
    if wine "dist/Batch File Sender/Batch File Sender.exe" --self-test 2>&1 | grep -q "Self-test passed"; then
        echo -e "${GREEN}✅ Windows self-test PASSED${NC}"
        WINDOWS_PASS=1
    else
        echo -e "${RED}❌ Windows self-test FAILED${NC}"
        WINDOWS_PASS=0
    fi
else
    echo -e "${RED}✗ Windows executable not created${NC}"
    exit 1
fi

echo ""
echo -e "${BLUE}╔════════════════════════════════════════════════════════╗${NC}"
echo -e "${BLUE}║  BUILD SUMMARY                                         ║${NC}"
echo -e "${BLUE}╚════════════════════════════════════════════════════════╝${NC}"
echo ""

if [ $LINUX_PASS -eq 1 ]; then
    echo -e "${GREEN}✅ Linux Build: SUCCESS${NC}"
else
    echo -e "${RED}❌ Linux Build: FAILED${NC}"
fi

if [ $WINDOWS_PASS -eq 1 ]; then
    echo -e "${GREEN}✅ Windows Build: SUCCESS${NC}"
else
    echo -e "${RED}❌ Windows Build: FAILED${NC}"
fi

echo ""

if [ $LINUX_PASS -eq 1 ] && [ $WINDOWS_PASS -eq 1 ]; then
    echo -e "${GREEN}🎉 ALL BUILDS SUCCESSFUL!${NC}"
    echo ""
    echo "Executables ready for distribution:"
    echo "  Linux:   dist/Batch File Sender/Batch File Sender"
    echo "  Windows: dist/Batch File Sender/Batch File Sender.exe"
    exit 0
else
    echo -e "${RED}⚠️  SOME BUILDS FAILED${NC}"
    exit 1
fi
