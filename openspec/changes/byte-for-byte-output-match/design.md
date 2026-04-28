# Design: Byte-for-Byte Output Match Testing

## Context

The batch-file-processor application converts EDI files to various formats (scannerware, csv, estore_einvoice, tweaks, etc.). These converters are critical for downstream integrations that expect specific output formats. However, there's no automated way to verify that code changes haven't inadvertently altered output.

The project already has:
- A converter plugin system (`dispatch/converters/convert_to_*.py`)
- A pipeline step for conversion (`dispatch/pipeline/converter.py`)
- Integration tests (`tests/integration/`)
- Existing converter unit tests

We need to add a "golden file" test framework that:
1. Stores reference output for each converter format
2. Runs converters against test inputs
3. Compares output byte-for-byte against stored references
4. Provides clear failure messages when output differs

## Goals

### Goals

- Detect output regressions before they reach production
- Document expected output format for each converter
- Make it easy to update golden files when changes are intentional
- Provide clear diff output when comparisons fail
- Work with existing test infrastructure (pytest)

### Non-Goals

- Replace existing unit/integration tests
- Test performance (focus on correctness)
- Test all possible input variations (focus on representative cases)
- Generate golden files automatically from production (manual curation)

## Decisions

### Decision: Golden files stored in repository

**Choice:** Store golden files in `tests/golden_files/` directory within the repository.

**Rationale:**
- Version controlled with code
- Reviewed in pull requests
- Easy to audit changes
- Backup/removal tracked in git

### Decision: YAML metadata alongside golden files

**Choice:** Each golden file has a corresponding `.yaml` metadata file with test parameters and expected behavior.

**Rationale:**
- Self-documenting test cases
- Parameters stored separately from binary data
- Can include expected exceptions, warnings
- Change history tracking in git

### Decision: Binary comparison, not text comparison

**Choice:** Compare files as binary, not as text.

**Rationale:**
- Line endings are part of the format spec
- Avoids Python's platform-specific line ending handling
- True byte-for-byte verification
- Simpler implementation

### Decision: pytest fixture-based approach

**Choice:** Implement as pytest fixtures and parameterized tests.

**Rationale:**
- Integrates with existing pytest infrastructure
- Easy to run subset of tests
- Supports `--update-golden` flag
- Existing team familiarity with pytest

### Decision: Separate "update" from "test" modes

**Choice:** Running tests has two modes: compare (default) and generate.

**Rationale:**
- Prevents accidental overwrites
- Explicit flag required to update
- Can require justification for updates
- Safe for CI/CD

## Directory Structure

```
tests/golden_files/
├── scannerware/
│   ├── inputs/
│   │   ├── 001_basic_invoice.edi
│   │   └── 002_credit_memo.edi
│   ├── expected/
│   │   ├── 001_basic_invoice.out
│   │   └── 002_credit_memo.out
│   └── metadata/
│       ├── 001_basic_invoice.yaml
│       └── 002_credit_memo.yaml
├── csv/
│   └── ...
├── tweaks/
│   └── ...
└── README.md  (workflow documentation)
```

## Test Implementation

### GoldenFixture

```python
@pytest.fixture
def golden_fixture(format_name, test_case_id):
    """Loads golden file test case and parameters."""
    # Load metadata from YAML
    # Load input file
    # Load expected output
    # Return tuple of (input_path, expected_path, params)
```

### GoldenTest class

```python
class TestGoldenOutput:
    @pytest.mark.parametrize("format,test_case", load_test_cases())
    def test_output_matches_golden(self, format, test_case):
        # Run converter
        # Compare output to golden
        # Fail with diff if mismatch
```

### CLI integration

```bash
# Run tests (compare mode)
pytest tests/unit/test_golden_output.py -v

# Generate/update golden files (with confirmation)
pytest tests/unit/test_golden_output.py --update-golden

# Update specific test case
pytest tests/unit/test_golden_output.py --update-golden -k "001_basic"
```

## Output Comparison

### Comparison Algorithm

1. Load expected file as bytes
2. Run converter with test input
3. Load actual output as bytes
4. If lengths differ → fail with size info
5. Compare byte-by-byte
6. On first difference → report offset and context

### Failure Message Format

```
AssertionError: Output mismatch for scannerware/001_basic_invoice
  File size: expected 1234 bytes, got 1235 bytes
  First difference at byte 567:
    Expected: 0x41 ('A')
    Actual:   0x61 ('a')
  Expected (hex): 41 42 43 44...
  Actual (hex):   61 62 63 64...
```

## Risks / Trade-offs

### Risk: Golden file maintenance burden

**Description:** Golden files must be updated when output changes intentionally.

**Mitigation:**
- Make update workflow easy and documented
- Require justification for updates (stored in git)
- Keep number of golden files manageable (representative cases, not exhaustive)

### Risk: Brittleness from over-specification

**Description:** Byte-for-byte comparison is very strict - minor formatting changes break tests.

**Mitigation:**
- Document acceptable variation per format
- Use `--update-golden` for intentional format evolution
- Focus on "representative" test cases, not edge cases

### Trade-off: Test coverage vs maintenance

**Trade-off:** More golden files = better coverage, but more maintenance.

**Resolution:** Start with 2-3 representative cases per format. Add more based on bug reports and regression history.

## Initial Implementation Scope

For the initial implementation, focus on:
1. **scannerware format** - Most commonly used
2. **tweaks format** - Complex transformations, high regression risk
3. **csv format** - Common output format

Add more formats as the framework proves stable.

## Testing the Testing Framework

The golden file framework itself needs tests:
- Unit test for comparison logic
- Test that confirms diff output is correct
- Test update mode works correctly

Initial golden files will be generated from known-good output, then verified to pass.

## Security Considerations

- Golden files could contain sensitive test data → use synthetic/fake data
- YAML metadata could contain injection paths → validate/sanitize
- No network access required for golden tests → safe for isolated environments