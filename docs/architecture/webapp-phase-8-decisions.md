# Decisions: Phase 8 — Pipeline Redesign

**Status:** APPROVED
**Author:** Project Owner
**Created:** 2026-09-02
**Updated:** 2026-09-02

> Phase 8's deliverable. Each decision below corresponds to a
> §4 item in [the Phase 8 design spec](../../specs/webapp-phase-8-pipeline-redesign.md).
> The decision is the answer; the rationale is the reasoning;
> the consequences are what Phase 9+ commits land.

---

## DECISION 1 — Config object shape

**Question:** Adapter dataclass over flat schema, or new
`folder_config` table with JSON column?

**Answer:** **Adapter dataclass, flat schema unchanged.**

**Rationale:**
- Zero migration risk. Existing folders databases work as-is.
- The flat schema is the *source of truth* today; an adapter
  reads it as a typed object without owning a second copy of the
  data.
- "Adapter tax" (the cost of having two read paths) is currently
  small: one `FolderConfigAdapter.from_row(dict) -> FolderConfig`
  function. If the schema grows past ~60 columns or the adapter
  becomes painful to evolve, revisit at the Phase 10 checkpoint
  (per ROADMAP §5.4).

**Consequences for Phase 9+:**
- `webapp/pipeline/config.py::FolderConfigAdapter` is the single
  read path.
- `webapp/folder_schema.py` continues to write flat columns.
- The adapter is read-only from the pipeline's perspective; the
  webapp editor is the only writer.
- Phase 11 builds on this: per-converter config dataclasses
  (`CSVConverterConfig`, etc.) are constructed by the adapter
  from `parameters_dict`.

---

## DECISION 2 — Two-progress-reporter merge

**Question:** Which of `dispatch/services/progress_reporter.py`
(Qt/CLI era) and `dispatch/services/progress_reporting.py`
(HTTP/SSE era) survives?

**Answer:** **Delete `progress_reporter.py`. Keep `progress_reporting.py`.**

**Rationale:**
- The webapp is the only operator surface (Phase 7's
  desktop-retirement decision).
- `progress_reporter.py`'s `UIProgressReporter` calls an
  `update_overlay(parent=...)` method that does nothing
  (`pass`). It was wired to Qt widgets that no longer exist.
- `progress_reporting.py` is the SSE-aware one already imported
  by `webapp/runner.py`. It's the canonical path.

**Consequences for Phase 9+:**
- `progress_reporter.py` deleted in 9.2.
- The 6-parameter `update(message, folder_num, folder_total,
  file_num, file_total, footer)` signature shrinks to what's
  actually used by the SSE path. (TBD in 9.2 — Phase 11 may
  collapse it further.)

---

## DECISION 3 — Sync pipeline + async wrapper

**Question:** Confirm the boundary: pipeline internals are
synchronous; the FastAPI side runs them via `run_in_executor`.

**Answer:** **Confirmed. Sync internals, `run_in_executor` from
the FastAPI side.**

**Rationale:**
- `DispatchOrchestrator.process()` is a single blocking call
  today. Wrapping it in `run_in_executor` is the proven pattern
  (already used in `webapp/runner.py::_worker`).
- Async-native pipeline internals (Candidate C) require rewriting
  every `for record in file` loop into async generators. The
  payoff (slightly cleaner cancellation) doesn't justify the
  rewrite cost for an internal tool that runs one operator at a
  time.
- Cancellation via `asyncio.wait_for` is bounded — the operator
  can't accidentally trigger a runaway pipeline.

**Consequences for Phase 9+:**
- `webapp/runner.py::_worker` thread is replaced by
  `loop.run_in_executor(None, pipeline.process, folder_config)`.
- `webapp/main.py::_lifespan` starts a single
  `concurrent.futures.ThreadPoolExecutor` at boot; the runner
  reuses it.
- `PipelineOrchestrator.process()` keeps a synchronous signature.

---

## DECISION 4 — Converter discovery

**Question:** Where does the converter registry live, and how
does it discover converters?

**Answer:** **`webapp/converters/registry.py` scans the
`webapp/converters/` directory at import time using
`pkgutil.iter_modules` + `CONVERTER_METADATA` per converter.**

**Rationale:**
- The discovery code already exists in
  `dispatch/converters/registry.py` (post-Phase 9.1, moves to
  `webapp/converters/registry.py`). Phase 9.4 ports it verbatim.
- Each converter declaring its own `CONVERTER_METADATA` is a
  pattern that's already established; 11 of 12 converters (now
  including x810 added in Phase X) have it.
- `webapp/converters_api.py::all_converter_specs()` becomes a
  thin wrapper around `registry.discover_converters()`.

**Consequences for Phase 9+:**
- Adding a 12th, 13th, ... converter is a one-file change.
- The webapp folder editor's converter dropdown auto-populates.
- Phase 11.4 hooks into this: the registry's metadata includes
  the converter's config dataclass type, which the
  `FolderConfigAdapter` uses to construct typed configs.

---

## DECISION 5 — Error ledger integration

**Question:** How does the redesigned pipeline report errors?

**Answer:** **Pipeline calls `webapp/errors.insert_error(...)`
directly. No `ErrorHandler` class. No adapter.**

**Rationale:**
- `webapp/errors.py` already owns the ledger (`dispatch_errors`
  table). Phase 5 wired this up.
- `dispatch/error_handler.py::ErrorHandler` is a 429-line class
  that wraps a list of errors and a file-rotation policy. The
  webapp uses *part* of it (the record-error method) via an
  adapter in `webapp/errors.py`. The class exists for the legacy
  Qt error dialog, which is gone.
- Direct calls are shorter, faster to read, and remove the
  adapter layer that has to be kept in sync with the underlying
  API.

**Consequences for Phase 9+:**
- `dispatch/error_handler.py` deleted in 9.5.
- Pipeline stages call `errors.insert_error(folder_id, file_path,
  error_type, error_message, stack_trace)` directly.
- `dispatch.error_handler.ErrorLogger` (a separate class in the
  same module) is also deleted; no callers exist outside
  `dispatch/`.

---

## DECISION 6 — Watcher integration

**Question:** Does the webapp watcher call the new orchestrator
directly, or keep going through `webapp/runner.py`?

**Answer:** **Watcher calls `webapp/pipeline/orchestrator.PipelineOrchestrator`
directly. No `webapp/runner.py` indirection for the watcher.**

**Rationale:**
- The watcher is a periodic background task, not a user-initiated
  run. It doesn't need the `RunStore` lifecycle (start_run /
  wait_run / cancel) that `runner.py` provides.
- `runner.py` becomes the *operator-initiated* path only
  (`POST /api/run` → start a run, expose cancellation, return
  status).
- The watcher's run is fire-and-forget; the per-run record in
  the `runs` table is written by the orchestrator itself.

**Consequences for Phase 9+:**
- `webapp/watcher.py::WatcherSupervisor` calls
  `loop.run_in_executor(None, orchestrator.process, folder)`
  directly.
- `webapp/runner.py::RunStore` keeps its current API; only its
  internals change (9.3).
- 9.6 (mid-term) is this work.

---

## DECISION 7 — Test fixture updates

**Question:** How do existing tests handle the import path
rename?

**Answer:** **Mechanical import updates + a `make_folder_row(...)`
factory in `tests/webapp/conftest.py`.**

**Rationale:**
- Test fixtures that *import* pipeline classes need their
  import paths updated (`from dispatch.orchestrator import ...`
  → `from webapp.pipeline.orchestrator import ...`). This is
  mechanical.
- Tests that *insert folder rows* use the existing
  `temp_database.folders_table` fixture. Adding rows by hand
  requires 50+ columns today; a factory makes this shorter and
  less error-prone.
- Tests that *assert on golden-file output* are unchanged —
  golden files don't move.

**Consequences for Phase 9+:**
- `tests/webapp/conftest.py` gains
  `make_folder_row(format="csv", backends=("copy",), **overrides)`.
- 9.7 (mid-term) is the bulk fixture-update commit.
- Test counts are preserved; no test is deleted because of the
  rename.

---

## DECISION 8 — Documentation

**Question:** Where does the post-rename documentation live?

**Answer:** **`webapp/pipeline/AGENTS.md` modeled on the
existing `dispatch/AGENTS.md`, but updated for the new shape.**

**Rationale:**
- The existing `dispatch/AGENTS.md` documents the package
  structure map; future contributors need the same map for the
  new path.
- The new doc reflects: async-aware orchestrator, single
  progress module, registry-driven converter discovery, typed
  records (Phase 11).
- Cross-references `webapp/pipeline/` as the canonical location
  for processing code.

**Consequences for Phase 9+:**
- `dispatch/AGENTS.md` deleted with the rest of `dispatch/`.
- `webapp/pipeline/AGENTS.md` written as part of 9.8 (mid-term).
- Per-converter `AGENTS.md` files are *not* created — the
  per-converter docs belong in each converter's module docstring.

---

## DECISION 9 — Backwards compatibility

**Question:** Keep `dispatch/` as a shim that re-exports from
`webapp/pipeline/` for one release?

**Answer:** **No shim. Hard cut.**

**Rationale:**
- Phase 7's desktop-retirement spec already removed `interface/`
  with no shim. The same precedent applies.
- A shim that says "the old name still works" defeats the
  purpose of Phase 8's ownership clarity. It also keeps the
  codebase two-pathed indefinitely.
- No external consumers of `dispatch.*` exist (verified — the
  webapp is the only caller in the repo, and no forks exist).

**Consequences for Phase 9+:**
- 9.1 is a hard `git mv` + import rewrite. No `dispatch/`
  directory remains.
- `find dispatch -name "*.py"` returns empty after 9.5 ships.
- A typo in `from dispatch...` after 9.1 is an immediate
  `ImportError` — that's the point.

---

## DECISION 10 — Sequencing within Phase 8 (= Phase 9 order)

**Question:** In what order do the implementation commits land?

**Answer:**

```
[9.1 rename + minimal-touch move]  ──►  [9.2 progress merge]
                                              │
                                              ▼
                                       [9.3 async boundary]
                                              │
                                              ▼
                              ┌────────┬──────┴──────┬────────┐
                              ▼        ▼             ▼        ▼
                          [9.4 reg]  [9.5 errors]  [9.6 watcher]  [9.7 fixtures]
                                                                       │
                                                                       ▼
                                                              [9.8 docs]
                                                                       │
                                                                       ▼
                                                          [Phase 10 decision]
```

**Rationale:**
- 9.1 must come first: it sets the new path that all later
  commits assume.
- 9.2, 9.3 are independent of each other and of 9.4/9.5; they
  ship in any order after 9.1.
- 9.4 and 9.5 are independent of 9.2 and 9.3; they ship after
  9.1 only.
- 9.6 (watcher) requires 9.1 + 9.3.
- 9.7 (fixtures) and 9.8 (docs) are independent mid-term cleanups
  that can run in parallel after 9.1.
- Phase 10 is gated on all of 9.x landing and a quarter of real
  use; it's a re-decision checkpoint, not a pre-decision.

**Consequences for Phase 9+:**
- Each commit is self-contained and revertable.
- `pytest tests/webapp -q` must be green after every commit.
- Effort estimates per ROADMAP §9.1: 0.5 + 0.5 + 1.0 + 0.5 +
  0.5 + 0.5 + 1.0 + 0.5 = ~5 days for 9.1-9.8.

---

## Summary

| # | Decision | One-line answer |
|---|----------|-----------------|
| 1 | Config shape | Adapter dataclass, flat schema |
| 2 | Progress merge | Delete Qt-era reporter; keep SSE one |
| 3 | Sync vs async | Sync internals, `run_in_executor` wrapper |
| 4 | Converter discovery | `pkgutil` + `CONVERTER_METADATA` per converter |
| 5 | Error ledger | Pipeline calls `webapp/errors.insert_error` direct |
| 6 | Watcher integration | Watcher calls orchestrator direct |
| 7 | Test fixtures | Mechanical + `make_folder_row` factory |
| 8 | Documentation | `webapp/pipeline/AGENTS.md` |
| 9 | Backwards compat | No shim; hard cut |
| 10 | Sequencing | 9.1 → 9.2/9.3/9.4/9.5 → 9.6/9.7/9.8 → Phase 10 |

All 10 decisions match the Phase 8 spec's §4 recommended answers.
No open questions remain from the Phase 8 design phase.

---

## Changelog

| Date | Author | Change |
|------|--------|--------|
| 2026-09-02 | Project Owner | Initial decisions document. All 10 §4 questions answered with rationale and consequences. Phase 8 status flipped to APPROVED in the design spec. |
