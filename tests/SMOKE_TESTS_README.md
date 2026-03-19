# Smoke Tests for Application Startup

This document describes the smoke tests that verify the Batch File Processor application can actually run.

## Overview

The smoke tests in `test_app_smoke.py` validate that the application can start and run in both GUI and automatic (headless) modes without crashing. These tests verify the real entry points that users would use.

## Test Categories

### 1. Main Entry Point Tests (`TestMainEntryPoint`)

Tests the core `interface/main.py` module:

- **Module imports**: Verifies all main entry point functions are importable
- **Argument parsing**: Tests `parse_arguments()` with default and `--automatic` flags
- **Database path**: Validates `get_database_path()` returns valid paths
- **Config directory**: Tests directory creation and handling of existing directories

### 2. Automatic Mode Tests (`TestAutomaticMode`)

Tests headless/batch processing mode:

- **No active folders**: Verifies graceful exit when no folders are configured
- **Function imports**: Validates `automatic_process_directories` is importable
- **Mode callable**: Tests `run_automatic_mode` function exists

### 3. GUI Mode Tests (`TestGUIMode`)

Tests GUI startup functionality:

- **Module imports**: Verifies PyQt6 modules can be imported
- **Application creation**: Tests `create_application` function
- **Main window creation**: Tests `create_main_window` function
- **Application controller**: Validates `ApplicationController` class exists

### 4. Processing Orchestrator Tests (`TestProcessingOrchestrator`)

Tests the core processing engine:

- **Orchestrator imports**: Verifies `ProcessingOrchestrator` can be imported
- **Initialization**: Tests orchestrator can be instantiated
- **Result dataclasses**: Validates `ProcessingResult` and `DispatchResult` exist

### 5. Run Script Tests (`TestRunScript`)

Tests the `run.sh` shell script:

- **Script exists**: Verifies `run.sh` exists and is executable
- **Help flag**: Tests `./run.sh --help` works
- **Syntax validation**: Uses `bash -n` to check for syntax errors

### 6. Test Script Tests (`TestRunTestsScript`)

Tests the `run_tests.sh` shell script:

- **Script exists**: Verifies `run_tests.sh` exists and is executable
- **Syntax validation**: Uses `bash -n` to check for syntax errors

### 7. Application Structure Tests (`TestApplicationStructure`)

Tests that critical files and directories exist:

- **Directories**: `interface/` directory
- **Entry points**: `interface/main.py`, `dispatch.py`, `utils.py`
- **Converter backends**: `convert_base.py`, `convert_to_csv.py`, `convert_to_fintech.py`
- **Send backends**: `send_base.py`, `email_backend.py`, `ftp_backend.py`, `copy_backend.py`

### 8. System Requirements Tests

Standalone tests for system compatibility:

- **Python version**: Verifies Python 3.11+ is being used
- **Requirements file**: Checks `requirements.txt` exists
- **Critical dependencies**: Validates `appdirs` can be imported

## Running the Tests

### Run all smoke tests:
```bash
pytest tests/test_app_smoke.py -v -m smoke
```

### Run smoke tests from both files:
```bash
pytest tests/test_smoke.py tests/test_app_smoke.py -v -m smoke
```

### Run including slow tests:
```bash
pytest tests/test_app_smoke.py -v
```

### Run with the test runner script:
```bash
./run_tests.sh
```

## Test Execution Time

The smoke tests are designed to be fast:
- **Smoke tests only** (`-m smoke`): ~0.3 seconds
- **All tests** (including slow): ~0.5 seconds

## Test Coverage

These tests verify:
- ✅ Application entry points exist and are callable
- ✅ Both GUI and automatic modes can be initialized
- ✅ Core processing components are importable
- ✅ Run scripts exist and have valid syntax
- ✅ Critical project structure is intact
- ✅ Required dependencies are available
- ✅ Python version compatibility

## Integration with Existing Tests

The new `test_app_smoke.py` complements the existing `test_smoke.py`:

- **`test_smoke.py`**: Tests utility functions (`utils.py`, `record_error.py`) and project structure
- **`test_app_smoke.py`**: Tests actual application startup and run scripts

Together, these provide comprehensive smoke test coverage for:
1. Core utilities (existing)
2. Application startup (new)
3. Processing orchestration (new)
4. Run scripts (new)

## CI/CD Integration

These tests are ideal for CI/CD pipelines:

```yaml
# Example GitHub Actions workflow
- name: Smoke tests
  run: |
    source .venv/bin/activate
    pytest tests/test_app_smoke.py tests/test_smoke.py -v -m smoke
```

Fast execution (~0.3s) makes them perfect for pre-commit hooks or quick validation.

## Notes

- **GUI tests**: Some GUI tests skip if PyQt6 is not installed (using `pytest.skip()`)
- **Isolation**: Tests use mocks and temporary directories to avoid affecting the real application
- **No actual execution**: These tests verify imports and basic initialization, but don't actually run the full processing workflow
- **Script validation**: Shell script tests use `bash -n` for syntax checking without execution

## Future Enhancements

Potential additions:
- Integration tests that actually run the application end-to-end
- Tests that verify database migrations work
- Tests that simulate processing a sample batch file
- Performance benchmarks for startup time
