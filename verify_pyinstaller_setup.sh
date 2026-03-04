#!/usr/bin/env bash
# Verification script for PyInstaller build setup
# Run this to verify your project is ready for building executables

set -e

YELLOW='\033[1;33m'
GREEN='\033[0;32m'
RED='\033[0;31m'
BLUE='\033[0;34m'
NC='\033[0m'

echo -e "${BLUE}╔════════════════════════════════════════════════════════╗${NC}"
echo -e "${BLUE}║  PyInstaller Build Setup Verification                  ║${NC}"
echo -e "${BLUE}╚════════════════════════════════════════════════════════╝${NC}"
echo ""

ERRORS=0
WARNINGS=0

# Check Python
echo -e "${YELLOW}1. Checking Python Installation...${NC}"
if command -v python3 &> /dev/null; then
    PYVER=$(python3 --version 2>&1 | awk '{print $2}')
    echo -e "${GREEN}   ✓ Python 3 found: $PYVER${NC}"
else
    echo -e "${RED}   ✗ Python 3 not found${NC}"
    ERRORS=$((ERRORS + 1))
fi

# Check virtual environment
echo ""
echo -e "${YELLOW}2. Checking Virtual Environment...${NC}"
if [[ -f ".venv/bin/python" ]]; then
    echo -e "${GREEN}   ✓ Virtual environment exists: .venv/${NC}"
    VENV_PY=.venv/bin/python
elif [[ -f ".venv/Scripts/python.exe" ]]; then
    echo -e "${GREEN}   ✓ Virtual environment exists: .venv/Scripts/${NC}"
    VENV_PY=.venv/Scripts/python.exe
else
    echo -e "${RED}   ✗ Virtual environment not found${NC}"
    ERRORS=$((ERRORS + 1))
    VENV_PY=python3
fi

# Check PyQt6
echo ""
echo -e "${YELLOW}3. Checking PyQt6 Installation...${NC}"
if $VENV_PY -c "import PyQt6; print(PyQt6.__version__)" &> /dev/null; then
    QTVER=$($VENV_PY -c "import PyQt6; print(PyQt6.__version__)")
    echo -e "${GREEN}   ✓ PyQt6 installed: $QTVER${NC}"
else
    echo -e "${RED}   ✗ PyQt6 not found${NC}"
    ERRORS=$((ERRORS + 1))
fi

# Check PyInstaller
echo ""
echo -e "${YELLOW}4. Checking PyInstaller Installation...${NC}"
if $VENV_PY -m pip show pyinstaller &> /dev/null; then
    PIVERSION=$($VENV_PY -m pip show pyinstaller | grep Version | awk '{print $2}')
    echo -e "${GREEN}   ✓ PyInstaller installed: $PIVERSION${NC}"
else
    echo -e "${YELLOW}   ⚠ PyInstaller not installed (will be installed by build scripts)${NC}"
    WARNINGS=$((WARNINGS + 1))
fi

# Check spec files
echo ""
echo -e "${YELLOW}5. Checking Spec Files...${NC}"
if [[ -f "main_interface_native.spec" ]]; then
    echo -e "${GREEN}   ✓ main_interface_native.spec exists${NC}"
else
    echo -e "${RED}   ✗ main_interface_native.spec not found${NC}"
    ERRORS=$((ERRORS + 1))
fi

if [[ -f "main_interface_windows.spec" ]]; then
    echo -e "${GREEN}   ✓ main_interface_windows.spec exists${NC}"
else
    echo -e "${RED}   ✗ main_interface_windows.spec not found${NC}"
    ERRORS=$((ERRORS + 1))
fi

# Check build scripts
echo ""
echo -e "${YELLOW}6. Checking Build Scripts...${NC}"
BUILD_SCRIPTS=("build_local.sh" "build_windows_docker.sh" "build_windows_wine.sh")
for script in "${BUILD_SCRIPTS[@]}"; do
    if [[ -f "$script" ]]; then
        if [[ -x "$script" ]]; then
            echo -e "${GREEN}   ✓ $script exists and is executable${NC}"
        else
            echo -e "${YELLOW}   ⚠ $script exists but isn't executable${NC}"
            echo -e "     Run: chmod +x $script${NC}"
            WARNINGS=$((WARNINGS + 1))
        fi
    else
        echo -e "${RED}   ✗ $script not found${NC}"
        ERRORS=$((ERRORS + 1))
    fi
done

# Check documentation
echo ""
echo -e "${YELLOW}7. Checking Documentation...${NC}"
DOC_FILES=("PYINSTALLER_BUILD_GUIDE.md" "PYINSTALLER_SETUP_COMPLETE.md")
for doc in "${DOC_FILES[@]}"; do
    if [[ -f "$doc" ]]; then
        echo -e "${GREEN}   ✓ $doc exists${NC}"
    else
        echo -e "${YELLOW}   ⚠ $doc not found (optional)${NC}"
        WARNINGS=$((WARNINGS + 1))
    fi
done

# Check requirements
echo ""
echo -e "${YELLOW}8. Checking Requirements File...${NC}"
if [[ -f "requirements.txt" ]]; then
    COUNT=$(wc -l < requirements.txt)
    echo -e "${GREEN}   ✓ requirements.txt exists ($COUNT dependencies)${NC}"
else
    echo -e "${RED}   ✗ requirements.txt not found${NC}"
    ERRORS=$((ERRORS + 1))
fi

# Check imports work
echo ""
echo -e "${YELLOW}9. Testing Application Imports...${NC}"
if $VENV_PY -c "from interface.qt.app import QtBatchFileSenderApp; print('OK')" &> /dev/null; then
    echo -e "${GREEN}   ✓ Application imports work correctly${NC}"
else
    echo -e "${RED}   ✗ Application import failed${NC}"
    ERRORS=$((ERRORS + 1))
fi

# Check for optional tools
echo ""
echo -e "${YELLOW}10. Checking Optional Build Tools...${NC}"

if command -v docker &> /dev/null; then
    DOCKER_VER=$(docker --version | awk '{print $3}' | sed 's/,//')
    echo -e "${GREEN}   ✓ Docker available: $DOCKER_VER${NC}"
else
    echo -e "${YELLOW}   ⚠ Docker not installed (optional, needed for build_windows_docker.sh)${NC}"
    WARNINGS=$((WARNINGS + 1))
fi

if command -v wine &> /dev/null; then
    WINE_VER=$(wine --version)
    echo -e "${GREEN}   ✓ Wine available: $WINE_VER${NC}"
else
    echo -e "${YELLOW}   ⚠ Wine not installed (optional, needed for build_windows_wine.sh)${NC}"
    WARNINGS=$((WARNINGS + 1))
fi

if [[ -f "winpython.sh" ]]; then
    echo -e "${GREEN}   ✓ winpython.sh wrapper available${NC}"
else
    echo -e "${YELLOW}   ⚠ winpython.sh not found (needed if using Wine builds)${NC}"
fi

# Summary
echo ""
echo -e "${BLUE}╔════════════════════════════════════════════════════════╗${NC}"
echo -e "${BLUE}║  Summary                                               ║${NC}"
echo -e "${BLUE}╚════════════════════════════════════════════════════════╝${NC}"

if [[ $ERRORS -eq 0 ]]; then
    echo -e "${GREEN}✓ Setup is ready!${NC}"
    echo ""
    echo "You can now build executables using:"
    echo ""
    echo -e "${BLUE}  Native platform build (recommended for testing):${NC}"
    echo "    ./build_local.sh --build-only"
    echo ""
    echo -e "${BLUE}  Windows build (requires Docker or Wine):${NC}"
    echo "    ./build_windows_docker.sh --build-only"
    echo "    or"
    echo "    ./build_windows_wine.sh --build-only"
    echo ""
    echo "For more information, see PYINSTALLER_BUILD_GUIDE.md"
    exit 0
else
    echo -e "${RED}✗ Setup has $ERRORS error(s) and $WARNINGS warning(s)${NC}"
    echo ""
    echo "Errors must be fixed before building. Warnings are optional."
    echo ""
    echo "Common fixes:"
    echo "  - Install missing dependencies: pip install -r requirements.txt"
    echo "  - Install PyInstaller: pip install pyinstaller"
    echo "  - Make scripts executable: chmod +x *.sh"
    echo "  - For Windows builds, install Docker or Wine"
    exit 1
fi
