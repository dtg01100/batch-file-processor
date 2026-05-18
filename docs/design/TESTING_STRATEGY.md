# Testing Strategy

**Version:** 1.0  
**Date:** 2026-05-18  
**Status:** DRAFT

---

## 1. Overview

The project uses pytest for testing with markers for parallel execution control.

## 2. Test Markers

| Marker | Purpose | Execution |
|--------|---------|-----------|
| `unit` | Fast unit tests | `pytest -m unit -n auto` |
| `integration` | Database/integration tests | `pytest -m integration -n auto` |
| `qt` | PyQt5 UI tests | `pytest -m qt -n0` |
| `conversion` | Converter parity tests | `pytest -m conversion -n auto` |
| `backend` | Backend tests | `pytest -m backend -n auto` |
| `fast` | Tests <5 seconds | `pytest -m "unit and fast" -n auto` |

## 3. Test Organization

```
tests/
├── unit/              # Unit tests (~4000+)
│   ├── dispatch_tests/    # Dispatch layer tests
│   ├── backend/          # Backend tests
│   ├── test_plugins/     # Plugin tests
│   └── ...
├── integration/      # Integration tests (~500+)
│   ├── test_all_processing_flows.py
│   ├── test_folder_management.py
│   └── ...
├── qt/               # GUI tests (~200+)
│   ├── test_edit_folders_dialog.py
│   ├── test_qt_app.py
│   └── ...
├── convert_backends/ # Converter output tests
└── fixtures/         # Test data
```

## 4. Test Patterns

### 4.1 Unit Testing

```python
def test_edi_validator():
    validator = EDIValidator()
    result = validator.validate("test.edi")
    assert result.is_valid
```

### 4.2 Mocking Patterns

```python
def test_file_processor(monkeypatch):
    mock_fs = MagicMock(spec=FileSystemInterface)
    processor = FileProcessor(file_system=mock_fs)
    # Test with mocked dependencies
```

### 4.3 Integration Testing

```python
@pytest.mark.integration
def test_folder_roundtrip(tmp_path):
    db_path = tmp_path / "test.db"
    init_database(db_path)
    manager = DatabaseManager(db_path)
    # Test database operations
```

### 4.4 Qt Testing

```python
@pytest.mark.qt
def test_edit_dialog(qtbot):
    dialog = EditFoldersDialog()
    qtbot.addWidget(dialog)
    # Test UI interactions
```

## 5. Running Tests

```bash
# All tests (excludes Qt, parallel)
make test-parallel

# Qt tests only (single-threaded!)
make test-qt

# Unit tests
make test-unit

# Specific file
make test-file FILE=tests/unit/dispatch/test_orchestrator.py

# Fail-fast
make test-failfast
```

## 6. Test Fixtures

```python
# tests/conftest.py
@pytest.fixture
def sample_edi():
    return """ISA*00*...*"""

@pytest.fixture
def temp_db(tmp_path):
    db_path = tmp_path / "test.db"
    init_database(db_path)
    return db_path
```

## 7. Coverage Goals

| Layer | Target | Key Files |
|-------|--------|-----------|
| dispatch/ | 90%+ | orchestrator, pipeline, services |
| backend/ | 85%+ | All backend modules |
| interface/ | 80%+ | Operations, form generation |
| core/ | 85%+ | EDI processing, utilities |

## 8. Related Documents

- [SYSTEM_OVERVIEW.md](SYSTEM_OVERVIEW.md) - Architecture
- `tests/AGENTS.md` - Test suite details
- `docs/testing/` - Testing guides
