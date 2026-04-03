# plugin-maintenance Skill

Workspace-scoped helper skill for plugin lifecycle tasks in `interface/plugins` and `dispatch/converters`.

## Purpose

- Capture actions around adding/removing/porting plugins, plus handling plugin-related runtime errors.
- Formalize discovery, registration, and compatibility checks for plugin architecture.

## When to use

- Adding a new converter format (e.g., `convert_to_format='newformat'`).
- Adding a new UI configuration plugin in `interface/plugins`.
- Fixing plugin load failures, errors due to missing `ConfigurationPlugin` metadata, or `dispatch/pipeline` plugin dispatch.

## Input

- Plugin package path (`interface/plugins/<plugin_name>` or `dispatch/converters/convert_to_<format>.py`).
- Functional requirements and config options.
- Target test location (`tests/unit`, `tests/dispatch`, and `tests/interface`).

## Workflow

1. Identify existing plugin conventions in `interface/plugins/plugin_manager.py` and existing plugin classes.
2. Implement plugin class with `ConfigurationPlugin` metadata and API methods.
3. Add/modify converter implementation in `dispatch/converters` to support new output format.
4. Add a regression test for plugin discovery + behavior.
   - `tests/unit/test_plugin_manager.py` and `tests/dispatch/test_converter_<format>.py`.
5. Validate via:
   - `pytest tests/unit/test_plugin_manager.py tests/dispatch/test_converter_<format>.py -q --timeout=30`
   - `ruff check interface/plugins dispatch/converters tests/unit tests/dispatch`
   - `black --check interface/plugins dispatch/converters tests/unit tests/dispatch`
6. Add docs to `docs/PLUGIN_DEVELOPER_GUIDE.md`.

## Decision points

- If a plugin is optional/soft-fail, ensure `PluginManager` gracefully logs and continues, not crash the whole UI.
- If new converter format is unsupported, explicit `convert_to_format` whitelist update is required plus `feature_flags` gating if needed.

## Output

- Plugin files and tests are in place.
- A maintenance checklist in PR description (discovery, test, docs, run results).