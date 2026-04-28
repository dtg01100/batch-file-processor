# Spec: Database Compatibility

## Overview

Define how existing SQLite databases from earlier versions remain compatible. Database compatibility is preserved; this spec documents existing behavior.

## MODIFIED Requirements

### Requirement: Database schema migration path maintained

The database migration system SHALL support migrating from the earliest supported version.

#### Scenario: Fresh database creation

**When** a new database is created  
**Then** it SHALL have the current schema version

#### Scenario: Existing database upgrade

**When** an existing database with schema version X is opened  
**Then** the system SHALL migrate it to the current version through all intermediate migrations

#### Scenario: Migration rollback safety

**When** a migration fails mid-way  
**Then** the database SHALL remain in its original state (transaction rollback)

---

### Requirement: Configuration format conversion

The compatibility layer SHALL convert between legacy flat config and modern nested config formats.

#### Scenario: Legacy config loading

**When** a legacy flat backend config is loaded  
**Then** it SHALL be converted to nested format via `convert_backend_config()`

#### Scenario: Modern config writing

**When** backend config is written to database  
**Then** it SHALL use the current schema format

#### Scenario: Folder config migration

**When** a folder record from an old database is loaded  
**Then** it SHALL be converted to the modern format via `legacy_config_to_modern()`

---

### Requirement: Database upgrades preserve user preferences

**CRITICAL: Database upgrades MUST preserve all user preferences and settings. If something is renamed in the schema, the database migration MUST follow and update stored preferences accordingly.**

#### Scenario: Column renamed in schema

**When** a schema upgrade renames a column (e.g., `format` -> `output_format`)  
**Then** the migration SHALL update all stored preferences referencing the old name

#### Scenario: Table renamed in schema

**When** a schema upgrade renames a table  
**Then** the migration SHALL update all references and foreign keys accordingly

#### Scenario: Format name changed

**When** a format name is changed in the schema (e.g., "tweaks" to "edi_tweaks")  
**Then** the migration SHALL update all folder records with the old format name to the new name

#### Scenario: Preference values preserved

**When** a database upgrade runs  
**Then** ALL preference values SHALL be preserved exactly as-is, only structural changes are applied

#### Scenario: Cascade updates for renamed entities

**When** an entity is renamed that has dependencies (foreign keys, references)  
**Then** the migration SHALL update all dependent records to maintain referential integrity