# release-preflight Skill

Workspace-scoped helper skill for release preflight checks and final staging validation.

## Purpose

- Standardize final validations before code is merged or a release is cut.
- Combine tests, lint, docs, and migration checks into a deterministic final checklist.

## When to use

- Right before raising a PR for merge to `master`/`main`.
- Before tagging or cutting a release candidate.

## Input

- Target branch, changelog entry, release notes.
- Any outstanding migration or schema changes.

## Workflow

1. Run full-targeted test suite with timeout and flag: `./.venv/bin/pytest -q --timeout=30`.
2. Run lint and formatting checks:
   - `ruff check .`
   - `black --check .`
3. Run specialized checks:
   - `pytest -m database -q --timeout=60` if DB changes
   - `pytest -m dispatch -q --timeout=60` if dispatch changes
4. Confirm docs updates and `MIGRATION_REFERENCE_TABLE.txt` if schema/migrations touched.
5. Verify version and changelog are updated (e.g., `pyproject.toml` or release notes file updated).
6. (Optional) Run static analysis / coverage thresholds.

## Decision points

- If any step fails, no merge.
- For fast iteration, allow a focused smoke test set on feature branches but require full preflight on final release.

## Output

- Final pre-merge status report with green checks; list of follow-up tickets for expected outstanding items.
