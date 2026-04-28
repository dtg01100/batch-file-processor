# Tasks: Byte-for-Byte Output Match Testing

## 1. Infrastructure Setup

### Directory Structure and Documentation

- [ ] 1.1 Create `tests/golden_files/` directory structure for all formats
- [ ] 1.2 Create `tests/golden_files/README.md` with workflow documentation
- [ ] 1.3 Create `tests/golden_files/scannerware/` subdirectories (inputs, expected, metadata)
- [ ] 1.4 Create `tests/golden_files/tweaks/` subdirectories
- [ ] 1.5 Create `tests/golden_files/csv/` subdirectories

## 2. Test Framework Implementation

### Core Test Infrastructure

- [ ] 2.1 Create `tests/unit/test_golden_output.py` with TestGoldenOutput class
- [ ] 2.2 Implement `load_test_cases()` function to discover golden file test cases
- [ ] 2.3 Implement `golden_fixture` pytest fixture for loading test data
- [ ] 2.4 Implement `compare_bytes()` function for binary comparison
- [ ] 2.5 Implement diff reporting with byte offset, hex dump, and context

### CLI Integration

- [ ] 2.6 Add `--update-golden` pytest flag to enable update mode
- [ ] 2.7 Add `--update-reason` option for documenting golden file changes
- [ ] 2.8 Implement confirmation prompt for golden file updates
- [ ] 2.9 Implement backup of previous golden file before update

## 3. Scannerware Golden Files

### Initial Test Cases

- [ ] 3.1 Create `tests/golden_files/scannerware/inputs/001_basic_invoice.edi` with basic EDI invoice
- [ ] 3.2 Create `tests/golden_files/scannerware/expected/001_basic_invoice.out` with known-good output
- [ ] 3.3 Create `tests/golden_files/scannerware/metadata/001_basic_invoice.yaml` with parameters
- [ ] 3.4 Create `tests/golden_files/scannerware/inputs/002_credit_memo.edi` with credit memo
- [ ] 3.5 Create `tests/golden_files/scannerware/expected/002_credit_memo.out`
- [ ] 3.6 Create `tests/golden_files/scannerware/metadata/002_credit_memo.yaml`
- [ ] 3.7 Create `tests/golden_files/scannerware/inputs/003_split_prepaid.edi` testing C-record generation
- [ ] 3.8 Create corresponding expected and metadata files

## 4. Tweaks Golden Files

### Initial Test Cases

- [ ] 4.1 Create `tests/golden_files/tweaks/inputs/001_basic_tweak.edi` with test data
- [ ] 4.2 Create `tests/golden_files/tweaks/expected/001_basic_tweak.out` with tweaked output
- [ ] 4.3 Create `tests/golden_files/tweaks/metadata/001_basic_tweak.yaml` with tweak parameters
- [ ] 4.4 Create test case for A-record padding (001_padding.edi)
- [ ] 4.5 Create test case for invoice date offset (001_date_offset.edi)
- [ ] 4.6 Create test case for UPC override from lookup table

## 5. CSV Golden Files

### Initial Test Cases

- [ ] 5.1 Create `tests/golden_files/csv/inputs/001_basic_invoice.csv` (EDI input, CSV output)
- [ ] 5.2 Create `tests/golden_files/csv/expected/001_basic_invoice.out` with CSV output
- [ ] 5.3 Create `tests/golden_files/csv/metadata/001_basic_invoice.yaml`
- [ ] 5.4 Create test case with quoted fields containing delimiters
- [ ] 5.5 Create test case with leading zeros preservation

## 6. Additional Converter Support

### Other Formats

- [ ] 6.1 Add golden files for `estore_einvoice` format
- [ ] 6.2 Add golden files for `estore_einvoice_generic` format
- [ ] 6.3 Add golden files for `fintech` format
- [ ] 6.4 Add golden files for `jolley_custom` format
- [ ] 6.5 Add golden files for `scansheet_type_a` format
- [ ] 6.6 Add golden files for `simplified_csv` format
- [ ] 6.7 Add golden files for `stewarts_custom` format
- [ ] 6.8 Add golden files for `yellowdog_csv` format

## 7. Test Coverage Tracking

### Coverage Reporting

- [ ] 7.1 Implement format coverage tracking in test collection
- [ ] 7.2 Add warning for formats without golden files during test collection
- [ ] 7.3 Create `coverage_report()` function to show coverage status
- [ ] 7.4 Add `--format-coverage` CLI option to show coverage report

## 8. Framework Self-Testing

### Test the Tests

- [ ] 8.1 Create unit tests for `compare_bytes()` function
- [ ] 8.2 Create unit tests for diff reporting format
- [ ] 8.3 Create integration test for `--update-golden` flag
- [ ] 8.4 Create test for confirmation prompt behavior
- [ ] 8.5 Create test for backup file creation

## 9. CI/CD Integration

### Automation

- [ ] 9.1 Add golden output tests to CI pipeline
- [ ] 9.2 Configure CI to fail on golden file mismatch (compare mode only)
- [ ] 9.3 Document golden file update process for developers

## 10. Documentation

### End-User Documentation

- [ ] 10.1 Update `tests/golden_files/README.md` with complete workflow
- [ ] 10.2 Document how to add new test cases
- [ ] 10.3 Document how to update existing golden files
- [ ] 10.4 Document CI behavior and expectations
- [ ] 10.5 Add examples of diff output for failed tests

## 11. Cleanup and Polish

### Final Tasks

- [ ] 11.1 Verify all existing converter tests still pass
- [ ] 11.2 Run full test suite with golden file tests
- [ ] 11.3 Create summary document of all golden file test cases

---

## Implementation Status

### Phase 1: Core Infrastructure - COMPLETED

- [x] 1.1 Create `tests/golden_files/` directory structure
- [x] 1.2 Create `tests/golden_files/README.md`
- [x] 1.3 Create `tests/golden_files/scannerware/` subdirectories
- [x] 1.4 Create `tests/golden_files/tweaks/` subdirectories
- [x] 1.5 Create `tests/golden_files/csv/` subdirectories
- [x] 2.1 Create `tests/unit/test_golden_output.py`
- [x] 2.2 Implement `load_test_cases()` function
- [x] 2.4 Implement `compare_bytes()` function
- [x] 2.5 Implement diff reporting
- [x] 2.6 Add `--update-golden` pytest flag
- [x] 8.1 Create unit tests for `compare_bytes()`
- [x] 8.2 Create unit tests for diff reporting

### Phase 2: Initial Golden Files - COMPLETED

- [x] 3.1 Create scannerware `001_basic_invoice.edi`
- [x] 3.2 Create scannerware `001_basic_invoice.out`
- [x] 3.3 Create scannerware `001_basic_invoice.yaml`
- [x] 4.1 Create tweaks `001_basic_tweak.edi`
- [x] 4.2 Create tweaks `001_basic_tweak.out`
- [x] 4.3 Create tweaks `001_basic_tweak.yaml`
- [x] 5.1 Create csv `001_basic_invoice.edi`
- [x] 5.2 Create csv `001_basic_invoice.out`
- [x] 5.3 Create csv `001_basic_invoice.yaml`

### Phase 3: Additional Formats - NOT STARTED

- [ ] 6.1-6.8 Add golden files for remaining 8 formats
- [ ] 3.4-3.8, 4.4-4.6, 5.4-5.5 Additional test cases per format
- [ ] 7.1-7.4 Coverage tracking implementation
- [ ] 2.7-2.9 CLI integration refinements
- [ ] 9.1-9.3 CI/CD integration
- [ ] 10.1-10.5 Documentation updates
- [ ] 11.1-11.3 Final cleanup