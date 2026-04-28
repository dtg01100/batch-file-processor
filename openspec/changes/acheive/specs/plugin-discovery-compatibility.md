# Spec: Plugin Discovery Compatibility

## Overview

Define how converter and backend plugins are discovered to ensure backward compatibility. **Converter selection MUST match the original implementation exactly - no exceptions.**

## ADDED Requirements

### Requirement: Converter naming convention matches original

Converter plugins SHALL be discovered using naming conventions identical to the original implementation.

#### Scenario: Format name to module mapping

**When** a format name is configured (e.g., "scannerware", "csv", "json")  
**Then** the system SHALL import `convert_to_<format>.py` exactly as the original did

#### Scenario: Case sensitivity preserved

**When** a format name has specific casing (e.g., "ScannerWare", "Scannerware")  
**Then** the module name SHALL match exactly (e.g., `convert_to_Scannerware.py`)

#### Scenario: Module-level edi_convert function

**When** a converter module is loaded  
**THEN** it SHALL have a module-level `edi_convert()` function

---

### Requirement: Converter selection logic identical to original

The algorithm that selects a converter based on format configuration SHALL be byte-for-byte identical to the original.

#### Scenario: Same format maps to same converter

**When** format "scannerware" is configured  
**THEN** the converter selected SHALL be identical to what the original selected

#### Scenario: Unrecognized format handling

**When** a format name doesn't match any converter  
**THEN** the error/exception raised SHALL be identical to the original

#### Scenario: Format alias resolution

**When** the original supported format aliases (e.g., "edi" -> "810")  
**THEN** the same aliases SHALL resolve identically

---

### Requirement: Backend discovery by naming convention

Backend plugins SHALL be discovered using the same naming convention as the earlier version.

#### Scenario: Backend name to module mapping

**When** a backend name is configured (e.g., "ftp", "email", "copy")  
**THEN** the system SHALL import `<name>_backend.py`

#### Scenario: Module-level do function

**When** a backend module is loaded  
**THEN** it SHALL have a module-level `do()` function

---

### Requirement: Plugin parameter passing matches original

Plugin invocation SHALL use parameter signatures identical to the original.

#### Scenario: Converter invocation

**When** `edi_convert()` is called on a converter  
**THEN** it SHALL receive: `(edi_process, output_filename, settings_dict, parameters_dict, upc_lookup)`

#### Scenario: Backend invocation

**When** `do()` is called on a backend  
**THEN** it SHALL receive: `(process_parameters, settings_dict, filename)`

---

### Requirement: Plugin parameter order and types preserved

**When** plugins are called  
**THEN** parameter order, types, and any default values SHALL match the original implementation exactly

### Requirement: EDI tweaks available as conversion target

The "tweaks" transformation SHALL be available as a first-class conversion format.

#### Scenario: Tweaks format selectable

**When** a user configures a folder with format "tweaks"  
**THEN** the system SHALL invoke `dispatch/converters/convert_to_tweaks.py` with `edi_convert()`

#### Scenario: Tweaks transformation identical to original

**When** EDI data is processed with "tweaks" format  
**THEN** the output SHALL be byte-for-byte identical to the legacy `edi_tweaks.py` implementation

#### Scenario: Existing tweak configurations continue to work

**When** a folder with existing tweak configuration is processed  
**THEN** the same transformation SHALL be applied as before the migration

#### Scenario: Tweaks appears in format dropdown

**When** the UI displays format options  
**THEN** "tweaks" SHALL appear as a selectable option alongside "scannerware", "csv", etc.

---

### Requirement: PyInstaller hidden imports for plugins

Plugin discovery via dynamic import MUST be reflected in PyInstaller spec file.

#### Scenario: Dynamic converter import

**When** `dispatch/converters/__init__.py` uses dynamic import (e.g., `importlib.import_module()`)  
**THEN** all converter modules SHALL be explicitly listed in `main_interface.spec` hiddenimports

#### Scenario: Dynamic backend import

**When** `backend/` uses dynamic backend discovery  
**THEN** all backend modules SHALL be explicitly listed in `main_interface.spec` hiddenimports

#### Scenario: Archive modules for legacy compatibility

**When** legacy modules are referenced for backward compatibility  
**THEN** archive modules SHALL be listed in `main_interface.spec` hiddenimports