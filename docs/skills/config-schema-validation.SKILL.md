# config-schema-validation Skill

Workspace-scoped helper skill for synchronizing JSON/YAML config schema with runtime code.

## Purpose

- Define schema validation checks for configuration files read by dispatch and UI.
- Ensure parser behavior remains consistent and invalid configs are rejected early.

## When to use

- Changes in config options or new fields in `dispatch/config` or `interface/settings`.
- Adding new document-based formats or policy controls.

## Input

- Config file path and expected schema.
- Runtime loading path and expected behavior on missing/extra fields.

## Workflow

1. Add or update jsonschema definitions in test helpers (e.g., `tests/helpers/config_schema.py`).
2. Add tests in `tests/unit/test_config_schema.py`.
   - Validate both good and bad examples.
3. Ensure code uses roundtrip validation on load (e.g., `jsonschema.validate()` in the config loader).
4. Run test and verify failures are clear and actionable.
5. Document schema in `docs/CONFIGURATION_DESIGN.md`.

## Decision points

- Use strict mode by default, but allow an explicit `allow_extra_fields` option when needed.
- Keep schema and code paths in sync with explicit cross-reference checks.

## Output

- Config validation tests and docs. Automated schema drift detection in CI.
