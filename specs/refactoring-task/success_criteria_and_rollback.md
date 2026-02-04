# Success Criteria and Rollback Procedures for Phase 1 Refactoring

## Success Criteria

The Phase 1 Refactoring (Utils & Dispatch) will be considered successful when the following criteria are met:

### 1. Functional Integrity
- **Test Suite**: All 1600+ existing tests must pass.
  - Command: `./run_tests.sh`
- **Parity Verification**: All converter parity tests must pass, ensuring byte-for-byte identical output for existing converters.
  - Command: `pytest tests/convert_backends/test_parity_verification.py`
- **Smoke Tests**: All application smoke tests (CLI, GUI startup) must pass.
  - Command: `pytest -m smoke`

### 2. Performance
- **Startup Time**: Application startup time (CLI --help) must be within 5% of the baseline measured in Step 1.
  - Baseline: Measured via `tests/test_performance.py`
- **Import Time**: Key module import times (`dispatch`, `interface.main`) must show no significant degradation (>10%).

### 3. Code Quality
- **Module Structure**:
  - `utils.py` functions successfully migrated to `utils/` package (edi, upc, validation, datetime, database).
  - Legacy `dispatch.py` calls successfully mapped and/or migrated to `dispatch/` package.
- **Complexity**:
  - Reduced cyclomatic complexity in migrated functions.
  - No new circular dependencies introduced.

### 4. Zero Regressions
- No changes to user-facing behavior (GUI, CLI arguments, database schema).
- No changes to file outputs (verified via Parity tests).

## Rollback Procedures

Since this is a refactoring task without database schema migrations, rollback is primarily achieved via version control.

### 1. Immediate Rollback (During Development/Testing)
If a step fails verification or introduces critical bugs:
1.  **Discard Uncommitted Changes**:
    ```bash
    git checkout .
    git clean -fd
    ```
2.  **Revert to Last Stable Commit**:
    ```bash
    git checkout <last_stable_commit_hash>
    ```

### 2. Post-Merge Rollback
If issues are discovered after merging a step:
1.  **Revert Commit**:
    ```bash
    git revert <commit_hash>
    ```
2.  **Verify Revert**:
    - Run full test suite: `./run_tests.sh`
    - Run parity tests: `pytest tests/convert_backends/test_parity_verification.py`

### 3. Checkpoint Recovery
The refactoring plan is divided into incremental steps. Each step is a checkpoint.
- **Step 1 Completion**: Baseline established.
- **Step 2 Completion**: `utils/edi.py` created and verified.
- ... etc.

**Procedure:**
1. Identify the last successful step.
2. Reset branch to that step's completion commit.
   ```bash
   git reset --hard <step_completion_commit_hash>
   ```
3. Run verification to confirm stability.

## Safety Mechanisms
- **Pre-Commit Checks**: Run smoke tests and linter before every commit.
- **Parallel Existence**: During migration, new `utils/` modules will exist alongside legacy `utils.py` (which will re-export them) to ensure backward compatibility and safe incremental updates.
