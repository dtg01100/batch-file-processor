# Testing Strategy Design Document

**Generated:** 2026-02-02  
**Commit:** c2898be44  
**Branch:** cleanup-refactoring

## 1. Overview

This document describes the testing strategy, framework configuration, and patterns used in the batch file processor test suite.

## 2. Testing Framework

### 2.1 Technology Stack

| Component | Technology | Purpose |
|-----------|------------|---------|
| Test Runner | pytest | Test discovery and execution |
| Qt Testing | pytest-qt | PyQt6 widget testing |
| Coverage | pytest-cov | Code coverage reporting |
| Fixtures | pytest fixtures | Test setup and teardown |
| Mocking | unittest.mock | Dependency isolation |

### 2.2 Configuration Files

**pytest.ini:**
```ini
[pytest]
qt_api = pyqt6
testpaths = tests
python_files = test_*.py
python_classes = Test*
python_functions = test_*
```

**pyproject.toml test dependencies:**
```toml
[project.optional-dependencies]
test = [
    "pytest>=8.0.0",
    "pytest-cov>=4.1.0",
    "pytest-qt>=4.2.0",
]
```

## 3. Test Organization

### 3.1 Directory Structure

```
tests/
├── conftest.py                    # Shared fixtures and markers
├── test_smoke.py                  # Utility smoke tests
├── test_app_smoke.py              # Application startup tests (31 tests)
│
├── unit/                          # Unit tests
│   ├── test_utils.py              # Utils module tests
│   ├── test_utils_full.py         # Comprehensive utils tests
│   ├── test_convert_base.py       # Converter base class tests
│   ├── test_converter_plugins.py  # Converter plugin tests
│   ├── test_send_base.py          # Send backend base tests
│   ├── test_send_backends.py      # Backend implementation tests
│   ├── test_backends.py           # Additional backend tests
│   ├── test_plugin_config.py      # Plugin configuration tests
│   ├── test_plugin_config_full.py # Comprehensive plugin tests
│   ├── test_dispatch_*.py         # Dispatch layer tests
│   ├── test_interface_*.py        # Interface layer tests
│   ├── test_edi_*.py              # EDI processing tests
│   └── test_backup_increment.py   # Backup tests
│
├── integration/                   # Integration tests
│   ├── database_schema_versions.py  # DB version utilities
│   ├── test_database_migrations.py  # Migration tests
│   ├── test_automatic_migrations.py # Auto-migration tests
│   └── test_interface_integration.py # Interface integration
│
├── operations/                    # Operations layer tests
│   ├── test_folder_operations.py  # Folder add/edit/delete
│   └── test_maintenance_operations.py # Maintenance ops
│
├── ui/                            # UI component tests
│   ├── test_application_controller.py # Controller tests
│   ├── test_widgets.py            # Widget tests (mock)
│   ├── test_widgets_qt.py         # Widget tests (Qt)
│   ├── test_dialogs.py            # Dialog tests (mock)
│   ├── test_dialogs_qt.py         # Dialog tests (Qt)
│   ├── test_interface_ui.py       # Interface UI tests
│   └── test_plugin_ui_generator.py # Plugin UI generation
│
└── convert_backends/              # Converter parity tests
    ├── conftest.py                # Converter fixtures
    ├── test_parity_verification.py # Output baseline comparison
    ├── test_backends_smoke.py     # Backend smoke tests
    ├── baselines/                 # Expected output files
    │   └── <backend>/             # Per-backend baselines
    └── data/                      # Test input data
        ├── EDI_FORMAT_SPECIFICATION.md
        └── OUTPUT_FORMAT_SPECIFICATION.md
```

### 3.2 Test Count

| Category | Count | Location |
|----------|-------|----------|
| Smoke Tests | ~50 | `test_smoke.py`, `test_app_smoke.py` |
| Unit Tests | ~600 | `unit/` |
| Integration Tests | ~100 | `integration/` |
| Operations Tests | ~200 | `operations/` |
| UI Tests | ~150 | `ui/` |
| Converter Tests | ~250 | `convert_backends/` |
| **Total** | **1600+** | - |

## 4. Test Markers

### 4.1 Registered Markers

```python
# conftest.py
def pytest_configure(config):
    config.addinivalue_line("markers", "unit: mark test as a unit test")
    config.addinivalue_line("markers", "integration: mark test as an integration test")
    config.addinivalue_line("markers", "slow: mark test as slow running")
    config.addinivalue_line("markers", "smoke: mark test as smoke test (quick production validation)")
    config.addinivalue_line("markers", "convert_backend: mark test as convert backend regression test")
    config.addinivalue_line("markers", "convert_smoke: mark test as quick convert backend smoke test")
    config.addinivalue_line("markers", "convert_parameters: mark test as convert parameter variation test")
    config.addinivalue_line("markers", "convert_integration: mark test as convert integration test")
    config.addinivalue_line("markers", "qt: mark test as requiring PyQt6/Qt")
    config.addinivalue_line("markers", "parity: mark test as parity verification test")
    config.addinivalue_line("markers", "db: mark test as database-related test")
```

### 4.2 Running by Marker

```bash
# Quick smoke tests (~0.2s)
pytest -m smoke

# Unit tests only
pytest -m unit

# Integration tests only
pytest -m integration

# Qt tests only
pytest -m qt

# Converter backend tests
pytest -m convert_backend

# Database tests
pytest -m db
```

## 5. Fixtures

### 5.1 Session Fixtures

```python
@pytest.fixture(scope="session")
def qapp():
    """Create QApplication for the test session (singleton)."""
    from PyQt6.QtWidgets import QApplication
    import sys
    
    app = QApplication.instance()
    if app is None:
        app = QApplication(sys.argv)
    yield app
```

### 5.2 Function Fixtures

```python
@pytest.fixture
def temp_dir():
    """Create a temporary directory for test files."""
    test_dir = tempfile.mkdtemp()
    yield test_dir
    shutil.rmtree(test_dir, ignore_errors=True)

@pytest.fixture
def sample_edi_file(temp_dir):
    """Create a sample EDI file for testing."""
    file_path = os.path.join(temp_dir, "test_sample.edi")
    with open(file_path, "w") as f:
        f.write(edi_content)
    return file_path

@pytest.fixture
def mock_db_manager():
    """Create mock database manager for testing."""
    from unittest.mock import Mock
    db = Mock()
    db.folders_table = Mock()
    db.settings = Mock()
    # ... configure return values
    return db

@pytest.fixture
def qtbot(qapp, request):
    """Provide QtBot for widget testing with fallback."""
    try:
        from pytestqt.qtbot import QtBot
        return QtBot(request)
    except ImportError:
        from unittest.mock import Mock
        return Mock()
```

### 5.3 Converter Fixtures

```python
# tests/convert_backends/conftest.py
@pytest.fixture
def corpus_file(request):
    """Load corpus file, skip if unavailable."""
    corpus_path = Path("alledi") / request.param
    if not corpus_path.exists():
        pytest.skip("corpus not available")
    return corpus_path
```

## 6. Test Patterns

### 6.1 Unit Test Pattern

```python
class TestModuleName:
    """Tests for module_name module."""
    
    def test_function_basic(self):
        """Test basic functionality."""
        result = function_under_test("input")
        assert result == "expected"
    
    def test_function_edge_case(self):
        """Test edge case handling."""
        result = function_under_test("")
        assert result is None
    
    def test_function_error_handling(self):
        """Test error handling."""
        with pytest.raises(ValueError):
            function_under_test(None)
```

### 6.2 Parametrized Test Pattern

```python
@pytest.mark.parametrize("input_value,expected", [
    ("valid_input", "expected_output"),
    ("edge_case", "edge_result"),
    ("empty", None),
], ids=["valid", "edge", "empty"])
def test_function_parametrized(input_value, expected):
    """Test function with multiple inputs."""
    result = function_under_test(input_value)
    assert result == expected
```

### 6.3 Mock-Based Test Pattern

```python
def test_with_mocked_dependencies(mock_db_manager):
    """Test with mocked dependencies."""
    # Configure mock
    mock_db_manager.folders_table.find.return_value = [
        {"id": 1, "alias": "Test"}
    ]
    
    # Call function under test
    result = function_under_test(mock_db_manager)
    
    # Verify mock calls
    mock_db_manager.folders_table.find.assert_called_once()
    assert result == expected
```

### 6.4 Qt Widget Test Pattern

```python
@pytest.mark.qt
def test_widget_creation(qapp, qtbot):
    """Test widget creation and basic functionality."""
    widget = MyWidget()
    qtbot.addWidget(widget)
    
    assert widget.isVisible() is False
    widget.show()
    assert widget.isVisible() is True

@pytest.mark.qt
def test_signal_emission(qapp, qtbot):
    """Test signal emission."""
    widget = MyWidget()
    qtbot.addWidget(widget)
    
    with qtbot.waitSignal(widget.my_signal, timeout=1000):
        widget.trigger_signal()
```

### 6.5 Database Migration Test Pattern

```python
def test_migration_v38_to_v39(temp_dir):
    """Test database migration from v38 to v39."""
    # Create database at starting version
    db = generate_database_at_version(38, temp_dir)
    
    # Apply migration
    from folders_database_migrator import upgrade_database
    upgrade_database(db, temp_dir, "linux", target_version=39)
    
    # Verify migration result
    version = db["version"].find_one(id=1)
    assert version["version"] == "39"
    
    # Verify new columns exist
    folders = db["folders"].find_one()
    assert "edi_format" in folders
```

### 6.6 Parity Verification Pattern

```python
@pytest.mark.parity
def test_converter_parity(converter_id, test_input, baseline_path):
    """Verify converter output matches baseline."""
    # Run converter
    output = run_converter(converter_id, test_input)
    
    # Compare to baseline
    with open(baseline_path, "r") as f:
        expected = f.read()
    
    assert output == expected, f"Output differs from baseline for {converter_id}"
```

## 7. Running Tests

### 7.1 Quick Commands

```bash
# Run all tests
./run_tests.sh

# Run with verbose output
pytest -v

# Run with coverage
pytest --cov=interface --cov-report=html

# Run specific test file
pytest tests/unit/test_utils.py -v

# Run specific test class
pytest tests/unit/test_utils.py::TestProcessUpc -v

# Run specific test
pytest tests/unit/test_utils.py::TestProcessUpc::test_upca_12_digit -v

# Run last failed
pytest --lf

# Run and stop on first failure
pytest -x
```

### 7.2 Headless Qt Testing

```bash
# Using offscreen platform
QT_QPA_PLATFORM=offscreen pytest tests/ui/ -v

# Using xvfb
xvfb-run -a pytest tests/ui/ -v
```

### 7.3 Coverage Reports

```bash
# Terminal coverage
pytest --cov=interface --cov-report=term-missing

# HTML coverage
pytest --cov=interface --cov-report=html
# Open htmlcov/index.html

# XML coverage (for CI)
pytest --cov=interface --cov-report=xml
```

## 8. Test Data

### 8.1 Sample EDI Content

```python
# Standard EDI test content
edi_content = """UNA:*'~
UNB+UNOC:3+SENDER+RECEIVER+210101:1200+1'
UNH+1+ORDERS:D:96A:UN'
BGM+220+ORDER001+9'
DTM+137:20210101:102'
NAD+BY+BuyerCode'
NAD+SU+SupplierCode'
LIN+1++ProductCode:EN'
QTY+1:100'
UNT+9+1'
UNZ+1+1'"""
```

### 8.2 Sample Folder Data

```python
sample_folders = [
    {"id": 1, "alias": "Test Folder 1", "folder_name": "/test/folder1", "folder_is_active": "True"},
    {"id": 2, "alias": "Test Folder 2", "folder_name": "/test/folder2", "folder_is_active": "False"},
]
```

### 8.3 Converter Baselines

```
tests/convert_backends/baselines/
├── csv/
│   ├── basic_output.csv
│   └── metadata.json
├── scannerware/
│   ├── basic_output.txt
│   └── metadata.json
└── fintech/
    ├── basic_output.csv
    └── metadata.json
```

## 9. CI/CD Integration

### 9.1 GitHub Actions Example

```yaml
name: Tests
on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - uses: actions/setup-python@v4
        with:
          python-version: '3.11'
      - run: pip install pytest pytest-cov pytest-qt
      - run: xvfb-run -a pytest --cov=interface --cov-report=xml
      - uses: codecov/codecov-action@v3
```

### 9.2 Local Automation

```bash
# run_tests.sh handles:
# 1. Virtual environment activation
# 2. Headless Qt setup (xvfb fallback)
# 3. Coverage reporting
./run_tests.sh
```

## 10. Test Execution Times

| Test Category | Approximate Time |
|---------------|------------------|
| Smoke Tests | ~0.2s |
| Unit Tests | ~15s |
| Integration Tests | ~7s |
| Operations Tests | ~5s |
| UI Tests | ~10s |
| Converter Tests | ~30s |
| **Full Suite** | **~60-90s** |

## 11. Best Practices

### 11.1 Test Naming

- Test files: `test_<module_name>.py`
- Test classes: `Test<ClassName>`
- Test methods: `test_<functionality>_<condition>`

### 11.2 Test Independence

- Each test should be independent and isolated
- Use fixtures for setup/teardown
- Clean up temporary files and resources
- Don't rely on test execution order

### 11.3 Mock External Dependencies

- Database connections
- File system operations (when appropriate)
- Network operations
- External services

### 11.4 Assertions

```python
# Prefer specific assertions
assert result == expected
assert isinstance(obj, MyClass)
assert "substring" in text
assert len(items) == 5

# Use pytest.raises for exceptions
with pytest.raises(ValueError, match="specific message"):
    function_that_raises()
```

### 11.5 Documentation

- Docstrings for test classes explaining scope
- Docstrings for non-obvious test methods
- Comments for complex test setup

## 12. Troubleshooting

### 12.1 Import Errors

```bash
# Ensure running from project root
cd /var/mnt/Disk2/projects/batch-file-processor
pytest tests/
```

### 12.2 Qt Test Failures

```bash
# Check Qt platform availability
QT_DEBUG_PLUGINS=1 pytest tests/ui/ -v

# Force offscreen
QT_QPA_PLATFORM=offscreen pytest tests/ui/ -v
```

### 12.3 Fixture Issues

```bash
# Debug fixture loading
pytest --fixtures tests/

# Show fixture setup/teardown
pytest -v --setup-show tests/
```

## 13. Future Improvements

1. **Parallel Execution:** Add pytest-xdist for parallel test execution
2. **Property-Based Testing:** Add hypothesis for property-based tests
3. **Performance Benchmarks:** Add pytest-benchmark for critical path timing
4. **Mutation Testing:** Add mutmut for mutation testing coverage
5. **Visual Regression:** Add screenshot comparison for UI tests
