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

## Running Tests

Always run the test suite with a per-test timeout. `pytest.ini` configures
`timeout = 60` and `timeout_method = signal`, so the timeout is active whenever
`pytest-timeout` is installed (it is listed in `requirements.txt`).

**Standard test command:**
```
pytest
```

**With an explicit timeout override (use when debugging or running a subset):**
```
pytest --timeout=60
```

**Never run the full suite without a timeout.** A hanging test is a bug that
must be diagnosed and fixed — do not work around it by removing or skipping the
test.

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

### If a test hangs
1. Identify the hanging test by running with `-x` and a short timeout:
   ```
   pytest -x --timeout=30
   ```
2. The test that times out first is the offending one.
3. Investigate *why* it hangs (blocked I/O, deadlock, infinite loop, missing
   mock for a network call) and fix the root cause.
4. Do not increase the global timeout as a workaround.

## Project Layout

| Directory | Purpose |
|-----------|---------|
| `core/` | Core utilities, database abstraction, EDI logic |
| `dispatch/` | Orchestration, pipeline, file utilities, send manager |
| `interface/` | PyQt6 UI layer |
| `backend/` | FTP, SMTP, and copy backend clients |
| `tests/` | All tests (unit, integration, e2e) |

## Markdown Organization

- Prefer updating existing documentation over creating a new Markdown file.
- Keep repository Markdown organized: do not add AI-generated reports, plans,
  audits, or summaries to the repository root unless the user explicitly asks
  for that location.
- Place new permanent Markdown documentation under `docs/` in the most relevant
  subdirectory; create a focused subdirectory when needed instead of scattering
  files across the repo.
- Keep ephemeral agent artifacts in the session workspace, not the repository.
- Use concise, descriptive kebab-case filenames that reflect the topic and
  avoid duplicate "final", "summary", or date-stamped variants unless the user
  requests them.

## Code Conventions

- Python 3.11+, formatted with **black** (line length 88) and linted with **ruff**.
- Use parameterized queries for all SQL — never interpolate values into query
  strings with f-strings or `.format()`.
- Use `os.path.join()` consistently for path construction (never `"{}/{}".format()`).
- File handles opened with bare `open()` must be wrapped in `try/finally` or a
  `with` statement to prevent leaks on exception.
- Thread exceptions must never be silently swallowed; capture them and re-raise
  in the calling thread.
- Prefer local variables over module-level `global` for inter-thread
  communication (use a closure-captured dict or `queue.Queue`).

## Linting and Formatting

```
ruff check .
black --check .
```

Fix formatting:
```
black .
```
