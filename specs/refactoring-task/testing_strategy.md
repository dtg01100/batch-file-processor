# Testing Strategy & Validation Plan for Refactoring

**Target Audience:** Development Team  
**Scope:** Refactoring Project (Phases 1-4)  
**Document Status:** DRAFT

## 1. Objective
Ensure the massive refactoring of `batch-file-processor` maintains 100% functional parity, introduces zero regressions, and keeps performance within 5% of the baseline.

## 2. Baseline Establishment
Before any code changes in Phase 1, we must establish a trusted baseline.

### 2.1 Functional Baseline
*   **Action:** Run the full existing test suite.
*   **Command:** `./run_tests.sh`
*   **Success Criteria:** All ~1600 tests must pass.
*   **Artifact:** Save output to `tests/baselines/functional_baseline.log`.

### 2.2 Parity Baseline
*   **Action:** Ensure all converter outputs match current production behavior.
*   **Command:** `pytest -m parity -v`
*   **Success Criteria:** 100% pass rate.
*   **Artifact:** Verify `tests/convert_backends/baselines/` is up-to-date. If not, regenerate with `capture_master_baselines.py`.

### 2.3 Performance Baseline (NEW)
*   **Action:** Create and run a benchmark script to measure critical paths.
*   **Script Location:** `tests/benchmark/benchmark_baseline.py` (to be created)
*   **Metrics to Capture:**
    1.  **Startup Time:** Time from `main.py` execution to `MainWindow` show.
    2.  **Processing Throughput:** Time to process 100 small EDI files.
    3.  **Large File Handling:** Time to process 1 large (10MB) EDI file.
    4.  **DB Query Latency:** Average time for `folders` table lookup.
*   **Success Criteria:** Variance < 5% between runs.
*   **Artifact:** `tests/baselines/performance_baseline.json`.

## 3. Testing Strategy by Phase

### Phase 1: Critical Risk (Dispatch & Migrator)
**Focus:** Core logic and Database integrity.
*   **Pre-Refactor:**
    *   Ensure `tests/integration/test_database_migrations.py` covers all version transitions.
    *   Ensure `tests/unit/test_dispatch_*.py` has high coverage.
*   **During Refactor:**
    *   **Split `utils.py`**: Create new test files mirroring the split (e.g., `tests/unit/test_utils_edi.py`, `tests/unit/test_utils_date.py`).
    *   **Dispatch Migration**: Run `pytest -m "unit and dispatch"` continuously.
*   **Validation:**
    *   Full Integration Suite: `pytest -m integration`
    *   Migration Parity: DB schema must be identical after migration.

### Phase 2: High Risk (Coordinator & Processing)
**Focus:** Orchestration and Threading.
*   **Pre-Refactor:**
    *   Review `tests/operations/test_processing.py`.
*   **During Refactor:**
    *   **DB Consolidation**: Mock `DatabaseManager` heavily in unit tests to verify calls.
    *   **Coordinator**: Verify signal emission and slot handling using `qtbot`.
*   **Validation:**
    *   **Concurrency Test**: Run processing on multiple files simultaneously to check for race conditions (which might be introduced by changing threading models).

### Phase 3: Medium Risk (Utils & Converters)
**Focus:** Data correctness.
*   **Pre-Refactor:**
    *   **CRITICAL:** `pytest -m parity` is the safety net here.
*   **During Refactor:**
    *   Any change to `convert_base.py` requires running full parity suite.
*   **Validation:**
    *   Byte-for-byte output comparison.
    *   No changes allowed in `tests/convert_backends/baselines/` without explicit approval.

### Phase 4: Refinement (UI & Validation)
**Focus:** User Interaction.
*   **Pre-Refactor:**
    *   Run all UI tests: `pytest -m qt`.
*   **During Refactor:**
    *   Verify dialog behavior with `qtbot`.
*   **Validation:**
    *   Manual smoke test of GUI (startup, open settings, process one file) recommended as automated UI tests might miss visual regressions.

## 4. Performance Benchmarking Implementation
We will introduce a lightweight benchmarking tool using `pytest-benchmark` (if available) or a custom timer script.

**Proposed Script (`tests/benchmark/benchmark_baseline.py`):**
```python
import time
import pytest
from dispatch.coordinator import Coordinator
# ... imports ...

def benchmark_processing(benchmark):
    coordinator = Coordinator()
    # Setup 100 sample files
    result = benchmark(coordinator.process_batch, batch_id="bench_1")
    assert result.success
```

**Thresholds:**
*   **Green:** < 2% regression.
*   **Yellow:** 2-5% regression (requires investigation).
*   **Red:** > 5% regression (BLOCKER).

## 5. Validation Plan

### 5.1 Continuous Integration (Local)
Developers must run this loop before every commit:
1.  `pytest -m "unit and not slow"` (Fast feedback)
2.  `pylint` / `ruff` on changed files.

### 5.2 Phase Gate Reviews
At the end of each Phase:
1.  **Full Regression:** `./run_tests.sh` (Must pass)
2.  **Parity Check:** `pytest -m parity` (Must pass)
3.  **Performance Check:** Run benchmark script. Compare with baseline.
4.  **Code Review:** Verify strict adherence to < 400 lines/file and nesting depth < 5.

## 6. Rollback Procedures

### 6.1 Triggers
*   **Functional Regression:** Any failure in `pytest -m smoke` on the main branch.
*   **Data Corruption:** Parity mismatch in critical fields (Amounts, Dates, UPCs).
*   **Performance:** > 10% slowdown in processing speed.

### 6.2 Process
1.  **Identify:** Bisect to find the culprit commit.
2.  **Revert:** `git revert <commit-hash>`.
3.  **Verify:** Run full suite to confirm stability.
4.  **Analyze:** Post-mortem analysis of why the test suite missed the regression.

## 7. Known Issues & Mitigations
*   **`edi_tweaks` Import Issue:** Current tests fail on missing `edi_tweaks` module.
    *   *Mitigation:* Fix this import error in `tests/conftest.py` or relevant files BEFORE starting Phase 1 to ensure a clean green baseline.
