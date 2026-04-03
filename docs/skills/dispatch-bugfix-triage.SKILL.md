# dispatch-bugfix-triage Skill

Workspace-scoped helper skill for quick bug triage and fix workflow in `dispatch/` code.

## Purpose

- Standardize root-cause investigation, reproducible scenario setup, and regression test addition for `dispatch/` issues.
- Capture the “investigate first, test second, fix third” cycle that has been used repeatedly.

## When to use

- A bug report points to a dispatch pipeline issue (validation, splitting, conversion, output send failure).
- A PR changes pipeline behavior and reviewers need a structured bughood checklist.
- Refactoring dispatch code and preserving existing behavior.

## Input

- A concise bug description and failing path (e.g., `convert_to_format='tweaks'` output zero bytes)
- Baseline reproducer input file(s) and expected outputs
- Target module(s) (e.g., `dispatch/orchestrator.py`, `dispatch/pipeline/splitter.py`)
- Existing tests to extend, or fallback to a new file name

## Workflow

1. Reproduce with the minimum command/entrypoint:
   - `./.venv/bin/pytest tests/dispatch/test_* --maxfail=1 -q --timeout=30` for existing tests
   - or run `dispatch/orchestrator.py` helper functions in a short script using `tmp_path` fixture style
2. Inspect trace and behavior in relevant dispatch layers:
   - validator -> splitter -> converter -> backend send manager
   - for conversion bugs, inspect `dispatch/converters` implementation and `SUPPORTED_FORMATS`
3. Create a focused regression test scenario:
   - `tests/dispatch/test_dispatch_bugfix.py`
   - `pytest.mark.dispatch` + marker for additional domains (`conversion`, `backend`)
4. Implement minimal code fix and keep side effects deterministic.
5. Verify fix with targeted and marker-level tests:
   - `pytest tests/dispatch/test_dispatch_bugfix.py -q --timeout=30`
   - `pytest -m "dispatch and not slow" -q --timeout=30`
6. Run checkers:
   - `ruff check dispatch tests/dispatch`
   - `black --check dispatch tests/dispatch`

## Decision points

- If the bug is due to invalid config values: add/strengthen preflight validation in `dispatch/preflight_validator.py`.
- If the issue is in third-party backend interactions: wrap and re-raise with context in `dispatch/error_handler.py`.
- If concurrency-related: use the same `queue.Queue` and error capture patterns from existing `dispatch/send_manager.py`.

## Output

- Repro script/test, fix in code, regression test, and no broken existing tests.
- PR description including “pre-fix behavior” and “post-fix behavior” checks.
