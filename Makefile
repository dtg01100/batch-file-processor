# Makefile for batch-file-processor
# Usage: make <target>

PYTEST := .venv/bin/pytest
PYTEST_XDIST := -n auto
PYTEST_QT := -n0

.PHONY: help test test-unit test-unit-fast test-integration test-file test-parallel test-quick test-all test-failfast test-qt test-qt-single test-no-qt

help:
	@echo "Testing targets:"
	@echo "  make test-unit        - Run unit tests (parallel)"
	@echo "  make test-unit-fast   - Run fast unit tests only"
	@echo "  make test-integration - Run integration tests"
	@echo "  make test-file FILE=  - Run specific test file"
	@echo "  make test-parallel    - Run all tests in parallel (excludes Qt tests)"
	@echo "  make test-quick       - Fail-fast, short timeout"
	@echo "  make test-all         - Run full suite"
	@echo "  make test-failfast    - Stop at first failure"
	@echo ""
	@echo "Qt-specific targets (use -n0 to avoid parallel execution issues):"
	@echo "  make test-qt          - Run all Qt tests (single-threaded)"
	@echo "  make test-qt-single   - Run Qt tests from single file"
	@echo "  make test-qt-file FILE= - Run Qt tests in specific file"

# Default: show available targets
test:
	@$(PYTEST) --co -q 2>/dev/null | tail -3

# Unit tests (parallel)
test-unit:
	$(PYTEST) -m unit $(PYTEST_XDIST) -v

# Fast unit tests only
test-unit-fast:
	$(PYTEST) -m "unit and fast" $(PYTEST_XDIST) -v

# Integration tests
test-integration:
	$(PYTEST) -m integration $(PYTEST_XDIST) -v

# Run a specific test file
# Usage: make test-file FILE=tests/unit/test_utils.py
test-file:
ifndef FILE
	@echo "Usage: make test-file FILE=tests/unit/test_utils.py"
	@exit 1
endif
	$(PYTEST) $(FILE) $(PYTEST_XDIST) -v

# Run a single test function
# Usage: make test-func FILE=tests/unit/test_utils.py FUNC=test_capture_records
test-func:
ifndef FILE
	@echo "Usage: make test-func FILE=tests/unit/test_utils.py FUNC=test_name"
	@exit 1
endif
ifdef FUNC
	$(PYTEST) $(FILE)::$(FUNC) $(PYTEST_XDIST) -v
else
	$(PYTEST) $(FILE) $(PYTEST_XDIST) -v
endif

# Run all tests in parallel (excludes Qt tests)
# Qt tests are excluded because PyQt5 + pytest-xdist parallel execution causes
# flaky segfaults due to worker thread cleanup issues. Use 'make test-qt' for Qt tests.
test-parallel:
	$(PYTEST) -m "not qt" $(PYTEST_XDIST) -v

# Quick iteration: fail-fast, short timeout
test-quick:
	$(PYTEST) -m "not qt" -x --timeout=30 $(PYTEST_XDIST) -v

# Quick iteration with parallel execution
test-quick-parallel:
	$(PYTEST) -x --timeout=30 $(PYTEST_XDIST) -v

# Run unit tests in parallel with fail-fast
test-unit-parallel:
	$(PYTEST) -m unit $(PYTEST_XDIST) -v

# Stop at first failure
test-failfast:
	$(PYTEST) -x $(PYTEST_XDIST) -v

# Full test suite (all tests, single-threaded for Qt stability)
test-all:
	$(PYTEST) -m "not qt" $(PYTEST_XDIST) -v
	$(PYTEST) tests/unit/interface/qt/ $(PYTEST_QT) -v

# Run tests by marker (examples)
test-backend:
	$(PYTEST) -m backend $(PYTEST_XDIST) -v

test-conversion:
	$(PYTEST) -m conversion $(PYTEST_XDIST) -v

test-dispatch:
	$(PYTEST) -m dispatch $(PYTEST_XDIST) -v

test-database:
	$(PYTEST) -m database $(PYTEST_XDIST) -v

# =============================================================================
# Qt Test Targets
# =============================================================================
# Qt tests MUST be run with -n0 (single-threaded) because PyQt5 widgets
# with background threads (QThread workers) cause segfaults when pytest-xdist
# runs them in parallel. The deleteLater() fix helps but doesn't fully resolve
# the race conditions in test teardown.
# =============================================================================

# Run all Qt tests (single-threaded)
test-qt:
	$(PYTEST) tests/unit/interface/qt/ $(PYTEST_QT) -v

# Run Qt tests from a single file
# Usage: make test-qt-file FILE=tests/unit/interface/qt/test_resend_dialog.py
test-qt-file:
ifndef FILE
	@echo "Usage: make test-qt-file FILE=tests/unit/interface/qt/test_resend_dialog.py"
	@exit 1
endif
	$(PYTEST) $(FILE) $(PYTEST_QT) -v

# Run Qt tests from a single file with fail-fast
# Usage: make test-qt-single FILE=tests/unit/interface/qt/test_resend_dialog.py
test-qt-single:
ifndef FILE
	@echo "Usage: make test-qt-single FILE=tests/unit/interface/qt/test_resend_dialog.py"
	@exit 1
endif
	$(PYTEST) $(FILE) $(PYTEST_QT) -x -v
