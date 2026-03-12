# Agent Instructions

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
