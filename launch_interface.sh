#!/bin/bash
# Launch the Batch File Sender main interface
#
# This script handles the necessary environment setup for running the Qt
# application in the dev container environment.
#
# Usage: ./launch_interface.sh [--offscreen]
#
# Options:
#   --offscreen    Run in offscreen mode (no display required, for testing)

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PYTHON="/usr/local/bin/python"
MAIN_INTERFACE="${SCRIPT_DIR}/main_interface.py"

# Check if --offscreen flag is provided
if [[ "${1:-}" == "--offscreen" ]]; then
    echo "Running in offscreen mode (no GUI)..."
    export QT_QPA_PLATFORM=offscreen
    exec "$PYTHON" "$MAIN_INTERFACE"
else
    # Check if X11 is running on display :99
    if pgrep -x "Xvfb" > /dev/null; then
        echo "X11 virtual display detected on :99"
        export DISPLAY=:99
        echo "Launching Batch File Sender GUI..."
        exec "$PYTHON" "$MAIN_INTERFACE"
    else
        echo "Warning: X11 display not detected."
        echo ""
        echo "To run the GUI, you need to start the X11 services first:"
        echo "  ./start_x11.sh"
        echo ""
        echo "Alternatively, run in offscreen mode (no GUI):"
        echo "  $0 --offscreen"
        echo ""
        echo "Attempting to run anyway..."
        exec "$PYTHON" "$MAIN_INTERFACE"
    fi
fi
