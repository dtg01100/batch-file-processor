# Test Organization Guide

This document describes how the test suite is organized and how to run tests in parts to avoid timeouts.

## Test Structure

Tests are organized into three main directories:

```
tests/
├── unit/           # Fast, isolated unit tests
├── integration/    # Integration tests with real components
└── qt/            # Qt/UI tests using pytest-qt
```

## Test Markers

We use pytest markers to categorize tests. This allows running specific subsets:

### Test Type Markers

| Marker | Description | Example Usage |
|--------|-------------|---------------|
| `unit` | Fast, isolated unit tests | `pytest -m unit` |
| `integration` | Tests with real database/filesystem | `pytest -m integration` |
| `e2e` | End-to-end workflow tests | `pytest -m e2e` |
| `qt` | Qt UI tests | `pytest -m qt` |
| `ui` | UI component tests | `pytest -m ui` |

### Speed Markers

| Marker | Description | Example Usage |
|--------|-------------|---------------|
| `fast` | Tests completing in < 5 seconds | `pytest -m fast` |
| `slow` | Tests taking > 30 seconds | `pytest -m slow` |

### Component Markers

| Marker | Description | Example Usage |
|--------|-------------|---------------|
| `database` | Database-related tests | `pytest -m database` |
| `dispatch` | Dispatch/orchestration tests | `pytest -m dispatch` |
| `conversion` | File conversion tests | `pytest -m conversion` |
| `backend` | Backend tests (FTP, Email, Copy) | `pytest -m backend` |
| `gui` | GUI component tests | `pytest -m gui` |

### Workflow Markers

| Marker | Description | Example Usage |
|--------|-------------|---------------|
| `workflow` | Complete workflow tests | `pytest -m workflow` |
| `upgrade` | Database upgrade tests | `pytest -m upgrade` |
| `pyinstaller` | PyInstaller build tests | `pytest -m pyinstaller` |
| `build` | Build-related tests | `pytest -m build` |

## Running Tests

### Using the Test Runner Scripts

We provide convenient scripts to run tests in parts:

#### Bash (Linux/macOS)

```bash
# Run unit tests only
./scripts/run_tests.sh unit

# Run integration tests
./scripts/run_tests.sh integration

# Run Qt/UI tests
./scripts/run_tests.sh qt

# Run fast tests only
./scripts/run_tests.sh fast

# Run CI-friendly tests (excludes slow)
./scripts/run_tests.sh ci

# Run quick tests (unit + fast)
./scripts/run_tests.sh quick

# With verbose output and exit on first failure
./scripts/run_tests.sh unit -v -x

# With custom timeout
./scripts/run_tests.sh integration --timeout 600
```

#### Python (Cross-platform)

```bash
# Run unit tests only
python scripts/run_tests.py unit

# Run integration tests
python scripts/run_tests.py integration

# Run CI-friendly tests
python scripts/run_tests.py ci

# List available test suites
python scripts/run_tests.py list

# With options
python scripts/run_tests.py unit -v -x --timeout 600
```

### Using pytest Directly

```bash
# Run unit tests
pytest -m unit

# Run integration tests (excluding slow)
pytest -m "integration and not slow"

# Run database tests only
pytest -m database

# Run workflow tests
pytest -m workflow

# Run all tests except slow ones
pytest -m "not slow"

# Run tests by directory
pytest tests/unit/
pytest tests/integration/
pytest tests/qt/

# Run specific test file
pytest tests/unit/test_utils.py

# Run with increased timeout
pytest --timeout=600 -m integration
```

## Test Suite Recommendations

### Quick Development Feedback

For fast feedback during development:

```bash
./scripts/run_tests.sh quick
# or
pytest -m "unit or fast"
```

### Pre-commit Checks

Before committing:

```bash
./scripts/run_tests.sh ci
# or
pytest -m "not slow" -x
```

### Full Test Suite

To run the full test suite (may take a while):

```bash
./scripts/run_tests.sh all
# or
pytest --timeout=600
```

### Specific Components

When working on specific components:

```bash
# Database changes
pytest -m database

# Backend changes
pytest -m backend

# Conversion changes
pytest -m conversion

# UI changes
pytest -m qt
```

## Timeout Configuration

The default timeout is 300 seconds (5 minutes). You can override this:

```bash
# In pytest.ini
[pytest]
timeout = 300

# On command line
pytest --timeout=600

# In run_tests scripts
./scripts/run_tests.sh integration --timeout 600
```

## Continuous Integration

For CI environments, use the `ci` suite which excludes slow tests:

```bash
./scripts/run_tests.sh ci
```

Or in your CI configuration:

```yaml
# GitHub Actions example
- name: Run tests
  run: |
    pytest -m "not slow"
```

## Adding Markers to New Tests

When creating new tests, add appropriate markers:

```python
import pytest

# Module-level marker (applies to all tests in file)
pytestmark = [pytest.mark.unit, pytest.mark.fast]

# Individual test markers
@pytest.mark.slow
def test_long_running_operation():
    pass

@pytest.mark.integration
@pytest.mark.database
def test_database_operation():
    pass
```

## Test File Organization Guidelines

1. **Unit tests** (`tests/unit/`): Fast, isolated, no external dependencies
2. **Integration tests** (`tests/integration/`): Tests with real database/filesystem
3. **Qt tests** (`tests/qt/`): UI tests requiring Qt framework

Each test file should have a module-level `pytestmark` defining its primary markers.

## Troubleshooting

### Timeouts

If tests timeout:

1. Run a smaller subset: `./scripts/run_tests.sh quick`
2. Increase timeout: `--timeout 600`
3. Run specific tests: `pytest -k test_name`

### Qt Tests Failing

Qt tests require a display. In headless environments:

```bash
export QT_QPA_PLATFORM=offscreen
pytest -m qt
```

### Import Errors

Ensure the project root is in PYTHONPATH:

```bash
export PYTHONPATH=/path/to/batch-file-processor:$PYTHONPATH
pytest
```

Or use the provided scripts which handle this automatically.
