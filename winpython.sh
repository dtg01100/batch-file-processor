#!/usr/bin/env bash
# Run Wine Python commands using the configured Wine prefix
# Usage: ./winpython.sh <command>
# Examples:
#   ./winpython.sh python --version
#   ./winpython.sh pip install pyinstaller
#   ./winpython.sh python -m PyInstaller main_interface_windows.spec

# Wine prefix relative to project directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
WINEPREFIX="${WINEPREFIX:-$SCRIPT_DIR/.wine}"

# Python executable path in Wine
PYTHON_EXE="C:\\Program Files\\Python311\\python.exe"

# If first argument is 'python', run Python with remaining args
if [[ "$1" == "python" ]]; then
    shift
    WINEPREFIX="$WINEPREFIX" wine "$PYTHON_EXE" "$@"
# If first argument is 'pip', run pip module
elif [[ "$1" == "pip" ]]; then
    shift
    WINEPREFIX="$WINEPREFIX" wine "$PYTHON_EXE" -m pip "$@"
# Otherwise, run the command directly with wine
else
    WINEPREFIX="$WINEPREFIX" wine "$@"
fi