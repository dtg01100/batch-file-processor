# db-migration-compatibility Skill

Workspace-scoped helper skill for running and validating database migrations safely.

## Purpose

- Codify the verified migration workflow used by this project for schema and data migrations.
- Ensure no data or behavior drift in database migration paths including legacy `v32` and custom migration scripts.

## When to use

- Adding or modifying migrations in `migrations/` and `schema.py`.
- Upgrading DB schema for features in `dispatch/` or `interface/`.
- Auditing compatibility with data from `tests/fixtures/legacy_v32_folders.db`.

## Input

- Migration target path and version (e.g., `migrations/2025-10-add-converter-settings.py`).
- Expected schema change and data contract.
- Test fixture DB (legacy or current) to apply migration against.

## Workflow

1. Review existing migration history in `migrations/` and `MIGRATION_REFERENCE_TABLE.txt`.
2. Write or update migration script with idempotent guard clauses.
3. Add regression integration test:
   - `tests/database/test_migrations.py`
   - Use `temp_database` fixture or copy of `tests/fixtures/legacy_v32_folders.db`
   - Assert pre-migration state, run `ensure_schema()` and/or `migrations.run_all()`.
   - Assert post-migration state and critical query results.
4. Add automated production acceptance:
   - `pytest tests/database/test_migrations.py -q --timeout=30`
   - optional local dry run copying a real dataset and verifying checksum from before/after data read path.
5. Ensure the migration is covered by release notes and `docs/migrations/AUTOMATIC_MIGRATION_GUIDE.md`.

## Decision points

- If a migration is non-reversible, document the write-once behavior in the script header and tests.
- If large data transformation is needed, prefer chunking and/or `PRAGMA synchronous=OFF` patterns for efficiency and safety.

## Output

- Migration script, tests, and updated migration guide section.
- CI-ready assertion that prevents applying broken migration on existing legacy DB fixture.
