# Golden File Tests

This directory contains reference output files for verifying converter output matches expected results byte-for-byte.

## Directory Structure

```
tests/golden_files/
├── <format_name>/
│   ├── inputs/           # Test input EDI files
│   ├── expected/        # Reference output files
│   └── metadata/         # Test parameters and configuration
├── scannerware/
├── tweaks/
├── csv/
└── README.md
```

## Adding New Test Cases

### 1. Create the test case files

For each test case, create three files:

**Input file** (`inputs/<test_id>_<description>.edi`):
```
EDI invoice content here
```

**Expected output** (`expected/<test_id>_<description>.out`):
```
Expected converter output here
```

**Metadata** (`metadata/<test_id>_<description>.yaml`):
```yaml
test_id: <test_id>
description: <description>
format: <converter_format>
parameters:
  convert_to_format: <format_name>
  # Additional converter parameters...
```

### 2. Test case naming conventions

- Use lowercase with underscores
- Include 3-digit numeric prefix for ordering (001, 002, etc.)
- Be descriptive: `001_basic_invoice`, `002_credit_memo`
- Match the prefix across all three files

## Running Tests

### Compare mode (default)

Run tests and compare output to golden files:
```bash
pytest tests/unit/test_golden_output.py -v
```

### Update mode

Update golden files with current output:
```bash
pytest tests/unit/test_golden_output.py --update-golden
```

You'll be prompted to enter a reason for the update, which is stored in the metadata.

### Specific format

Run tests only for a specific format:
```bash
pytest tests/unit/test_golden_output.py -v -k "scannerware"
```

### Specific test case

Run tests only for a specific test case:
```bash
pytest tests/unit/test_golden_output.py -v -k "001_basic"
```

## Understanding Test Failures

When a test fails, the output shows:
- Which test case failed
- Expected vs actual file size
- Byte offset of first difference
- Hex dump of differing region

Example failure output:
```
FAILED test_output_matches_golden[scannerware-001_basic]
AssertionError: Output mismatch for scannerware/001_basic
  File size: expected 1234 bytes, got 1235 bytes
  First difference at byte 567:
    Expected: 0x41 ('A')
    Actual:   0x61 ('a')
```

## When to Update Golden Files

Golden files should be updated when:
1. The converter's output intentionally changes
2. A bug fix changes the expected behavior
3. A new feature adds new output

Golden files should NOT be updated when:
1. There's a bug - fix the bug, not the golden file
2. Output differs without explanation - investigate first

## Supported Formats

The following formats have working golden file tests:

### Non-Database Formats

- `scannerware` - Scannerware EDI format (4 test cases)
- `tweaks` - EDI tweaks processing (3 test cases)
- `csv` - CSV output (3 test cases)

### Database-Dependent Formats

The following formats require AS400 database credentials:

| Format | Description | Test Cases |
|--------|-------------|------------|
| `jolley_custom` | Jolley custom CSV | 1 |
| `stewarts_custom` | Stewart's custom CSV | 1 |
| `fintech` | Fintech format | 1 |
| `estore_einvoice` | Estore E-Invoice | 1 |
| `estore_einvoice_generic` | Generic E-Invoice | 1 |

**Note:** `scansheet_type_a` was removed because it produces ZIP-based Excel files with non-deterministic timestamps, making byte-for-byte comparison unreliable.

Some converters require AS400 database credentials to run. These can be provided via environment variables without committing secrets.

#### Environment Variables

Set credentials in environment variables:
```bash
export AS400_USERNAME=your_username
export AS400_PASSWORD=your_password
export AS400_ADDRESS=your_address
```

#### Metadata Configuration

In metadata YAML files, reference environment variables using `${VAR}` syntax:

```yaml
test_id: "001"
description: "basic_invoice"
format: "jolley_custom"
parameters:
  convert_to_format: "jolley_custom"
  as400_username: "${AS400_USERNAME}"
  as400_address: "${AS400_ADDRESS}"
  as400_password: "${AS400_PASSWORD}"
```

The test framework automatically resolves `${VAR}` patterns from environment variables. Missing variables resolve to empty string.

#### Security Notes

- **Never commit credentials** - The `.gitignore` excludes `.env`, `.env.*`, `credentials*.txt`, and `secrets*.txt` files
- Use environment variables or a local `.env` file (gitignored) for development
- In CI, set credentials via secure environment variables

#### Available Database-Dependent Formats

| Format | Description | Required Credentials |
|--------|-------------|---------------------|
| `estore_einvoice` | Estore E-Invoice | as400_username, as400_address, as400_password |
| `estore_einvoice_generic` | Generic E-Invoice | as400_username, as400_address, as400_password |
| `fintech` | Fintech format | as400_username, as400_address, as400_password |
| `jolley_custom` | Jolley custom | as400_username, as400_address, as400_password |
| `stewarts_custom` | Stewart's custom | as400_username, as400_address, as400_password |

**Note:** `scansheet_type_a` produces ZIP-based Excel files with non-deterministic timestamps, so it was removed from golden file tests.

## CI/CD Integration

In CI, golden file tests run in compare mode only:
```bash
pytest tests/unit/test_golden_output.py -v
```

Updates require developer action and should be reviewed in pull requests.
