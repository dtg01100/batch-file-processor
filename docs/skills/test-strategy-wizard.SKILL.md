# test-strategy-wizard Skill

This is a workspace-scoped helper skill for Batch File Processor to drive consistent, high-quality test development by selecting the right markers, fixtures, and structure based on code changes.

## Purpose

- Teach an AI assistant to choose optimal test markers (`unit`, `integration`, `qt`, `dispatch`, `backend`, `conversion`, `database`) based on code scope.
- Select appropriate fixtures (`tmp_path`, `temp_database`, `qtbot`, etc.) based on dependencies.
- Enforce repository conventions (pytest, `--timeout=30`, real Qt widgets via offscreen backend).

## When to use

- Adding new features or fixing bugs and unsure which test markers to use
- Choosing between unit, integration, or Qt tests for a code change
- Determining which fixtures are appropriate for the test scenario
- Structuring a new test file for unfamiliar code areas

## Input (prompt for this skill)

- Target code area: `interface/` (Qt UI), `dispatch/` (pipeline), `backend/` (FTP/SMTP/copy), `core/` (utilities/EDI), or `migrations/` (DB schema)
- Change type: `bugfix`, `new-feature`, `refactor`
- External dependencies: `database`, `filesystem`, `network` (FTP/SMTP), `ui`
- Scope: `single-function`, `module`, `cross-component`

## Decision Tree

### Step 1: Choose Primary Marker(s)

| Code Area | Primary Marker | Additional Markers |
|-----------|---------------|-------------------|
| `dispatch/pipeline/` | `dispatch` | `conversion` if converter involved |
| `dispatch/converters/` | `dispatch` + `conversion` | — |
| `dispatch/orchestrator.py` | `dispatch` | `integration` if full pipeline tested |
| `interface/qt/` | `qt` | `integration` for DB-backed dialogs |
| `interface/plugins/` | `qt` | — |
| `backend/` | `backend` | `integration` for real protocol tests |
| `core/` | `unit` | `integration` if DB or file I/O required |
| `migrations/` | `database` | — |
| `schema.py` | `database` | `integration` for schema apply/verify |

### Step 2: Choose Fixtures

| Fixture | Use When |
|---------|----------|
| `tmp_path` | File creation/deletion tests; no persistence needed |
| `temp_database` | DB queries, schema changes, CRUD operations |
| `qtbot` | Qt widget interactions, signals, dialog testing |
| `mock_events` | Event-dependent logic in dispatch |
| DatabaseObj (from conftest) | UI-database integration (EditSettings, Maintenance) |

**Rule**: Prefer real implementations over mocks. Use mocks only for:
- External services (FTP/SMTP servers)
- UI display servers
- Truly expensive operations

### Step 3: Structure the Test

#### Bugfix Test Template
```python
# filepath: tests/<marker>/test_<module>_<issue>.py
@pytest.mark.<marker>
def test_<function>_<bug_description>(...):
    """Regression test: <bug description>."""
    # Arrange: set up inputs that trigger the bug
    # Act: call the function
    # Assert: verify bug is fixed (behavior matches expected)
```

#### New Feature Test Template
```python
# filepath: tests/<marker>/test_<module>_<feature>.py
@pytest.mark.<marker>
@pytest.mark.<secondary>  # if applicable
def test_<function>_<feature>_<case>(...):
    """Test <feature> behavior for <case>."""
    # Arrange
    # Act
    # Assert
```

### Step 4: Markers for Test Isolation

| Marker | Isolation Level | Runtime |
|--------|---------------|---------|
| `unit` | Fast, isolated, no I/O | <1s |
| `integration` | Real DB, filesystem, or component | 1-10s |
| `qt` | Real PyQt6 widgets, offscreen | 1-5s |
| `database` | DB-specific (schema, queries) | 1-5s |
| `backend` | Real FTP/SMTP/copy protocols | 5-30s |
| `dispatch` | Pipeline orchestration | 5-30s |
| `conversion` | File format conversion | 1-10s |
| `slow` | Tests taking >30 seconds | >30s |

## Workflow

1. **Analyze the code change**
   - What module/file is being modified?
   - What does the change do (bugfix, feature, refactor)?
   - What external systems does it interact with?

2. **Select markers** using Decision Tree above
   - Primary marker based on code area
   - Additional markers for cross-cutting concerns

3. **Select fixtures**
   - Use `tmp_path` for file operations
   - Use `temp_database` for DB operations
   - Use `qtbot` for any Qt widget interactions
   - Use `DatabaseObj` for UI-DB integration

4. **Write the test**
   - Follow bugfix or new feature template
   - Include docstring describing what/why
   - Add minimal assertions (test one thing per test)

5. **Run targeted tests**
   ```bash
   # Single test file
   ./.venv/bin/pytest tests/<marker>/test_<file>.py -q --timeout=30
   
   # By marker
   ./.venv/bin/pytest -m "<marker>" -q --timeout=30
   
   # Quick failure focus
   ./.venv/bin/pytest -x --timeout=30
   ```

6. **Verify with lint**
   ```bash
   ruff check tests/<marker>/test_<file>.py
   black --check tests/<marker>/test_<file>.py
   ```

## Output

- A structured test file in the appropriate `tests/<marker>/` directory
- Correct pytest markers on test functions
- Appropriate fixtures for the test scenario
- Minimal, focused assertions

## Example prompts

- "Use test-strategy-wizard to add a test for `dispatch/pipeline/converter.py` format validation logic."
- "Use test-strategy-wizard to choose markers and fixtures for testing `interface/dialogs/EditSettings.py` database save behavior."
- "Use test-strategy-wizard to structure a regression test for `backend/ftp_backend.py` retry logic on connection failure."

## Related customizations

- `/create-skill dispatch-test-wizard` (dispatch-specific test development pattern)
- `/create-skill ui-widget-integration` (Qt UI test development pattern)
- `/create-prompt dispatch-test-cases.md` (edge-case matrix generator for dispatch)
