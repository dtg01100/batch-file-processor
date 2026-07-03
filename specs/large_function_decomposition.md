# Large Function Decomposition Plan

## Overview

This document outlines a plan to decompose large functions in the dispatch module to improve maintainability and readability.

## Target Files and Methods

### 1. dispatch/services/file_processor.py (757 lines)

| Method | Lines | Priority |
|--------|-------|----------|
| `_execute_pipeline` | 78 | High |
| `_run_validation` | 73 | High |
| `_run_conversion_and_tweaks` | 67 | High |
| `process_file` | 60 | Medium |
| `_send_file` | 53 | Medium |

#### `_execute_pipeline` (78 lines)
Current responsibilities:
- Calculate checksum
- Run validation
- Run splitting
- Run conversion/tweaks
- Send to backends

**Suggested decomposition:**
- Extract checksum calculation → `_calculate_checksum` (already exists at line 681)
- Refactor to call smaller methods for each pipeline stage

#### `_run_validation` (73 lines)
Current responsibilities:
- Validation setup
- Validation execution
- Error handling

**Suggested decomposition:**
- Split into: `_prepare_validation()`, `_execute_validation()`, `_handle_validation_errors()`

#### `_run_conversion_and_tweaks` (67 lines)
**Suggested decomposition:**
- Split into: `_prepare_conversion()`, `_execute_conversion()`, `_apply_tweaks()`

---

### 2. dispatch/orchestrator.py (1770 lines)

| Method | Lines | Priority |
|--------|-------|----------|
| `process_folder_with_pipeline` | 79 | High |
| `process` | 76 | High |
| `discover_pending_files` | 69 | Medium |
| `_execute_file_pipeline` | 65 | High |
| `_apply_conversion_and_tweaks` | 63 | Medium |

#### `process_folder_with_pipeline` (79 lines)
**Suggested decomposition:**
- Extract file discovery logic to `_discover_folder_files()`
- Extract progress setup to `_setup_folder_progress()`
- Extract file loop logic to `_process_folder_file_list()`

#### `process` (76 lines)
**Suggested decomposition:**
- Split into: `_prepare_processing()`, `_iterate_folders()`, `_finalize_processing()`

---

### 3. dispatch/pipeline/converter.py (795 lines)

| Method | Lines | Priority |
|--------|-------|----------|
| `execute` | 130 | High |
| `convert` | 105 | High |
| `_load_converter_module` | 72 | Medium |
| `_validate_conversion_format` | 50 | Medium |

#### `EDIConverterStep.execute` (130 lines)
**Suggested decomposition:**
- Extract pre-checks to `_pre_execution_checks()`
- Extract result handling to `_handle_conversion_result()`
- Extract error handling to `_handle_conversion_error()`

#### `EDIConverterStep.convert` (105 lines)
**Suggested decomposition:**
- Split into: `_prepare_conversion()`, `_run_conversion()`, `_finalize_conversion()`

---

### 4. dispatch/error_handler.py (589 lines)

| Method | Lines | Priority |
|--------|-------|----------|
| `record_error` | 54 | Medium |
| `record_error_to_logs` | 42 | Medium |
| `write_error_log_file` | 29 | Low |

These methods are reasonably sized. Focus only if other refactoring requires it.

---

## Decomposition Principles

1. **Single Responsibility** - Each method should do one thing
2. **Cohesion** - Related logic should be together
3. **Testability** - Smaller methods are easier to test
4. **Naming** - Clear names reduce need for comments
5. **Preserve Behavior** - Don't change functionality, only restructure

## Implementation Order

1. **Phase 1**: `file_processor.py` - most isolated, lowest risk
2. **Phase 2**: `orchestrator.py` - core orchestration, careful with public APIs
3. **Phase 3**: `converter.py` - complex converter logic

## Pass 2 status (refactor-dispatch-simplification, 6 phases complete)

**Resolutions applied since the original decomposition tables were drafted:**
- `_normalize_validation_output` divergence (orchestrator.py:710-736 vs file_processor.py:445-466) — unified to `dispatch.pipeline.validator.normalize_validation_output` (Phase 1, commit fd12e6f92).
- One-call wrappers `_run_conversion`, `_apply_rename`, `orchestrator._apply_file_rename`, `_is_strict_database_lookup` — all inlined or replaced with direct utility calls (Phase 3, commit 49f064719).
- `_log_message` / `_log_error` orchestrator helpers — collapsed to direct `log_with_context` + `write_to_run_log` at each callsite (Phase 4, commit 901a846f2).


## Testing Strategy

- All existing tests must pass after each phase
- Add targeted unit tests for decomposed methods
- Focus on edge cases in extracted methods

## Notes

- Do NOT change public method signatures without coordination
- Preserve all logging and error handling behavior
- Keep type hints accurate after refactoring