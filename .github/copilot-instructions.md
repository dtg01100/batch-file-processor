# Copilot Instructions

## Project Overview

Batch File Processor is a PyQt6 desktop application that processes EDI (Electronic Data Interchange) files through a configurable pipeline — validating, splitting, converting, and sending files via FTP, SMTP, or local filesystem.

## Documentation

**Main Documentation**: [`DOCUMENTATION.md`](../DOCUMENTATION.md) - Central index for all documentation

**Documentation Structure**:
- `docs/user-guide/` - User-facing guides (EDI formats, quick reference, troubleshooting)
- `docs/testing/` - Testing documentation (guides, best practices, corpus testing)
- `docs/migrations/` - Database migration guides
- `docs/architecture/` - Architecture and design documents
- `docs/api/` - API specifications and contracts
- `docs/design/` - Detailed design specifications
- `docs/archive/` - Historical documents and session summaries

**Key Files**:
- [`README.md`](../README.md) - Project overview and quick start
- [`DOCUMENTATION.md`](../DOCUMENTATION.md) - Complete documentation index
- [`AGENTS.md`](../AGENTS.md) - Agent-specific instructions
- [`docs/user-guide/EDI_FORMAT_GUIDE.md`](../docs/user-guide/EDI_FORMAT_GUIDE.md) - EDI format configuration
- [`docs/testing/TESTING.md`](../docs/testing/TESTING.md) - Testing guide
- [`docs/migrations/AUTOMATIC_MIGRATION_GUIDE.md`](../docs/migrations/AUTOMATIC_MIGRATION_GUIDE.md) - Migration guide

## Commands

```bash
# Run all tests (timeout configured in pytest.ini)
pytest

# Run a single test file
pytest tests/unit/test_foo.py

# Run a single test by name
pytest tests/unit/test_foo.py::test_bar_function

# Run tests by marker
pytest -m unit
pytest -m "integration and database"
pytest -x --timeout=30   # stop on first failure, short timeout for debugging

# Lint
ruff check .

# Format check / auto-fix
black --check .
black .
```

**Never run tests without a timeout.** A hanging test is a bug. If a test hangs, use `pytest -x --timeout=30` to identify it.

### Testing Philosophy

**Minimize Mocks and Fakes:** Keep mocks and fakes to an absolute minimum.
Prefer:
- Real implementations with isolated test fixtures (temp directories, test DBs)
- In-memory implementations over mock objects
- Integration tests with real components over mocked unit tests
- Test doubles only for: external services (FTP/SMTP), UI display servers, or
  truly expensive operations

**Qt/PyQt6 Testing Requirements:**
- ALWAYS use real Qt widgets in tests with the offscreen backend (QT_QPA_PLATFORM=offscreen)
- NEVER implement fake/mock Qt API classes (e.g., don't create FakeWidget, FakeEvent, etc.)
- Use `qtbot` fixture for widget interactions and signal testing
- For UI tests, inject real dependencies (DatabaseObj, MaintenanceFunctions) using temp_database fixture
- When testing dialogs, use real service objects, not fake implementations
- The offscreen backend handles rendering without a display - trust it

When mocks are necessary:
- Use them sparingly and only for clear boundaries (I/O, external services)
- Prefer `pytest` fixtures with real implementations over `unittest.mock`
- Document why a mock was necessary in comments

## Regression Testing Requirement

- When fixing a bug, add a regression test that covers the bug path.
- New code changes should include a test that would fail before the fix and pass after.
- Prefer small focused tests that assert behavior as narrowly as possible.

## Architecture

```
core/           Core utilities, EDI parser/splitter, database abstraction
dispatch/       Pipeline orchestration and file sending
backend/        Protocol clients (FTP, SMTP, local filesystem)
interface/      PyQt6 UI layer
batch_file_processor/  Package namespace (compatibility shim re-exporting root modules)
migrations/     Lightweight custom migration scripts (not Alembic)
schema.py       Centralized table definitions; call ensure_schema() at DB init
```

### Pipeline (dispatch/)

The pipeline is mandatory and runs sequentially in `dispatch/orchestrator.py`:

1. **Validator** – validates EDI format
2. **Splitter** – splits invoices/credits into individual files
3. **Converter** – converts to target format (CSV, Fintech, EStore, etc.)
4. **Tweaker** – post-conversion modifications

Each step lives in `dispatch/pipeline/` and implements a Protocol-based interface. Steps are optional; configure them via `DispatchConfig`. Entry point: `process_folder_with_pipeline()`.

### Plugin System (interface/plugins/)

Plugins provide format-specific UI configuration panels. `plugin_manager.py` auto-discovers classes inheriting `ConfigurationPlugin` by scanning the `interface.plugins` package with `pkgutil.iter_modules()`. Ten concrete plugins exist (CSV, Fintech, EStore, etc.). Instantiate with `PluginManager.instantiate_plugin()`.

### Database

- Schema defined in `schema.py` (`ensure_schema()` is idempotent)
- Migrations are plain Python functions in `migrations/` applied at DB init
- Migrations are idempotent (wrapped in try/except for schema changes)
- `core/database/` provides the database abstraction layer used by non-UI code
- `interface/database/` provides the UI-facing database layer

### UI Structure (interface/qt/)

- `app.py` – `QtBatchFileSenderApp`, the main window
- `window_controller.py` – builds the sidebar + folder list layout
- `dialogs/` – EditSettings, EditFolders, Maintenance, ResendDialog, etc.
- `widgets/` – FolderListWidget, SearchWidget, ExtraWidgets
- `services/qt_services.py` – UI and progress service implementations
- `theme.py` – centralized styling

## Key Conventions

- **Python 3.11+**, Black (line length 88), Ruff, isort (black profile)
- **SQL:** Parameterized queries only — never interpolate values with f-strings or `.format()`
- **Paths:** Use `os.path.join()` — never `"{}/{}".format()` or f-string path construction
- **File handles:** Always use `with` statements or `try/finally`; no bare `open()` left unclosed
- **Threading:** Never silently swallow exceptions in threads; capture and re-raise in the calling thread. Prefer `queue.Queue` or closure-captured dicts over module-level `global`
- **`batch_file_processor/` package:** Acts as a compatibility shim — it re-exports root-level modules via `sys.modules` injection to support `import batch_file_processor.utils` etc. Do not remove this without migrating all callers

## Test Markers

Tests use strict markers (`--strict-markers`). Decorate new tests appropriately:

| Marker | When to use |
|--------|-------------|
| `unit` | Fast, isolated, no I/O |
| `integration` | Real DB, filesystem, or real component interaction |
| `qt` | PyQt6 UI tests (requires `pytest-qt`) |
| `database` | Database-specific tests |
| `dispatch` | Pipeline/orchestration tests |
| `conversion` | File conversion tests |
| `backend` | FTP/SMTP/copy backend tests |
| `slow` | Tests taking >30 seconds |

## Test Fixtures

- `tests/conftest.py` – shared fixtures including a legacy v32 database and mock events
- `tests/fixtures/legacy_v32_folders.db` – real legacy production DB used for upgrade/compatibility tests
