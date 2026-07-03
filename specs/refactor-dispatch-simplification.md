# Spec: Dispatch Module Simplification

**Status:** DRAFT
**Author:** Refactoring pass 2026-07-03
**Created:** 2026-07-03
**Updated:** 2026-07-03

---

## 1. Summary

Reduce complexity in the dispatch layer by collapsing duplicated validation-output normalization, eliminating over-extracted one-call wrapper methods, hoisting module-top imports, and slimming one method that has multiple dead parameters. Targets **65–95 LOC reduction** across `dispatch/orchestrator.py`, `dispatch/services/file_processor.py`, and `dispatch/services/folder_discovery.py` (revised from initial draft — see §10.3). Note: this is NOT purely behavior-preserving — Phase 1 unifies two divergent validator-output contracts (see §3.4); all other phases are behavior-preserving.

---

## 2. Background

### 2.1 Problem Statement

After the prior decomposition merge (`cc741304c` — "decompose large functions in dispatch module"), the orchestrator and file processor no longer have 70+ LOC methods, but they now carry symptoms of over-decomposition:

1. **Divergent validator-output normalization** — `orchestrator._normalize_validation_output` (orchestrator.py:710-736) and `file_processor._handle_validation_result` head (file_processor.py:445-466) both implement an isinstance cascade, but they accept different input shapes and emit different error messages for unknown inputs. See §3.4 for the per-shape divergence table. The unified normalizer is a **contract unification**, not a pure refactor — every caller must accept the chosen behavior.

2. **Wrapper methods with one caller** — `_run_conversion` (file_processor.py:558) gates on `validation_passed` and default-inits result flags before calling `_execute_conversion` (file_processor.py:597); `_apply_rename` (file_processor.py:695) and `orchestrator._apply_file_rename` (orchestrator.py:811) wrap the same `apply_file_rename` utility; `_is_strict_database_lookup` (orchestrator.py:385) is called from exactly one place (orchestrator.py:404); `_build_context` (file_processor.py:199) has a 17-line body for a 4-field dataclass.

3. **Imports inside method bodies** — 6 function-scope import sites total: `dispatch/file_utils.{apply_file_rename, write_to_run_log, extract_invoice_numbers}` at orchestrator.py:1061, 1083, 1096; `dispatch/file_utils.{apply_file_rename, extract_invoice_numbers}` at file_processor.py:697, 797; `core.utils.file_utils.calculate_file_checksum` at file_processor.py:258 and orchestrator.py:705. Both target modules are stdlib-clean (verified by reading their imports) — safe to hoist.

4. **Parameter-list explosion** — ruff reports 62 `PLR0913` (>5 args) violations. Most are legitimate constructors/dataclasses. Four in `dispatch/orchestrator.py` and one in `dispatch/services/file_processor.py` are evidence of methods with dead or absorbable parameters: `_apply_validation_outcome` (7 args, orchestrator.py:738), `_process_split_pipeline` (6 args, orchestrator.py:444), `_send_file` (6 args, file_processor.py:641), `_filter_processed_files` (6 args, orchestrator.py:945, **0 production callers**), and a matching `_filter_processed_files` in `folder_discovery.py:202` (active but with a dead `_folder_name` parameter). See §3.8 for honest assessment of which are reducible without behavior change.

5. **Logging boilerplate** — `orchestrator._log_message` (orchestrator.py:1081) and `orchestrator._log_error` (orchestrator.py:1094) follow the same `log_with_context` + `write_to_run_log` shape. Two near-identical functions.

### 2.2 Motivation

- **Readability**: anyone tracing a validation failure today must read both normalizers to know the contract. One normalizer = one source of truth.
- **Testability**: over-extracted wrappers force tests to mock at two layers for one behavior.
- **Performance**: function-scope imports cost a `sys.modules` lookup per call (microseconds, but multiplied across the per-file pipeline loop).
- **Maintenance**: dead wrappers and dead parameters (e.g. `_folder_name`) accumulate cognitive debt.

### 2.3 Prior Art

- `specs/large_function_decomposition.md` lists 13 methods already decomposed. This spec is its second pass — it does NOT re-decompose anything, it removes the wrappers introduced during decomposition.
- `specs/refactoring-task/plan.md` (Steps 8–11) targets `dispatch.py` legacy module migration, which is orthogonal (already substantially complete — see `dispatch/orchestrator.py:1`).
- `docs/architecture/SPAGHETTI_CODE_ANALYSIS.md` flagged the orchestrator as a "God class" (1785 LOC at time of writing, now 1121 after Phase 1). This spec targets the remaining ~150 LOC of low-risk noise inside it.
- Recent commits show the codebase favors incremental, behavior-preserving cleanup: `38c6866f3` (dead field), `8e3503991` (dead shims), `0a5878031` (API migration). This spec fits that pattern.

---

## 3. Design

### 3.1 Architecture Alignment

- [x] Reviewed `docs/architecture/SPAGHETTI_CODE_ANALYSIS.md` (God-class problem matches)
- [x] Reviewed `dispatch/AGENTS.md` (Pipeline = Protocol-based, our changes preserve)
- [x] Reviewed `dispatch/services/file_processor.py` (target file)
- [x] Reviewed `dispatch/pipeline/validator.py` (landing site for new normalizer)

**Principles followed:**

- **No public API change.** `DispatchOrchestrator.process_folder`, `process_file`, `discover_and_process_folder`, `reset`, `get_summary` keep their signatures.
- **Protocol boundaries respected.** Pipeline steps remain opaque to the orchestrator.
- **Existing dataclasses absorb parameters.** `ProcessingContext` (file_processor.py:50) and `FileResult` (file_processor.py:28) already carry most fields currently passed positionally.

### 3.2 Technical Approach

**Components affected:**

- [x] `dispatch/orchestrator.py` — Phases 1, 2, 3, 4, 5 (multiple methods touched)
- [x] `dispatch/services/file_processor.py` — Phases 1, 2, 3 (wrappers inlined, imports hoisted, FileResult method added)
- [x] `dispatch/pipeline/validator.py` — Phase 1 (new `normalize_validation_output` function)
- [x] `dispatch/file_utils.py` — Phase 4 (new `write_run_log` helper appended)
- [x] `dispatch/services/folder_discovery.py` — Phase 3 (dead `_folder_name` arg removed; one callsite updated)
- [ ] `interface/` — no change (consumers unchanged)
- [ ] `core/` — no change

**No database, no UI, no schema, no public API, no plugin contract changes.**

### 3.3 API Changes

**None to public API.**

Internal helper signatures change (private methods; only test files in this repo consume them):

```python
# dispatch/services/file_processor.py — unchanged
def process_file(self, file_path, folder, upc_dict, run_log=None, effective_folder=None) -> FileResult

# dispatch/orchestrator.py — unchanged
def process_folder(self, folder, run_log, processed_files=None, ...) -> FolderResult
def discover_and_process_folder(self, folder, run_log, ...) -> FolderResult
def process_file(self, file_path, folder) -> FileResult
```

### 3.4 Refactor: Canonical validation-output normalizer

**Current state (divergent):**


```python
# orchestrator.py:710-736 (_normalize_validation_output)
if isinstance(validation_output, tuple):
    return validation_output          # returns tuple UNCHECKED — no length validation
if isinstance(validation_output, ValidationResult):
    return output.is_valid, (output.errors if not output.is_valid else current_file)
if isinstance(validation_output, bool):
    return validation_output, current_file
logger.warning("Unexpected validation output type: %s, treating as invalid",
               type(validation_output).__name__)
return False, [str(validation_output)]   # ← encodes the unknown object as str()

# file_processor.py:445-466 (head of _handle_validation_result)
if isinstance(validation_output, tuple):
    is_valid, errors_or_file = validation_output   # ← positional unpack — REQUIRES 2-tuple
elif isinstance(validation_output, dict):
    is_valid = validation_output.get("valid", True)
    errors_or_file = (validation_output.get("file_path", current_file)
                      if is_valid
                      else validation_output.get("errors", []))
elif isinstance(validation_output, bool):
    is_valid = validation_output
    errors_or_file = current_file
else:
    logger.warning("Unexpected validation output type: %s, treating as invalid",
                   type(validation_output).__name__)
    is_valid = False
    errors_or_file = [f"Validator returned unexpected type: {type(validation_output).__name__}"]
```

**Behavioral differences today (MUST be addressed by Phase 1):**

| Input | orchestrator returns | file_processor returns |
|---|---|---|
| 3-tuple | `(a, b, c)` (returned as-is) | `TypeError` (positional unpack fails) |
| `dict` | `(False, [str(dict)])` (treated as unknown) | `(bool, file_path or errors)` |
| `ValidationResult` | `(is_valid, errors or current_file)` | `(False, [<type msg>])` (treated as unknown) |
| unknown object | `(False, [str(obj)])` — stringifies the object | `(False, [f"...type: {TypeName}"])` — names the type |

**This is NOT a pure refactor — it is a contract unification.** The unified normalizer below picks one behavior per shape. Both call sites adopt the unified behavior. Decisions encoded:

- 3-tuple → `(is_valid, errors_or_file)` (orchestrator's lenient return is dropped — 3-tuples were never a documented contract; the documented contract is a 2-tuple)
- `dict` → supported in both (orchestrator gains this — only affects callers that already passed a dict to the orchestrator's validator step, which currently silently broke)
- `ValidationResult` → supported in both (file_processor gains this — same reasoning)
- Unknown → standard message: `[f"Validator returned unexpected type: {TypeName}"]` (file_processor's wording is the survivor — clearer for debugging)

**Target (replaces both):**

```python
# dispatch/pipeline/validator.py (additions)

def normalize_validation_output(
    output: object,
    current_file: str,
) -> tuple[bool, Any]:
    """Normalize a validator step's return into (is_valid, errors_or_file).

    Accepts tuple (must be 2-element), ValidationResult, dict{"valid": ...}, or bool.
    Any other type logs a warning and returns (False, [<type-error-message>]).
    """
    if isinstance(output, tuple) and len(output) == 2:
        return bool(output[0]), output[1]
    if isinstance(output, ValidationResult):
        return output.is_valid, (
            output.errors if not output.is_valid else current_file
        )
    if isinstance(output, dict):
        is_valid = bool(output.get("valid", True))
        return (
            is_valid,
            output.get("file_path", current_file)
            if is_valid
            else output.get("errors", []),
        )
    if isinstance(output, bool):
        return output, current_file
    logger.warning(
        "Unexpected validation output type: %s, treating as invalid",
        type(output).__name__,
    )
    return False, [f"Validator returned unexpected type: {type(output).__name__}"]
```

Both call sites become a single line:
`is_valid, errors_or_file = normalize_validation_output(validation_output, current_file)`.

**Pre-Phase-1 verification (required):** before swapping either call site, write a parametrized test asserting the unified function's output for every input shape BOTH current normalizers see. Run both call sites' existing tests. Any divergence is a contract question to resolve with the team, not a silent behavior change.

### 3.5 Refactor: Collapse one-call wrappers

| Wrapper | Caller(s) | Action |
|---|---|---|
| `file_processor._run_conversion` (558) | `_execute_pipeline:321` | Inline — gates on `validation_passed` and default-inits flags; body is 8 lines, inlines to 10 in caller |
| `file_processor._apply_rename` (695) | `_send_file:670` | Inline — single call to `apply_file_rename` |
| `orchestrator._apply_file_rename` (811) | `_process_split_pipeline:487` | Replace with direct call to module function |
| `orchestrator._is_strict_database_lookup` (385) | `_get_upc_dictionary:404` | Inline the 1-line constant check |
| `orchestrator._filter_processed_files` (945) | **0 production callers**; 2 test callers in `tests/unit/dispatch_tests/test_orchestrator_pipeline.py:814,857` | Remove dead `_folder_name` parameter + the `_folder_index`/`_folder_total`/`progress_reporter` overload (also unused at the orchestrator layer — verified by reading body at 945-993, only `folder`/`processed_files`/`files` reach `filter_pending_files`) |
| `file_processor._build_context` (199) | `process_file:157` | Compress to ternary (3 lines) |
| `folder_discovery._filter_processed_files` (folder_discovery.py:202) | 2 production callers in same file: `discover_and_filter_files:149` and `_discover_for_folder:174` | **Same dead-param removal**: `_folder_name` is unused (parameter declared at line 209), and `_discover_for_folder:180` actively passes `_folder_name=alias` — drop both. Keeps `folder_index`/`folder_total`/`progress_reporter` since `_discover_for_folder:174-181` does use them |

**Why `orchestrator._filter_processed_files` exists at all** is a question worth raising with the team — it has zero production callers. Options: (a) delete the method entirely and rely on `FolderPipelineExecutor._filter_processed_files`, (b) leave it for tests only. Phase 3 takes the conservative path: drop the dead params, leave the method in place. A follow-up commit can delete it if the tests are updated to call the executor's version directly.


### 3.6 Refactor: Hoist imports

Move to module-top imports (no behavior change — both target modules are stdlib-clean: `dispatch/file_utils.py` imports only stdlib + `core.structured_logging` + `dispatch.interfaces`; `core/utils/file_utils.py` imports only stdlib + `core.structured_logging` — no circular-import risk):

- `dispatch.file_utils.{apply_file_rename, write_to_run_log, extract_invoice_numbers}` — orchestrator.py:1061, 1083, 1096
- `dispatch.file_utils.{apply_file_rename, extract_invoice_numbers}` — file_processor.py:697, 797
- `core.utils.file_utils.calculate_file_checksum` — file_processor.py:258 (function-scope)
- `core.utils.file_utils.calculate_file_checksum` — orchestrator.py:705 (function-scope)

**6 function-scope import sites total.** After Phase 4 deletes `_log_message`/`_log_error`, the orchestrator's `write_to_run_log` import can be trimmed (no remaining users). Phase 2 ships the import-hoist only; Phase 4 ships the dead-import trim.

### 3.7 Refactor: Consolidate logging helper

Add a thin wrapper to the existing `dispatch/file_utils.py` (NOT a new `dispatch/services/run_log_writer.py` module — `file_utils.py` already houses `write_to_run_log`, and adding it next door keeps related logic colocated). The wrapper handles the `log_with_context` + `write_to_run_log` pair that today lives in two near-identical private methods on the orchestrator.

```python
# dispatch/file_utils.py (additions, ~15 LOC at the bottom of the module)

def write_run_log(
    run_log: RunLog | None,
    message: str,
    *,
    level: int = logging.INFO,
    prefix: str = "",
) -> None:
    """Write a message to run_log AND emit it via the structured logger.

    Single-source replacement for the orchestrator's _log_message / _log_error
    pair. The `level` and `prefix` parameters cover both info and error paths.
    """
    log_with_context(
        logger,
        level,
        message,
        correlation_id=get_or_create_correlation_id(),
        operation="run_log",
    )
    write_to_run_log(run_log, message, prefix=prefix)
```

Replaces `orchestrator._log_message` (1081) and `orchestrator._log_error` (1094) with one function. Callsite translation:

- `self._log_message(run_log, "msg")` → `write_run_log(run_log, "msg")`
- `self._log_error(run_log, "msg")` → `write_run_log(run_log, "msg", level=logging.ERROR, prefix="ERROR: ")`

`write_to_run_log`'s binary/text detection (bugfix commit `9f75db9b9`) is preserved because `write_run_log` is a thin wrapper that delegates without altering the payload.

### 3.8 Refactor: Parameter-list reductions

**`_apply_validation_outcome` (orchestrator.py:738, 7 args → 5 args):**
- Read the function body (lines 755-777): every parameter is used. Realistic refactor: extract the `result.validated = is_valid` + `result.errors.extend(...)` mutations into a `FileResult.record_validation_outcome(is_valid, errors_or_file)` method that returns `None`. The orchestrator method shrinks to the flow-control + logging + force-continue check (5 args: `*, is_valid, errors_or_file, current_file, context` — `result` and `file_basename` move into the FileResult method or get read from `context`).
- `file_basename` is used only inside the log message (`f"Validation failed for {file_basename}: ..."`). `run_log` does not naturally belong on `FileResult`. So `run_log` stays as an arg of the orchestrator's wrapper method (the FileResult method does NOT take run_log).
- Target signature: `_apply_validation_outcome(self, *, is_valid, errors_or_file, current_file, run_log, context) -> tuple[bool, str]` (6 args → ruff still flags; see "Honest assessment" below).

**`_process_split_pipeline` (orchestrator.py:444, 6 args → 6 args, no reduction possible):**
- Every arg is used in the body (verified lines 460-502): `current_file`, `file_path`, `file_basename`, `context`, `result`, `run_log`. None are dead.
- `ProcessingContext` does NOT currently carry `current_file`, `file_basename`, or `run_log` (verified dataclass at file_processor.py:50-69). Adding `current_file` and `file_basename` is plausible (both are per-pipeline-call values), but `run_log` is per-folder and belongs on the orchestrator or folder executor, not the per-file context.
- **Honest assessment:** no safe reduction without behavior change. Phase 5 leaves this method's arg count as-is. The "ruff-clean" version would require either (a) adding fields to `ProcessingContext` and threading `run_log` separately, or (b) inlining the method into a parent loop — both are larger refactors out of scope for behavior-preserving cleanup.

**`_send_file` (file_processor.py:641, 6 args → 6 args, no reduction possible):**
- Same situation. All 6 args used (verified lines 661-693). No dead params, no logical grouping onto `ProcessingContext` that fits `run_log`. Phase 5 leaves arg count as-is.

**`_filter_processed_files` (orchestrator.py:945, 6 args → 3 args):**
- Verified unused at the orchestrator level: `_folder_index`, `_folder_total`, `_folder_name`, `progress_reporter` are all declared but never read in the body (lines 945-993). Only `files`, `processed_files`, `folder` reach `filter_pending_files`.
- Phase 5 reduces this method to `_filter_processed_files(self, files, processed_files, folder)` — 3 args + self = 4, well under ruff's threshold.
- **This is the only ruff-reduction Phase 5 can deliver at the orchestrator level** (since `_process_split_pipeline` and `_send_file` are stuck).
- Test-side: `tests/unit/dispatch_tests/test_orchestrator_pipeline.py:814,857` only pass `files, processed_files, {"id": 42}` — already below the new signature. No test changes needed.

### 3.9 Out of scope

- Decomposition of `dispatch/services/file_processor.py:_execute_pipeline` (already decomposed in Phase 1; remaining complexity is intrinsic to its 4-stage audit-log timing).
- `dispatch/pipeline/converter.py:execute` / `convert` — long but each branch is a distinct format with no shared logic to extract.
- `dispatch/orchestrator.py:_send_pipeline_file` — keep as-is; logic is linear.
- Public API changes (rejected: would require coordinated updates across UI/services/CLI consumers).
- Anything in `interface/` (no consumer of these wrappers).

### 3.10 Alternatives Considered

| Alternative | Pros | Cons | Why Not Chosen |
|---|---|---|---|
| Rewrite `DispatchOrchestrator` into a pure façade | Maximum clarity | Breaks subclassing, removes useful helpers, large diff | Spec scope = behavior-preserving cleanup |
| Move all dispatch logic into a `dispatch/pipeline/orchestrator.py` namespace | Cleaner package layout | High churn, no behavior change, no LOC reduction | Not aligned with current package layout |
| Delete `_run_validation` / `_run_splitting` and inline into `_execute_pipeline` | Fewer methods | Re-introduces the long methods Phase 1 just decomposed | Regresses existing work |
| Add a `ValidationRunner` class encapsulating all 3 normalizer call sites | Single home | Marginal benefit over a free function; the steps are already Protocol-isolated | Free function is sufficient at current scale |
| Migrate `ProcessingContext` to a `TypedDict` | Lighter | Loses default values + type safety already in place | No payoff |

---

## 4. Implementation Plan

Six phases. Each phase is one or more commits. Each phase ends with a green test suite.

### Phase 1: One canonical normalizer (Bucket 1c) — ~50 LOC

**Files:** `dispatch/pipeline/validator.py`, `dispatch/orchestrator.py`, `dispatch/services/file_processor.py`

1. Add `normalize_validation_output` free function in `validator.py` (per §3.4).
2. Replace `_normalize_validation_output` (orchestrator.py:710) with one-line import + call.
3. Replace the isinstance cascade head of `_handle_validation_result` (file_processor.py:445-466) with a call to the same function.
4. Run unit tests for both modules; confirm identical outputs for the four accepted input shapes plus the unknown-type warning path.
5. Commit: `refactor(dispatch): unify validation-output normalization into dispatch.pipeline.validator`

**Deliverable:** Two normalizers → one. No public API change.

### Phase 2: Hoist function-scope imports (Bucket 1b) — ~10 LOC

**Files:** `dispatch/orchestrator.py`, `dispatch/services/file_processor.py`

1. Move `from dispatch.file_utils import apply_file_rename, write_to_run_log, extract_invoice_numbers` to module-top in `orchestrator.py`.
2. Same for `file_processor.py`.
3. Move `from core.utils.file_utils import calculate_file_checksum` to module-top in both files.
4. Run smoke tests; confirm imports remain non-circular.
5. Commit: `chore(dispatch): hoist dispatch.file_utils imports to module scope`

**Deliverable:** No more in-method imports of `dispatch.file_utils`.

### Phase 3: Collapse one-call wrappers + dead-parameter removal — ~80 LOC

**Files:** `dispatch/orchestrator.py`, `dispatch/services/file_processor.py`, `dispatch/services/folder_discovery.py`

In a single commit (all wrappers, all atomic — small, well-bounded changes belong together):

1. Inline `file_processor._run_conversion` → `_execute_pipeline` (body is 8 lines, inlines to ~10 lines in caller; preserves the `validation_passed` gate).
2. Inline `file_processor._apply_rename` → `_send_file` (single call to `apply_file_rename`).
3. Inline `orchestrator._apply_file_rename` → `_process_split_pipeline` (replace with a direct call to `apply_file_rename` from `dispatch.file_utils`).
4. Inline `orchestrator._is_strict_database_lookup` → `_get_upc_dictionary` (1-line constant check).
5. Compress `file_processor._build_context` to a 3-line ternary.
6. Remove dead `_folder_name`, `_folder_index`, `_folder_total`, `progress_reporter` parameters from `orchestrator._filter_processed_files` (orchestrator.py:945). The 2 test callsites (`test_orchestrator_pipeline.py:814,857`) already pass only `files, processed_files, {"id": 42}` — no test changes needed.
7. Remove dead `_folder_name` parameter from `folder_discovery._filter_processed_files` (folder_discovery.py:202, 209). Drop `_folder_name=alias` from the `_discover_for_folder:180` callsite. The other callsite at `discover_and_filter_files:149` never passed it — no change.
8. Run targeted unit tests: `tests/unit/dispatch_tests/`, `tests/unit/dispatch/services/`.
9. Run smoke tests: `pytest -m smoke`.
10. Commit: `refactor(dispatch): collapse 5 one-call wrappers + strip dead _folder_name from 2 methods`

**Deliverable:** ~80 LOC reduction across 3 files; 2 methods have 4 fewer params each; 1 dead alias computation at `folder_discovery.py:167` (`alias = folder.get("alias", folder_path)` is now used only at the alias-fallback site — verify before removing; if no other consumers, drop the local too).

### Phase 4: Consolidate run-log helper (Bucket 1a) — ~25 LOC

**Files:** `dispatch/file_utils.py` (additions), `dispatch/orchestrator.py`

1. Add `write_run_log` function to the bottom of `dispatch/file_utils.py` (per §3.7).
2. Update `dispatch/orchestrator.py` module-top imports to include `write_run_log` (replacing the function-scope import of `write_to_run_log` — Phase 2 should already have hoisted it; Phase 4 swaps the symbol).
3. Replace `orchestrator._log_message` and `orchestrator._log_error` callsites (4 sites total — search `self._log_message` and `self._log_error`) with calls to `write_run_log`.
4. Delete both private methods from the orchestrator.
5. Verify that `write_to_run_log`'s binary/text detection (bugfix commit `9f75db9b9`) is preserved — `write_run_log` is a thin wrapper that delegates the payload unchanged.
6. Run `tests/unit/dispatch_tests/test_orchestrator.py` and `test_orchestrator_pipeline.py`.
7. Commit: `refactor(dispatch): consolidate _log_message/_log_error into dispatch.file_utils.write_run_log`

**Deliverable:** Two orchestrator methods → one free function in `file_utils.py`.

### Phase 5: Parameter-list reductions (Bucket 2) — ~10 LOC, **partial scope**

**Files:** `dispatch/orchestrator.py`, `dispatch/services/file_processor.py` (FileResult dataclass only)

**Honest scope statement (per §3.8):** Phase 5 can ONLY reduce the `_filter_processed_files` method to ruff-clean. `_process_split_pipeline` and `_send_file` are stuck at 6 args because (a) every arg is used, (b) `ProcessingContext` does not carry per-folder `run_log`, and (c) adding it would be a behavior change. `_apply_validation_outcome` can be partially reduced via a `FileResult` method but its new signature still trips ruff (6 args). Net ruff reduction: **1 violation**, not the 4 originally targeted.

1. Add `FileResult.record_validation_outcome(is_valid, errors_or_file)` method (per §3.8). It mutates `self.validated` and `self.errors` only — no logging, no run_log. Returns `None`.
2. Update `orchestrator._apply_validation_outcome` (orchestrator.py:738) to delegate the mutation to the new method. New signature: `(self, *, is_valid, errors_or_file, current_file, run_log, context)` — 6 args, ruff-clean target is 5 → **still flagged**. Acceptable trade-off: this method has a real responsibility (logging + force-continue) and collapsing further requires inlining.
3. Reduce `orchestrator._filter_processed_files` (orchestrator.py:945) from 6 args to 3: keep `files`, `processed_files`, `folder`. Drop `_folder_index`, `_folder_total`, `_folder_name`, `progress_reporter` (all verified unused at lines 945-993). This is the one ruff reduction Phase 5 delivers.
4. **Do NOT touch `_process_split_pipeline` or `_send_file`** — leave at 6 args, document the reason in a code comment so future readers don't try to fix what's not broken.
5. Run full dispatch unit suite: `pytest tests/unit/dispatch_tests tests/unit/dispatch -m "not qt" -n0`.
6. Commit: `refactor(dispatch): strip dead params from _filter_processed_files + extract FileResult.record_validation_outcome`

**Deliverable:** 1 ruff violation fixed (orchestrator.py:945). `_process_split_pipeline` and `_send_file` left untouched with a documenting comment.

### Phase 6: Update decomposition plan + add regression tests — ~90 LOC (mostly tests)

**Files:** `specs/large_function_decomposition.md`, `tests/unit/dispatch_tests/test_validation_normalizer.py` (new)

1. Update `specs/large_function_decomposition.md` Phase 2 / 3 tables to reflect this pass — note that the `_normalize_validation_output` row is now resolved.
2. Create `tests/unit/dispatch_tests/test_validation_normalizer.py` with parametrized cases covering every input shape the unified normalizer handles:
   - tuple (2-element): `(True, "newpath.edi")` → `(True, "newpath.edi")`
   - tuple (3-element): `(True, "a.edi", "extra")` → graceful rejection (not a TypeError)
   - `ValidationResult(is_valid=False, errors=["x"])`: → `(False, ["x"])`
   - `dict` valid: `{"valid": True, "file_path": "/x.edi"}` → `(True, "/x.edi")`
   - `dict` invalid: `{"valid": False, "errors": ["bad"]}` → `(False, ["bad"])`
   - `bool`: `True` / `False` → `(True/False, current_file)`
   - unknown: `"a string"` → `(False, [<type-error-msg>])` and a warning is logged (use `caplog` to assert)
3. Append a regression test to `tests/unit/dispatch_tests/test_orchestrator.py` that asserts `DispatchOrchestrator._filter_processed_files.__code__.co_varnames` does NOT include `_folder_name`, `_folder_index`, `_folder_total`, or `progress_reporter` (catches accidental re-addition).
4. Run `pytest tests/unit/dispatch_tests tests/unit/dispatch -m "not qt" -n0`.
5. Run final smoke: `pytest -m smoke`.
6. Commit: `test(dispatch): regression tests for normalize_validation_output and slim _filter_processed_files`
7. Separate docs commit: `docs(decomposition): mark phase-2 cleanup complete in large_function_decomposition.md`

**Deliverable:** Documentation reflects state; one test per new invariant.

## 5. Database Changes

None. No schema, no migrations, no SQL.

---
## 6. Testing Strategy

### 6.1 Test Cases

| Test Case | Type | Description | Expected Result |
|---|---|---|---|
| `test_normalize_tuple_two_element` | unit | `(True, "newpath.edi")` | `(True, "newpath.edi")` |
| `test_normalize_tuple_three_element` | unit | `(True, "a.edi", "extra")` | graceful rejection — not a TypeError; either the `len == 2` check rejects and the unknown branch fires, or the 3-tuple is accepted as `(True, ("a.edi", "extra"))` — implementation chooses; test asserts no crash |
| `test_normalize_validation_result_invalid` | unit | `ValidationResult(is_valid=False, errors=["x"])` | `(False, ["x"])` |
| `test_normalize_validation_result_valid` | unit | `ValidationResult(is_valid=True, errors=[])` | `(True, current_file)` |
| `test_normalize_dict_valid` | unit | `{"valid": True, "file_path": "/x.edi"}` | `(True, "/x.edi")` |
| `test_normalize_dict_invalid` | unit | `{"valid": False, "errors": ["bad"]}` | `(False, ["bad"])` |
| `test_normalize_bool_true` | unit | `True` | `(True, current_file)` |
| `test_normalize_bool_false` | unit | `False` | `(False, current_file)` |
| `test_normalize_unknown` | unit | `"a string"` | `(False, [<type-error-msg>])` + warning logged (assert via `caplog`) |
| `test_filter_processed_files_signature` | unit | Inspect `_filter_processed_files.__code__.co_varnames` | No `_folder_name`, `_folder_index`, `_folder_total`, `progress_reporter` |
| `test_write_run_log_info` | unit | Call `write_run_log(run_log, "x")` | Logs at INFO, writes to run_log |
| `test_write_run_log_error` | unit | Call `write_run_log(run_log, "x", level=ERROR, prefix="ERROR: ")` | Logs at ERROR, prefix prepended on run_log |
| `test_existing_orchestrator_suite` | regression | All `tests/unit/dispatch_tests/test_orchestrator*.py` tests | All pass |
| `test_existing_file_processor_suite` | regression | All `tests/unit/dispatch_tests/test_file_processor.py` tests | All pass |

### 6.2 Test File Locations

- New tests: `tests/unit/dispatch_tests/test_validation_normalizer.py` (new file for Phase 1 — covers the unified normalizer)
- New test: append to `tests/unit/dispatch_tests/test_orchestrator.py` (Phase 6 signature check)
- Existing tests: `tests/unit/dispatch_tests/` and `tests/unit/dispatch/services/` — must remain green at every commit

### 6.3 Coverage Requirements

- [x] New `normalize_validation_output` has 9 parametrized cases (one per accepted shape + warning path + 3-tuple edge)
- [x] New `write_run_log` has 2 cases (info + error)
- [x] No reduction in coverage of changed files
- [x] All smoke tests pass: `pytest -m smoke`
- [x] Ruff complexity: target **1** PLR0913 reduction (the `_filter_processed_files` slim-down; orchestrator.py:945). Zero new violations.

### 6.4 Test Run Commands

```bash
# Fast iteration per phase
uv run pytest tests/unit/dispatch_tests -m "not qt" -n0
uv run pytest tests/unit/dispatch/services -m "not qt" -n0

# Smoke (final)
uv run pytest -m smoke --timeout=30

# Lint (final)
uv run ruff check dispatch/ --select PLR0913,PLR0915,C901
```

---

## 7. Risk Assessment

| Risk | Likelihood | Impact | Mitigation |
|---|---|---|---|
| **Behavior change in `normalize_validation_output`** (orchestrator lacks dict handling; file_processor lacks `ValidationResult`; both have different unknown-error messages) | **High** | **Med** | Per §3.4: this is a contract unification, not a pure refactor. Pre-Phase-1 work: write parametrized tests against the union of BOTH normalizers' accepted inputs. Document the chosen behavior for each shape (table in §3.4). Run both call sites' existing tests before AND after the swap. Any test failure is a contract question to resolve, not a silent behavior change. |
| **Behavior change for 3-tuple input** (orchestrator returns it as-is; unified normalizer rejects) | Med | Med | Search `tests/` for any test passing a non-2-tuple to a validator step. If found, mark xfail or update the call. If none, proceed. |
| Circular import from hoisting `dispatch.file_utils` / `core.utils.file_utils` | Low | High | Verified clean: `dispatch/file_utils.py` imports only stdlib + `core.structured_logging` + `dispatch.interfaces`; `core/utils/file_utils.py` imports only stdlib + `core.structured_logging`. Neither imports back into `dispatch.orchestrator` or `dispatch.services.file_processor`. Confirm via `python -c "import dispatch.orchestrator"`. |
| `ProcessingContext` carrying `run_log` is wrong (run_log is per-folder, not per-file) | **Resolved** | Low | **Decision: do NOT add `run_log` to `ProcessingContext`.** Phase 5 leaves `_process_split_pipeline` and `_send_file` at 6 args with a documenting comment. |
| Inlined wrapper breaks exception handling | Low | Med | `_run_conversion`'s try/except is preserved when inlined into `_execute_pipeline`; covered by `tests/unit/dispatch_tests/test_file_processor.py`. |
| Dead-parameter removal breaks test that still passes the old kwarg | Med | Low | `tests/unit/dispatch_tests/test_orchestrator_pipeline.py:814,857` already only passes `files, processed_files, {"id": 42}` — no kwargs to strip. For folder_discovery's `_discover_for_folder:180`, drop `_folder_name=alias` in the same commit. |
| Public API signature change slips in | Low | High | Each phase diff is reviewed against `git diff master -- dispatch/orchestrator.py dispatch/services/file_processor.py` for public-method signatures only (process_folder, process_file, discover_and_process_folder, get_summary, reset). Internal helpers are fair game. |
| Test suite timing regressions | Low | Low | No loops added; one wrapper removed per method. |

### 7.1 Rollback Plan

Each phase is a separate commit. Revert the offending commit(s):

```bash
git log --oneline -- dispatch/orchestrator.py dispatch/services/file_processor.py dispatch/pipeline/validator.py dispatch/file_utils.py dispatch/services/folder_discovery.py
git revert <commit-sha>
pytest tests/unit/dispatch_tests tests/unit/dispatch -m "not qt" -n0
```

No database migration rollback needed. No deployment state to clean up.

---

## 8. Success Criteria

- [ ] All 6 phases merged with green test suite at every commit boundary
- [ ] `ruff check dispatch/ --select PLR0913,PLR0915,C901` reports **≥1 fewer** PLR0913 violations (realistic target; the `_filter_processed_files` slim-down at orchestrator.py:945 — see §3.8 honest assessment for why this is 1, not 4 or 8)
- [ ] Zero new ruff violations introduced
- [ ] `pytest tests/unit/dispatch_tests tests/unit/dispatch -m "not qt" -n0` passes at each phase
- [ ] `pytest -m smoke` passes after Phase 6
- [ ] Net LOC reduction in `dispatch/orchestrator.py` ≥ 30 lines (revised down from 60 — less reduction once `_process_split_pipeline` and `_send_file` are left untouched per §3.8)
- [ ] Net LOC reduction in `dispatch/services/file_processor.py` ≥ 50 lines (unchanged — wrappers there still inline cleanly)
- [ ] Net LOC reduction in `dispatch/services/folder_discovery.py` ~5 lines (dead `_folder_name` arg + dead alias binding)
- [ ] No public API signature changes (verified by `git diff master` against `process_folder`/`process_file`/`discover_and_process_folder`/`get_summary`/`reset`)
- [ ] New regression test file: `tests/unit/dispatch_tests/test_validation_normalizer.py` with ≥9 parametrized cases
- [ ] Regression test appended to `tests/unit/dispatch_tests/test_orchestrator.py` for `_filter_processed_files` signature
- [ ] `specs/large_function_decomposition.md` updated to mark phase-2 cleanup complete
- [ ] Pre-Phase-1 contract table (in §3.4) circulated to team before any code change

---

## 9. Open Questions

1. **`folder_discovery._filter_processed_files` deletion scope.** Phase 3 strips the dead `_folder_name` param. The follow-up question (separate commit, not in this spec): should the method itself be inlined into its 2 callers (`discover_and_filter_files:149` and `_discover_for_folder:174`)? Both callers do exactly the same thing (`if processed_files: files = self._filter_processed_files(files, processed_files, folder, ...)`), so the wrapper is thin. **Owner: team decision.**

2. **`orchestrator._filter_processed_files` deletion.** It has 0 production callers. Options: (a) delete entirely; (b) leave for the 2 test callers that exercise it (`tests/unit/dispatch_tests/test_orchestrator_pipeline.py:814,857`); (c) replace those tests with calls to `FolderPipelineExecutor._filter_processed_files`. **Owner: team decision.**

3. **`_process_split_pipeline` and `_send_file` arg-count.** Confirmed unfixable without behavior change (every arg used; `ProcessingContext` cannot carry per-folder `run_log`). Leave at 6 args each, document the reason. **Resolved — no further action needed.**

4. **`write_run_log` module location.** Resolved: add to `dispatch/file_utils.py` (existing module). §3.7 updated. **Resolved.**

5. **3-tuple validator output.** Per §3.4 contract table, the unified normalizer rejects non-2-tuples. Search the test corpus for any fixture that passes a 3-tuple to a validator step; if found, document the test failure as part of Phase 1 and update the test or the validator. **Owner: implementer during Phase 1.**

---

## 10. Appendix

### 10.1 References

- `specs/large_function_decomposition.md` — the prior phase; this spec is its successor
- `specs/refactoring-task/plan.md` — orthogonal (legacy `dispatch.py` migration)
- `specs/dispatch-migration.md` — context: dispatch package already established
- `docs/architecture/SPAGHETTI_CODE_ANALYSIS.md` — God-class analysis
- Recent commits: `cc741304c` (Phase 1 decompose), `0a5878031` (orchestrator API), `8e3503991` (dead shims), `38c6866f3` (dead field)

### 10.2 Affected Files Summary

| File | LOC change | Public API change |
|---|---|---|
| `dispatch/orchestrator.py` | −30 to −45 (revised down; `_process_split_pipeline` and `_send_file` left untouched) | No |
| `dispatch/services/file_processor.py` | −50 to −70 (wrappers still inline cleanly here) | No |
| `dispatch/services/folder_discovery.py` | −5 (dead `_folder_name` arg + dead alias binding) | No |
| `dispatch/pipeline/validator.py` | +25 (new function `normalize_validation_output`) | No (additive, public — already in a public module) |
| `dispatch/file_utils.py` | +20 (new `write_run_log` wrapper) | No (additive, internal) |
| `tests/unit/dispatch_tests/test_validation_normalizer.py` | +90 (new file, ≥9 parametrized cases) | N/A |
| `tests/unit/dispatch_tests/test_orchestrator.py` | +15 (signature regression test) | N/A |
| `specs/large_function_decomposition.md` | update prose only | N/A |

**Net change: −65 to −95 LOC across dispatch; +105 LOC of new tests + docs.** (Revised from initial draft's −115 to −145.)

### 10.3 Changelog

| Date | Author | Change |
|---|---|---|
| 2026-07-03 | Refactoring pass | Initial draft |
| 2026-07-03 | Refactoring pass | Verification pass: corrected `_filter_processed_files` call-site confusion (§3.5, §4 Phase 3), elevated Phase 1 from "refactor" to "contract unification" (§3.4, §7 risk #1), corrected ruff-reduction target from "≥8" to "1" (§3.8, §8), replaced `tests/unit/dispatch/` paths with `tests/unit/dispatch_tests/` throughout (§4, §6, §7.1, §8, §10.2), reconciled `write_run_log` location to `dispatch/file_utils.py` (§3.7, §9), tightened import-count claim from "5+" to 6 sites (§2.1, §3.6), revised LOC-reduction target from −115/−145 to −65/−95 (§8, §10.2) |