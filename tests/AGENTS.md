# TESTS (1346+ Tests)

Test organization: unit, integration, operations, ui, convert_backends. Pytest + pytest-qt.

## STRUCTURE

```
tests/
├── unit/              # Unit tests (utils, dispatch, converters, backends)
├── integration/       # DB migrations, schema, DatabaseManager
├── operations/        # Folder ops, maintenance ops
├── ui/                # PyQt5 UI tests (dialogs, widgets)
├── convert_backends/  # Converter parity/baseline tests (see convert_backends/AGENTS.md)
├── conftest.py        # Shared fixtures (qapp, qtbot, temp_dir, mock_db_manager)
├── test_smoke.py      # Utility smoke tests
└── test_app_smoke.py  # Application startup tests (31 tests)
```

## WHERE TO LOOK

| Task | Location | Notes |
|------|----------|-------|
| Shared fixtures | `conftest.py` | qapp, qtbot (fallback), temp_dir, sample files |
| DB test helpers | `integration/database_schema_versions.py` | generate_database_at_version, DatabaseConnectionManager |
| Migration tests | `integration/test_database_migrations.py` | All versions v5→v39 |
| Folder operations | `operations/test_folder_operations.py` | add/remove/toggle/update |
| Maintenance ops | `operations/test_maintenance_operations.py` | clear_processed, mark_processed |
| UI dialogs | `ui/test_dialogs_qt.py`, `ui/test_dialogs.py` | PyQt5 dialog tests |
| Converter tests | `convert_backends/` | Parity, baselines, smoke tests |

## CONVENTIONS

**Fixtures** (conftest.py):
- `qapp` (session): Single QApplication for all Qt tests
- `qtbot(qapp)`: pytest-qt QtBot or Mock fallback if pytest-qt missing
- `temp_dir`: Temporary directory, cleaned up after test
- `sample_file`, `sample_csv_file`, `sample_edi_file`: On-disk test files
- `mock_db_manager`: unittest.mock DB manager for tests without real DB

**Markers** (registered in conftest.py):
- `smoke`, `unit`, `integration`, `slow`, `qt`
- `convert_backend`, `convert_smoke`, `convert_parameters`, `convert_integration`, `parity`

**Qt tests**: Require `QT_QPA_PLATFORM=offscreen` or `xvfb-run -a pytest`

**Corpus fixtures** (convert_backends/conftest.py):
- Many fixtures skip with `pytest.skip()` if corpus files missing (`alledi/` not committed)
- Pattern: `if not corpus_file.exists(): pytest.skip("corpus not available")`

## PATTERNS

**Parametrization**: Heavy use of `@pytest.mark.parametrize` with `ids=` for readability

**Standalone execution**: Many test files include `pytest.main([__file__])` at bottom for direct execution

**DB tests**: Use `DatabaseConnectionManager` context manager (enforces PRAGMA foreign_keys, unique connection names)

**Migration tests**: `generate_database_at_version(version)` creates v5 baseline then migrates to target version using real migrator

## MOCKING CONVENTIONS

**Use `spec=` for all `MagicMock()` calls** — This enforces the mock to only allow attributes that exist on the specified class/protocol. Without spec, MagicMock auto-creates any attribute, hiding typos and making tests pass for wrong reasons.

```python
# ✗ Wrong - allows any attribute
mock_handler = MagicMock()

# ✓ Correct - only allows real attributes
mock_handler = MagicMock(spec=ErrorHandler)
mock_db = MagicMock(spec=DatabaseManager)
```

**Use `MockFactories` from `conftest.py`** for reusable spec'd mocks:

```python
from tests.conftest import MockFactories

mock_factories = MockFactories()

# In tests
ftp_service = mock_factories.ftp_service()  # spec'd to FTPSyncService
email_service = mock_factories.email_service()  # spec'd to SMTPSyncService
```

**Use real values for datetime objects** — Avoid `MagicMock(spec=datetime)` for datetime values. Use `datetime(2025, 1, 1)` instead.

**Callback mocks** — Bare `MagicMock()` is acceptable for callbacks (e.g., `on_complete=MagicMock()`) since the callback signature is unknown and there's no protocol to spec against.

**When `spec=` catches bugs** — If you get `AttributeError: Mock object has no attribute 'xyz'`, that mock was never properly configured in the real code. This is a test catching a real bug, not a test being too strict.
