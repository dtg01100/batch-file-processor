# Spec: EDI Tweaks as Conversion Target

## Overview

Define how EDI tweaks transformations are migrated to become a first-class conversion format. **Customers using tweaks historically MUST continue to do so with identical results.**

## ADDED Requirements

### Requirement: Tweaks transformation available as format

The "tweaks" transformation SHALL be selectable as a format in the converter system.

#### Scenario: Format name "tweaks"

**When** a format name "tweaks" is configured in a folder  
**Then** the system SHALL select `convert_to_tweaks.py` via the plugin discovery mechanism

#### Scenario: Module naming convention

**When** the converter plugin for tweaks is loaded  
**Then** it SHALL be named `convert_to_tweaks.py` following the standard converter naming pattern

#### Scenario: Edi_convert function signature

**When** `edi_convert()` is called on the tweaks converter  
**Then** it SHALL receive: `(edi_process, output_filename, settings_dict, parameters_dict, upc_lookup)`  
**And** it SHALL return output identical to the original `edi_tweaks.py` implementation

---

### Requirement: Tweaks transformation identical to original

The tweaks transformation logic SHALL be byte-for-byte identical to the legacy implementation.

#### Scenario: Output comparison

**When** the same EDI input is processed through "tweaks" format  
**Then** the output SHALL be byte-for-byte identical to the legacy `edi_tweaks.py` output

#### Scenario: Transformation steps preserved

**When** the tweaks transformation is analyzed  
**Then** it SHALL include all transformation steps from the original (e.g., field modifications, formatting changes)

#### Scenario: Edge cases preserved

**When** edge cases from the original implementation are tested  
**Then** the new implementation SHALL handle them identically (same behavior, same errors, same output)

---

### Requirement: Existing tweak configurations continue to work

Customers who have already configured folders to use tweaks SHALL continue to process files correctly.

#### Scenario: Existing folder with tweaks format

**When** a folder record in the database has format="tweaks"  
**Then** processing that folder SHALL invoke the new `convert_to_tweaks.py` with identical results

#### Scenario: Migration of tweak-specific parameters

**When** tweak-specific configuration is stored in folder settings  
**Then** it SHALL be read and passed to `edi_convert()` in the same manner as the original

#### Scenario: No data loss during migration

**When** the migration from `edi_tweaks.py` to `convert_to_tweaks.py` occurs  
**Then** no tweak functionality SHALL be lost or altered

---

### Requirement: Tweaks selectable in UI

The tweaks format SHALL be visible and selectable in the user interface.

#### Scenario: Format dropdown includes tweaks

**When** a user opens the folder configuration dialog  
**Then** "tweaks" SHALL appear in the format dropdown alongside other formats (scannerware, csv, etc.)

#### Scenario: Tweaks description

**When** the user hovers over or views the tweaks option  
**Then** a description SHALL indicate it applies EDI tweaks/transformation

---

### Requirement: Tweaks behavior matches original exactly

**When** any aspect of tweaks behavior is tested against the original  
**Then** it SHALL match byte-for-byte with no exceptions
