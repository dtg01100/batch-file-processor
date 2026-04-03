# dispatch-test-wizard Skill

This is a workspace-scoped helper skill for Batch File Processor to drive consistent, high-quality dispatch pipeline test development.

## Purpose

- Teach an AI assistant a repeatable pattern for adding or fixing tests in `dispatch/`.
- Enforce the repository’s conventions (`pytest`, markers, regression coverage, no mocks beyond clear boundaries, etc.).

## When to use

- Creating a new dispatch feature (validator/splitter/converter/orchestrator behavior)
- Fixing a bug in dispatch logic and adding regression coverage
- Refactoring dispatch code with test-maintained behavior guarantees

## Input (prompt for this skill)

- Target module/functionality (e.g., `dispatch/orchestrator.py`, `dispatch/converters/convert_to_tweaks.py`)
- Behavior change summary (“avoid generating 0-byte output for empty invoice blocks”) and expected status: pass/fail scenario
- Existing test path (if known) or “discover based on target module”
- Marker preference (`unit`, `dispatch`, `conversion`, `integration`, etc.)

## Workflow

1. Browse existing tests in `tests/dispatch/` and `tests/unit/` for similar behavior:
   - `grep -R "tweaks" tests` or `grep -R "process_folder_with_pipeline" tests`
   - Identify existing fixtures (`tmp_path`, `temp_database`, `qtbot`, etc.)
2. Inspect the target production code path:
   - Locate entrypoints in `dispatch/orchestrator.py` and pipeline interfaces in `dispatch/pipeline/`.
   - Confirm where the bug or feature should be applied.
3. Design minimal regression test flow:
   - Arrange: create synthetic input files and config state for the desired case.
   - Act: run the targeted function (e.g., `process_folder_with_pipeline()`).
   - Assert: expected outputs and side effects (files, DB states, exceptions) using `assert` statements.
4. Write test file in existing namespace or new file with clear name:
   - `tests/dispatch/test_<feature>.py`
   - Add markers: `@pytest.mark.dispatch`, plus `@pytest.mark.integration/database` when relevant.
5. Run targeted tests first:
   - `./.venv/bin/pytest tests/dispatch/test_<feature>.py -q --timeout=30`
   - If green, run combined marker set quickly: `./.venv/bin/pytest -m dispatch -q --timeout=30`.
6. Check formatting and lint:
   - `ruff check tests/dispatch/test_<feature>.py dispatch/<target>.py`
   - `black --check tests/dispatch/test_<feature>.py dispatch/<target>.py`
7. Create or update docs if needed:
   - `docs/PROCESSING_PIPELINE.md` or `docs/architecture/backend-selection-hardening.md` as appropriate

## Decision points and validation

- If behavior is unambiguous and simple, implement in `dispatch/pipeline/` layer for easier unit testing.
- If external state required (DB/filesystem), use integration-style tests with fixtures and explicit cleanup.
- Avoid interface-level timeouts or infinite loops; fail fast with detailed assertion messages.

## Output

- A new or updated `tests/dispatch/test_*.py` containing a regression scenario that fails pre-fix and passes post-fix.
- Side effects checked via file exists/size/content or mapped pipeline result objects.

## Example prompts

- "Use dispatch-test-wizard to add a regression test for 0-byte tweak conversion output in `dispatch/converters/convert_to_tweaks.py`."
- "Use dispatch-test-wizard to fix `process_folder_with_pipeline()` error handling when `convert_to_format` is unknown, and add a dispatch marker test."

## Related customizations

- `/create-instruction debug-dispatch-guidelines.md` (detailed coding patterns for dispatch modules)
- `/create-prompt dispatch-test-cases.md` (interactive generator for edge-case matrix)
