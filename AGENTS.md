# AGENTS.md — Project-Wide Agent Configuration

## Python Virtual Environment (MANDATORY)

**ALWAYS use the Python virtual environment at `.venv/`.**

- **Running Python**: `./.venv/bin/python` or activate first: `source .venv/bin/activate`
- **Running pytest**: `./.venv/bin/pytest` or `source .venv/bin/activate && pytest`
- **Installing packages**: `./.venv/bin/pip install <package>` or `uv pip install <package>`

**DO NOT**:
- Run `python` or `python3` directly without `.venv/bin/` prefix
- Use system Python for any project operations
- Install packages globally

**Activation shortcut** (if needed for multiple commands):
```bash
source .venv/bin/activate
python <script>
pytest <tests>
deactivate
```

## Project Overview

Batch file processor — Python/PyQt5 GUI application for processing EDI/batch files with email, FTP, and copy backends.

## Key Commands

| Command | Description |
|---------|-------------|
| `./.venv/bin/python interface/main.py` | Run GUI application |
| `./.venv/bin/python interface/main.py -a` | Run in automatic/headless mode |
| `./.venv/bin/pytest tests/` | Run test suite |
| `./.venv/bin/pytest tests/ -x` | Stop on first failure |

## Module Structure

- `interface/` — PyQt5 GUI (see `interface/AGENTS.md`)
- `dispatch/` — Core file processing (see `dispatch/AGENTS.md`)
- `tests/` — Test suite (see `tests/AGENTS.md`)
- `convert_*.py` — Conversion backends
- `*_backend.py` — Output backends (email, FTP, copy)

## Environment

- Python 3.11+ (tested with 3.13)
- Virtual environment: `.venv/` (managed by uv or pip)
- Dependencies: `requirements.txt`, `requirements-dev.txt`
- Config: `pyproject.toml`

## Code Style

### noqa Comments — Always Justify

When adding `# noqa` suppressions, always include a justification comment explaining **why** the suppression is needed. Never leave a bare `# noqa`.

**Good:**
```python
context: dict[str, Any],  # noqa: ARG001 - required by PipelineStep protocol but unused by adapter
```

**Bad:**
```python
context: dict[str, Any],  # noqa: ARG001
```

### Justification Requirements by Error Type

| Error Code | Meaning | When Appropriate |
|------------|---------|------------------|
| `ARG001` | Unused argument | Required by protocol/interface but not used in implementation |
| `FBT001/FBT003` | Qt boolean-to-int conversion | Qt signal handlers that require specific signatures |
| `N802` | Qt method override naming | Qt method overrides using Qt conventional parameter names |
| `E402` | Module import at module level | Backward compatibility re-exports |
| `F401` | Unused import | Re-exports for backward compatibility |
| `BLE001` | Bare except clause | Intentional exception fallthrough in logging |
| `type: ignore[arg-type]` | PyQt5 stub incompatibilities | PyQt5 type stubs are incorrect, code works at runtime |

### Resolution Before Suppression

Always try to fix the underlying issue first. Suppressions should be a last resort when:
- The code is correct but linter/type checker is wrong
- External API requires specific signatures
- Type stubs are incorrect (document which)

Document the reason clearly so future maintainers understand why the suppression exists.
