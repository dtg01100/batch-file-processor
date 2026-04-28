# Spec: Entry Point Compatibility

## Overview

Define how CLI entry points and scripts from the earlier version remain functional.

## ADDED Requirements

### Requirement: main_interface.py entry point works

The `main_interface.py` file SHALL remain the primary entry point for running the application.

#### Scenario: Direct script execution

**When** user runs `python main_interface.py`  
**Then** the application SHALL start and display the Qt interface

#### Scenario: Module execution

**When** user runs `python -m main_interface`  
**Then** the application SHALL start

---

### Requirement: main_qt.py alias works

The `main_qt.py` file SHALL delegate to `main_interface.main()`.

#### Scenario: Alternative entry point

**When** user runs `python main_qt.py`  
**Then** it SHALL behave identically to `main_interface.py`

---

### Requirement: CLI arguments remain compatible

The application SHALL accept the same CLI arguments as the earlier version.

#### Scenario: Automatic/headless mode

**When** user runs `python main_interface.py -a`  
**Then** the application SHALL run in headless/automatic processing mode

#### Scenario: Help flag

**When** user runs `python main_interface.py --help`  
**Then** the application SHALL display usage information

---

### Requirement: Run scripts work

Any shell scripts that invoked the application SHALL continue to work.

#### Scenario: run.sh execution

**When** user runs `./run.sh`  
**Then** the application SHALL start normally