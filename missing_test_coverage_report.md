# Missing Test Coverage Report

## Overview
This report identifies Python source files that lack corresponding unit or integration tests in the batch-file-processor project.

## Source Files Without Tests

### Backend Module
- `./backend/protocols.py`

### Root Level Files
- `./backup_increment.py`
- `./batch_log_sender.py`
- `./clear_old_files.py`
- `./convert_to_csv.py`
- `./convert_to_estore_einvoice_generic.py`
- `./convert_to_estore_einvoice.py`
- `./convert_to_fintech.py`
- `./convert_to_jolley_custom.py`
- `./convert_to_scannerware.py`
- `./convert_to_scansheet_type_a.py`
- `./convert_to_simplified_csv.py`
- `./convert_to_stewarts_custom.py`
- `./convert_to_yellowdog_csv.py`
- `./copy_backend.py`
- `./create_database.py`
- `./database_import.py`
- `./dialog.py`
- `./_dispatch_legacy.py`
- `./doingstuffoverlay.py`
- `./edi_tweaks.py`
- `./email_backend.py`
- `./folders_database_migrator.py`
- `./ftp_backend.py`
- `./main_interface.py`
- `./mover.py`
- `./mtc_edi_validator.py`
- `./print_run_log.py`
- `./query_runner.py`
- `./rclick_menu.py`
- `./record_error.py`
- `./resend_interface.py`
- `./setup.py`
- `./tk_extra_widgets.py`
- `./utils.py`

### Core EDI Module
- No missing tests found (all files have corresponding tests)

### Dispatch Module
- `./dispatch/interfaces.py`

### Interface Module
- `./interface/models/folder_configuration.py`
- `./interface/services/ftp_service.py` (has test in edit dialog tests but could benefit from direct unit test)
- `./interface/validation/folder_settings_validator.py` (has test in edit dialog tests but could benefit from direct unit test)

## Summary
- Total source files analyzed: 48
- Files with tests: ~20
- Files missing tests: ~28
- Priority files needing tests:
  - Main entry points: `main_interface.py`, `create_database.py`
  - Converters: Multiple convert_to_* files
  - Core functionality: `dispatch/interfaces.py`, `utils.py`, `backend/protocols.py`

## Recommendations
1. Create unit tests for converter modules (convert_to_*.py)
2. Add tests for utility functions in utils.py
3. Develop tests for main interface components
4. Add tests for legacy dispatch functionality
5. Create tests for database import functionality