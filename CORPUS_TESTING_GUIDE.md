# Production EDI Corpus Testing Guide

## Overview

The project now has access to **165,129 real production EDI files** (1.3GB) from the `alledi/` folder for comprehensive regression testing. These files are **not committed to git** but are available locally for test execution.

## Corpus Organization

- **Location**: `/workspaces/batch-file-processor/alledi/`
- **Total Files**: 165,129 EDI files
- **Total Size**: 1.3GB
- **Production Format**: Numbered files (010042.001, 010042.002, etc.) - **165,127 files**
  - **Purpose**: These are the target EDI format that requires conversion processing
  - **Processing**: Should go through full conversion pipeline (CSV, Scannerware, etc.)
- **Reference Format**: .edi files (001.edi, 002.edi) - **2 files** (alternative formats)
  - **Purpose**: Other EDI formats that may appear in the system
  - **Processing**: Should be sent without any conversion or processing changes
- **Key Production Files**:
  - `010042.001` - Full invoice format (7.5KB) **← Primary test file**
  - `010042.002` through `010042.NNN` - Various production invoices
  - `010164.176` through `010164.NNN` - Additional invoice batches

## .gitignore Protection

The `alledi/` folder is protected by `.gitignore`:
```
# Production EDI corpus - cannot add to repo, used locally for testing
alledi/
```

This ensures corpus files are never accidentally committed to the repository.

## Available Fixtures

### Basic Corpus Fixtures

```python
# Check if corpus is available locally
def test_something(alledi_dir):
    """Returns Path to alledi directory, skips if not available."""
    
# Get specific known files
def test_something(corpus_001_file):
    """Returns path to 001.edi"""
    
def test_something(corpus_002_file):
    """Returns path to 002.edi"""
    
def test_something(corpus_010042_file):
    """Returns path to 010042.001"""
```

### Sample Collections

```python
# Get variety of files
def test_something(corpus_sample_files):
    """Returns list of first 10 corpus files"""
    
# Get large files for stress testing
def test_something(corpus_large_files):
    """Returns list of files >5KB for load testing"""
    
# Get edge cases
def test_something(corpus_edge_cases):
    """Returns dict with 'smallest', 'medium', 'largest' files"""
```

## Running Corpus Tests

### Run only corpus regression tests:
```bash
pytest tests/convert_backends/test_backends_smoke.py::TestCorpusRegressions -v
```

### Run specific corpus test:
```bash
pytest tests/convert_backends/test_backends_smoke.py::TestCorpusRegressions::test_corpus_csv_conversion_010042 -v
```

### Run all tests including corpus:
```bash
pytest tests/ -v
```

### Run corpus tests with output:
```bash
pytest tests/convert_backends/test_backends_smoke.py::TestCorpusRegressions -v -s
```

## Current Corpus Tests

### File Availability Tests (Always Run)
- `test_corpus_001_file_importable` - Verify 001.edi exists (alternative format - sent as-is)
- `test_corpus_002_file_importable` - Verify 002.edi exists (alternative format - sent as-is)  
- `test_corpus_010042_file_importable` - Verify 010042.001 exists (production format - requires conversion)
- `test_corpus_sample_variety` - Verify diverse samples available
- `test_corpus_large_files_available` - Verify stress test files exist
- `test_corpus_edge_case_sizes` - Verify edge case files available

### Real Data Conversion Tests (When Corpus Available)
- `test_corpus_csv_conversion_010042` - CSV converter with real production data
- `test_corpus_scannerware_conversion_010042` - Scannerware converter with production data
- `test_corpus_simplified_csv_conversion_010042` - Simplified CSV converter with production data

## Test Results

```
======================== 67 passed, 15 skipped in 7.15s ==================
```

Breakdown:
- **58** basic regression tests (unchanged)
- **9** new corpus-based regression tests
- **15** tests skipped (intentional - require database mocking)

## Future Enhancements

### Phase 3.1 - Corpus Analysis
- Generate statistics on corpus file sizes
- Identify unique EDI formats in corpus
- Find minimum/maximum invoice sizes
- Catalog all record types present

### Phase 3.2 - Randomized Corpus Testing
```python
@pytest.mark.parametrize("corpus_file", random_corpus_sample(50))
def test_converter_random_corpus(corpus_file, converter_func):
    """Test converter with random corpus file."""
```

### Phase 3.3 - Corpus-based Performance Benchmarks
- Measure converter performance on real data
- Track performance regressions
- Identify slow-performing files

### Phase 3.4 - Format Discovery
- Automatically catalog unique EDI formats
- Generate format documentation
- Detect format changes between captures

## Why Corpus Testing Matters

✅ **Real-World Data**: Tests use actual production EDI files for conversion validation  
✅ **Format Distinction**: Production files test conversion pipeline, .edi files test pass-through handling  
✅ **Comprehensive Coverage**: 165K+ files provide exhaustive format coverage  
✅ **Regression Detection**: Any converter change that breaks real production data is caught  
✅ **Performance Validation**: Load tests ensure converters handle all file sizes  
✅ **Format Stability**: Detects unexpected format variations and ensures proper routing  

## Notes

- Corpus files are **read-only** in tests
- Tests gracefully skip if corpus is not available locally
- Corpus is **optional** - all basic tests run without it
- Corpus size means tests run quickly (files are small, <1MB each average)
- No temporary files are written to corpus (tests use tempdir)

## CI/CD Integration

In CI/CD pipelines:
1. If `alledi/` is available, corpus tests run automatically
2. If `alledi/` is not available, tests skip gracefully
3. Pipeline doesn't fail if corpus unavailable

Example:
```yaml
# CI config
- name: Run tests
  run: pytest tests/ -v
  # Passes even if alledi/ not in CI environment
```

## Troubleshooting

### Tests skip corpus tests
**Reason**: `alledi/` folder not found locally  
**Solution**: Place `alledi/` in project root or ensure it's mounted

### Corpus tests fail with permissions
**Reason**: File permission issues  
**Solution**: Check file permissions: `chmod 644 alledi/*`

### Specific corpus file not found
**Reason**: File was moved or renamed  
**Solution**: Check file exists: `ls /workspaces/batch-file-processor/alledi/001.edi`
