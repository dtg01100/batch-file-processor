# Spec: Webapp Phase 8 — Pipeline Redesign

**Status:** DRAFT (2026-08-18)
**Author:** Project Owner
**Created:** 2026-08-18
**Updated:** 2026-08-18

> **This is a *design* spec, not an *implementation* spec.**
> Phase 8's deliverable is "the next agent knows what to build,"
> not "the next agent has built it." The actual code work ships in
> Phase 9+ as a sequence of small implementation specs. This spec
> ends with a numbered list of design decisions that must be made
> (in order, with rationale), and three candidate architectures
> the decisions should be measured against. No decision is
> pre-made; the spec exists so the decisions have a coherent
> structure when they're made.

---

## 1. Summary

Phase 6 made the webapp safe to deploy; Phase 7 makes the
desktop-era code honest about its future (deleted). Phase 8
redesigns the file-processing pipeline so that it is owned by the
webapp, designed for a single-host async model, and free of the
15-year accreted complexity the current `dispatch/` tree carries.

The redesign is not a rename and not a rewrite-for-the-sake-of-it.
It is a *targeted simplification* with three goals:

1. **Ownership clarity** — every line of processing code lives
   under `webapp/`; there is no top-level `dispatch/` package.
2. **Async-native** — the pipeline is designed around the
   FastAPI async model, not around the desktop Qt thread-per-folder
   model.
3. **Honest complexity** — code that exists because "the desktop
   app needed it once" is removed; code that exists because the
   *operator* needs it today is preserved with a clear name.

No behavior changes ship in Phase 8 itself. Phase 8 produces a
decision document; Phase 9+ ships the code.

---

## 2. Background

### 2.1 Problem Statement

`webapp/runner.py:23` imports `dispatch.orchestrator.DispatchOrchestrator`.
`webapp/errors.py:31` imports `dispatch.file_utils.build_error_log_filename`.
`webapp/routers/system.py:17` imports
`dispatch.preflight_validator.PreflightValidator`. The webapp is a
thin HTTP layer over `dispatch/`. There is no webapp-native
pipeline.

`dispatch/` is 14,952 lines across 55 files. It is the engine that
powers processing — every `POST /api/run`, every watcher tick, every
resend goes through it. It is *also* the legacy of 15 years of
accretion:

- **`dispatch/orchestrator.py` (691 lines)** — the main coordinator.
  Reads `DispatchConfig`, calls `FolderPipelineExecutor` per folder,
  collects `FolderResult`s. The class structure mirrors the
  desktop app's processing flow, which was synchronous and
  thread-pool-driven.
- **`dispatch/services/`** — eleven modules:
  - `file_processor.py` (per-file)
  - `folder_processor.py` (per-folder)
  - `folder_discovery.py`
  - `database_connector.py`
  - `progress_reporter.py` and `progress_reporting.py` (two parallel
    implementations of the same idea — see §3.1)
  - `upc_service.py`, `customer_lookup_service.py`,
    `uom_lookup_service.py` (lookup abstractions)
  - `item_processing.py`, `file_filter.py` (line-item filtering)
- **`dispatch/pipeline/`** — the per-stage pipeline abstraction
  (validator → splitter → converter → tweaker → sender), each with
  its own module. The factory at
  `dispatch/pipeline/factory.py::create_standard_pipeline` wires the
  standard set.
- **`dispatch/converters/`** — 11 converter plugins under
  `BaseEDIConverter` (an ABC), each with `CONVERTER_METADATA`,
  `convert_to_format` registration, and per-format quirks. Total
  ~6,000 lines.
- **`dispatch/send_manager.py` (426 lines)** — the multi-channel
  delivery engine. `BackendFactory` knows about FTP/SMTP/HTTP/copy.
- **`dispatch/error_handler.py` (429 lines)** — the error-capture
  contract that Phase 5 wired into the webapp. Already partly
  webapp-owned (the ledger lives in `webapp/errors.py`).
- **`dispatch/edi_validator.py` (329 lines)** — EDI A/B/C record
  validation with major/minor classification.
- **`dispatch/preflight_validator.py` (255 lines)** — config
  validation, already used by the webapp.
- **`dispatch/feature_flags.py`, `file_system.py`, `file_utils.py`,
  `hash_utils.py`, `log_sender.py`, `interfaces.py`,
  `processed_files_tracker.py`, `results.py`** — supporting modules,
  each with its own role.

Three structural issues make this hard to evolve:

1. **Two parallel progress-reporting modules** (`progress_reporter.py`,
   `progress_reporting.py`) implement the same contract. One was
   added when the desktop GUI existed and needed Qt-friendly
   progress; the other was added when the webapp needed
   HTTP-friendly progress. Neither was deleted when the other
   became canonical.
2. **Synchronous-only design.** `DispatchOrchestrator.process()`
   is a single blocking call. The webapp wraps it in a worker
   thread (`webapp/runner.py::RunStore._worker`). That works but
   it is two layers of orchestration (the FastAPI background task
   + the worker thread) where one would do.
3. **The 50+ flat `folder_*` columns.** The folders table carries
   `folder_is_active`, `process_backend_copy`, `process_backend_ftp`,
   `process_backend_email`, `process_backend_http`,
   `alert_on_failure`, `tweak_edi`, `prepend_date_files`,
   `split_edi`, `force_edi_validation`, `calculate_upc_check_digit`,
   `upc_target_length`, `include_a_records`, `include_c_records`,
   `include_headers`, `filter_ampersand`, `pad_a_records`,
   `invoice_date_custom_format`, `force_txt_file_ext`,
   `split_prepaid_sales_tax_crec`, `split_edi_include_invoices`,
   `split_edi_include_credits`, `retail_uom`, `force_each_upc`,
   `include_item_numbers`, `include_item_description`, `override_upc_bool`,
   ... 30+ columns, all read by `dispatch/`. The configuration is
   *configuration-shaped like a 1990s desktop app*: a flat bag of
   per-row booleans and strings. Today, a structured config object
   (validated, typed, defaultable) would be safer and shorter.

### 2.2 Motivation

The webapp is the only operator surface (Phase 7's
desktop-retirement decision). Every line of `dispatch/` that
exists *only* because a PyQt5 GUI used to import it is dead code
on the way to the wrong abstraction. The redesign pays off in
three concrete ways:

- **Maintainability.** A new agent who wants to add a converter
  today reads 11 separate plugin files and a 200-line ABC plus a
  factory. A redesigned converter system reads one base class
  and one registry.
- **Observability.** The current error ledger, run history, and
  progress reporting are three different persistence paths. The
  redesign unifies them so an operator with a failing run gets a
  single timeline to read.
- **Async-native.** The webapp is FastAPI. The pipeline is a thread
  pool. They meet in the middle at `webapp/runner.py` with a manual
  `asyncio.run_in_executor` shim. A redesigned pipeline can use
  `asyncio.Task` groups directly and drop the executor hop.

The 11 converters are not in scope to rewrite *semantically* — the
operator's domain logic ("convert this EDI to CSV with these
columns") doesn't change. What changes is the *plumbing*: where
they live, how they're discovered, how they're instantiated, how
their errors propagate.

### 2.3 Prior Art

- **Webapp runner** (`webapp/runner.py`) — already shows the
  intended pattern: a `RunStore` with `start_run` /
  `wait_run`, a `_worker` thread, structured per-folder results
  with timestamps. Phase 8's pipeline needs to *be* this kind of
  thing, not be wrapped by it.
- **Phase 5 errors module** (`webapp/errors.py`) — already
  webapp-owned. The error ledger lives here, not in
  `dispatch/error_handler.py`. Phase 8's pipeline should
  write errors through `webapp/errors.insert_error` directly,
  not through the `dispatch.error_handler.ErrorHandler`
  adapter.
- **Phase 6.4 soft-delete** — established the pattern of webapp
  modules owning their own data flow (table DDL in
  `webapp/database.py`, endpoints in `webapp/routers/`, supervisor
  class colocated with the endpoints that use it). Phase 8
  applies the same pattern to the pipeline.
- **FastAPI lifespan** (`webapp/main.py::_lifespan`) — already
  starts the scheduler, the watcher, and (since 6.4) the
  soft-delete trim job. The redesigned pipeline should start
  here too.
- **Plugin API surface** (`webapp/converters_api.py`) — Phase 6
  added a webapp-side `all_converter_specs()` that the folder
  editor uses to render per-format config UIs. It hardcodes the
  11 converter keys. Phase 8 should make this registry-driven
  so adding a 12th converter is a one-file change.

---

## 3. Design

### 3.1 Architecture Alignment

- [x] Reviewed `docs/ARCHITECTURE.md` — the webapp module is the
  operator-facing layer; `dispatch/` is the processing layer.
  Phase 8 collapses them: the processing layer *is* the webapp.
- [x] Reviewed `docs/DATABASE_DESIGN.md` — the folders table's flat
  column bag is the constraint. A redesigned config object
  either persists as JSON in a single column (breaking the
  schema) or as a child `folder_config` table (one more table).
  This is an open design question (§4.1).
- [x] Reviewed `docs/PROCESSING_DESIGN.md` — the pipeline stages
  (validator → splitter → converter → tweaker → sender) are the
  right stages. Phase 8 doesn't change the stages; it changes the
  *plumbing*.
- [x] Reviewed `docs/PLUGIN_DESIGN.md` and
  `docs/PLUGIN_DEVELOPER_GUIDE.md` — the converter plugin model is
  documented. Phase 8 keeps the plugin model but moves it under
  `webapp/converters/`.
- [x] Reviewed `docs/TESTING_DESIGN.md` — new pipeline tests live
  in `tests/webapp/test_pipeline_*.py`. The fixture pattern from
  `test_soft_delete.py` and `test_database_repair.py` applies.
- [x] Reviewed `AGENTS.md` — no silent `except: pass`; the
  redesigned pipeline must log pipeline failures the way the
  current one does (via `webapp/errors.insert_error` with
  consecutive-failure dedupe).

### 3.2 Components affected (target shape)

```
webapp/
├── pipeline/                # NEW: the redesigned pipeline
│   ├── __init__.py
│   ├── orchestrator.py      # was dispatch/orchestrator.py
│   ├── folder_executor.py   # was dispatch/services/folder_processor.py
│   ├── file_processor.py    # was dispatch/services/file_processor.py
│   ├── config.py            # new typed config (see §4.1)
│   ├── stages/              # was dispatch/pipeline/{validator,splitter,converter,temp_dir_utils}.py
│   │   ├── validator.py
│   │   ├── splitter.py
│   │   └── converter.py
│   ├── discovery.py         # was dispatch/services/folder_discovery.py
│   ├── backends.py          # was dispatch/send_manager.py
│   ├── edi.py               # was dispatch/edi_validator.py
│   ├── preflight.py         # was dispatch/preflight_validator.py
│   └── hash.py              # was dispatch/hash_utils.py
├── converters/              # NEW: 11 converters move here
│   ├── base.py              # was dispatch/converters/convert_base.py
│   ├── csv.py               # was dispatch/converters/convert_to_csv.py
│   ├── estore_einvoice.py   # was dispatch/converters/convert_to_estore_einvoice.py
│   ├── ... (8 more)
│   └── registry.py          # NEW: discovers converters from this dir
├── errors.py                # EXISTING: absorbs dispatch/error_handler.py
├── watcher.py               # EXISTING: calls into webapp/pipeline/
└── runner.py                # EXISTING: simplified — now a thin async wrapper

# Top-level removals:
dispatch/                    # ENTIRELY DELETED
interface/                    # ALREADY GONE per Phase 7
```

`webapp/pipeline/` is the new home for processing logic. The
folder editor and Diagnostics card already import from
`webapp/`; the rename + move is the visible change. Importers
of `dispatch.*` (currently just `webapp/runner.py:23`,
`webapp/errors.py:31`, `webapp/routers/system.py:17`) get updated
to import from `webapp/pipeline.*`.

### 3.3 Three candidate architectures

The Phase 8 implementation will pick one of these (or a hybrid).
Listing them here with their trade-offs so the decision is
visible.

#### Candidate A: Rename and minimal-touch

**Shape.** Move `dispatch/` → `webapp/pipeline/` (or
`webapp/dispatch/`) without rewriting any semantics. Update the
three importers. Add the async wrapper in `webapp/runner.py`
that's currently a manual `run_in_executor` shim.

**Pros.** Lowest risk. No behavior changes. Each existing test
still passes without modification. Can ship in days, not weeks.

**Cons.** Inherits all of `dispatch/`'s complexity. The
two-progress-reporter modules, the flat-bag config, the
synchronous orchestrator — all stay. The next agent who wants
to add a 12th converter still has to read 200 lines of ABC plus
a factory plus a registry.

**Best for.** A team that wants ownership clarity *now* and is
willing to do the real simplification in a follow-on Phase 9.x.

#### Candidate B: Rename + targeted simplifications

**Shape.** Move `dispatch/` → `webapp/pipeline/`. While moving,
collapse the two progress reporters into one, fold
`dispatch/results.py` into `webapp/pipeline/config.py`, and
introduce a structured `FolderConfig` dataclass that reads from
the existing flat `folders` columns via a thin adapter. Keep the
11 converters' bodies unchanged.

**Pros.** Inherits Candidate A's low risk for the renames, and
gets real structural wins (one progress module, typed config,
cleaner import graph). The converter plugins stay
operator-domain-stable.

**Cons.** The structured config is an *adapter* over a flat
schema — there's a small ongoing tax (two ways to read config
fields) until the schema itself changes. The two progress
reporters still have to merge their APIs.

**Best for.** A team that wants ownership clarity *and* structural
cleanup without committing to a full schema redesign.

#### Candidate C: Full redesign (rename + config object + async pipeline)

**Shape.** Move `dispatch/` → `webapp/pipeline/`. Replace the flat
`folders` column bag with a JSON `config_json` column (or a
child `folder_config` table). Make the orchestrator a class
that takes an `asyncio.TaskGroup` and yields per-folder results
as they complete. Replace the two progress reporters with a
single async-aware reporter. Keep the 11 converters' bodies
unchanged.

**Pros.** Maximally future-proof. The pipeline becomes
asyncio-native; the config becomes typed and validated; the
import graph collapses to a single tree. New agents have one
place to look for everything.

**Cons.** Schema migration. Every existing test fixture that
inserts `process_edi=False` etc. needs updating. The webapp
folder editor (Phase 4's `FolderEditSchema`) needs to round-trip
the new config. Risk of behavioral drift if the converter
defaults aren't carried verbatim.

**Best for.** A team that wants to *finish* the migration and
is willing to commit weeks of focused work, with a dedicated
test reviewer.

#### Phase 8 recommendation

**Pick Candidate B.** The rename gives ownership clarity
(Candidate A's win); the targeted simplifications give real
structural cleanup without a schema migration (Candidate C's
risk without its schema reward); the converters stay stable,
which is the operator-facing promise.

Candidate C is not wrong; it's a Phase 9+ follow-on if the
adapter tax in Candidate B becomes painful.

### 3.4 Async-native design (the part that applies to whichever candidate wins)

The webapp is FastAPI. Today the pipeline runs in a worker
thread spawned by `webapp/runner.py::RunStore._worker`. The
candidate architectures above all share this property: there's a
*boundary* between FastAPI's event loop and the pipeline.

**Phase 8's design question:** should the pipeline itself be
async, or should the boundary be a thread-pool submit?

**Argument for thread-pool.** The pipeline touches the
filesystem (blocking `iterdir`, blocking `read`), the database
(blocking `sqlite3` calls), and the network (blocking FTP/SMTP
sockets). Making these calls async is a rewrite, not a
refactor. The current `run_in_executor` shim is honest about
this: "the pipeline is blocking; we run it on a worker."

**Argument for async.** Per-folder processing is mostly I/O
wait. Running N folders as N coroutines on one event loop is
~zero-overhead compared to N threads. The watcher tick + run
+ scheduler + restore can share one event loop instead of N
threads.

**Phase 8's answer:** thread-pool stays. The boundary is
`asyncio.run_in_executor` with `asyncio.wait_for` cancellation
on operator-initiated stop. The pipeline internals stay
synchronous. This is the lowest-risk path that *still* unifies
the FastAPI + pipeline interface into one async-aware module.

(The "fully async pipeline" is Candidate C's territory. If
Phase 9+ takes Candidate C, the pipeline internals become async.
Phase 8's design doesn't preclude that — it just doesn't force
it.)

### 3.5 Converter registry (applies to whichever candidate wins)

Today, `webapp/converters_api.py::all_converter_specs()` returns a
hardcoded list of 11 specs. The Phase 6.0 work added UI for all
11 formats; the list is in two places (the converters dir and
the converter specs).

**Phase 8's design:** one registry, in `webapp/converters/registry.py`,
discovers converters by scanning the `webapp/converters/`
directory. Adding a 12th converter becomes a one-file change:
drop `webapp/converters/foo.py` with `CONVERTER_METADATA = {...}`
at module scope.

```python
# webapp/converters/registry.py (shape, not implementation)

@dataclass(frozen=True)
class ConverterSpec:
    format_key: str          # e.g. "csv"
    display_name: str        # e.g. "CSV"
    module_path: str         # e.g. "webapp.converters.csv"
    config_fields: tuple[ConfigField, ...]

def discover_converters() -> tuple[ConverterSpec, ...]:
    """Scan webapp/converters/ for modules exposing CONVERTER_METADATA."""

def get_converter(format_key: str) -> BaseConverter:
    """Resolve a format key to a converter instance."""

# webapp/converters/csv.py (shape)
CONVERTER_METADATA = ConverterSpec(
    format_key="csv",
    display_name="CSV",
    module_path=__name__,
    config_fields=(...),
)
```

This is a small change (~100 lines) but it removes a class of
"the converter exists but the UI doesn't know about it" bugs.

### 3.6 What does *not* change

- **The 11 converter bodies** — operator domain logic. Moving
  them to `webapp/converters/` is a path change, not a rewrite.
  Any conversion that works today works tomorrow.
- **The folders table schema** — at least in Phase 8 itself.
  Candidate B's structured-config adapter reads the existing flat
  columns verbatim.
- **The error ledger** (`webapp/errors.py`) — already webapp-owned.
  The redesigned pipeline writes errors here directly, not via
  the `dispatch.error_handler` adapter.
- **The Phase 6 endpoints** — `POST /api/run`, `POST /api/resend`,
  etc. Their request/response shapes don't change.

---

## 4. Open Design Decisions (the questions Phase 8 must answer)

The list below is in **decision order** — each later decision
depends on earlier ones. Phase 8's job is to make these decisions
and document the rationale, not to debate them again in Phase 9.

### 4.1 Config object shape (DECISION 1)

**Question.** Should the pipeline read configuration from
`webapp/pipeline/config.py::FolderConfig` (a typed dataclass
that adapts from the existing flat `folders` columns), or from a
new `folder_config` table that stores structured config?

| Option | Pros | Cons |
|--------|------|------|
| Adapter dataclass, flat schema unchanged | Zero migration; works on existing DBs | Two ways to read config (the dataclass + the flat columns); adapters rot if the schema grows |
| New `folder_config` table, JSON column | Type-safe; clean; future-proof | Migration; every fixture needs updating; risk of behavioral drift in the JSON serialization |

**Phase 8 picks:** Adapter dataclass (Candidate B's path). The
schema can move to JSON in a Phase 9+ if the adapter tax becomes
unmanageable. Document the trade-off in
`webapp/pipeline/config.py`'s module docstring so a future agent
knows where to look.

### 4.2 Two-progress-reporter merge (DECISION 2)

**Question.** The two `dispatch/services/progress_reporter*.py`
modules both implement "report progress." Which one stays?

The webapp uses both — `dispatch/services/progress_reporting.py`
is the HTTP/SSE-aware one (used by `webapp/runner.py`); the
desktop-era `dispatch/services/progress_reporter.py` is the
Qt-friendly one. The desktop-era one is unused after the
webapp-pivot.

**Phase 8 picks:** Delete `dispatch/services/progress_reporter.py`
(after the move, that becomes `webapp/pipeline/progress.py`).
The HTTP/SSE-aware reporter becomes the only one. The
`ProgressReporter` interface (`webapp/pipeline/types.py`)
shrinks to just the methods the SSE path needs.

### 4.3 Sync pipeline + async wrapper (DECISION 3)

**Question.** Confirm the boundary: pipeline internals are
synchronous; the FastAPI side runs them via `run_in_executor`.

**Phase 8 picks:** confirmed (see §3.4). The `webapp/runner.py`
simplifies — no more `_worker` thread, no more
`asyncio.run_in_executor` shim duplicated; the lifespan starts
a single `concurrent.futures.ThreadPoolExecutor` and the
pipeline calls `loop.run_in_executor(None, fn, *args)` for
each pipeline run.

### 4.4 Converter discovery (DECISION 4)

**Question.** Where does the converter registry live, and how
does it discover converters?

**Phase 8 picks:** `webapp/converters/registry.py` scans the
`webapp/converters/` directory at import time using
`pkgutil.iter_modules` + a `CONVERTER_METADATA` module attribute
on each converter. `webapp/converters_api.py::all_converter_specs()`
becomes a thin wrapper around `discover_converters()`.

### 4.5 Error ledger integration (DECISION 5)

**Question.** How does the redesigned pipeline report errors?

The current `dispatch/error_handler.py::ErrorHandler` is a
class that wraps a list of errors and a file-rotation policy.
The webapp uses it via `webapp/errors.py::LedgerDatabase`
adapter (which writes to `dispatch_errors` table).

**Phase 8 picks:** The redesigned pipeline calls
`webapp/errors.insert_error(...)` directly. No
`ErrorHandler` class. No `LedgerDatabase` adapter. The
`dispatch/error_handler.py` file gets deleted in the move.

### 4.6 Watcher integration (DECISION 6)

**Question.** The webapp's `webapp/watcher.py` currently calls
`dispatch/orchestrator.DispatchOrchestrator` via
`webapp/runner.py`. After Phase 8, the watcher calls
`webapp/pipeline/orchestrator.PipelineOrchestrator` (or
whatever the new class is named) directly.

**Phase 8 picks:** yes, the watcher calls the new orchestrator
directly. No intermediate `webapp/runner.py` indirection for
the watcher — only for the operator-initiated `POST /api/run`.

### 4.7 Test fixture updates (DECISION 7)

**Question.** Every existing test that inserts a folder row with
flat `process_edi=False` etc. continues to work because the flat
schema is unchanged. But tests that *mock* the pipeline
(`tests/webapp/test_runner.py`, etc.) need to point at the new
import path.

**Phase 8 picks:** Rename the test fixtures' import paths. No
behavior changes in the tests. A `tests/webapp/conftest.py`
helper provides a `make_folder_row(...)` factory that knows
both the old and new shapes, so future tests don't have to
hand-roll the 50-column insert.

### 4.8 Documentation (DECISION 8)

**Question.** `dispatch/AGENTS.md` documents the package
layout. After Phase 8, `webapp/pipeline/AGENTS.md` documents
the new layout.

**Phase 8 picks:** write `webapp/pipeline/AGENTS.md` modeled on
the existing `dispatch/AGENTS.md`, but updated to reflect
that the orchestrator is now async-aware, the progress module
is consolidated, and the converter registry is the single
source of truth.

### 4.9 Backwards compatibility (DECISION 9)

**Question.** Do we keep the `dispatch/` package as a thin
shim that re-exports from `webapp/pipeline/` for one release?

**Phase 8 picks:** No shim. The Phase 7 spec already removes
`interface/`. A shim that says "the old name still works"
defeats the purpose. Any external caller (and there are none
outside the repo) gets a hard import error; that's a feature.

### 4.10 Sequencing within Phase 8 (DECISION 10)

**Question.** In what order do the implementation commits land?

**Phase 8 picks:** this is also the Phase 9 sequencing. See
§6.2.

---

## 5. Database Changes

### 5.1 Schema Changes

None. Candidate B's adapter keeps the existing flat schema. A
follow-on phase can move to JSON-in-a-column or a child config
table if the adapter tax becomes painful.

### 5.2 Migration Strategy

No migration. The schema is unchanged.

### 5.3 Migration Checklist

- [ ] No `migrations/` version bump.
- [ ] No `core/database/schema.py` change.
- [ ] No `backend/database/sqlite_wrapper.py` change.

---

## 6. Testing Strategy

### 6.1 Test Cases

The Phase 8 deliverable is a *decision document*, not code.
Tests live in Phase 9+. This section documents the test plan
that Phase 9+ commits against.

| Test Case | Type | Description | Expected Result | Phase |
|-----------|------|-------------|-----------------|-------|
| `test_pipeline_module_layout` | import | `import webapp.pipeline` succeeds; `import dispatch` raises `ImportError` | new path works, old path gone | 9.x |
| `test_pipeline_uses_webapp_errors` | integration | Trigger a pipeline failure; assert the error is in the `dispatch_errors` table via `webapp/errors.list_errors` | error captured via webapp path | 9.x |
| `test_converter_registry_discovers_all_11` | registry | `discover_converters()` returns exactly 11 specs | 11 | 9.x |
| `test_pipeline_async_boundary` | threading | `webapp/runner.py` runs the pipeline via `run_in_executor`; assert no synchronous-blocking call happens on the FastAPI event loop | executor used | 9.x |
| `test_folder_config_adapter_round_trip` | config | For every existing folder row in `tests/fixtures/folders.db`, the `FolderConfig` adapter reads the same field values as the flat row | values match | 9.x |
| `test_pipeline_replaces_dispatch_in_watcher` | integration | A watcher tick triggers a pipeline run; assert the run completes | run succeeds | 9.x |

### 6.2 Test File Locations

- `tests/webapp/test_pipeline_layout.py` (new) — 9.x
- `tests/webapp/test_pipeline_errors.py` (new) — 9.x
- `tests/webapp/test_pipeline_registry.py` (new) — 9.x
- `tests/webapp/test_pipeline_async.py` (new) — 9.x
- `tests/webapp/test_folder_config.py` (new) — 9.x
- `tests/webapp/test_watcher_pipeline.py` (new) — 9.x

### 6.3 Coverage Requirements

- [ ] New code covered by tests.
- [ ] Existing tests still pass — baseline 304 webapp python + 116
  DOM + 5 new (from Phase 7) + 6 new (from Phase 9.x).
- [ ] `ruff check webapp/ tests/webapp/ backend/database/` clean.
- [ ] `black --check webapp/ tests/webapp/ backend/database/` clean
  on changed files.
- [ ] **No file under `dispatch/` exists after Phase 9.x ships.**
  Verified by `find dispatch -name "*.py"` returning empty.

---

## 7. Risk Assessment

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| A converter's behavior subtly changes during the move | Medium | High (operator-facing) | Phase 8 commits to *moving*, not rewriting. Each converter's body is copied verbatim. A per-converter golden-file test (existing pattern: `tests/golden_files/`) is added in Phase 9.x to catch any drift. |
| Two-progress-reporter merge loses a method call the webapp depends on | Medium | Medium | The merge is a documented decision (DECISION 2). The unused reporter is verified unused before deletion (`grep -rn "ProgressReporter" webapp/` finds zero hits in the SSE path). |
| Async-boundary change introduces a hang | Low | High | Phase 8 picks `run_in_executor` (Candidate B), not a full async pipeline. The pattern is already proven in `webapp/runner.py`. Cancellation via `asyncio.wait_for` is bounded. |
| Schema migration needed despite DECISION 1's "no" | Low | High | DECISION 1 is the *explicit* Phase 8 decision. If a Phase 9 implementation discovers it can't be done without a migration, the implementation halts and reports; Phase 8's decision is re-opened. |
| External consumer of `dispatch.*` breaks | Very Low | Low | No external consumer (verified — `dispatch/` is internal). |
| 11 converters' `BaseEDIConverter` subclasses diverge | Medium | Low | The ABC stays the same. Subclasses are moved verbatim. Golden-file tests catch output drift. |
| Webapp folder editor (`webapp/folder_schema.py`) round-trips the new config poorly | Low | Medium | DECISION 1 keeps the flat schema. `FolderEditSchema` continues to read/write the flat columns. The `FolderConfig` dataclass is *read-only* on the webapp side. |
| `webapp/runner.py` rewrite loses edge cases | Medium | High | Phase 9.x keeps the existing `RunStore` class; the change is replacing the `_worker` thread with a `run_in_executor` call. Every existing `test_runner.py` case continues to apply. |

### 7.1 Rollback Plan

Each Phase 9.x commit is self-contained.

- **Phase 9.1** (rename + move, no behavior change): `git revert`
  restores the original paths. Tests still pass.
- **Phase 9.2** (two-progress-reporter merge): if a missing
  method call is discovered, `git revert` and document the
  method that needed to stay.
- **Phase 9.3** (async-boundary change): revert the
  `run_in_executor` swap; restore the worker thread.
- **Phase 9.4** (converter registry): the new registry can
  coexist with the old hardcoded list — fall back to the old
  list by deleting the new `registry.py` import.

---

## 8. Success Criteria

**Phase 8 itself (the design document):**

- [ ] All 10 design decisions in §4 have a documented answer.
- [ ] Three candidate architectures are documented in §3.3 with
  their trade-offs.
- [ ] The async-boundary question is answered (§3.4 / DECISION 3).
- [ ] The converter registry design is concrete (§3.5 / DECISION 4).
- [ ] The Phase 9 sequencing (§6.2) is ordered and small enough
  that each commit is reviewable in under 30 minutes.

**Phase 9+ (the implementation, future):**

- [ ] No file under `dispatch/` exists.
- [ ] `import webapp.pipeline` succeeds.
- [ ] `webapp/runner.py` runs the pipeline via `run_in_executor`.
- [ ] The 11 converters are discovered automatically from
  `webapp/converters/`.
- [ ] Golden-file tests pass for every converter (no behavior
  drift).
- [ ] `pytest tests/webapp -q` is 100% green.
- [ ] `ruff check` and `black --check` clean.

---

## 9. Open Questions

1. **Should Phase 9 also rewrite `dispatch/converters/` converters
   into typed dataclass-style plugins, or keep the
   `parameters_dict` config bag?** The current API passes a flat
   dict. A typed config dataclass would catch more errors at
   load time. **TENTATIVE:** Phase 9 keeps the flat dict for
   backward compatibility; a Phase 10+ introduces the typed
   version as an opt-in.
2. **Should Phase 9 also rename `webapp/runner.py` to
   `webapp/pipeline/runner.py`?** Renaming the file moves it
   into the new package, which is cleaner. **TENTATIVE:** yes;
   the rename is mechanical.
3. **Does `dispatch/observability/` (the structured-logging
   integration) get folded into `webapp/pipeline/` or stay in
   `core/`?** `core/structured_logging.py` already exists.
   **TENTATIVE:** Phase 9 deletes `dispatch/observability/` as a
   separate package and relies on `core/structured_logging` for
   all pipeline logs.
4. **Should Phase 8 ship its decision document as a
   `decisions.md` file or as the §4 table in this spec?** Splitting
   decisions into their own file makes Phase 9+ referencing
   easier. **TENTATIVE:** keep in §4 for now; split out into
   `docs/architecture/webapp-phase-8-decisions.md` if Phase 9
   finds the table getting referenced a lot.
5. **Should `webapp/pipeline/` be `webapp/dispatch/` instead?** The
   current `dispatch/` name has 15 years of muscle memory behind
   it. **TENTATIVE:** `webapp/pipeline/` (the new package
   doesn't dispatch anything — it *processes* files). The
   rename is the whole point of Phase 8.

---

## 10. Appendix

### 10.1 References

- `dispatch/AGENTS.md` — the current dispatch package's structure
  map; this is what Phase 9 deletes.
- `dispatch/orchestrator.py` (691 lines) — the current
  orchestrator; becomes `webapp/pipeline/orchestrator.py`.
- `dispatch/services/folder_processor.py`,
  `dispatch/services/file_processor.py` — the per-folder and
  per-file executors.
- `dispatch/pipeline/factory.py::create_standard_pipeline` — the
  current standard pipeline factory.
- `dispatch/converters/` — the 11 converter plugins.
- `dispatch/send_manager.py` (426 lines) — the multi-channel
  delivery engine.
- `dispatch/error_handler.py` (429 lines) — the error handler.
- `webapp/runner.py` — the current runner that wraps the
  pipeline in a worker thread.
- `webapp/errors.py` — the webapp-owned error ledger.
- `webapp/converters_api.py` — the hardcoded converter spec list.
- `webapp/main.py::_lifespan` — the lifespan that starts the
  scheduler, watcher, and trim job; Phase 9 starts the pipeline
  runner here too.
- `docs/PROCESSING_PIPELINE.md`,
  `docs/PROCESSING_DESIGN.md` — the existing pipeline docs.
- `specs/webapp-phase-7-operator-confidence.md` — the Phase 7
  spec that scopes `interface/` deletion.

### 10.2 Changelog

| Date | Author | Change |
|------|--------|--------|
| 2026-08-18 | Project Owner | Initial draft — three candidate architectures; ten design decisions; Phase 9+ sequencing |
