# audit-tests Prompt

This prompt is a workspace-scoped helper for auditing and improving tests in the Batch File Processor repository.

## Intent

- Find existing incomplete, ineffective, or incorrect tests in a target area (e.g., dispatch pipeline, conversion modules, backend clients).
- Update/repair tests when needed.
- Identify missing coverage cases and implement new tests.

## Input

- Scope/target: file or module path (e.g., `dispatch/converters`, `tests/dispatch`, `core/edi`).
- Goal: audit existing tests and add missing scenarios.
- Quality criteria: assertion specificity, marker correctness, fixture use, no flakey timing behavior.

## Workflow

1. Scan existing tests in scope:
   - Use `grep -R` and `pytest -q` to identify candidate files and failures.
   - Focus on tests with generic broad assertions, over-mocking, or skipped marks.
2. For each candidate test:
   - Confirm if it is already sufficient for desired behavior.
   - If broken, fix code or test expectations as needed.
   - If ambiguous, refine with explicit input/output assertions and comments.
3. Identify behavior not covered by tests:
   - Compare with module/feature requirements in docs (e.g., `docs/PROCESSING_PIPELINE.md`).
   - Add targeted tests for boundary cases and failure modes.
4. Add regression tests for bugs discovered during audit.
5. Run tests and lint:
   - `./.venv/bin/pytest tests/<scope> -q --timeout=30`
   - `ruff check <updated files>`
   - `black --check <updated files>`

## Output

- Updated and validated tests in `tests/` with proper markers.
- New test modules where gaps were found.
- Short summary of changes and coverage improvements.

## Example commands

- `Use audit-tests to inspect tests/dispatch and patch weak converter tests with explicit assert and edge cases.`
- `Use audit-tests to verify backend error paths are covered in tests/backend and add missing error handling tests.`

## Next customizations

- `/create-skill dispatch-test-wizard` (done)
- `/create-instruction test-audit-policy.md` (explicit test smell rules)
