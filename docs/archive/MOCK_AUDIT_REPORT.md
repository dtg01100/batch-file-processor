# Mock and Fake Audit Report

**Date:** March 18, 2026  
**Branch:** rambunctious-bike  
**Auditor:** GitHub Copilot

## Executive Summary

This audit examined the use of mocks and fakes across the batch-file-processor codebase to assess alignment with the project's testing philosophy of **minimizing mocks and fakes**. 

### Key Findings

✅ **Positive:**
- Strong testing philosophy documented in `.github/copilot-instructions.md` and `AGENTS.md`
- Comprehensive real-implementation fixtures available (temp databases, legacy DB fixtures)
- Deprecated fakes module with clear migration guidance
- Good use of pytest markers for test categorization
- Real Qt widgets used in offscreen mode for UI tests
- **Qt Testing Requirements now codified in instructions**: Use real widgets, never fake Qt APIs

⚠️ **Concerns**:
- Heavy mock usage in unit tests (especially `unittest.mock` imports)
- Benchmark scripts use mocks for external dependencies
- Some tests mock standard library functions that could use real implementations
- Documentation files contain mock-heavy examples

### Migration Progress (March 18, 2026)

✅ **Completed**:
- Removed deprecated `FakeEvent` fixtures from `tests/conftest.py`
- Migrated `test_pipeline_logging_validation.py` to use `temp_database` instead of `FakeTable`
- Replaced `FakeMaintenanceFunctions` with real implementation in `test_maintenance_dialog_extra.py`
- Replaced fake implementations with real `DatabaseObj` and `MaintenanceFunctions` in `test_dialog_contracts_wave4.py`
- Updated `test_folder_manager.py` protocol compliance tests to use real database
- Fixed `test_gui_stress_and_edge_cases.py` to use real implementations
- Removed unnecessary `os.path.getsize` and `os.path.exists` mocks
- Added Qt testing requirements to `.github/copilot-instructions.md` and `AGENTS.md`

⏳ **Remaining**:
- Documentation files still contain mock-heavy examples
- Some unit tests still over-mock file system operations

---

## Detailed Findings

### 1. Mock Usage by Category

#### A. **Test Files (Actual Code)**

**Heavy Mock Usage:**
- `tests/unit/test_utils_full.py` - Mocks `query_runner`, file operations
- `tests/unit/test_query_runner.py` - Extensive `@patch` decorators for pyodbc
- `tests/unit/test_send_base.py` - Uses mock backends (appropriate for I/O boundary)
- `tests/ui/test_widgets.py` - Mocks for signal testing
- `tests/ui/test_dialogs.py` - Mock dependencies
- `tests/operations/test_maintenance_operations.py` - Multiple mock imports
- `tests/operations/test_folder_operations.py` - Mock repository patterns

**Moderate/Justified Mock Usage:**
- `tests/integration/test_pipeline_logging_validation.py` - Uses fake backend implementations (tracking/failing) which is appropriate for integration testing
- `tests/qt/test_qt_widgets.py` - Real Qt widgets with minimal mocking
- `tests/test_dataset_shim.py` - Real database operations

**Benchmark Scripts:**
- `benchmark_performance.py` - Mocks `query_runner` to prevent DB connections
- `benchmark_full_pipeline.py` - Mocks converter modules and EDI processor

#### B. **Fake Implementations**

**Deprecated Fakes Module:** `tests/fakes.py`
- Contains: `FakeTable`, `FakeConnection`, `FakeDatabaseObj`, `FakeEvent`, `FakeWidget`, `FakeUIService`, `FakeProgressService`, `FakeMaintenanceFunctions`, `FakeResendService`
- **Status:** Deprecated with clear warnings
- **Migration Guide:** Points to `temp_database` fixture and real Qt widgets
- **Current Usage:** Still imported in some tests (e.g., `test_pipeline_logging_validation.py`)

**Legacy Stubs:**
- `doingstuffoverlay.py` - No-op stub for backward compatibility
- `database_import.py` - Stub with "not implemented" message
- `dialog.py` - Legacy base class stub

#### C. **Documentation Files (Mock Examples)**

**Heavy Mock Documentation:**
- `TESTING_BEST_PRACTICES.md` - Contains both good and bad examples
- `MINIMAL_MOCKING_REFERENCE.md` - Reference guide with mock examples
- `plans/NEXT_REFACTORING_BATCH_PLAN.md` - Extensive mock code samples (2800+ lines)
- `plans/TKINTER_CALLBACKS_TESTING_PLAN.md` - Mock-heavy testing patterns
- `SEPARATION_IMPLEMENTATION_PLAN.md` - Mock examples for service layer
- `docs/TESTING_DESIGN.md` - Mock patterns for testing design

---

### 2. Mock Patterns Identified

#### Pattern 1: **Standard Library Mocking** (⚠️ Concern)
```python
@patch('os.path.exists')
@patch('builtins.open')
@patch('json.load')
def test_process_files(mock_json, mock_open, mock_isfile, mock_listdir):
```
**Issue:** These could use `tmp_path` and real file operations instead.

#### Pattern 2: **Database Connection Mocking** (⚠️ Mixed)
```python
@patch('sqlite3.connect')
def test_database(mock_connect):
    mock_conn = MagicMock()
```
**Better Approach:** Use `temp_database` fixture with real SQLite connections.

#### Pattern 3: **External Service Mocking** (✅ Appropriate)
```python
@patch('backend.ftp_backend.FTP')
def test_ftp_upload(mock_ftp_class):
```
**Justification:** FTP/SMTP are external services - mocking is appropriate.

#### Pattern 4: **Query Runner Mocking** (⚠️ Could Be Real)
```python
with patch("query_runner.query_runner") as mock_qr:
    mock_qr.return_value.run_arbitrary_query.return_value = []
```
**Better Approach:** Use in-memory SQLite or temp database where possible.

#### Pattern 5: **Protocol-Compliant Fakes** (✅ Good)
```python
class TrackingBackend:
    def send(self, params, settings, filename):
        self.sent.append(filename)
        return True
```
**Justification:** Real implementations that satisfy interfaces without I/O.

---

### 3. Test Fixture Quality Assessment

#### Excellent Fixtures (✅)

**`tests/conftest.py`:**
- `legacy_v32_db` - Real legacy database copy
- `migrated_v42_db` - Real migrated database
- `temp_database` - In-memory SQLite for isolation

**`tests/qt/conftest.py`:**
- Real Qt application instances
- Offscreen platform configuration

#### Areas for Improvement (⚠️)

**Over-reliance on `MagicMock`:**
- Many unit tests use `MagicMock` where simple objects would suffice
- Example: Testing signal connections could use real Qt signals

**Missing Fixtures:**
- No fixture for common mock configurations (e.g., standard settings dict)
- No shared mock event objects (still using deprecated `FakeEvent`)

---

### 4. Compliance with Testing Philosophy

| Principle | Status | Notes |
|-----------|--------|-------|
| Minimize mocks and fakes | ⚠️ Partial | Heavy mock usage in unit tests |
| Prefer real implementations | ✅ Good | Database fixtures excellent |
| Use in-memory over mocks | ⚠️ Mixed | SQLite used, but query_runner often mocked |
| Mock only I/O boundaries | ✅ Good | FTP/SMTP appropriately mocked |
| Document why mocks used | ❌ Missing | Rarely documented why mock was necessary |

---

## Recommendations

### Priority 1: **Reduce Standard Library Mocking** (High Impact)

**Current:**
```python
@patch('os.path.exists')
@patch('builtins.open')
def test_file_processing(mock_open, mock_exists):
```

**Better:**
```python
def test_file_processing(tmp_path):
    test_file = tmp_path / "test.txt"
    test_file.write_text("content")
    # Use real file operations
```

**Action Items:**
1. Audit all `@patch('os.')` and `@patch('builtins.open')` usages
2. Replace with `tmp_path` fixture where feasible
3. Update `TESTING_BEST_PRACTICES.md` to emphasize this pattern

### Priority 2: **Migrate Away from Deprecated Fakes** (Medium Impact)

**Current:**
```python
from tests.fakes import FakeTable, FakeEvent
```

**Better:**
```python
# Use temp_database fixture
# Use real Qt widgets with qtbot
```

**Action Items:**
1. Search for all `from tests.fakes import` statements
2. Create migration tasks per test file
3. Eventually remove `tests/fakes.py` entirely

### Priority 3: **Database Mocking Reduction** (Medium Impact)

**Current:**
```python
@patch('sqlite3.connect')
def test_database(mock_connect):
```

**Better:**
```python
def test_database(temp_database):
    # Real SQLite operations
```

**Action Items:**
1. Identify tests mocking database connections
2. Convert to use `temp_database` or in-memory SQLite
3. Keep mocks only for external DB systems (AS/400, etc.)

### Priority 4: **Documentation Updates** (Low Impact)

**Action Items:**
1. Update `MINIMAL_MOCKING_REFERENCE.md` with real-implementation examples
2. Add "Why This Mock?" comments to existing mock-heavy tests
3. Create "Mock Decision Tree" in testing documentation

### Priority 5: **Benchmark Script Improvements** (Low Impact)

**Current:**
```python
with patch("query_runner.query_runner") as mock_qr:
```

**Better:**
```python
# Use real in-memory database for benchmarks
# More realistic performance measurements
```

**Action Items:**
1. Evaluate if benchmarks need query_runner at all
2. If yes, use real lightweight database
3. Document why mocks are necessary for benchmarks

---

## Mock Usage Statistics

### Import Patterns (by frequency)

| Import Pattern | Occurrences | Files |
|----------------|-------------|-------|
| `from unittest.mock import` | 50+ | Test files, benchmarks, scripts |
| `MagicMock()` | 100+ | Throughout test suite |
| `@patch()` | 100+ | Decorators in test files |
| `Mock()` | 50+ | Simple mock objects |

### Files with Heaviest Mock Usage

1. `plans/NEXT_REFACTORING_BATCH_PLAN.md` - 2800+ lines of mock examples
2. `plans/TKINTER_CALLBACKS_TESTING_PLAN.md` - 600+ lines of mock examples
3. `TESTING_BEST_PRACTICES.md` - 250+ lines of mock examples
4. `tests/unit/test_utils_full.py` - Heavy unittest.mock usage
5. `tests/unit/test_query_runner.py` - Extensive patching
6. `benchmark_full_pipeline.py` - Multiple patch contexts
7. `tests/operations/test_maintenance_operations.py` - Multiple mock imports

### Appropriate Mock Usage Examples

✅ **External Services:**
- FTP connections (`backend.ftp_backend.FTP`)
- SMTP connections (`smtplib.SMTP`)
- Network operations

✅ **UI Display Servers:**
- PyQt6 widget rendering (using offscreen mode instead)
- Screen display operations

✅ **Truly Expensive Operations:**
- AS/400 database queries (when real DB not available)
- External API calls

### Inappropriate Mock Usage Examples

⚠️ **File System Operations:**
- `os.path.exists` → Use `tmp_path`
- `builtins.open` → Use `tmp_path` with real files
- `os.listdir` → Use `tmp_path` with real directories

⚠️ **Database Operations:**
- `sqlite3.connect` → Use `temp_database` fixture
- `query_runner` → Use in-memory SQLite where possible

⚠️ **Standard Library:**
- `json.load` → Write real JSON files to `tmp_path`
- `datetime.now` → Use dependency injection or freeze_time

---

## Positive Patterns to Emulate

### 1. **Real Database Fixtures**
```python
@pytest.fixture
def legacy_v32_db(tmp_path):
    """Copy real legacy database for testing."""
    dest = str(tmp_path / "folders.db")
    shutil.copy2(LEGACY_DB_PATH, dest)
    return dest
```

### 2. **Protocol-Compliant Test Doubles**
```python
class TrackingBackend:
    """Real implementation that tracks calls without I/O."""
    def send(self, params, settings, filename):
        self.sent.append(filename)
        return True
```

### 3. **Integration Tests with Real Components**
```python
def test_pipeline_with_real_database(temp_database):
    """Test full pipeline with real DB, fake backend."""
    # Real database operations
    # Fake backend (appropriate boundary)
```

### 4. **Qt Offscreen Testing**
```python
@pytest.mark.qt
def test_widget_behavior(qtbot):
    """Real Qt widgets in offscreen mode."""
    widget = MyWidget()
    qtbot.addWidget(widget)
    # Real widget behavior, no display needed
```

---

## Migration Roadmap

### Phase 1: Quick Wins (1-2 weeks)
- [ ] Replace `os.path.exists` mocks with `tmp_path`
- [ ] Replace `builtins.open` mocks with real file operations
- [ ] Update 5 most mock-heavy test files

### Phase 2: Database Migration (2-3 weeks)
- [ ] Audit all `sqlite3.connect` mocks
- [ ] Convert to `temp_database` fixture
- [ ] Remove `FakeTable` and `FakeDatabaseObj` usage

### Phase 3: Documentation Cleanup (1 week)
- [ ] Update testing best practices
- [ ] Add "Why This Mock?" comments
- [ ] Create mock decision tree

### Phase 4: Legacy Cleanup (Ongoing)
- [ ] Remove deprecated `tests/fakes.py`
- [ ] Migrate remaining `FakeEvent` usage
- [ ] Clean up stub files if features not needed

---

## Conclusion

The project has a **strong foundation** for minimal mocking with excellent fixtures and clear philosophy. However, there's **significant technical debt** in the form of over-mocked tests, especially for standard library functions and database operations.

**Priority Focus:**
1. File system mocking → real `tmp_path` operations
2. Database mocking → real SQLite with temp databases
3. Documentation → emphasize real implementations over mocks

**Estimated Effort:** 4-6 weeks for comprehensive migration  
**Risk:** Low - changes are test-only, no production code affected  
**Benefit:** More reliable tests, better coverage, faster debugging

---

## Appendix: Quick Reference

### When to Mock ✅
- External services (FTP, SMTP, HTTP APIs)
- Display servers (unless using offscreen mode)
- Truly expensive operations (with justification)
- Legacy systems not available in test environment

### When NOT to Mock ❌
- File system (use `tmp_path`)
- SQLite databases (use `temp_database`)
- Standard library (unless truly necessary)
- Your own code (refactor for testability instead)

### Better Alternatives

| Instead of Mock | Use This |
|-----------------|----------|
| `@patch('os.path.exists')` | `tmp_path` with real files |
| `@patch('builtins.open')` | `tmp_path` with real I/O |
| `@patch('sqlite3.connect')` | `temp_database` fixture |
| `MagicMock()` for protocols | Real implementation or protocol-compliant fake |
| `FakeEvent` | Real Qt events with `qtbot` |
| `FakeTable` | Real database tables via fixtures |

---

**Generated by:** GitHub Copilot  
**Audit Date:** March 18, 2026  
**Next Review:** After Phase 1 completion
