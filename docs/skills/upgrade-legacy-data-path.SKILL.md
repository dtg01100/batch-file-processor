# upgrade-legacy-data-path Skill

Workspace-scoped helper skill for legacy data migration compatibility and verification.

## Purpose

- Protect against breakage when migrating and supporting old data formats or DB schema versions.
- Establish a cross-check workflow for backwards compatibility with legacy fixtures.

## When to use

- Schema migration or schema strictness changes in `schema.py` and `migrations/`.
- Legacy input format support changes in `core/edi` or `dispatch/` pipeline.
- When adding new code paths that must support existing production data.

## Input

- Legacy fixture path (e.g., `tests/fixtures/legacy_v32_folders.db`).
- Expected migration output and compatibility behavior.

## Workflow

1. Review required migration scripts and existing legacy fixture tests.
2. Create integration tests in `tests/database/test_upgrade_legacy.py`.
   - `temp_database` fixture or copy fixture DB into location, then run migration functions.
3. Assert on key legacy data and new schema entries.
4. For legacy EDI formats, run `process_folder_with_pipeline()` with legacy files and compare output.
5. Include rollback/update plan in docs: `docs/migrations/AUTOMATIC_MIGRATION_GUIDE.md`.
6. Run: `pytest -m database -q --timeout=30`, `ruff check`, `black --check`.

## Decision points

- Preserve old behavior by default; document intentional edits as behavior changes.
- Rebaseline golden fixtures where data transformation is expected after accepted API changes.

## Output

- Verified test coverage of migration path and legacy dataset compatibility.
