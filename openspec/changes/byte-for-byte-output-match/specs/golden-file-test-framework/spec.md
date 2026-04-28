# Spec: Golden File Test Framework

## Overview

Define the test infrastructure for verifying converter output matches reference files byte-for-byte.

## ADDED Requirements

### Requirement: Golden file storage structure

The system SHALL store reference output files in a structured directory hierarchy.

#### Scenario: Format-based directory organization

**When** a golden file is stored for a converter format  
**Then** it SHALL be stored in `tests/golden_files/<format_name>/` directory

#### Scenario: Test case file naming

**When** a golden file represents a specific test case  
**Then** it SHALL be named `<test_case_id>_<description>.edi` or `<test_case_id>_<description>.csv`

#### Scenario: Golden file metadata

**When** a golden file is stored  
**Then** a corresponding `<test_case_id>.yaml` metadata file SHALL exist with input parameters and expected behavior

---

### Requirement: Golden file comparison mechanism

The system SHALL provide a mechanism to compare current output against golden files.

#### Scenario: Byte-for-byte comparison

**When** a test compares output  
**Then** it SHALL perform binary comparison, not text comparison

#### Scenario: Whitespace and line ending handling

**When** the format specification allows for variable whitespace/line endings  
**Then** the comparison SHALL normalize these before comparing, OR the golden file SHALL match exactly

#### Scenario: Difference reporting

**When** a comparison fails  
**Then** the test SHALL report:
- Which file differs (expected vs actual)
- Byte offset of first difference
- Hex dump of differing region
- Size difference

---

### Requirement: Golden file test fixture

The system SHALL provide test fixtures that load golden files and run converters.

#### Scenario: Fixture loads golden file and input

**When** a test uses the golden fixture  
**Then** it SHALL automatically load:
- Input file from `tests/golden_files/<format>/inputs/`
- Expected output from `tests/golden_files/<format>/expected/`
- Metadata from `tests/golden_files/<format>/metadata/`

#### Scenario: Fixture parameterizes converter

**When** a test runs with a golden fixture  
**Then** it SHALL pass the converter's parameters from the metadata file

---

### Requirement: Test execution with golden comparison

Tests using golden files SHALL execute the converter and compare output.

#### Scenario: Successful match

**When** converter output matches golden file exactly  
**Then** the test SHALL pass

#### Scenario: Mismatch detected

**When** converter output differs from golden file  
**Then** the test SHALL fail with detailed diff output

#### Scenario: First-time golden file creation

**When** a test runs in "generate" mode  
**Then** it SHALL create the golden file from current output instead of comparing

---

### Requirement: Golden file update workflow

The system SHALL support intentional golden file updates with approval.

#### Scenario: Generate new golden file

**When** `--update-golden` flag is passed to test runner  
**Then** the test SHALL:
1. Run converter
2. Overwrite golden file with new output
3. Report that file was updated

#### Scenario: Update requires justification

**When** a golden file is updated  
**Then** the test SHALL:
1. Prompt for update reason
2. Store reason in metadata file's `change_reason` field
3. Create backup of previous golden file

---

### Requirement: Coverage tracking

The system SHALL track which converter formats have golden file tests.

#### Scenario: Format coverage report

**When** tests run with coverage tracking  
**Then** a report SHALL show which formats have golden files and which don't

#### Scenario: Missing coverage alert

**When** a converter format exists but has no golden files  
**Then** a warning SHALL be logged during test collection