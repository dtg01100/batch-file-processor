# ui-widget-integration Skill

Workspace-scoped helper skill for PyQt5 UI integration + plugin lifecycle verification.

## Purpose

- Capture a repeatable UI integration test workflow for `interface/` components.
- Validate plugin form behavior, settings persistence, dialogs, and window state.

## When to use

- GUI changes in `interface/qt` or `interface/plugins`.
- Plugin form fields and save/load behaviors with `PluginManager`.
- Regression in user workflow (add folder, edit settings, start pipeline from UI).

## Input

- UI component to test (`EditFoldersDialog`, `FolderListWidget`, `PluginManager` form).
- Target behavior and success criteria.

## Workflow

1. Use `pytest-qt` and `qtbot` (offscreen): `pytest tests/qt -q --timeout=60`.
2. Create tests in `tests/qt/test_<component>.py` with real widgets.
3. Assert signal emissions and UI state changes:
   - `widget.checkState()`, button enabled/disabled, field values.
4. For plugin config forms, simulate user input and save event.
5. Add going through persistence: start with temp DB and `temp_database` fixture.
6. Run `ruff check interface tests/qt` and `black --check`.

## Decision points

- For hard-to-test dialogs requiring user interaction, use helper wrappers to emit accepted/rejected.
- Avoid fake Qt classes; use a real `QApplication` fixture, offscreen mode only.

## Output

- UI integration tests ensuring functional behavior and no regressions across PyQt5 updates.
