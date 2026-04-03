# config-drift-validation Skill

This is a workspace-scoped helper skill for Batch File Processor to define and enforce behavior/output regression checks for configuration-driven processing pipelines.

## Purpose

- Capture a repeatable workflow for validating that configuration changes do not drift behavior (pipeline semantics, conversions, outputs) over time.
- Enable consistent regression-files and golden-output tests for EDI pipeline configs.
- Provide a template for building checks into CI (pytest markers, git hooks, baseline artifact comparisons).

## When to use

- Adding or changing a configuration schema (format, converters, router rules, tweaks options)
- Upgrading the pipeline (new validator/splitter/converter behavior) and you need behavior guardrails
- Preventing silent regressions when config JSON/YAML gets tweaked

## Input (prompt for this skill)

- Config artifact(s) to lock down (e.g., `config/dispatch.yml`, `edi_formats/**`)
- Behavior or output contract to enforce (example: same row count and checksum for the converted file)
- Target code path (`dispatch/orchestrator.py`, `dispatch/converters/convert_to_csv.py`, etc.)
- Baseline sample input file(s) and expected output file(s)
- Marker preference (`unit`, `dispatch`, `integration`, `database`, `conversion`)

## Workflow

1. Identify existing golden baseline tests for similar config behavior in `tests/`.
   - `grep -R "golden" tests` or `grep -R "config.*regression" tests`
   - Identify fixtures and utilities used for output comparison (`tmp_path`, `filecmp`, custom validators)
2. Define a clear regression assertion: behavior contract must be explicit.
   - e.g., `validate_pipeline_result` should assert no dropped segments, same number of output files, same SHA-256 for output content
   - For format conversions, compare using canonical/parsing + round-trip checks (parse->emit->parse equivalence)
3. Add or update test(s):
   - `tests/dispatch/test_config_drift.py` with one or more scenarios
   - include “golden data” sample input and expected output in `tests/data/golden/` or similar
   - use `pytest.mark.<marker>` and short failure messages
4. Add optional config-drift metadata and CI check logic
   - create a helper `tests/helpers/config_drift.py` that can be reused
   - enforce `@pytest.mark.drift` in CI as part of `python -m pytest -m drift`
   - add a README note (docs/testing/TESTING.md) and a task description in `docs/architecture/` if needed
5. Validate via test & lint
   - `./.venv/bin/pytest tests/dispatch/test_config_drift.py -q --timeout=30`
   - `ruff check tests/dispatch test` and `black --check` as project policy
6. Monitor and rebaseline carefully
   - If intended behavior changes, update `tests/data/golden/*` and add a comment in test code documenting why change is allowed.

## Decision points and validation

- If config change is backward-compatible: use non-breaking contract tests asserting additional fields allowed, behavior unchanged for previous behavior.
- If config introduces optional feature toggle: add tests for both `enabled` and `disabled` paths and assert drift guard behavior.
- If output is non-deterministic (timestamps, UUIDs): normalize or redact before comparison.

## Output

- A new regression test suite under `tests/dispatch/test_config_drift.py` (or existing matching namespace).
- Baseline golden fixtures under `tests/data/golden/config_drift/`.
- `pytest` marker(s) for drift guard, e.g., `@pytest.mark.drift`, `@pytest.mark.dispatch`.
- Documentation snippet in `docs/testing/TESTING.md` and/or `docs/architecture/` linking to this skill.

## Example prompts

- "Use config-drift-validation to add a regression guard for `convert_to_format='tweaks'` output when `tweaks` mapping changes." 
- "Use config-drift-validation to compare converted CSV produced by old and new `edi_format` definitions and ensure row/column equivalence." 
- "Use config-drift-validation to ensure `dispatch/pipeline` behavior does not regress when `settings.max_retries` is changed from 3 to 5."

## Related customizations

- `/create-instruction regression-test-guidelines.md` (process for baseline fixtures and golden file maintenance)
- `/create-prompt compare-drift-case.md` (interactive helper to generate drift assertions and `pytest` expectations)