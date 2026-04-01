# Makefile for batch-file-processor
# Usage: make <target>

PYTEST := python3 -m pytest
PYTEST_XDIST := -n auto

.PHONY: help test test-unit test-unit-fast test-integration test-file test-parallel test-quick test-all test-failfast

help:
	@echo "Testing targets:"
	@echo "  make test-unit        - Run unit tests (657 tests)"
	@echo "  make test-unit-fast   - Run fast unit tests only (157 tests)"
	@echo "  make test-integration - Run integration tests (835 tests)"
	@echo "  make test-file FILE=  - Run specific test file"
	@echo "  make test-parallel    - Run all tests in parallel"
	@echo "  make test-quick       - Fail-fast, short timeout, single file"
	@echo "  make test-all         - Run full suite"
	@echo "  make test-failfast    - Stop at first failure"

# Default: show available targets
test:
	@$(PYTEST) --co -q 2>/dev/null | tail -3

# Unit tests (657 tests)
test-unit:
	$(PYTEST) -m unit -v

# Fast unit tests only (157 tests)
test-unit-fast:
	$(PYTEST) -m "unit and fast" -v

# Integration tests (835 tests)
test-integration:
	$(PYTEST) -m integration -v

# Run a specific test file
# Usage: make test-file FILE=tests/unit/test_utils.py
test-file:
ifndef FILE
	@echo "Usage: make test-file FILE=tests/unit/test_utils.py"
	@exit 1
endif
	$(PYTEST) $(FILE) -v

# Run a single test function
# Usage: make test-func FILE=tests/unit/test_utils.py FUNC=test_capture_records
test-func:
ifndef FILE
	@echo "Usage: make test-func FILE=tests/unit/test_utils.py FUNC=test_name"
	@exit 1
endif
ifdef FUNC
	$(PYTEST) $(FILE)::$(FUNC) -v
else
	$(PYTEST) $(FILE) -v
endif

# Run all tests in parallel (uses all CPU cores)
test-parallel:
	$(PYTEST) $(PYTEST_XDIST) -v

# Quick iteration: fail-fast, short timeout, stop on first failure
test-quick:
	$(PYTEST) -x --timeout=30 -v

# Quick iteration with parallel execution
test-quick-parallel:
	$(PYTEST) -x --timeout=30 $(PYTEST_XDIST) -v

# Run unit tests in parallel with fail-fast
test-unit-parallel:
	$(PYTEST) -m unit $(PYTEST_XDIST) -v

# Stop at first failure
test-failfast:
	$(PYTEST) -x -v

# Full test suite
test-all:
	$(PYTEST) -v

# Run tests by marker (examples)
test-backend:
	$(PYTEST) -m backend -v

test-conversion:
	$(PYTEST) -m conversion -v

test-dispatch:
	$(PYTEST) -m dispatch -v

test-database:
	$(PYTEST) -m database -v
