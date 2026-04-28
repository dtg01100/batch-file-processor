# AGENT_PLAN.md

## Byte-for-Byte Output Match - Next Session Plan

**Last Session:** 2026-04-28 12:15-12:17 UTC
**Status:** Phase 1 (Infrastructure) and Phase 2 (Initial Golden Files) complete

---

## Work Prioritization Matrix

| Priority | Task | Est. Time | Status | Blocker |
|----------|------|-----------|--------|---------|
| 1 | Add more test cases per format | 2-3 hours | not-started | None |
| 2 | Add golden files for remaining 8 formats | 4-6 hours | not-started | None |
| 3 | CLI integration (--update-golden) | 1-2 hours | not-started | None |
| 4 | CI/CD integration | 1 hour | not-started | None |
| 5 | Documentation updates | 1 hour | not-started | None |

---

## Task Breakdown

### Task 1: Add More Test Cases Per Format

**Why:** Need comprehensive coverage of converter features

#### Scannerware (4.1-4.6)
- [ ] `002_credit_memo.edi` - Test credit memo records
- [ ] `003_split_prepaid.edi` - Test C-record generation
- [ ] `004_date_offset.edi` - Test invoice date offsetting
- [ ] `005_multi_item.edi` - Test multiple B records

#### Tweaks (5.1-5.6)
- [ ] `002_a_record_padding.edi` - Test A-record padding
- [ ] `003_upc_override.edi` - Test UPC lookup override

#### CSV (6.1-6.5)
- [ ] `002_quoted_fields.edi` - Test quoted fields with delimiters
- [ ] `003_leading_zeros.edi` - Test leading zeros preservation

### Task 2: Add Golden Files for Remaining Formats

**Why:** Expand coverage to all 11 formats

| Format | Test Cases | Priority |
|--------|-----------|----------|
| estore_einvoice | 1-2 | medium |
| estore_einvoice_generic | 1-2 | medium |
| fintech | 1-2 | medium |
| jolley_custom | 1-2 | low |
| scansheet_type_a | 1-2 | medium |
| simplified_csv | 1-2 | low |
| stewarts_custom | 1-2 | low |
| yellowdog_csv | 1-2 | low |

### Task 3: CLI Integration

**Why:** Make golden file updates easier

- [ ] Add pytest plugin for `--update-golden` flag
- [ ] Add confirmation prompt
- [ ] Add backup of previous golden file

### Task 4: CI/CD Integration

**Why:** Automate golden file checks

- [ ] Add golden output tests to CI pipeline
- [ ] Configure CI to fail on golden file mismatch (compare mode only)
- [ ] Document golden file update process

### Task 5: Documentation Updates

**Why:** Ensure team can use the system

- [ ] Update README with complete workflow
- [ ] Add examples of diff output
- [ ] Document CI behavior

---

## Testing Requirements

### What Needs Testing

1. **New test cases:** Run converter, verify output, save golden files
2. **Existing tests:** Ensure no regression
3. **CLI integration:** Test --update-golden flag
4. **Coverage report:** Verify all formats listed

### How to Verify

```bash
# Run all golden output tests
.venv/bin/python -m pytest tests/unit/test_golden_output.py -v

# Run with coverage report
.venv/bin/python -m pytest tests/unit/test_golden_output.py::TestFormatCoverage -v

# Verify converter output matches
.venv/bin/python -c "
from dispatch.converters.convert_to_scannerware import edi_convert
import tempfile, os

# Read input, run converter, compare to golden
..."
```

### Regression Checks

- Scannerware converter still produces correct output
- Tweaks converter still processes A/B/C records
- CSV converter still produces quoted CSV format

---

## Known Blockers

1. **Tweaks requires numeric invoice number:** Some test cases may fail if "[REDACTED]" is used in A-record position 7-17
2. **Format discovery relies on directory naming:** Must follow `tests/golden_files/<format>/` pattern

---

## Files to Check Before Starting

- `tests/golden_files/README.md` - Workflow documentation
- `tests/unit/test_golden_output.py` - Test framework
- `tests/golden_files/scannerware/` - Existing scannerware test case
- `tests/golden_files/tweaks/` - Existing tweaks test case
- `tests/golden_files/csv/` - Existing csv test case

---

## Quick Start Commands

```bash
# 1. Verify current state
.venv/bin/python -m pytest tests/unit/test_golden_output.py -v

# 2. Add new test case for scannerware:
#    - Create tests/golden_files/scannerware/inputs/002_<name>.edi
#    - Run converter manually to generate expected output
#    - Save to tests/golden_files/scannerware/expected/002_<name>.out
#    - Create metadata in tests/golden_files/scannerware/metadata/002_<name>.yaml

# 3. Run tests again to verify
.venv/bin/python -m pytest tests/unit/test_golden_output.py -v
```