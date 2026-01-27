# Testing Documentation for batch-file-processor

## Overview

This project now uses **pytest** as its testing framework. The test suite captures the current production functionality to serve as baseline tests and prevent regressions.

## Quick Start

### Running All Tests

```bash
# Run all tests
pytest tests/ -v

# Run tests with coverage report
pytest tests/ -v --cov=. --cov-report=html
```

### Running Specific Test Categories

```bash
# Run only smoke tests (quick validation)
pytest tests/ -v -m smoke

# Run only unit tests
pytest tests/ -v -m unit

# Run only integration tests
pytest tests/ -v -m integration
```

### Running Specific Test Files

```bash
# Test utility functions
pytest tests/unit/test_utils.py -v

# Test error recording functionality
pytest tests/integration/test_record_error.py -v

# Run smoke tests
pytest tests/test_smoke.py -v
```

## Test Structure

```
tests/
├── conftest.py                 # Shared fixtures and pytest configuration
├── test_smoke.py              # Smoke tests for quick validation
├── unit/
│   └── test_utils.py          # Unit tests for utility functions
├── integration/
│   └── test_record_error.py    # Integration tests for error recording
├── api/
│   └── [future API tests]
└── pipeline/
    └── [future pipeline tests]
```

## Test Categories

### Smoke Tests (`@pytest.mark.smoke`)
- **Purpose**: Quick validation that the system is in a working state
- **Run time**: < 1 second
- **Coverage**: Verifies all key modules can be imported and basic functions are callable
- **Use case**: Pre-deployment checks, CI/CD smoke test stage

### Unit Tests (`@pytest.mark.unit`)
- **Purpose**: Test individual functions in isolation
- **Coverage**: Current behavior of:
  - DAC time/date conversions
  - Price formatting
  - UPC code conversions
  - Check digit calculations
  - String-to-integer conversion
- **Note**: Tests capture current production behavior exactly

### Integration Tests (`@pytest.mark.integration`)
- **Purpose**: Test interaction between modules
- **Coverage**: Error recording functionality across file and threaded modes

## Fixtures Available

All fixtures are defined in `conftest.py`:

### `temp_dir`
Creates a temporary directory that's cleaned up after the test.
```python
def test_something(temp_dir):
    # temp_dir is a path to a temporary directory
    file_path = os.path.join(temp_dir, "test_file.txt")
```

### `sample_file`
Creates a simple text file for testing.
```python
def test_something(sample_file):
    # sample_file is a path to a file containing "test content\n"
    with open(sample_file) as f:
        content = f.read()
```

### `sample_csv_file`
Creates a sample CSV file with headers and one data row.
```python
def test_something(sample_csv_file):
    # sample_csv_file is a path to a CSV file
    pass
```

### `sample_edi_file`
Creates a sample EDI file for testing conversions.
```python
def test_something(sample_edi_file):
    # sample_edi_file is a path to an EDI format file
    pass
```

### `project_root`
Returns the project root directory as a Path object.
```python
def test_something(project_root):
    # project_root is the batch-file-processor directory
    pass
```

## Adding New Tests

### Basic Unit Test Template

```python
import pytest
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import your_module

@pytest.mark.unit
class TestYourModule:
    """Tests for your_module."""
    
    def test_something(self):
        """Test description."""
        result = your_module.function_name()
        assert result == expected_value
```

### Using Fixtures in Tests

```python
@pytest.mark.unit
def test_with_fixture(temp_dir, sample_file):
    """Test using multiple fixtures."""
    # Use both temp_dir and sample_file
    assert os.path.exists(sample_file)
    assert os.path.isdir(temp_dir)
```

## Current Test Coverage

**38 total tests passing:**

- **Smoke Tests**: 10 tests
  - Module availability checks
  - Function callability verification
  - Project structure validation

- **Unit Tests**: 24 tests
  - `TestDacStrIntToInt`: 4 tests
  - `TestConvertToPrice`: 3 tests
  - `TestDactimeFromDatetime`: 3 tests
  - `TestDatetimeFromDactime`: 3 tests
  - `TestDatetimeFromInvtime`: 2 tests
  - `TestDactimeFromInvtime`: 2 tests
  - `TestCalcCheckDigit`: 1 test
  - `TestConvertUPCEToUPCA`: 6 tests

- **Integration Tests**: 4 tests
  - `TestRecordErrorBasic`: 4 tests (file and threaded logging)

## Configuration

### pytest.ini
Configures pytest behavior:
- Test discovery patterns
- Test output format (verbose by default)
- Warnings disabled
- Configurable via `pytest.ini` in the project root

## CI/CD Integration

### Running with Coverage

```bash
pytest tests/ -v --cov=. --cov-report=html --cov-report=term
```

This generates an HTML coverage report in `htmlcov/index.html`.

### Running Specific Test Markers

```bash
# Fast smoke tests only (ideal for pre-commit)
pytest tests/ -m smoke -v

# All tests except slow
pytest tests/ -m "not slow" -v
```

## Troubleshooting

### Test Discovery Issues
If pytest isn't finding your tests:
1. Ensure files start with `test_` or end with `_test.py`
2. Check that test functions start with `test_`
3. Verify `conftest.py` is in the tests directory

### Import Issues
If you get import errors:
1. Ensure `conftest.py` exists in the tests directory
2. Check that the main modules are in the project root (same level as tests/)
3. Use the fixture-based path setup shown in test examples

### Module Not Found
Add this to your test file:
```python
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
```

## Future Test Expansion

These test categories are ready for expansion:
- **tests/api/**: API endpoint tests
- **tests/pipeline/**: Full pipeline integration tests
- **tests/api/**: Batch processing tests

Add test files to these directories as needed and mark them appropriately with `@pytest.mark.unit`, `@pytest.mark.integration`, `@pytest.mark.slow`, etc.

## References

- [pytest Documentation](https://docs.pytest.org/)
- [pytest Fixtures](https://docs.pytest.org/en/stable/fixture.html)
- [pytest Markers](https://docs.pytest.org/en/stable/how-to-use-pytest-mark.html)
