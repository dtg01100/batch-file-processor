# Makefile for batch-file-processor (local webapp)
# Usage: make <target>

PYTEST := .venv/bin/pytest
# -n 2 beats -n auto on this test suite: most tests are <100ms and the
# per-worker setup cost (~6s each) dominates with 4 workers. Override via
# PYTEST_XDIST_AUTO_NUM_WORKERS env var when more parallelism helps.
PYTEST_XDIST := -n 2

.PHONY: help test test-unit test-integration test-file test-func test-parallel test-fast test-failfast test-webapp test-js test-meta lint type-check run webapp

help:
	@echo "Testing targets:"
	@echo "  make test-unit        - Run unit tests (parallel)"
	@echo "  make test-integration - Run integration tests"
	@echo "  make test-file FILE=  - Run specific test file"
	@echo "  make test-func FILE= FUNC= - Run a single test function"
	@echo "  make test-parallel    - Run all tests in parallel"
	@echo "  make test-fast        - Fast dev loop (skips slow + meta tests)"
	@echo "  make test-webapp      - Run the webapp test suite"
	@echo "  make test-js          - Run the webapp JS unit tests (node:test)"
	@echo "  make test-meta        - Run the meta-tests (hygiene, coverage, markers)"
	@echo "  make test-failfast    - Stop at first failure"
	@echo ""
	@echo "Webapp targets:"
	@echo "  make run              - Start the webapp with uvicorn (BFS_BASE_DIR env)"
	@echo ""
	@echo "Linting targets:"
	@echo "  make lint             - Run ruff linter"
	@echo "  make type-check       - Run mypy type checker"

# Default: show available targets
test:
	@$(PYTEST) --co -q 2>/dev/null | tail -3

# Unit tests (parallel)
test-unit:
	$(PYTEST) -m unit $(PYTEST_XDIST) -v

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

# Run all tests in parallel
test-parallel:
	$(PYTEST) $(PYTEST_XDIST) -v

# Fast dev loop: skip the migration cluster (~60s) and the meta-tests,
# failed-first so re-runs focus on what's broken.
test-fast:
	$(PYTEST) -m "not slow" $(PYTEST_XDIST) -x --ff --ignore=tests/meta

# Webapp suite (importer rebasing, runner, API endpoints)
test-webapp:
	$(PYTEST) tests/webapp -v

# Webapp JS tests: unit tests for static/api.js + static/helpers.js +
# static/templates.js (node:test, no deps) plus the jsdom DOM
# integration test (needs `npm install` once for node_modules/jsdom).
test-js:
	node --test tests/webapp/api.test.js tests/webapp/helpers.test.js tests/webapp/templates.test.js tests/webapp/dom.test.js

# Meta-tests (test hygiene, module coverage, marker placement, ...)
test-meta:
	$(PYTEST) tests/meta -n 0 -v

# Stop at first failure
test-failfast:
	$(PYTEST) -x $(PYTEST_XDIST) -v

# =============================================================================
# Webapp
# =============================================================================
# Start the local webapp. BFS_BASE_DIR is the root all configured folder
# paths resolve against (a Docker volume in production). Defaults to ./data.
# BFS_DATA_DIR is where folders.db lives (default: <base-dir>/config).
#   BFS_BASE_DIR=/srv/batch ./venv/bin/python -m webapp.main
#   make run
run:
	@BFS_BASE_DIR=$${BFS_BASE_DIR:-./data} .venv/bin/python -m webapp.main

# =============================================================================
# Linting and Type Checking
# =============================================================================

lint:
	.venv/bin/ruff check .

type-check:
	.venv/bin/mypy backend core dispatch webapp

# =============================================================================
# Run tests by marker (examples)
test-backend:
	$(PYTEST) -m backend $(PYTEST_XDIST) -v

test-conversion:
	$(PYTEST) -m conversion $(PYTEST_XDIST) -v

test-dispatch:
	$(PYTEST) -m dispatch $(PYTEST_XDIST) -v

test-database:
	$(PYTEST) -m database $(PYTEST_XDIST) -v
