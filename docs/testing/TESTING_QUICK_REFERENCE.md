# New Test Suite Quick Reference

**Created:** March 10, 2026  
**Total New Tests:** 220+ test cases across 8 files

---

## Quick Start

### Run All New Tests
```bash
pytest tests/qt/test_processed_files_dialog_comprehensive.py \
       tests/qt/test_qt_components.py \
       tests/integration/test_complete_user_workflows_e2e.py \
       tests/integration/test_multi_folder_processing_e2e.py \
       tests/integration/test_plugin_system_e2e.py \
       tests/integration/test_data_migration_scenarios.py \
       tests/integration/test_performance_benchmarks.py \
       -v
```

### Run by Test Type
```bash
# GUI Tests
pytest tests/qt/ -v -k "processed_files or components"

# E2E Workflow Tests  
pytest tests/integration/test_complete_user_workflows_e2e.py -v

# Multi-Folder Tests
pytest tests/integration/test_multi_folder_processing_e2e.py -v

# Plugin Tests
pytest tests/integration/test_plugin_system_e2e.py -v -m plugin

# Migration Tests
pytest tests/integration/test_data_migration_scenarios.py -v -m migration

# Performance Tests (slow - run separately)
pytest tests/integration/test_performance_benchmarks.py -v -m performance
```

---

## Test Files Overview

| File | Tests | Category | Priority |
|------|-------|----------|----------|
| `test_processed_files_dialog_comprehensive.py` | 28 | GUI | High |
| `test_qt_components.py` | 29 | GUI | Medium |
| `test_complete_user_workflows_e2e.py` | 18 | E2E | High |
| `test_multi_folder_processing_e2e.py` | 17 | E2E | High |
| `test_plugin_system_e2e.py` | 17 | E2E | High |
| `test_data_migration_scenarios.py` | 19 | E2E | High |
| `test_performance_benchmarks.py` | 15 | Perf | Low |

---

## Test Markers

New markers added to `pytest.ini`:

```bash
# Run by marker
pytest -m performance  # Performance benchmarks
pytest -m security     # Security validation
pytest -m migration    # Database migration
pytest -m plugin       # Plugin system
pytest -m workflow     # Complete workflows
```

---

## Key Test Coverage

### ✅ GUI Components
- ProcessedFilesDialog (search, filter, bulk ops, export)
- Edit Folders Dialog components (builders, extractors, handlers)
- Keyboard shortcuts
- Large dataset handling (1000+ files)

### ✅ End-to-End Workflows
- Add Folder → Configure → Process → View Results
- Edit Settings → Save → Verify Persistence  
- Error → Retry → Success
- Multi-folder processing (sequential & parallel)
- Plugin system integration
- Database migration (v1/v2/v3 → current)

### ✅ Performance
- File count scalability (10 → 1000 files)
- Database size (10 → 10,000 records)
- Memory usage tracking
- Disk I/O benchmarks
- UI responsiveness
- Concurrent processing

### ✅ Security
- SQL injection prevention
- Path traversal attacks
- Malicious file content
- Invalid EDI formats
- Unicode/encoding attacks

---

## CI/CD Integration

### GitHub Actions Example
```yaml
name: Tests
on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      
      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.11'
      
      - name: Install dependencies
        run: pip install -r requirements-dev.txt
      
      - name: Run unit tests
        run: pytest -m unit -v
      
      - name: Run integration tests
        run: pytest -m integration -v
      
      - name: Run GUI tests
        run: pytest -m qt -v
      
      - name: Run E2E workflow tests
        run: pytest -m e2e -m workflow -v

  performance:
    runs-on: ubuntu-latest
    if: github.event_name == 'schedule'  # Nightly
    steps:
      - uses: actions/checkout@v3
      - name: Run performance tests
        run: pytest -m performance -v
```

---

## Performance Test Guidelines

Performance tests are marked with `@pytest.mark.performance` and should be run separately:

```bash
# Quick tests (exclude performance)
pytest -m "not performance" -v

# Performance benchmarks only
pytest -m performance -v

# With timing output
pytest -m performance -v -s
```

**Expected Performance Benchmarks:**
- 10 files: < 5 seconds
- 100 files: < 30 seconds
- 1000 files: < 300 seconds
- Database query (10k records): < 5 seconds
- Memory usage: < 500 MB peak

---

## Troubleshooting

### Tests Too Slow
```bash
# Run specific test class
pytest tests/integration/test_performance_benchmarks.py::TestScalabilityByFileCount::test_process_10_files -v

# Run with shorter timeout
pytest --timeout 60 -v
```

### Qt Tests Fail
```bash
# Ensure offscreen platform
export QT_QPA_PLATFORM=offscreen
pytest tests/qt/ -v
```

### Database Tests Fail
```bash
# Clean test database
rm -rf /tmp/test_databases/*
pytest tests/integration/ -v
```

---

## Test Development

### Adding New Tests

1. **Choose correct file:**
   - GUI tests → `tests/qt/`
   - E2E tests → `tests/integration/`
   - Performance → `test_performance_benchmarks.py`

2. **Add appropriate markers:**
   ```python
   pytestmark = [pytest.mark.qt, pytest.mark.gui]
   
   @pytest.mark.performance
   def test_something():
       pass
   ```

3. **Use fixtures:**
   ```python
   @pytest.fixture
   def sample_data():
       # Setup
       yield data
       # Teardown
   ```

4. **Follow naming convention:**
   - File: `test_<feature>.py`
   - Class: `Test<Feature>`
   - Function: `test_<scenario>`

---

## Coverage Reports

```bash
# Generate coverage report
pytest --cov=. --cov-report=html

# View coverage for new tests only
pytest --cov=dispatch --cov=interface tests/qt/test_processed_files_dialog_comprehensive.py
```

---

## Maintenance

### Regular Tasks
- [ ] Run full test suite weekly
- [ ] Run performance benchmarks nightly
- [ ] Review and update benchmarks quarterly
- [ ] Add tests for new features
- [ ] Remove or update flaky tests

### Test Metrics to Track
- Total test count
- Test execution time
- Coverage percentage
- Flaky test rate
- Performance trends

---

## Documentation

- `TESTING_GAP_ANALYSIS_2026.md` - Original gap analysis
- `TESTING_IMPLEMENTATION_SUMMARY.md` - Implementation details
- `TESTING_QUICK_REFERENCE.md` - This document

---

## Support

For questions about the new test suite:
1. Check documentation files
2. Review test examples in existing files
3. Run `pytest --help` for pytest options
4. Consult pytest-qt documentation for GUI tests

---

**Last Updated:** March 10, 2026  
**Maintained By:** Development Team
