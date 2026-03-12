# Copilot Instructions

## Project Overview

Batch File Processor is a PyQt6 desktop application that processes EDI (Electronic Data Interchange) files through a configurable pipeline — validating, splitting, converting, and sending files via FTP, SMTP, or local filesystem.

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
