# Spec: Webapp Phase 5 — Operator Observability

**Status:** COMPLETE (5.1–5.4 all implemented)
**Author:** Project Owner
**Created:** 2026-08-12
**Updated:** 2026-08-13

---

## 1. Summary

Close the last unfulfilled capability in `specs/PROJECT_SPEC.md` (§3.2.5, Capability E) by making processing errors, folder-watcher health, and run metrics queryable from the browser. Phase 5 adds a database-backed error ledger with API + UI, live health telemetry on the Watching card and schedule card, and per-run throughput metrics.

---

## 2. Background

### 2.1 Problem Statement

The webapp pivot shipped phases 1.1–1.3 (import, folder CRUD, resend), 2.1–2.3 (scheduler, run history + SSE, backup/restore), and 4.1–4.3 (per-folder run, EDI preview, folder watcher). Phase 3.x was never committed; the numbering skips it entirely, so the next phase after 4.3 is phase 5.

Capability E of the project spec is an explicit intent contract: *"What errors occurred, for which file, with what stack trace?"* must be answerable from the app, with errors recorded to a dedicated table. Today it is not:

- `webapp/runner.py` constructs `ErrorHandler(errors_folder=..., run_log_directory=...)` **without `database=`** at all three call sites (`run_folders`, `run_resend`, `run_folder`), so every processing error lands only in flat files under `data/config/errors/` — invisible to the browser.
- There is no errors endpoint, no errors card, and no `dispatch_errors` table: the `INSERT INTO dispatch_errors` in `dispatch/error_handler.py:290` has **no matching `CREATE TABLE` anywhere in the repo**, so wiring the database in today would fail at runtime.
- The desktop app's error viewer was dropped in the pivot commit (`9864dc7e5`); nothing replaced it.
- The Watching card (4.3) shows *what* is watched but not *whether it is working*: no last-tick time, last triggered run, or scan error.

### 2.2 Motivation

Operators rely on the webapp for unattended overnight processing (scheduler) and automatic per-folder pickup (watcher). When a run fails, the browser currently reports only "files_failed: N" — the why lives in a text file on the server volume. Phase 5 closes that loop: failures become visible, filterable, and stack-traceable without SSH-ing into the container. Watcher health answers the operator's most common question ("is it actually watching?") and run metrics make backlog performance measurable.

### 2.3 Prior Art

- Desktop error viewer: existed pre-pivot (`interface/qt/dialogs/`), shipped in spec Phase 1, deleted by `9864dc7e5`.
- `dispatch/error_handler.py` already owns the error-capture contract (`record_error`, `_persist_to_database`, `get_errors`, `write_error_log_file`); the webapp reuses it today but never passes a `database`.
- The 4.3 watcher established the pattern this phase extends: idempotent column DDL in `webapp/database.py::_ensure_columns`, `list_watched` as the API surface, `WatcherSupervisor` refresh loop.
- `webapp/history.py::RunHistory` shows the established pattern for a webapp-owned persisted table created on first use (idempotent `CREATE TABLE IF NOT EXISTS`).

---

## 3. Design

### 3.1 Architecture Alignment

- [x] Reviewed `docs/ARCHITECTURE.md` — webapp module is the operator-facing layer; `dispatch/` pipeline is reused untouched.
- [x] Reviewed `docs/DATABASE_DESIGN.md` — schema additions follow the existing folders-table + kv_settings discipline; the error ledger is a new table in the "error ledger" category (§5.1 of the project spec forbids sharing tables across the four schema kinds).
- [x] Reviewed `docs/TESTING_DESIGN.md` — new tests land in `tests/webapp/` alongside the existing 13 files.
- [x] Reviewed `docs/PROCESSING_DESIGN.md` — no change to pipeline stages; only the error-handler wiring in the webapp runner.
- [x] Reviewed `AGENTS.md` — no silent `except: pass`; the ledger-append path must log failures (mirroring the existing `_persist_to_database` guard).
- [x] Reviewed `docs/ERROR_HANDLING_DESIGN.md` — the ledger reuses `dispatch/error_handler.py` rather than adding a parallel error path.

### 3.2 Technical Approach

**Components affected:**

- [x] `webapp/database.py` — `_ensure_columns` gains an idempotent `dispatch_errors` `CREATE TABLE IF NOT EXISTS` + the three watcher-health columns (same pattern as the watcher columns; the table lives in the same `folders.db`).
- [x] `webapp/errors.py` (new) — ledger helpers: `list_errors(db, *, folder_id, limit)`, `clear_errors(db)`, plus `insert_error` with consecutive-failure dedupe and a `MAX_ERROR_ROWS` trim. Modeled on `webapp/resend.py::list_processed_files`.
- [x] `webapp/runner.py` — pass a database-backed `ErrorHandler` into `run_folders` / `run_resend` / `run_folder`. Because each run already opens a `DatabaseObj` under `lock()`, the handler's `database` is set to an adapter exposing `raw_connection` (the `_persist_to_database` contract). The `errors_folder`/`run_log_directory` args stay, so file artifacts continue to be written.
- [x] `webapp/watcher.py` — record scan failures (folder missing, `OSError` on `iterdir`, corrupt DB) into the ledger via `insert_error` (deduped); persist `last_tick_at` / `last_run_id` / `last_error` per folder.
- [x] `webapp/scheduler.py` — monotonic `runs_triggered` counter in kv_settings; exposed in `get_schedule_summary`.
- [x] `webapp/main.py` — new endpoints (below).
- [x] `webapp/static/index.html` + `webapp/static/app.js` — Errors card; Watching card live-state column; Recent-runs metrics (metrics pending 5.3).
- [x] `webapp/folder_schema.py` — no schema change to the edit form (watcher health is read-only, not editable).

**API changes:**

```python
# New endpoints (main.py)
GET  /api/errors?folder_id=<int>&limit=<int>   -> {"count": N, "errors": [ {id, timestamp,
                                                 folder, filename, error_type,
                                                 error_message, error_source,
                                                 stack_trace, created_at,
                                                 error_file}, ... ],
                                                 "folder_counts": {folder_id: total}}
GET  /api/errors/file?path=<errors-dir-path>   -> raw error-text file (text/plain)
GET  /api/errors/folder-file?folder_id=<int>   -> one folder's full error text (text/plain,
                                                 artifacts + row fallback; used by the banner's
                                                 "Download raw" button)
POST /api/errors/clear                          -> {"cleared": N}

# Extended responses
GET  /api/watched  -> {"folders": [ {id, alias, watch_enabled,
                                     watch_interval_seconds, watch_path,
                                     last_tick_at, last_run_id, last_error}, ... ]}
GET  /api/schedule -> {..., "runs_triggered": N}

# Extended RunReport (runner.py)
duration_seconds: float        # finished_at - started_at
files_per_second: float        # total_processed / duration_seconds
```

**Data flow:**

```
dispatch pipeline failure
        │  record_error()
        ▼
ErrorHandler ──► data/config/errors/*.txt   (unchanged, file artifacts)
        │  _persist_to_database()           (new wiring: runner passes database)
        ▼
folders.db: dispatch_errors  ◄── GET /api/errors ── Errors card (UI)
                                        ▲
watcher tick failure / success ─────────┘  (last_tick_at, last_run_id, last_error
                                           persisted on the folders table;
                                           exposed via GET /api/watched)
```

### 3.3 Alternatives Considered

| Alternative | Pros | Cons | Why Not Chosen |
|-------------|------|------|----------------|
| Errors as flat-file listing only (read `data/config/errors/` dirs via API) | No schema change | No per-error metadata, no filtering, text-file parsing is brittle, no clear/delete semantics | The project spec mandates a dedicated errors table (§3.2.5, §5.1) |
| Reuse `dispatch_errors` via a schema migration (`migrations/`) | Uses the "canonical" legacy name | `dispatch_errors` was never created in any schema version; migrating a nonexistent table adds ceremony | Idempotent `CREATE TABLE IF NOT EXISTS` in `webapp/database.py` matches the established webapp pattern (watcher columns) |
| Fold errors into `run_history.report_json` only | No new table | Loses per-error queryability, folder filtering, and clear semantics; history is capped at 100 runs | Ledger must outlive run-history rotation |
| Watchdog per folder via inotify | Real-time pickup | Deployment is single-host single-user; polling every 30s is cheap; contradicts spec §3.3 "not a real-time system" | Keep polling; phase 5 only makes it observable |

---

## 4. Implementation Plan

### Phase 5.1: Error ledger (Estimated: 2 days) — **implemented (commit `bafa1f4e3`) + ledger hygiene (`7091afe55`)**

- [x] Task 5.1.1: Add `dispatch_errors` table creation to `webapp/database.py::_ensure_columns` (idempotent; columns: `id`, `timestamp`, `folder`, `filename`, `error_message`, `error_type`, `error_source`, `stack_trace`, `created_at`).
- [x] Task 5.1.2: New `webapp/errors.py` with `list_errors` / `clear_errors` (mirror `webapp/resend.py` SQL style).
- [x] Task 5.1.3: Wire a database-backed `ErrorHandler` into the three runner call sites; confirm `_persist_to_database`'s `raw_connection` path is used.
- [x] Task 5.1.4: New endpoints `GET /api/errors` + `POST /api/errors/clear` in `main.py`.
- [x] Task 5.1.5: Errors card in the UI — count pill, table (when / folder / file / type / message), clickable rows with folder filtering, active-filter banner + scoped clear.
- [x] Deliverable: a failing run writes a queryable ledger row; the browser shows it with its stack trace.

### Phase 5.2: Watcher + scheduler health telemetry (Estimated: 1–2 days) — **implemented (commit `5de53b9c9`)**

- [x] Task 5.2.1: Persist `last_tick_at`, `last_run_id`, `last_error` on the folders table (extend `_ensure_columns`); update them in `FolderWatcher._maybe_run`.
- [x] Task 5.2.2: Extend `list_watched` to return the health fields.
- [x] Task 5.2.3: Record watcher scan failures into the error ledger (same 5.1 path).
- [x] Task 5.2.4: Track `runs_triggered` in the scheduler's kv_settings; expose in `get_schedule_summary`.
- [x] Task 5.2.5: Watching card gains a live state column (ticking / idle / error) + last-run id + last-tick time; schedule card shows runs triggered.
- [x] Deliverable: the Watching card distinguishes "watching and healthy" from "watching but failing" without inspecting the server.

### Phase 5.3: Run metrics (Estimated: 1 day) — **implemented**

- [x] Task 5.3.1: Add `duration_seconds` + `files_per_second` to `RunReport` (computed in `runner.py::_finalize_run_report` at completion, stamped in the `finally` of all three runner call sites).
- [x] Task 5.3.2: Surface in `_run_summary` and render in the Recent-runs list (`runMetricsText`) + run card (`runMetricsLine`, `.run-meta` line).
- [x] Task 5.3.3: Update `webapp/history.py` serialization if `dataclasses.asdict` needs a custom encoder for floats (verify — plain JSON handles floats, so likely no change). **Verified:** `json.dumps(dataclasses.asdict(report), default=str)` serializes floats natively; persisted runs round-trip the new fields with no schema change.
- [x] Deliverable: every run row shows duration + throughput; the running placeholder and older payloads without the fields render without metrics.

### Phase 5.4: Testing & Documentation (Estimated: 1 day) — **done**

- [x] Write `tests/webapp/test_errors.py` (persistence on failed run, filtering, clear, missing-DB tolerance, dedupe, trim) — 23 tests.
- [x] Extend `tests/webapp/test_watcher.py` end-to-end test to assert a failing file lands in the ledger + watcher health / dedupe tests.
- [x] API coverage for the two new endpoints (landed in `tests/webapp/test_errors.py::test_api_errors_*` rather than `test_api.py`).
- [x] Extend `tests/webapp/test_scheduler.py` for `runs_triggered`.
- [x] Update `webapp/main.py` module docstring endpoint list + `README.md` API table — docstring now lists every endpoint including the phase-2/4/5 additions (watcher, preview, folder-run, backups, errors); the `README.md` API table now covers the full surface.
- [x] Deliverable: full `tests/webapp` suite green (168 pass), ruff clean on `webapp/` + `tests/webapp/`. Note: `test_run_store_active_count_drops_after_run_completes` is a pre-existing timing test that flakes when the host machine is saturated (passes on an idle box).

---

## 5. Database Changes

### 5.1 Schema Changes

```sql
-- New table (created idempotently in webapp/database.py::_ensure_columns,
-- same folders.db file, no version bump)
CREATE TABLE IF NOT EXISTS dispatch_errors (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp     TEXT,
    folder        TEXT,
    filename      TEXT,
    error_message TEXT,
    error_type    TEXT,
    error_source  TEXT,
    stack_trace   TEXT,
    created_at    TEXT
);

-- New folders-table columns (watcher health, same idempotent pattern)
ALTER TABLE folders ADD COLUMN last_tick_at   TEXT DEFAULT '';
ALTER TABLE folders ADD COLUMN last_run_id    TEXT DEFAULT '';
ALTER TABLE folders ADD COLUMN last_error     TEXT DEFAULT '';
```

### 5.2 Migration Strategy

- No `migrations/` version bump. The webapp already handles in-place additions via `webapp/database.py::_ensure_columns` (used for `watch_enabled` / `watch_interval_seconds` in 4.3). The error ledger and health columns follow the identical pattern; `DatabaseObj` migration logic is untouched.
- Backup: unaffected — the existing backup/restore feature snapshots `folders.db`, which now includes the new table/columns.

### 5.3 Migration Checklist

- [x] Add `dispatch_errors` `CREATE TABLE IF NOT EXISTS` to `_ensure_columns`
- [x] Add the three health columns to `_ensure_columns`
- [x] Verify a pre-4.3 database (missing all four) upgrades in place on `open_database`
- [x] No changes to `core/database/schema.py` or `migrations/`

---

## 6. Testing Strategy

### 6.1 Test Cases

| Test Case | Type | Description | Expected Result | Status |
|-----------|------|-------------|-----------------|--------|
| test_errors_persist_on_failed_run | webapp | A folder with a failing backend writes a ledger row | `GET /api/errors` returns the row with message + type | ✅ `test_failing_run_records_error_in_ledger` |
| test_errors_filter_by_folder | webapp | Two folders, errors in one | Filter returns only that folder's rows | ✅ |
| test_errors_clear | webapp | Clear endpoint | Rows deleted, count reflects it | ✅ |
| test_errors_missing_db | webapp | No database imported | `GET /api/errors` returns 503 or empty, not a crash | ✅ |
| test_watcher_records_scan_error | webapp | Watched folder's input dir is deleted mid-watch | Ledger gets a row; `last_error` populated | ✅ `test_maybe_run_records_missing_folder_error` |
| test_watched_health_fields | webapp | Watcher tick runs | `last_tick_at` / `last_run_id` present in `/api/watched` | ✅ |
| test_run_report_duration | webapp | Completed run | `duration_seconds` ≥ 0, `files_per_second` computed | ✅ `test_run_report_duration` (API) + `test_run_report_duration_metrics` (runner) + JS `runRows`/`runResults` metric tests |
| test_schedule_runs_triggered | webapp | Scheduler fires N runs | `runs_triggered` == N | ✅ |

### 6.2 Test File Locations

- `tests/webapp/test_errors.py` (new)
- `tests/webapp/test_watcher.py` (extend end-to-end test)
- `tests/webapp/test_api.py` (extend for endpoints)
- `tests/webapp/test_scheduler.py` (extend for runs_triggered)
- `tests/webapp/test_runner.py` (extend for duration metrics)

### 6.3 Coverage Requirements

- [x] New code covered by tests
- [x] Existing tests still pass (baseline 144 → 168; the pre-existing `test_run_store_active_count_drops_after_run_completes` timing test flakes only when the host machine is saturated)
- [x] ruff clean on `webapp/` + `tests/webapp/`

---

## 7. Risk Assessment

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| `_persist_to_database` fails on the webapp's `DatabaseObj` shape (raw_connection vs dataset wrapper) | Med | Med | Unit-test the adapter against a real `open_database()` before wiring the runner; fall back to `db.insert(error_record)` path if raw_connection is absent |
| Ledger table grows unbounded over months of unattended runs | Med | Low | **Implemented (commit `7091afe55`):** `MAX_ERROR_ROWS` (10_000) trims the oldest rows on insert, mirroring `MAX_HISTORY_ROWS`; the watcher additionally dedupes consecutive identical scan failures (`insert_error(dedupe=True)`) so a permanent failure is one row, not one per tick |
| Watcher writes health columns on every tick → write contention with runs | Low | Low | Ticks are 30s apart and SQLite writes are serialized by the existing `lock()`; updates are one `UPDATE` per tick |
| Stack traces contain filenames that leak internal paths | Low | Low | Ledger is local-only (same DB as config); no new network surface added |
| Adding error persistence slows the hot path | Low | Low | One INSERT per failure (failures are rare by design); not per file |

### 7.1 Rollback Plan

- Each sub-phase is a self-contained commit. Reverting 5.1 removes the table creation + wiring; the runner returns to file-only error output (current behavior). No data migration to unwind — new columns/table are additive and harmless if left in place. The existing backup/restore feature is the escape hatch if a database must be reverted wholesale.

---

## 8. Success Criteria

- [x] A folder run with a failing backend produces a visible, filterable, stack-trace-able error in the browser — no server access required
- [x] Watcher scan failures and health (last tick / last run / last error) are visible on the Watching card
- [x] Every run row shows duration + files/second (5.3)
- [x] All existing webapp tests pass (168); new tests cover the ledger, endpoints, watcher health, scheduler counter, and dedupe
- [x] `ruff check webapp/ tests/webapp/` clean
- [x] PROJECT_SPEC §3.2.5 Capability E fully satisfied (folders, state, processed files, errors all queryable; the work queue is a separate roadmap item)

---

## 9. Open Questions

1. ~~Should the ledger cap (`MAX_ERROR_ROWS`) be exposed as a kv_settings key, or is a module constant consistent with `history.py::MAX_HISTORY_ROWS` sufficient?~~ **RESOLVED (commit `7091afe55`):** module constant `MAX_ERROR_ROWS = 10_000` chosen, consistent with `MAX_HISTORY_ROWS`; the watcher additionally dedupes consecutive identical failures so the cap is rarely reached in practice.
2. ~~Should `GET /api/errors` also surface the pre-existing file artifacts (a "download raw error text" link), or is the structured row enough?~~ **RESOLVED (commit `b68c1d764`):** the runner now writes one raw error-text file per folder-run under `data/config/errors/<folder>/<alias> errors.<timestamp>.txt` (reusing the legacy `build_error_log_filename` naming), stores the path in a new `error_file` column on each ledger row it produced (`max_error_id` watermark + `link_error_files`), and exposes a `GET /api/errors/file` download endpoint (path-traversal guarded to `errors_dir`, mirroring `/api/maintenance/download`). The Errors card renders a `raw` link on linked rows.
3. ~~Does the operator want per-folder error counts on the folders table itself, or is the global Errors card + filter sufficient?~~ **RESOLVED (commit `b68c1d764`):** per-folder counts on the Errors card — `GET /api/errors` now returns a `folder_counts` map (`{folder_id: total}`) and the folder-filter dropdown labels each folder with its count (`ACME (3)`). The folders table stays untouched.
4. ~~Should the scheduler's `runs_triggered` counter be monotonic (kv_settings) or derived from `run_history` (`kind='normal'` rows)? Derived is more robust across restores; monotonic is cheaper.~~ **RESOLVED (commit `5de53b9c9`):** monotonic kv_settings counter chosen. Known tradeoff: after a backup restore the counter reflects the snapshot, not the true lifetime total — acceptable for a per-import lifetime readout.

---

## 10. Appendix

### 10.1 References

- `specs/PROJECT_SPEC.md` §3.2.5 (Capability E), §5.1 (schema kinds), §6.2 (test invariants)
- `dispatch/error_handler.py` (`record_error`, `_persist_to_database` at ~line 290)
- `webapp/runner.py` (ErrorHandler construction at `run_folders`/`run_resend`/`run_folder`)
- `webapp/watcher.py` (`FolderWatcher._maybe_run`, `list_watched`)
- `webapp/database.py` (`_ensure_columns` idempotent DDL pattern)
- `webapp/history.py` (`RunHistory` persisted-table pattern)
- `webapp/scheduler.py` (`get_schedule_summary`, kv_settings keys)
- Commit `9864dc7e5` (pivot; dropped the desktop error viewer)

### 10.2 Changelog

| Date | Author | Change |
|------|--------|--------|
| 2026-08-12 | Project Owner | Initial draft — audit findings + 5.1/5.2/5.3 scope |
| 2026-08-12 | Project Owner | 5.1 implemented (`bafa1f4e3`): `dispatch_errors` table, `webapp/errors.py`, ErrorHandler wiring in all three runner call sites, `/api/errors` + `/api/errors/clear`, Errors card UI with folder filter + scoped clear, backend tests + Node frontend test harness |
| 2026-08-12 | Project Owner | 5.2 implemented (`5de53b9c9`): watcher-health columns + `list_watched` fields, scan failures recorded in the ledger, Watching card state/last-tick columns; scheduler `runs_triggered` counter + Schedule card display |
| 2026-08-12 | Project Owner | Ledger hygiene (`7091afe55`): `insert_error` consecutive-failure dedupe + `MAX_ERROR_ROWS` trim; spec open questions 1 and 4 resolved |
| 2026-08-12 | Project Owner | Spec status → IN PROGRESS; 5.1/5.2 + testing checklist marked done; success criteria updated; `README.md` API-table item left pending |
| 2026-08-12 | Project Owner | Open questions 2 + 3 resolved (`b68c1d764`): runner writes per-folder raw error artifacts + `error_file` column + `GET /api/errors/file` download; `folder_counts` in `/api/errors` + count labels in the Errors-card folder dropdown |
| 2026-08-12 | Project Owner | Watcher scan-failure rows get raw artifacts too (`dedupe_matches` + `write_error_artifact` shared with the runner); `GET /api/errors/folder-file` serves one folder's full error text for the filter banner's "Download raw" button |
| 2026-08-13 | Project Owner | 5.3 implemented: `duration_seconds` + `files_per_second` on `RunReport` via `_finalize_run_report` (all three runner call sites), surfaced in `_run_summary` + Recent-runs rows + run card; `history.py` serialization verified float-safe with no change; tests in `test_api.py`, `test_runner.py`, `templates.test.js`, `dom.test.js` (198 webapp + 78 JS green) |
| 2026-08-13 | Project Owner | 5.4 docs finished: `webapp/main.py` docstring endpoint list + `README.md` API table updated to the full phase-2/4/5 surface; spec status → COMPLETE |
| 2026-08-14 | Project Owner | 5.3 follow-up: per-folder run-warning thresholds — `max_duration_seconds` + `max_failure_rate_percent` columns (0 = off), editable in the folder editor; the runner times each folder (`FolderRunReport.duration_seconds`) and stamps a `warning` via `_folder_warning`; the run card renders an amber banner per offending folder; surfaced in `_run_summary` |
