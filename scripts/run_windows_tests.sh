#!/usr/bin/env bash
# Run Windows tests using Wine in Docker with --privileged.
# Wine prefix init, pip, and deps install run at container start.
#
# Usage:
#   ./scripts/run_windows_tests.sh                    # Default: non-Qt tests
#   ./scripts/run_windows_tests.sh -x -v tests/unit/  # Custom test paths
#
# Environment:
#   SKIP_BUILD=1        Skip Docker build (use existing image)
#   NO_CACHE=1          Disable Docker build cache

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

IMAGE_NAME="batch-file-processor-windows-test"
DOCKERFILE="$PROJECT_ROOT/Dockerfile.windows.test"

echo "========================================"
echo "  Windows Test Runner (Wine in Docker)"
echo "========================================"
echo ""

if [ "${SKIP_BUILD:-}" != "1" ]; then
    BUILD_OPTS=()
    if [ "${NO_CACHE:-}" = "1" ]; then
        BUILD_OPTS+=("--no-cache")
        echo "[Build] Rebuilding image from scratch..."
    else
        echo "[Build] Building image..."
    fi

    docker build "${BUILD_OPTS[@]}" \
        -f "$DOCKERFILE" \
        -t "$IMAGE_NAME" \
        "$PROJECT_ROOT"

    echo ""
    echo "[Build] Done."
    echo ""
fi

# Remaining args are passed to pytest
TEST_ARGS="${*:--m 'not qt' -x -v tests/}"
echo "[Run]  pytest args: $TEST_ARGS"
echo ""

set -x
docker run --rm \
    --name "windows-test-run" \
    --privileged \
    "$IMAGE_NAME" \
    bash -c '
set -euo pipefail

WINEPREFIX=/wineprefix
export WINEPREFIX
export WINEDEBUG=-all
export QT_QPA_PLATFORM=offscreen
export WINEDLLOVERRIDES="mscoree,mshtml="

echo "--- Initializing Wine prefix ---"
xvfb-run wineboot --init 2>/dev/null
xvfb-run wineserver -w 2>/dev/null || true

echo "--- Installing pip ---"
wget -q https://bootstrap.pypa.io/get-pip.py -O /tmp/get-pip.py
xvfb-run wine /opt/pywin/python.exe /tmp/get-pip.py --no-warn-script-location
rm /tmp/get-pip.py

echo "--- Installing dependencies ---"
xvfb-run wine /opt/pywin/python.exe -m pip install --no-warn-script-location \
    -r /src/requirements.txt

echo "--- Installing dev dependencies ---"
xvfb-run wine /opt/pywin/python.exe -m pip install --no-warn-script-location \
    -r /src/requirements-dev.txt

echo "--- Running pytest ---"
xvfb-run wine /opt/pywin/python.exe -m pytest '"$TEST_ARGS"'
'
