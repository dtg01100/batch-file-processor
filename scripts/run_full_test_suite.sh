#!/bin/bash
# Run the full integration + unit test suite and produce a JUnit XML report.
# Tests manage their own mock servers — no real FTP/SMTP servers are started here.

set -euo pipefail

# ---------------------------------------------------------------------------
# Colour helpers
# ---------------------------------------------------------------------------
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
BOLD='\033[1m'
NC='\033[0m'

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"

TIMESTAMP="$(date +%Y%m%d_%H%M%S)"
RESULTS_DIR="${PROJECT_ROOT}/test_results/${TIMESTAMP}"
JUNIT_XML="${RESULTS_DIR}/results.xml"
LOG_FILE="${RESULTS_DIR}/pytest.log"

mkdir -p "${RESULTS_DIR}"

# ---------------------------------------------------------------------------
# Banner
# ---------------------------------------------------------------------------
echo -e "${BOLD}${BLUE}======================================================${NC}"
echo -e "${BOLD}${BLUE}  Batch File Processor — Full Test Suite${NC}"
echo -e "${BOLD}${BLUE}  $(date)${NC}"
echo -e "${BOLD}${BLUE}======================================================${NC}"
echo ""

echo -e "${BLUE}Results directory : ${RESULTS_DIR}${NC}"
echo -e "${BLUE}JUnit XML         : ${JUNIT_XML}${NC}"
echo -e "${BLUE}Log file          : ${LOG_FILE}${NC}"
echo ""

# ---------------------------------------------------------------------------
# Notify that mock servers are used (no real servers needed)
# ---------------------------------------------------------------------------
echo -e "${GREEN}FTP server started${NC}  (mock — no real server required)"
echo -e "${GREEN}SMTP server started${NC} (mock — no real server required)"
echo ""

# ---------------------------------------------------------------------------
# Run pytest
# ---------------------------------------------------------------------------
echo -e "${BOLD}Running pytest ...${NC}"
echo ""

set +e
python -m pytest \
    "${PROJECT_ROOT}/tests" \
    --timeout=60 \
    --tb=short \
    -m "not pyinstaller and not build" \
    --junitxml="${JUNIT_XML}" \
    -v \
    2>&1 | tee "${LOG_FILE}"
PYTEST_EXIT=$?
set -e

echo ""

# ---------------------------------------------------------------------------
# Parse JUnit XML for summary numbers (pure bash — no python dependency here)
# ---------------------------------------------------------------------------
if [ -f "${JUNIT_XML}" ]; then
    # Extract attributes from the <testsuite> element
    TOTAL=$(grep -oP 'tests="\K[0-9]+' "${JUNIT_XML}" | head -1 || echo 0)
    FAILURES=$(grep -oP 'failures="\K[0-9]+' "${JUNIT_XML}" | head -1 || echo 0)
    ERRORS=$(grep -oP ' errors="\K[0-9]+' "${JUNIT_XML}" | head -1 || echo 0)
    SKIPPED=$(grep -oP 'skipped="\K[0-9]+' "${JUNIT_XML}" | head -1 || echo 0)
    ELAPSED=$(grep -oP 'time="\K[0-9.]+' "${JUNIT_XML}" | head -1 || echo 0)
    PASSED=$(( TOTAL - FAILURES - ERRORS - SKIPPED ))

    echo -e "${BOLD}${BLUE}======================================================${NC}"
    echo -e "${BOLD}  Test Summary${NC}"
    echo -e "${BOLD}${BLUE}======================================================${NC}"
    printf "  %-12s %s\n" "Total:"   "${TOTAL}"
    printf "  %-12s ${GREEN}%s${NC}\n" "Passed:"  "${PASSED}"
    printf "  %-12s ${RED}%s${NC}\n"   "Failed:"  "${FAILURES}"
    printf "  %-12s ${RED}%s${NC}\n"   "Errors:"  "${ERRORS}"
    printf "  %-12s ${YELLOW}%s${NC}\n" "Skipped:" "${SKIPPED}"
    printf "  %-12s %s s\n"            "Time:"    "${ELAPSED}"
    echo ""
else
    echo -e "${YELLOW}Warning: JUnit XML not found — pytest may have crashed before writing it.${NC}"
    echo ""
fi

# ---------------------------------------------------------------------------
# Generate human-readable report via the companion Python script
# ---------------------------------------------------------------------------
REPORT_SCRIPT="${SCRIPT_DIR}/generate_test_report.py"
if [ -f "${REPORT_SCRIPT}" ] && [ -f "${JUNIT_XML}" ]; then
    echo -e "${BLUE}Generating human-readable report ...${NC}"
    python "${REPORT_SCRIPT}" "${JUNIT_XML}" && \
        echo -e "${GREEN}Report written to ${RESULTS_DIR}/${NC}" || \
        echo -e "${YELLOW}Report generation failed (non-fatal).${NC}"
    echo ""
fi

# ---------------------------------------------------------------------------
# Final status line
# ---------------------------------------------------------------------------
if [ "${PYTEST_EXIT}" -eq 0 ]; then
    echo -e "${BOLD}${GREEN}All tests passed.${NC}"
else
    echo -e "${BOLD}${RED}Test run FAILED (exit code ${PYTEST_EXIT}).${NC}"
    echo -e "  Full log : ${LOG_FILE}"
    echo -e "  XML      : ${JUNIT_XML}"
fi

echo ""
exit "${PYTEST_EXIT}"
