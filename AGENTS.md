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

Batch file processor — Python/PyQt6 GUI application for processing EDI/batch files with email, FTP, and copy backends.

## Key Commands

| Command | Description |
|---------|-------------|
| `./.venv/bin/python interface/main.py` | Run GUI application |
| `./.venv/bin/python interface/main.py -a` | Run in automatic/headless mode |
| `./.venv/bin/pytest tests/` | Run test suite |
| `./.venv/bin/pytest tests/ -x` | Stop on first failure |

## Module Structure

- `interface/` — PyQt6 GUI (see `interface/AGENTS.md`)
- `dispatch/` — Core file processing (see `dispatch/AGENTS.md`)
- `tests/` — Test suite (see `tests/AGENTS.md`)
- `convert_*.py` — Conversion backends
- `*_backend.py` — Output backends (email, FTP, copy)

## Environment

- Python 3.11+ (tested with 3.13)
- Virtual environment: `.venv/` (managed by uv or pip)
- Dependencies: `requirements.txt`, `requirements-dev.txt`
- Config: `pyproject.toml`
