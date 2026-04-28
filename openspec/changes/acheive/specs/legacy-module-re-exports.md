# Spec: Legacy Import Migration

## Overview

Define how legacy import paths are migrated to modern package paths. Single code path principle: no duplication, no compatibility layers - migrate code to modern imports.

## ADDED Requirements

### Requirement: Code migrates to modern import paths

All code SHALL use modern import paths from `dispatch/`, `backend/`, `interface/` packages.

#### Scenario: Internal imports use modern paths

**When** code in `dispatch/`, `backend/`, or `interface/` imports dispatch functionality  
**Then** it SHALL import from `dispatch.package.module` not root-level `dispatch`

#### Scenario: Test imports use modern paths

**When** test code imports dispatch functionality  
**Then** it SHALL import from `dispatch.orchestrator` not `dispatch`

#### Scenario: Documentation examples use modern paths

**When** documentation shows import examples  
**Then** it SHALL show modern import paths (e.g., `from dispatch.orchestrator import DispatchOrchestrator`)

---

### Requirement: Legacy root modules are removed

Root-level legacy modules SHALL be deleted:
- `dispatch.py`
- `utils.py`
- `edi_tweaks.py`
- `edi_validator.py`
- `schema.py`
- `create_database.py`

#### Scenario: Deleted modules are not importable

**When** a script tries to import from a deleted legacy module  
**Then** it SHALL fail with `ModuleNotFoundError`

#### Scenario: Scripts using deleted modules are updated

**When** a script imports from a deleted legacy module  
**Then** the script SHALL be updated to use the modern import path

---

### Requirement: Single canonical location for each symbol

Each symbol SHALL be defined in exactly one location in the modern package structure.

#### Scenario: DispatchOrchestrator canonical location

**When** code needs `DispatchOrchestrator`  
**Then** it SHALL import from `dispatch.orchestrator` (its canonical location)

#### Scenario: No duplicate symbol definitions

**When** a symbol is available via `dispatch/__init__.py`  
**Then** it SHALL be importable from both the package root and its defining module