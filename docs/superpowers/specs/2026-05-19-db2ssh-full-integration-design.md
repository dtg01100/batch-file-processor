# DB2 SSH Adapter Full Integration

**Date:** 2026-05-19
**Status:** Approved design

## Problem

The `adapters/db2ssh/` adapter is functionally complete and in production use, but carries "future/stub" documentation, lacks dedicated unit tests, and has minor code quality gaps (missing context manager, untyped attributes, bare except clause, incomplete exports).

## Scope of Work

### 1. Test Coverage — 3 new test files + expansion

**1a. `tests/unit/adapters/db2ssh/test_vendored_driver.py`**

Tests for the vendored PEP 249 driver (`adapters/db2ssh/__init__.py`):
- `_parse_db2_output()` — columnar output parsing, edge cases (empty, malformed)
- `_parse_error()` — error message extraction
- `_qmark_to_positional()` — parameter substitution correctness
- `Cursor` class — `execute()`, `fetchone()`, `fetchmany()`, `fetchall()`, `close()`, iterator
- `Connection` class — `open()`, `close()`, `commit()`, `rollback()`, context manager
- `connect()` factory — argument forwarding

**1b. `tests/unit/adapters/db2ssh/test_db2ssh_connection.py`**

Tests for the `DatabaseConnectionProtocol` adapter:
- `DB2SSHConnectionConfig` — defaults, custom values
- `_connect()` — success path (verifies logging), failure path (`ConnectionError`)
- `execute()` — with params, without params, no-result queries
- `execute()` — error propagation
- `close()` — connection lifecycle
- Lazy initialization — connection created on first `execute()`, not on construction

**1c. `tests/unit/dispatch/services/test_database_connector.py`**

Tests for the `DatabaseConnector` service:
- `init_connection()` — valid settings, missing keys, missing both password and key
- `close()` — successful close, double-close safety
- `is_initialized` — transitions correctly
- Double-init guard — second `init_connection()` is no-op

**1d. Expand `tests/unit/core/database/test_query_runner.py`**

- Verify `create_query_runner_from_settings` is exported from `core.database`

### 2. Code Polish — 3 files changed

**2a. `adapters/db2ssh/connection.py`**

- Add `__enter__`/`__exit__` to `DB2SSHConnection` for context manager support
- Add threading lock to `_ensure_connection()` for thread safety

**2b. `dispatch/services/database_connector.py`**

- Declare `ssh_key_filename` and `as400_password` as typed instance attributes in `__init__`
- Replace bare `except AttributeError` with targeted non-fatal logging pattern per AGENTS.md conventions

**2c. `core/database/__init__.py`**

- Add `create_query_runner_from_settings` to imports and `__all__`

### 3. Documentation Updates — 3 files changed

**3a. `AGENTS.md`** (line 91)
- `adapters/db2ssh/ (future)` → `adapters/db2ssh/ (production)`

**3b. `docs/design/COMPONENT_MAP.md`** (Section 6.2)
- "DB2 SSH Adapter (Future)" → "DB2 SSH Adapter"
- Remove "(Future)" from section references

**3c. `docs/design/DESIGN_CORRECTIONS.md`**
- Remove "future stub" language referencing `DB2SSHConnectionConfig`

## Architecture

No architectural changes. The existing layered architecture remains:

```
EditSettingsDialog → Settings Table → DatabaseConnector
    → create_query_runner_from_settings → create_query_runner
    → DB2SSHConnection (DatabaseConnectionProtocol)
    → vendored db2ssh driver (PEP 249) → paramiko → SSH → IBM i
```

Changes are additive (tests, docs, minor code improvements) — no behavioral changes to production code paths.

## Testing Strategy

| Layer | Approach | Coverage |
|-------|----------|----------|
| Vendored driver | Mock SSH calls, test parsing/output logic directly | Internal parsing, cursor, connection |
| DB2SSHConnection | Mock `db2ssh_connect()`, verify protocol compliance | execute/close/logging/error |
| DatabaseConnector | Mock `create_query_runner_from_settings` | init/close/validation |
| Factory functions | Already tested, add export check | One assertion |

All tests: `pytest -m unit` compatible, no Qt dependency.
