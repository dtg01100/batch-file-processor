#!/bin/bash
# Test runner script for batch-file-processor
# Allows running tests in parts to avoid timeouts

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Default timeout (seconds)
TIMEOUT=300

# Parse arguments
COMMAND="$1"
shift || true

print_usage() {
    echo -e "${BLUE}Usage: $0 <command> [options]${NC}"
    echo ""
    echo "Commands:"
    echo "  unit              Run unit tests only (fast, no external deps)"
    echo "  integration       Run integration tests only"
    echo "  qt                Run Qt/UI tests only"
    echo "  e2e               Run end-to-end tests only"
    echo "  fast              Run fast tests only (< 5 seconds each)"
    echo "  slow              Run slow tests only"
    echo "  database          Run database-related tests"
    echo "  backend           Run backend tests (FTP, Email, Copy)"
    echo "  conversion        Run file conversion tests"
    echo "  dispatch          Run dispatch/orchestration tests"
    echo "  workflow          Run workflow tests"
    echo "  upgrade           Run database upgrade tests"
    echo "  pyinstaller       Run PyInstaller tests"
    echo "  all               Run all tests (may timeout!)"
    echo "  quick             Run unit + fast integration tests"
    echo "  ci                Run tests suitable for CI (excludes slow)"
    echo ""
    echo "Options:"
    echo "  -v, --verbose     Verbose output"
    echo "  -x, --exitfirst   Exit on first failure"
    echo "  -k EXPRESSION     Only run tests matching expression"
    echo "  --timeout SECS    Set timeout (default: 300)"
    echo ""
    echo "Examples:"
    echo "  $0 unit -v                    # Run unit tests with verbose output"
    echo "  $0 integration --timeout 600  # Run integration tests with 10 min timeout"
    echo "  $0 ci -x                      # CI mode, exit on first failure"
}

# Build pytest arguments
PYTEST_ARGS="-v"
while [[ $# -gt 0 ]]; do
    case $1 in
        -v|--verbose)
            PYTEST_ARGS="$PYTEST_ARGS -v"
            shift
            ;;
        -x|--exitfirst)
            PYTEST_ARGS="$PYTEST_ARGS -x"
            shift
            ;;
        -k)
            PYTEST_ARGS="$PYTEST_ARGS -k '$2'"
            shift 2
            ;;
        --timeout)
            TIMEOUT="$2"
            shift 2
            ;;
        -h|--help)
            print_usage
            exit 0
            ;;
        *)
            echo -e "${RED}Unknown option: $1${NC}"
            print_usage
            exit 1
            ;;
    esac
done

run_tests() {
    local marker="$1"
    local description="$2"
    local extra_args="${3:-}"

    echo -e "${BLUE}========================================${NC}"
    echo -e "${BLUE}$description${NC}"
    echo -e "${BLUE}========================================${NC}"
    echo ""

    if [ -n "$marker" ]; then
        # shellcheck disable=SC2086
        python -m pytest tests $PYTEST_ARGS -m "$marker" --timeout="$TIMEOUT" $extra_args
    else
        # shellcheck disable=SC2086
        python -m pytest tests $PYTEST_ARGS --timeout="$TIMEOUT" $extra_args
    fi

    local exit_code=$?
    echo ""

    if [ $exit_code -eq 0 ]; then
        echo -e "${GREEN}✓ $description passed${NC}"
    else
        echo -e "${RED}✗ $description failed${NC}"
    fi

    return $exit_code
}

case "$COMMAND" in
    unit)
        run_tests "unit" "Unit Tests"
        ;;
    integration)
        run_tests "integration" "Integration Tests"
        ;;
    qt)
        run_tests "qt" "Qt/UI Tests"
        ;;
    e2e)
        run_tests "e2e" "End-to-End Tests"
        ;;
    fast)
        run_tests "fast" "Fast Tests"
        ;;
    slow)
        run_tests "slow" "Slow Tests"
        ;;
    database)
        run_tests "database" "Database Tests"
        ;;
    backend)
        run_tests "backend" "Backend Tests (FTP, Email, Copy)"
        ;;
    conversion)
        run_tests "conversion" "File Conversion Tests"
        ;;
    dispatch)
        run_tests "dispatch" "Dispatch/Orchestration Tests"
        ;;
    workflow)
        run_tests "workflow" "Workflow Tests"
        ;;
    upgrade)
        run_tests "upgrade" "Database Upgrade Tests"
        ;;
    pyinstaller)
        run_tests "pyinstaller" "PyInstaller Tests"
        ;;
    all)
        echo -e "${YELLOW}Warning: Running all tests may exceed timeout limits${NC}"
        run_tests "" "All Tests"
        ;;
    quick)
        echo -e "${BLUE}Running quick test suite (unit + fast)...${NC}"
        run_tests "unit or fast" "Quick Tests"
        ;;
    ci)
        echo -e "${BLUE}Running CI test suite (excludes slow tests)...${NC}"
        run_tests "not slow" "CI Tests"
        ;;
    -h|--help|help)
        print_usage
        exit 0
        ;;
    *)
        echo -e "${RED}Unknown command: $COMMAND${NC}"
        print_usage
        exit 1
        ;;
esac
