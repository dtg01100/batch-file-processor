---
applyTo: 'tests/**/*.py'
description: 'Standardized testing workflow patterns for the Batch File Processor project'
---

# Testing Workflow

## Core Principles

- **Always use the virtual environment** — never run tests with system Python
- **Always set a timeout** — a hanging test is a bug
- **Run targeted tests first** — don't run the full suite unless necessary
- **Use appropriate markers** — respect the strict marker configuration
- **Minimize mocks** — prefer real implementations with isolated fixtures
- **Add regression tests** — every bug fix needs a test

## Test Execution Commands

### Quick Checks (During Development)

```bash
# Run a single test file
./.venv/bin/pytest tests/unit/test_file.py -x --timeout=30

# Run a single test by name
./.venv/bin/pytest tests/unit/test_file.py::test_function_name -x --timeout=30

# Run tests matching a keyword
./.venv/bin/pytest tests/ -k "keyword" -x --timeout=30

# Stop on first failure, short timeout for debugging
./.venv/bin/pytest -x --timeout=30
```

### Marker-Based Execution

```bash
# Run only unit tests (fast, isolated)
./.venv/bin/pytest -m unit --timeout=30

# Run integration tests (real DB, filesystem)
./.venv/bin/pytest -m integration --timeout=60

# Run Qt UI tests (offscreen backend)
QT_QPA_PLATFORM=offscreen ./.venv/bin/pytest -m qt --timeout=60

# Run database tests
./.venv/bin/pytest -m database --timeout=60

# Run dispatch/orchestration tests
./.venv/bin/pytest -m dispatch --timeout=60

# Run conversion tests
./.venv/bin/pytest -m conversion --timeout=60

# Run backend tests (FTP, Email, Copy)
./.venv/bin/pytest -m backend --timeout=60

# Combine markers
./.venv/bin/pytest -m "integration and database" --timeout=60
```

### Full Test Suite

```bash
# Run all tests (default: parallel with xdist, 120s timeout per test)
./.venv/bin/pytest tests/ -q

# Run with coverage
./.venv/bin/pytest tests/ --cov=. --cov-report=html -q

# Verbose output
./.venv/bin/pytest tests/ -v --timeout=30
```

## Test Markers Reference

The project uses `--strict-markers`, so all tests must have appropriate markers.

### Primary Markers

| Marker | Purpose | When to Use |
|--------|---------|-------------|
| `unit` | Fast, isolated, no I/O | Testing pure functions, logic, calculations |
| `integration` | Real DB, filesystem, or components | Testing with real database, file operations |
| `qt` | PyQt UI tests (offscreen mode) | Testing dialogs, widgets, UI interactions |
| `database` | Database-specific tests | Schema, queries, migrations |
| `dispatch` | Pipeline/orchestration tests | File processing workflow |
| `conversion` | File conversion tests | Format converters |
| `backend` | FTP/SMTP/copy backend tests | Output backend functionality |
| `slow` | Tests taking >30 seconds | Long-running tests, warn reviewers |

### Secondary Markers

| Marker | Purpose |
|--------|---------|
| `smoke` | Quick sanity checks |
| `e2e` | End-to-end workflow tests |
| `fast` | Tests under 5 seconds |
| `pyinstaller` | Build-related tests |
| `build` | Build system tests |
| `gui` | GUI component tests |
| `workflow` | Complete workflow tests |
| `upgrade` | Database upgrade tests |
| `error_recovery` | Error recovery tests (exempt from fail-fast) |
| `performance` | Performance benchmarks |
| `security` | Security validation tests |
| `migration` | Database migration tests |

### Adding Markers to Tests

```python
import pytest

@pytest.mark.unit
def test_calculate_discount():
    assert calculate_discount(100, 0.15) == 15.0

@pytest.mark.integration
@pytest.mark.database
def test_folder_creation(legacy_v32_db):
    # Uses real database
    folder = legacy_v32_db["folders"].insert_one(name="test")
    assert folder["id"] is not None

@pytest.mark.qt
def test_dialog_opens(qtbot, edit_dialog):
    # Uses real Qt widgets with offscreen backend
    dialog = edit_dialog()
    qtbot.addWidget(dialog)
    dialog.show()
    assert dialog.isVisible()
```

## Test Fixtures

### Database Fixtures

```python
# Legacy v32 database (real production data)
@pytest.fixture
def legacy_v32_db(tmp_path):
    """Copy real legacy v32 database to temp directory."""
    # Auto-skips if fixture file missing
    # Returns path to copied database

# Migrated v42 database
@pytest.fixture
def migrated_v42_db(legacy_v32_db, tmp_path):
    """Fully migrated v32 -> v42 database connection."""
    # Yields open database connection
    # Auto-closes on teardown

# Single folder row
@pytest.fixture
def real_folder_row(migrated_v42_db):
    """Return known-good folder row (id=21)."""
    # Useful for unit-level assertions
```

### Using Fixtures Correctly

```python
# ✅ GOOD: Use provided fixtures
def test_folder_processing(legacy_v32_db):
    db_path = legacy_v32_db
    process_folder(db_path)

# ❌ BAD: Create your own database
def test_folder_processing():
    db_path = "/tmp/test.db"  # Don't do this
    # ...
```

## Qt/PyQt5 Testing Requirements

### Mandatory Rules

- **ALWAYS use real Qt widgets** with the offscreen backend
- **NEVER implement fake/mock Qt API classes** (no `FakeWidget`, `FakeEvent`, etc.)
- **Use `qtbot` fixture** for widget interactions and signal testing
- **Set `QT_QPA_PLATFORM=offscreen`** for headless testing

### Example Qt Test

```python
import pytest
from PyQt5.QtWidgets import QDialog

@pytest.mark.qt
def test_dialog_accepts_valid_input(qtbot, edit_dialog):
    dialog = edit_dialog()
    qtbot.addWidget(dialog)
    
    # Interact with real widgets
    qtbot.keyClicks(dialog.name_input, "Test Folder")
    qtbot.mouseClick(dialog.accept_button, Qt.LeftButton)
    
    assert dialog.result() == QDialog.Accepted
```

## Mocking Guidelines

### Philosophy: Minimize Mocks

**Prefer:**
- Real implementations with isolated test fixtures
- In-memory implementations over mock objects
- Integration tests with real components
- Test doubles only for external services or expensive operations

### When Mocking is Acceptable

```python
# ✅ Acceptable: External services (FTP/SMTP servers)
@pytest.mark.unit
def test_ftp_retry_logic(mock_ftp_server):
    # Mock the network layer, test the retry logic
    pass

# ✅ Acceptable: UI display servers
@pytest.mark.unit
def test_progress_updates(mock_display):
    # Mock the display, test progress reporting
    pass

# ✅ Acceptable: Truly expensive operations
@pytest.mark.unit
def test_cache_logic(mock_expensive_computation):
    # Mock the computation, test the caching
    pass

# ❌ Not Acceptable: Domain logic
def test_discount_calculation(mock_calculate_discount):
    # Don't mock the thing you're trying to test!
    pass
```

### Using pytest Fixtures Over unittest.mock

```python
# ✅ GOOD: pytest fixture with real implementation
@pytest.fixture
def temp_config_file(tmp_path):
    config = tmp_path / "config.ini"
    config.write_text("[section]\nkey=value")
    return config

# ❌ BAD: Mocking a file
@pytest.fixture
def mock_config_file():
    mock_file = Mock()
    mock_file.read_text.return_value = "[section]\nkey=value"
    return mock_file
```

## Regression Testing

### When Fixing a Bug

1. **Write a test that fails before the fix**
2. **Implement the fix**
3. **Verify the test passes**
4. **Add appropriate markers**

### Example Regression Test

```python
@pytest.mark.unit
@pytest.mark.dispatch
def test_converter_handles_empty_output():
    """Regression: converter previously returned 0-byte file for empty input."""
    converter = get_converter('tweaks')
    result = converter.process(input_data="")
    
    # This assertion would have failed before the fix
    assert result is None or result.output_path is None
```

### Test Naming Conventions

```python
# Pattern: test_<what_is_being_tested>_<expected_behavior>
def test_calculate_discount_returns_zero_for_no_discount():
def test_folder_validation_fails_for_missing_path():
def test_ftp_reconnects_after_timeout():

# Pattern: test_<scenario>_<outcome>
def test_empty_file_raises_validation_error():
def test_invalid_format_converts_to_csv():
```

## Debugging Failing Tests

### Common Issues and Solutions

#### Test Hangs/Timeouts

```bash
# Run with short timeout to identify hanging test
./.venv/bin/pytest -x --timeout=30

# Run with verbose output to see where it's stuck
./.venv/bin/pytest -v --timeout=30

# Run without parallel execution for clearer output
./.venv/bin/pytest -x --timeout=30 -n 0
```

#### Import Errors

```bash
# Ensure you're using the venv
which python
# Should be: ./.venv/bin/python

# Reinstall dependencies
source .venv/bin/activate
pip install -r requirements.txt
pip install -r requirements-dev.txt
```

#### Database Fixture Issues

```bash
# Check if fixture file exists
ls -la tests/fixtures/legacy_v32_folders.db

# If missing, tests using legacy_v32_db will auto-skip
```

#### Qt Test Failures

```bash
# Ensure offscreen platform is set
QT_QPA_PLATFORM=offscreen ./.venv/bin/pytest -m qt

# Check if PyQt5 is installed correctly
./.venv/bin/python -c "from PyQt5.QtWidgets import QApplication; print('OK')"
```

### Using pytest Features for Debugging

```bash
# Print stdout from tests
./.venv/bin/pytest -s

# Drop into debugger on failure
./.venv/bin/pytest --pdb

# Show local variables on failure
./.venv/bin/pytest -l

# Run last failed tests
./.venv/bin/pytest --lf

# Run tests that failed previously + new tests
./.venv/bin/pytest --ff
```

## Coverage Reporting

### Generate Coverage Report

```bash
# HTML report (opens in browser)
./.venv/bin/pytest --cov=. --cov-report=html

# Terminal report with missing lines
./.venv/bin/pytest --cov=. --cov-report=term-missing

# Fail if coverage drops below threshold
./.venv/bin/pytest --cov=. --cov-fail-under=80
```

### Interpreting Coverage

- **High coverage ≠ good tests** — focus on critical paths
- **Look for untested branches** — edge cases, error handling
- **Prioritize new code** — ensure changes have test coverage
- **Use coverage as a guide** — not a gate

## CI/CD Integration

### Standard CI Test Command

```bash
# In CI/CD pipeline
source .venv/bin/activate
pytest tests/ -q --timeout=30
ruff check .
black --check .
```

### Local Pre-Commit Checklist

Before committing code:

```bash
# 1. Run relevant tests
./.venv/bin/pytest tests/unit/test_changed_file.py -x --timeout=30

# 2. Run full suite if changes are widespread
./.venv/bin/pytest tests/ -q --timeout=30

# 3. Lint
./.venv/bin/ruff check .

# 4. Format check
./.venv/bin/black --check .

# 5. Fix formatting if needed
./.venv/bin/black .
```

## Best Practices

1. **Always activate the venv** before running tests
2. **Always set a timeout** — hanging tests block CI
3. **Use targeted execution** — don't run full suite unnecessarily
4. **Mark tests appropriately** — respect strict markers
5. **Prefer real implementations** — minimize mocking
6. **Add regression tests** — every bug fix gets a test
7. **Name tests descriptively** — test names should explain what they verify
8. **Keep tests isolated** — no test should depend on another
9. **Clean up resources** — use fixtures with proper teardown
10. **Document complex setups** — explain non-obvious test configurations

## Project-Specific Notes

### Parallel Test Execution

The project uses `pytest-xdist` with `loadscope` distribution:

```ini
# pytest.ini
addopts = --tb=short --strict-markers -n auto --dist loadscope
```

This runs tests in parallel, grouped by module/class for better isolation.

### Timeout Configuration

```ini
# pytest.ini
timeout = 120
timeout_method = signal  # POSIX: allows rest of suite to continue
```

- Default timeout: 120 seconds per test
- Uses signal method on POSIX (better isolation)
- Falls back to thread method on Windows

### Test Discovery

```ini
# pytest.ini
testpaths = tests
python_files = test_*.py
python_classes = Test*
python_functions = test_*
```

Tests are discovered in the `tests/` directory following standard pytest naming conventions.

### Environment Variables

```bash
# Set in conftest.py
DISPATCH_STRICT_TESTING_MODE=true  # Enables strict validation
QT_QPA_PLATFORM=offscreen          # Headless Qt testing
```

These are set automatically by the test configuration, but you can override them if needed.
