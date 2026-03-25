# Agent Instructions

## Documentation

**IMPORTANT**: All permanent documentation is organized under `docs/`. Refer to [`DOCUMENTATION.md`](DOCUMENTATION.md) for the complete index.

- **User Guides**: `docs/user-guide/` (EDI formats, quick reference, troubleshooting)
- **Testing**: `docs/testing/` (test guides, best practices, corpus testing)
- **Migrations**: `docs/migrations/` (database migration guides)
- **Architecture**: `docs/architecture/` (design documents)
- **Archive**: `docs/archive/` (historical/session files - do not create new files here)

**When creating documentation**:
1. Prefer updating existing docs over creating new files
2. Place new permanent docs in the appropriate `docs/` subdirectory
3. Use kebab-case filenames (e.g., `edi-format-guide.md`)
4. Session artifacts (summaries, reports, plans) go in `docs/archive/` or session memory

## Build/Lint/Test Commands

### Running Tests

**Always run the test suite with a per-test timeout.** `pytest.ini` configures `timeout = 120` and `timeout_method = signal`.

```bash
# Standard test command (full suite with timeout)
pytest

# Run a single test file
pytest tests/unit/test_foo.py

# Run a single test by name
pytest tests/unit/test_foo.py::test_bar_function

# Run tests by marker
pytest -m unit
pytest -m "integration and database"
pytest -m qt

# Debugging: stop on first failure, short timeout
pytest -x --timeout=30

# Run with verbose output
pytest -v

# Run tests by file path pattern
pytest tests/unit/
```

**Never run the full suite without a timeout.** A hanging test is a bug that must be diagnosed and fixed — do not work around it by removing or skipping the test.

### Linting and Formatting

```bash
# Check linting
ruff check .

# Check formatting
black --check .

# Auto-fix formatting
black .

# Auto-fix import ordering
isort .
```

### Development Setup

```bash
# Install dependencies
pip install -r requirements.txt

# Install in editable mode with dev dependencies
pip install -e .[dev]
```

## Project Layout

| Directory | Purpose |
|-----------|---------|
| `core/` | Core utilities, database abstraction, EDI logic |
| `dispatch/` | Orchestration, pipeline, file utilities, send manager |
| `interface/` | PyQt6 UI layer |
| `backend/` | FTP, SMTP, and copy backend clients |
| `tests/` | All tests (unit, integration, e2e) |
| `migrations/` | Lightweight custom migration scripts (not Alembic) |

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
| `edi` | EDI file processing tests |
| `slow` | Tests taking >30 seconds |
| `smoke` | Quick smoke tests to verify basic functionality |

## Testing Philosophy

**Minimize Mocks and Fakes:** Keep mocks and fakes to an absolute minimum.
Prefer:
- Real implementations with isolated test fixtures (temp directories, test DBs)
- In-memory implementations over mock objects
- Integration tests with real components over mocked unit tests
- Test doubles only for: external services (FTP/SMTP), UI display servers, or truly expensive operations

**Qt/PyQt6 Testing Requirements:**
- ALWAYS use real Qt widgets in tests with the offscreen backend (QT_QPA_PLATFORM=offscreen)
- NEVER implement fake/mock Qt API classes (e.g., don't create FakeWidget, FakeEvent, etc.)
- Use `qtbot` fixture for widget interactions and signal testing
- For UI tests, inject real dependencies (DatabaseObj, MaintenanceFunctions) using temp_database fixture
- When testing dialogs, use real service objects, not fake implementations
- The offscreen backend handles rendering without a display - trust it

**If a test hangs:**
1. Identify the hanging test by running with `-x` and a short timeout: `pytest -x --timeout=30`
2. The test that times out first is the offending one.
3. Investigate *why* it hangs (blocked I/O, deadlock, infinite loop, missing mock for a network call) and fix the root cause.
4. Do not increase the global timeout as a workaround.

## Code Style Guidelines

### General
- **Python 3.11+**
- Line length: **88 characters** (black default)
- Format with **black**, lint with **ruff**, sort imports with **isort** (black profile)

### Imports
- Use absolute imports (e.g., `from core.utils import ...`)
- Use `noqa: F401` comment to suppress unused import warnings when re-exporting
- Sort imports according to isort with black profile

### Naming Conventions
- **Modules**: kebab-case (e.g., `edi_parser.py`)
- **Classes**: PascalCase (e.g., `EdiParser`, `FolderConfig`)
- **Functions/methods**: snake_case (e.g., `parse_edi_file`, `get_folder_by_id`)
- **Constants**: SCREAMING_SNAKE_CASE (e.g., `MAX_RETRY_COUNT`, `DEFAULT_TIMEOUT`)
- **Variables**: snake_case (e.g., `file_path`, `is_enabled`)

### Type Annotations
- Use type hints for function parameters and return values
- Use `typing.Optional[T]` or `T | None` for nullable types
- Use `typing.List[T]`, `typing.Dict[K, V]`, etc. for collections

### SQL
- **Always use parameterized queries** — never interpolate values with f-strings or `.format()`
- Use the database abstraction layer's parameterized query methods

### Paths
- **Always use `os.path.join()`** for path construction
- Never use `"{}/{}".format()` or f-string path construction

### File Handling
- **Always use `with` statements** or `try/finally` for file handles
- No bare `open()` left unclosed on exception paths

### Error Handling
- Never silently swallow thread exceptions — capture and re-raise in the calling thread
- Use custom exception classes from `core.exceptions` when appropriate
- Prefer local variables over module-level `global` for inter-thread communication (use closure-captured dicts or `queue.Queue`)

### Threading
- Thread exceptions must never be silently swallowed
- Capture exceptions in threads and re-raise in the calling thread
- Prefer `queue.Queue` or closure-captured dicts over module-level `global` for inter-thread communication

## Convert Backend Selection

**Philosophy**: Fail-fast is preferred over silent fallback. An incorrect format should cause the run to fail rather than send in the wrong format or pass through unchanged.

### Current Protections
- **Whitelist validation**: `dispatch/pipeline/converter.py:391` checks format against `SUPPORTED_FORMATS` list
- **Module interface check**: Verifies `edi_convert` function exists after loading module
- **No-output detection**: `orchestrator.py:1063-1068` raises error if conversion requested but no output produced

### Agent Guidelines
- When adding new converters, register a corresponding `ConfigurationPlugin` (not just the module)
- Never add runtime "smart" fallback logic to route to a different format
- Unknown/empty `convert_to_format` values should result in no conversion, not a fallback to "csv"
- Database migrations should validate `convert_to_format` values against the whitelist

### Where to Learn More
See `docs/architecture/backend-selection-hardening.md` for detailed guidance including edge cases and testing recommendations.

## Markdown Organization

- Prefer updating existing documentation over creating a new Markdown file.
- Keep repository Markdown organized: do not add AI-generated reports, plans, audits, or summaries to the repository root unless the user explicitly asks for that location.
- Place new permanent Markdown documentation under `docs/` in the most relevant subdirectory.
- Keep ephemeral agent artifacts in the session workspace, not the repository.
- Use concise, descriptive kebab-case filenames.
