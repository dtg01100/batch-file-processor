# api-contract-review Skill

Workspace-scoped helper skill for API contract change validation and compatibility checks.

## Purpose

- Enforce stable contract behavior for API layer changes (request/response, versioning, error payloads).
- Provide a standard workflow for API/back-end wire-level tests and documentation updates.

## When to use

- Modifying backend API endpoints in `backend/http_*` or `dispatch/interfaces`.
- Updating API documentation in `docs/API_SUMMARY.md` or related API contract files.
- Introducing new API fields, optional parameters, or status-code semantics.

## Input

- Target API endpoint and payload examples.
- Existing contract expected values and deprecation plan.
- Affected tests and integration points.

## Workflow

1. Inspect current API behavior and schema in code and docs.
   - `docs/API_SUMMARY.md`, `backend/http_*` and any contract serializer.
2. Validate behavior with unit+integration tests.
   - Add or update tests in `tests/` under `tests/unit`, `tests/integration`.
   - Use `pytest` with request/response schema validation assertions.
3. Add compatibility guards for old clients.
   - Accept missing fields, keep old response shape where possible, and include a migration plan in docs.
4. Add contract assertions:
   - response shape matches JSON schema (if available) or explicit dict keys.
   - API errors are structured and status codes are verified.
5. Run and verify: `./.venv/bin/pytest tests -q --timeout=30`, `ruff check`, `black --check`.

## Decision points

- Breaking changes require version bump and explicit migration notes in `API_SUMMARY`.
- New fields should be optional defaulted to existing behavior unless mandatory.

## Output

- Updated tests covering the contract and verification scripts.
- API docs sync and versioning notes in `docs/API_SUMMARY.md`.
