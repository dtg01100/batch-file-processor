---
created: 2026-03-30
last_edited: 2026-03-30
agent_generated: true
---

# Workspace Instructions (Qt5-focused)

This repository uses a Qt5-focused codebase and QiTho compatibility layer as an intentionally Qt5 project. If you see PyQt6 references from upstream docs, treat them as compatible conceptual references and prefer Qt5 APIs in implementation.

## Source of truth

- `.github/copilot-instructions.md` (existing project bootstrap policies)
- `AGENTS.md` (agent-specific requirements)
- `README.md` + `DOCUMENTATION.md` for user and dev quickstart
- `docs/*` (module-level design and tests)

## Key aspects for AI agents

1. Follow the bootstrap workflow in `.github/copilot-instructions.md`.
2. Preserve existing content and link rather than duplicate.
3. For code changes, include regression tests and correct markers (`unit`, `integration`, `database`, `qt`, `dispatch`, `backend`, `conversion`).
4. Maintain platform invariants:
   - Python 3.11+, black style (line length 88), ruff/isort
   - SQL parameterized queries; no f-string SQL
   - Paths via `os.path.join`
   - `with` context for file handles

## Tests

- `pytest` with `--timeout=30` is required; avoid deadlocks.
- Qt tests use `QT_QPA_PLATFORM=offscreen` and `qtbot`.
- Use fixtures like `temp_database`, `tmp_path`.

## Special note

- This workspace is intentionally Qt5; if a code path uses PyQt6 imports, verify whether there is a Qt5 substitute available.
- Use `interface/qt` and `interface/plugins` for GUI components.

## Practical prompt examples

- "Find where `DispatchConfig` is defined and add a `timeout` option with tests."
- "Refactor `dispatch/orchestrator.py` path lookup to use `pathlib.Path` and add unit tests."

## Next steps

1. Run `./.venv/bin/pytest tests/unit/test_foo.py -q --timeout=30` for quick validation.
2. Run `ruff check .` and `black --check .`.
