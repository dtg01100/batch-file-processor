# Component Communication Test Matrix

_Last updated: 2026-03-10_

This matrix tracks behavior-level communication coverage between components (caller → callee), focusing on wiring, callback propagation, and side effects.

## Qt App / GUI Orchestration

- `QtBatchFileSenderApp._toggle_folder` → `FolderManager.enable_folder/disable_folder` + `UIService.show_error`
  - `tests/qt/test_backend_gui_communication.py`
- `QtBatchFileSenderApp.run` (`--graphical-automatic`) → `QTimer.singleShot` → `_graphical_process_directories`
  - `tests/qt/test_backend_gui_communication.py`
- `QtBatchFileSenderApp._process_directories` → `dispatch.process(progress_callback=...)` and `ReportingService.send_report_emails(progress_callback=...)`
  - `tests/qt/test_backend_gui_communication.py`
- Dialog/callback wiring (`EditSettings`, `Maintenance`, `ProcessedFiles`, `Resend`)
  - `tests/qt/test_qt_app.py`

## Qt Services

- `QtProgressService` method-to-widget communication:
  - `update_detailed_progress` → folder/file/footer labels
  - `update_progress` / `set_indeterminate` → throbber/progress-bar mode switch
  - `progress_dialog` property → overlay exposure
  - `set_total` + `set_current` → computed percentage updates
  - Tests: `tests/qt/test_qt_services.py`

## Interface Operations

- `FolderManager.add_folder` → template retrieval (`get_oversight_or_default`) + insert
- `FolderManager.delete_folder_with_related` → delete fan-out (`folders_table`, `processed_files`, `emails_table`)
- `FolderManager.update_folder_by_name` → ID resolution + keyed update
- `FolderManager.batch_add_folders(skip_existing=False)` → unconditional add calls
- Tests:
  - `tests/unit/interface/operations/test_folder_manager.py`

## Interface Services

- `ReportingService.add_run_log_to_queue` → conditional queue insert
- `ReportingService.send_report_emails` →
  - queue-to-batch table transfer
  - batch sender invocation (`batch_log_sender.do`)
  - progress callback passthrough
  - missing-log error-log generation and batch send
- Tests:
  - `tests/unit/interface/services/test_reporting_service.py`

## Dispatch Pipeline / Services

- `FileProcessor.process_file` pipeline handoff:
  - splitter output file → tweaker input
  - tweaker output file → converter input
  - converter output file → send manager `send_all`
- `FileProcessor.process` return-path behavior for clean validation path
- Tests:
  - `tests/unit/dispatch_tests/test_services.py`

## Dispatch Converter / Send Manager (existing robust suites)

- `EDIConverterStep` → dynamic module loader + converter function + error handler
  - `tests/unit/dispatch_tests/test_pipeline_converter.py`
- `SendManager` → backend selection, module dispatch, error capture/continuation
  - `tests/unit/dispatch_tests/test_send_manager.py`

## Plugin / Dynamic Form Communication

- `FormGenerator.add_plugin_section` + `QtFormGenerator._render_plugin_sections`
  - section schema/config handoff into `SectionFactoryRegistry.create_section`
  - rendered section registration and section ID propagation
  - Tests: `tests/unit/test_form_generator.py`
- `FormGenerator` plugin section APIs:
  - `get_plugin_section_values`
  - `set_plugin_section_values`
  - `validate_plugin_sections` (both `validate()` and `get_validation_errors()` paths)
  - Tests: `tests/unit/test_form_generator.py`
- Plugin manager ↔ configuration plugin communication (existing suites)
  - format lookup, widget creation, validation/serialize/deserialize delegation
  - Tests:
    - `tests/unit/test_plugins/test_plugin_manager_configuration.py`
    - `tests/unit/test_plugins/test_form_generator_plugins.py`
    - `tests/integration/test_plugin_system_e2e.py`

## Script Harness Communication

- `scripts/graphical_mock_automatic_run.py`
  - mocked dispatch progress updates and run-log emission
  - harness artifact creation and graphical auto-run path
  - Tests: `tests/integration/test_graphical_mock_automatic_run.py`
- `scripts/mock_automatic_run.py`
  - automatic harness artifact creation and mocked dispatch run
  - Tests: `tests/integration/test_mock_automatic_run.py`

## Recent Validation Runs

Targeted communication suite executed on 2026-03-10:

- `tests/unit/interface/services/test_reporting_service.py`
- `tests/unit/dispatch_tests/test_services.py`
- `tests/unit/interface/operations/test_folder_manager.py`
- `tests/qt/test_qt_services.py`
- `tests/qt/test_backend_gui_communication.py`
- `tests/integration/test_graphical_mock_automatic_run.py`

Result: **127 passed**, **0 failed**.

Plugin/form-focused validation run executed on 2026-03-10:

- `tests/unit/test_form_generator.py`
- `tests/unit/test_plugins/test_form_generator_plugins.py`
- `tests/unit/test_plugins/test_plugin_manager_configuration.py`
- `tests/integration/test_plugin_system_e2e.py`

Result: **55 passed**, **0 failed**.

Consolidated communication mega-suite executed on 2026-03-10:

- `tests/qt/test_backend_gui_communication.py`
- `tests/integration/test_graphical_mock_automatic_run.py`
- `tests/unit/interface/operations/test_folder_manager.py`
- `tests/qt/test_qt_services.py`
- `tests/unit/interface/services/test_reporting_service.py`
- `tests/unit/dispatch_tests/test_services.py`
- `tests/unit/test_form_generator.py`
- `tests/unit/test_plugins/test_form_generator_plugins.py`
- `tests/unit/test_plugins/test_plugin_manager_configuration.py`
- `tests/integration/test_plugin_system_e2e.py`

Result: **182 passed**, **0 failed**.
