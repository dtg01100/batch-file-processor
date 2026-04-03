# Skills Index

This folder collects all workspace-scoped SKILL.md workflows for common Batch File Processor tasks.

## Purpose

- Provide a single entrypoint for engineering workflows that are repeated across the project.
- Help contributors choose the right workflow and execute consistent steps.

## Skills

- `api-contract-review.SKILL.md`
  - API schema/contract changes, versioning, request/response compatibility.

- `config-drift-validation.SKILL.md`
  - Validate config behavior/output does not drift after config updates.

- `config-schema-validation.SKILL.md`
  - JSON/YAML config schema consistency and runtime validation.

- `db-migration-compatibility.SKILL.md`
  - DB migration path validation (legacy fixture compatibility and schema upgrades).

- `dispatch-bugfix-triage.SKILL.md`
  - Dispatcher pipeline bug triage, regression test canonicalization.

- `dispatch-test-wizard.SKILL.md`
  - Dispatch test development pattern with coverage and markers.

- `end-to-end-pipeline-validation.SKILL.md`
  - Full EDI pipeline e2e integration tests and golden data checks.

- `performance-regression-monitoring.SKILL.md`
  - Benchmark and fail on performance regression for key flows.

- `plugin-maintenance.SKILL.md`
  - Plugin add/update/removal process for UI and converter plugins.

- `release-preflight.SKILL.md`
  - Final pre-merge release checks: tests, lint, docs, migrations.

- `security-audit.SKILL.md`
  - Security review and tests for injection, path traversal, credentials.

- `ui-widget-integration.SKILL.md`
  - PyQt UI integration tests and plugin form behavior.

- `upgrade-legacy-data-path.SKILL.md`
  - Legacy DB/file migration verification and compatibility.

- `create-instructions.SKILL.md`
  - Capture chat->instruction file workflow and persist agent customization rules.

## Usage

1. Pick the matching skill file for your change.
2. Read the `Workflow` section in that SKILL for exact steps.
3. Execute the commands in your local environment:
   - `./.venv/bin/pytest -q --timeout=30`
   - `ruff check .`
   - `black --check .`
4. Add a short note in PR description referencing the exact skill used.
