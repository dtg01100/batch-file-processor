# Test Audit Policy

This instruction file defines test quality criteria for Batch File Processor and is intended for agents guiding test improvements.

## Goals

- Ensure automated tests are predictable, meaningful, and maintainable.
- Prevent weak assertions, overuse of mocking, and hidden dependency side effects.
- Enforce breadth (positive + negative + boundary coverage) and depth (bug regression).

## Scope

- All tests under `tests/` and new tests related to `dispatch/`, `backend/`, `core/`, and `interface/`.

## Policies

1. Test markers
   - Use strict markers.
   - `unit` for pure logic, no filesystem/network.
   - `integration` for DB/filesystem/network interactions.
   - `dispatch`, `backend`, `conversion`, `database`, `qt` as applicable.

2. Assertion quality
   - Avoid one-line generic asserts like `assert result`.
   - Prefer explicit checks: `assert len(out) == 3`, `assert last_event.status == "failed"`.
   - Assert error messages in exceptions where behavior depends on them.

3. Fixture use and dependencies
   - Use built-in fixtures (`tmp_path`, `monkeypatch`, `temp_database`, `qtbot`) over manual setup when available.
   - No global state leaks; always cleanup resources in `finally` or fixture scope.

4. Mocking and external services
   - Minimize mocks; prefer in-memory or local test doubles.
   - If mocking external calls (FTP/SMTP/HTTP), document in comments why absolutely required.

5. Coverage and edge cases
   - Each new feature or bug fix includes at least one positive and one negative test.
   - Add boundary tests for off-by-one, empty input, invalid config, and permission errors where applicable.

6. Regression test requirement
   - Fixes require a regression test that fails before the fix.
   - For behavior changes, include the old and new expected outcomes in assertions.

7. Flake and timing
   - Statically avoid sleep-based timing; use explicit hooks, event waiters, or deterministic triggers.
   - Mark long-running scenarios with `@pytest.mark.slow`.

## Audit Workflow

- Use `audit-tests.prompt.md` workflow to apply this policy.
- After edits:
  - `./.venv/bin/pytest -q --timeout=30 tests/<module>`
  - `ruff check .`
  - `black --check .`

## Notes

- This policy is for human + agent collaborators; prioritize minimal changes that reflect behavior requirements.
- Link to existing docs for reference (e.g., `docs/testing/TESTING.md`, `docs/PROCESSING_PIPELINE.md`).
