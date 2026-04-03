# coverage-gap-finder Prompt

This prompt helps identify untested behavior in the repository and create targeted tests for missing cases.

## Intent

- Discover gaps in unit/integration coverage for a specified area (module/package).
- Propose and implement missing test cases.

## Input

- Target scope: path or module (e.g., `dispatch/converters`, `backend/ftp_backend.py`, `core/edi`).
- Optional focus: new feature, defect branch, existing bug report.

## Workflow

1. Determine current coverage indicators:
   - Run `./.venv/bin/pytest --maxfail=1 --disable-warnings -q --durations=10 tests/<scope>`.
   - Use `coverage run -m pytest` and `coverage report -m` if available.
2. Identify untested lines or unasserted behavior:
   - Identify functions or branch paths not covered in source files (`grep -R "def ..."` and matches in tests).
   - Check exception branches and boundary conditions (empty, malformed, large, unauthorized).
3. For each missing behavior, write a new test:
   - Use explicit assertions and fixtures.
   - Add markers (`unit`, `integration`, `dispatch`, etc.) as required.
4. Execute new tests and confirm coverage improvement.
5. Document the new coverage gaps and tests added in gist comments in the test file.

## Output

- New tests under `tests/` for missing paths.
- Clear list of gaps filled (function names + branch conditions).

## Example usage

- `Use coverage-gap-finder on dispatch/converters to add missing tests for `convert_to_tweaks` when input has no segments.`
- `Use coverage-gap-finder on backend/ftp_backend.py to test connection failures and timeout branch coverage.`

## Pertinent ties

- Link with `test-audit-policy.md` for assert quality.
- Use `audit-tests.prompt.md` for broad audit and cleanup integration.
