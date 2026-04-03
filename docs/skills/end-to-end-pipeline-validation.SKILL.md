# end-to-end-pipeline-validation Skill

Workspace-scoped helper skill for validating full EDI pipeline behavior from input to delivery.

## Purpose

- Prevent regression of entire pipeline flow by validating key end-to-end paths through conversion and backend delivery.
- Provide a repeatable approach for integration-level pipeline checks.

## When to use

- New pipeline features or format conversion changes.
- Backend delivery behavior changes (FTP, SMTP, local copy).
- Core behavior path tests after refactors in `dispatch/orchestrator.py`.

## Input

- Representative input EDI fixtures and expected output artifacts.
- Delivery backend type and validation endpoint (local filesystem, fake FTP/SMTP).

## Workflow

1. Identify a baseline scenario and golden data in `tests/data`.
2. Implement tests in `tests/integration/test_e2e_pipeline.py`.
   - Run `process_folder_with_pipeline()` or appropriate orchestration method.
   - Assert output file content, DB processed state, and send status.
3. Use temporary paths and fixtures:
   - `tmp_path`, `temp_database`, mocked backend server for SMTP/FTP.
4. Add message boundary assertions, error handling behavior.
5. Run targeted tests and CI marker: `pytest -m integration -q --timeout=30`.
6. Update docs at `docs/PROCESSING_DESIGN.md` or `docs/ARCHITECTURE.md` with path coverage.

## Decision points

- Use deterministic golden fixture comparison for file contents when possible.
- For nondeterministic metadata (timestamps, async receipts), compare key fields only.

## Output

- End-to-end integration test coverage and artifacts confirming pipeline behavior.
