# Dispatch Import Architecture (and the Import Cycle)

**Last updated:** 2026-08-09
**Scope:** `dispatch/`, `interface/`, and anything that imports them.

This document explains the `dispatch.results -> dispatch.services ->
dispatch.pipeline -> dispatch.results` import cycle: how it forms, why it was
latent for a long time, what fixed it, and the rules that keep it from coming
back.

## The cycle

```
dispatch.results
    │  (1) from dispatch.services.progress_reporter import ProgressReporter   ← RUNTIME edge (was)
    ▼
dispatch.services/__init__.py          ← eager re-export: importing ANY
    │  (2) from dispatch.services.file_processor import ...                    services.* submodule runs this file
    ▼
dispatch.services.file_processor
    │  (3) from dispatch.pipeline.splitter import SplitterResult               ← module-level edge (was)
    ▼
dispatch.pipeline/__init__.py          ← eager re-export: importing ANY
    │  (4) from dispatch.pipeline.factory import create_standard_pipeline      pipeline.* submodule runs this file
    ▼
dispatch.pipeline.factory
    │  (5) from dispatch.results import DispatchConfig
    ▼
dispatch.results  ────────────────────────── CYCLE (results is mid-load) ✗
```

Two `__init__.py` files make this far worse than a two-module tangle:

- `dispatch/services/__init__.py` eagerly re-exports every public name, so
  `import dispatch.services.progress_reporter` (edge 1) boots the *entire*
  services package, including `file_processor`.
- `dispatch/pipeline/__init__.py` eagerly re-exports every pipeline step, so
  `import dispatch.pipeline.splitter` (edge 3) boots the *entire* pipeline
  package, including `factory`, which imports `dispatch.results` (edge 5).

## Root cause

`dispatch/results.py` is supposed to be a leaf — it holds shared dataclasses
(`DispatchConfig`, `FolderResult`) with no business logic. But it imported a
concrete service type at runtime:

```python
# dispatch/results.py (before the fix)
from dispatch.services.progress_reporter import ProgressReporter   # annotation-only use!
...
progress_reporter: ProgressReporter | None = None
```

`ProgressReporter` is used **only as a type annotation**. The runtime import
was the single edge that let `dispatch.results` reach back into
`dispatch.services` (1), which reaches `file_processor` (2), which — once any
module-level `dispatch.pipeline` import existed — reaches `factory` (4) and
returns to `results` (5).

Why it was latent for so long: the loop only closes when **both** directions
exist. For a long time `dispatch.services.*` had no module-level
`dispatch.pipeline` imports, so the graph was a DAG and every import order
worked. In 2026-08, `file_processor.py` gained module-level pipeline imports
for the split flow, closing the loop — and `import dispatch.results` /
`import dispatch.orchestrator` as a **first** import started raising
`ImportError: cannot import name 'DispatchConfig' from partially initialized
module 'dispatch.results'`.

Most tests and the Qt app never noticed because their import order happened to
load `dispatch.pipeline` fully before `dispatch.results` (Python caches the
partially initialized module in `sys.modules`, so the second attempt to import
it is skipped and the cycle only *sometimes* blows up — it depends entirely on
which module is imported first in a given process).

## The fix (2026-08-09)

Two changes, one at the root and one at the trigger:

1. **`dispatch/results.py` — make it a true leaf.** `ProgressReporter` is now
   imported under `TYPE_CHECKING` (with `from __future__ import annotations`).
   `dispatch.results` no longer reaches into `dispatch.services` at runtime,
   so there is no path from `dispatch.pipeline` back into `dispatch.services`
   through `factory` — the loop is structurally impossible again.

2. **`dispatch/services/file_processor.py` — keep pipeline imports
   function-local.** `SplitterResult` is imported under `TYPE_CHECKING` for
   annotations and inside `_run_splitting()` for runtime use. `temp_dir_utils`
   is also imported inside the function. This matches the codebase's existing
   convention (e.g. `_normalize_validation_output` imports
   `dispatch.pipeline.validator` locally).

## Rules for future changes

1. **`dispatch/results.py` and `dispatch/interfaces.py` are leaves.** Never
   add a runtime import from them into `dispatch.services.*`,
   `dispatch.pipeline.*`, or anything that transitively reaches those
   packages. If a name is only used in a type annotation, import it under
   `TYPE_CHECKING` (and add `from __future__ import annotations` if the module
   does not have it).

2. **`dispatch/services/*` must not module-level-import `dispatch.pipeline.*`.**
   The two packages form a bidirectional dependency through
   `pipeline.factory -> results` (fine, results is a leaf) — do not add the
   opposite module-level edge. Function-local imports are the sanctioned
   pattern when a service needs a pipeline step type at runtime.

3. **Be careful with the eager `__init__.py` re-exports.** Because
   `dispatch/services/__init__.py` and `dispatch/pipeline/__init__.py`
   re-export everything, a dependency that looks harmless at the submodule
   level ("I only import `dispatch.pipeline.splitter`") actually pulls in the
   whole package. When adding a new import, trace what its parent package
   `__init__.py` drags in before assuming the graph is acyclic.

4. **When adding a new module-level `dispatch.*` import anywhere, run the
   import-order smoke check below.** Import cycles in Python are
   order-dependent: the same code that imports fine in tests can crash in a
   fresh process.

## Verification

These must all succeed in a **fresh interpreter** (first import order):

```bash
python -c "import dispatch.results"
python -c "import dispatch.orchestrator"
python -c "import dispatch.pipeline"
python -c "import dispatch.services.file_processor"
python -c "import dispatch.send_manager"
python -c "import interface.qt.app"
```

If any raises `ImportError` about a *partially initialized module*, an import
cycle has been reintroduced — see the rules above.

The regression test `tests/unit/dispatch_tests/test_import_order.py` runs
these as subprocesses on every test run.

## How to debug a cycle if one reappears

1. Reproduce with the failing first import: `python -c "import dispatch.X"`.
   The traceback shows the chain that loops back.
2. Identify which edge is new (compare against the diagram above).
3. Decide the fix:
   - annotation-only use → `TYPE_CHECKING` (leaf modules),
   - runtime use inside a service → function-local import,
   - genuine structural need → break the cycle at the `__init__.py` level
     (make one package's re-exports lazy) instead of adding `# noqa` or
     import hacks.
