# Spec: Webapp Phase 7 — Operator Confidence & Desktop Retirement

**Status:** DRAFT (2026-08-18, revised)
**Author:** Project Owner
**Created:** 2026-08-18
**Updated:** 2026-08-18

> **Scope change (2026-08-18):** the original Phase 7 draft proposed
> leaving `interface/qt/` alone because the §3.7 addendum still
> recommended the PyQt5 GUI for on-host operators. The decision to
> **completely drop the desktop version** supersedes that
> recommendation. `interface/qt/` was already removed in the
> 2026-08-04 webapp-pivot; this phase finishes the cleanup by
> removing the orphaned `interface/` Qt-free layer (3,819 lines,
> 16 files, no callers) and the desktop packaging machinery.
> The pipeline-redesign work is scoped into a separate Phase 8
> spec (architectural, not implementation).

---

## 1. Summary

Phase 6 closed the webapp's *deployment* gap (safe-by-default,
authenticated, observable). Phase 7 closes two gaps in one:

1. **Operator-confidence cleanup**: a correctness wart in the
   schema-repair pass that bit Phase 6.4 testing, plus the absence
   of an operator runbook that ties the existing endpoints into
   "if X, do Y" flows.
2. **Desktop-era tree cleanup**: delete `interface/` (the
   Qt-free orphan), `plans/` (stale refactoring plans), and the
   legacy desktop packaging machinery (`interface.spec`,
   `launch_interface.sh`, `nuitka-crash-report.xml`). The pipeline
   rewrite is out of scope for Phase 7.

No new product capability. Pure correctness, docs, and tree
hygiene. Three small items, all independent, all reversible on a
single `git revert`.

---

## 2. Background

### 2.1 Problem Statement

**Schema-repair wart.** Phase 6.4's `test_soft_delete_restore_round_trip`
failed initially because every `open_database()` call at current schema
version runs the v33→v51 migration's `_backfill_defaults` UPDATE against
the `folders` table — even when the schema is already consistent. A row
inserted with NULLs for columns the migration knows defaults for gets
*backfilled* by the next open, so the same row reads differently after
`open_database` than it did right after the insert. This is harmless for
production (every open converges to the same shape), but it makes any
"snapshot-then-round-trip" test fragile unless the test fixture also
forces a re-open between insert and snapshot.

The deeper problem: the `_run_current_version_repairs` path was added
to defend against a database that *claims* to be at the current version
but is missing columns expected by newer code. The repair pass exists
to defend against that scenario; the backfill UPDATEs are a side effect.
Today the repair pass runs on **every** open unconditionally, which is
wasted work in the common case (a healthy at-version DB) and a foot-gun
for any code that expects "what I just wrote is what I'll read back."

**No runbook.** `webapp/diagnostics.py::collect_diagnostics` (Phase 6.3)
exposes a payload covering platform, paths, database, scheduler,
watcher, backends, modules, runs, errors. There is no document that
says "if `runtime.recent_run_failures_24h > 0`, check X; if
`backends_health.smtp.ok` is false, check Y." Operators with a failing
run today have to know which endpoint answers which question.

**Tree clutter from the desktop era.** Three categories of dead/wrong
code:

- **`interface/` package** — 16 files, 3,819 lines. The PyQt5 GUI
  (`interface/qt/`) was deleted in the webapp-pivot, but the
  Qt-free business-logic layer (`models/`, `operations/`,
  `services/`, `validation/`) was left behind. No webapp module
  imports from `interface/` (verified by grep — see §5). The
  package's own `__init__.py` docstring says *"the former Qt UI
  layer (`interface/qt`) was removed in the webapp pivot"*, which
  confirms the intent.
- **`plans/`** — 14 files, all gitignored. Stale refactoring plans
  from before the webapp-pivot. None of them describe work that
  is going to happen.
- **Desktop packaging machinery** — `interface.spec` (PyInstaller
  spec, tracked), `launch_interface.sh` (tracked), `nuitka-crash-report.xml`
  (frozen artifact). `dist/`, `dist_windows/`, `dist_linux/`, `sdist/`,
  `outdir/` are all gitignored. None of it is used by the webapp.

The §3.7 addendum in `PROJECT_SPEC.md` was the only thing keeping
`interface/` from being deletable: it recommended the PyQt5 GUI for
on-host operators. The 2026-08-18 decision to drop the desktop version
removes that constraint.

### 2.2 Motivation

The schema-repair wart is a real correctness hazard: any future test
that needs a stable round-trip (Phase 8+, or any future test author
who hits the same trap) will trip over it. Removing the side-effect
makes the trap go away and lets the v33→v51 migration do its job
exactly once per schema lifetime.

The runbook is the highest-leverage operator-confidence win available
without writing new product code: every endpoint it would reference
already exists, the data it would surface is already collected, and
the operator who follows it learns the system's shape at the same
time.

The tree cleanup is mechanical but removes the cognitive tax of
"what's this folder for?" when a new agent (or a returning human)
opens the repo. The `interface/` package in particular is a trap:
the docstring says it was meant to be the *non-UI* business logic
for the GUI, but without the GUI it has no caller. Future agents
who grep for "where do I find folder operations?" will find
`interface/operations/folder_manager.py` and think it's the active
code path — when actually the active path is `webapp/routers/folders.py`.

### 2.3 Prior Art

- **Phase 6.4 test workaround** (`tests/webapp/test_soft_delete.py:30-35`)
  documents the symptom and the fix: re-open the DB between insert and
  snapshot so the repair pass can run before the test reads back. This
  is the workaround Phase 7.1 removes.
- **Desktop-era runbook** lived in `DOCUMENTATION.md` (24 KB, pre-pivot).
  It was operator-facing prose for the PyQt5 GUI; the webapp equivalent
  doesn't exist.
- **Tree cleanup pattern**: the gap-2.x items shipped in Phase 6 deleted
  nothing — they added. The natural place for "what can be deleted" is
  a follow-on phase, not a gap-audit item, because deletion isn't an
  audit finding, it's a deliberate operator decision.
- **`_EXPLICIT_BOOLEAN_COLUMNS_BY_TABLE`** in
  `backend/database/sqlite_wrapper.py` already models the right
  separation between "schema defaults" and "Python-side boolean
  coercion"; Phase 7.1's fix lives at the same layer.

---

## 3. Design

### 3.1 Architecture Alignment

- [x] Reviewed `docs/ARCHITECTURE.md` — no architectural changes; Phase 7
  is correctness, docs, and tree hygiene.
- [x] Reviewed `docs/DATABASE_DESIGN.md` — the schema-repair fix in 7.1
  is *removing* an existing behavior, not adding. No schema change.
- [x] Reviewed `docs/TESTING_DESIGN.md` — 7.1's regression test belongs in
  `tests/webapp/test_database_repair.py` (new file), modeled on the
  fixture pattern from `test_soft_delete.py`.
- [x] Reviewed `docs/ERROR_HANDLING_DESIGN.md` — the runbook (7.2) is a
  doc that points operators at `dispatch_errors` (already exposed via
  `/api/errors`); no new error path.
- [x] Reviewed `AGENTS.md` — no silent `except: pass`; 7.1's fix
  preserves the `_safe()` wrapper around `_ensure_columns` so a
  missing table still shows as 0, not 500.
- [x] Reviewed `specs/PROJECT_SPEC.md §3.7` (the Phase 6 addendum) —
  **the §3.7 addendum is now obsolete** because the PyQt5 GUI
  recommendation is being rescinded. Phase 7 includes a §3.7
  rewrite in §4.2 below. The PROJECT_SPEC.md update is tracked
  in §4.5.
- [x] Reviewed the package layout for `dispatch/` and `interface/`
  before scoping the deletions. `interface/` has no callers in the
  webapp (verified by `grep -rn "from interface\|import interface"
  webapp/ dispatch/` — empty result). Safe to delete.

### 3.2 Components affected

**7.1 schema repair:**
- [x] `backend/database/database_obj.py` — `_run_current_version_repairs`
  gates on a one-shot marker (see §3.3.7.1).
- [x] `migrations/modern_migrations.py` — no change. The migration's
  `_backfill_defaults` UPDATE stays as-is (it must still run during
  the v33→v51 transition for pre-existing NULL rows). The fix is at
  the *caller* side (`_run_current_version_repairs`), not the
  migration side.
- [x] `webapp/database.py::_ensure_columns` — no change.
- [x] `tests/webapp/test_database_repair.py` (new) — 3 cases.

**7.2 runbook:**
- [x] `docs/runbook.md` (new) — operator-facing troubleshooting guide.
- [x] `README.md` — new "Runbook" section linking to `docs/runbook.md`.

**7.3 tree cleanup:**
- [x] `interface/` — directory removed (16 files, 3,819 lines).
  Includes `interface/__init__.py`, `interface/AGENTS.md`,
  `interface/interfaces.py`, `interface/ports.py`, `interface/models/`,
  `interface/operations/`, `interface/services/`, `interface/validation/`.
  None are imported by `webapp/` or `dispatch/` (verified).
- [x] `plans/` — directory removed (14 files, all gitignored anyway).
- [x] `interface.spec` — `git rm`.
- [x] `launch_interface.sh` — `git rm`.
- [x] `nuitka-crash-report.xml` — `git rm`.
- [x] `.gitignore` — drop the `plans/` entry; add an explanatory
  comment block describing why `dist/`, `dist_windows/`, `dist_linux/`,
  `sdist/`, `outdir/`, `build/nuitka-wine-dist/` stay ignored.
- [x] `docs/api/` — left alone. These are pre-pivot API docs that
  describe the `core/domain/models` and `core/domain/services` layers
  that are still in active use by `dispatch/`. Out of scope for
  Phase 7.

### 3.3 Technical Approach per Item

#### 7.1 One-shot current-version repair

The current `_run_current_version_repairs` runs unconditionally whenever
`db_version == self._database_version`. The fix gates it on a one-shot
marker:

```python
# backend/database/database_obj.py
def _run_current_version_repairs(self) -> None:
    """Run safe repair migrations for current-version databases.

    Gated on a one-shot ``schema_repaired_at`` row in the ``kv_settings``
    table so a healthy at-version database does not pay the repair cost
    on every open. The kv_settings table already exists (Phase 4 created
    it for the import's per-DB config); the new key is set on first
    successful repair and never cleared.

    The migrator is still safe to call again (its ALTER TABLE / UPDATE
    statements are idempotent), but skipping it removes the
    ``_backfill_defaults`` side effect that breaks any
    "snapshot-then-round-trip" test.
    """
    kv_settings = self.database_connection["kv_settings"]
    existing = kv_settings.find_one(key="schema_repaired_at")
    if existing is not None:
        return
    if self._migrator_func is None:
        from migrations import folders_database_migrator
    folders_database_migrator.upgrade_database(
        self.database_connection, self._config_folder, self._running_platform
    )
    kv_settings.insert({"key": "schema_repaired_at", "value": _utcnow_iso()})
```

The marker is written by `_run_current_version_repairs` itself, not by
the migrator — that way the gate is a property of `DatabaseObj`, not of
the migrator function. A custom `_migrator_func` injected by a test
fixture that doesn't write the marker would still get re-called on every
open, but that's the existing behavior and is the right default for
tests that want to drive the migrator manually.

The migration's `_backfill_defaults` UPDATE stays in place — it must
run *once* during the v32→v51 transition for the (now-archived) case of
a pre-existing DB whose rows have NULLs. The fix is "make that *once*",
not "stop doing the update."

Tests:

- `test_repair_runs_only_once_across_opens` — open DB twice at current
  version with a counting `_migrator_func`; assert call count is 1.
- `test_repair_marker_is_persisted` — open DB once, close, open a fresh
  `DatabaseObj` on the same file with a counting `_migrator_func`;
  assert call count is 1 (not 2).
- `test_round_trip_stable_without_reopen` — the exact pattern from
  `tests/webapp/test_soft_delete.py:30-35` (insert, find_one,
  restore-via-soft-delete path) — the fixture's re-open becomes
  unnecessary; this test passes without it. Acts as a regression
  test that the fix actually resolves the symptom.

#### 7.2 Operator runbook

New file `docs/runbook.md` — pure prose, no code. Sections map 1:1 to
the existing `/api/*` endpoints the operator already has:

1. **"A run failed"** — start at `GET /api/runs/{run_id}` (status +
   per-folder breakdown), drill into `GET /api/runs/{run_id}/log`
   (SSE stream of per-folder logs), then `GET /api/errors?folder_id=N`
   for the captured error rows. If empty, fall back to
   `GET /api/errors/file` (download the raw error-text artifact).
2. **"Files aren't being picked up"** — `GET /api/watched` for the
   watcher's `last_tick_at` / `last_run_id` / `last_error` per
   folder; then the Diagnostics card's
   `runtime.watched_with_errors` count.
3. **"The dashboard says SMTP/FTP is unreachable"** — direct to the
   Diagnostics card's Backends table (Phase 6.3); explain what
   `{ok, latency_ms, error}` means and what "not configured" looks
   like.
4. **"I deleted a folder by accident"** — `GET /api/folders/deleted`
   to find it, then `POST /api/folders/{id}/restore` (Phase 6.4).
5. **"I want to know if the operator-configured things still work"**
   — `GET /api/diagnostics` (the whole card); explain the `ok` /
   `warnings` aggregation.
6. **"The database looks weird"** — `GET /api/config` for base-dir /
   data-dir / DB status, then `GET /api/backups` for available
   snapshots, then `POST /api/backup/create` +
   `POST /api/backup/restore`.

Each section gets:

- A one-line symptom → "go to endpoint X" pointer.
- A copy-pasteable `curl` example that uses `BFS_API_TOKEN` if set
  (matching the Phase 6.2 bearer-token contract).
- A "what you'll see" snippet of the JSON shape (taken from the
  existing tests in `tests/webapp/`).
- A "what to do next" pointer for each non-trivial case.

The runbook is **not** a feature spec — it doesn't change any API,
it just narrates the endpoints that already exist. It belongs in
`docs/` rather than `specs/` because it's a reference for operators,
not a contract for implementers.

The README gains a one-line "Runbook: see [docs/runbook.md](docs/runbook.md)"
in the Features section so it's discoverable.

#### 7.3 Tree cleanup of desktop-era code

Pure mechanical changes, no test impact.

**Before deleting**, verify no live callers:

```bash
# Must return empty:
grep -rn "from interface\|import interface" webapp/ dispatch/ tests/
# Must return only intentional references (none today):
grep -rn "interface.spec\|launch_interface.sh" .
```

**Delete:**

- `interface/` — 16 files, 3,819 lines. Includes `interface/__init__.py`
  (whose own docstring documents that the Qt UI layer was removed).
- `plans/` — 14 files, all gitignored. None are tracked.
- `interface.spec` — tracked, `git rm`.
- `launch_interface.sh` — tracked, `git rm`.
- `nuitka-crash-report.xml` — untracked artifact, just `rm`.

**Update `.gitignore`:**

- Drop the `plans/` entry.
- Add a comment block above the legacy build dirs explaining why they
  stay ignored:

```gitignore
# Legacy desktop packaging artifacts from the pre-webapp-pivot era.
# The PyQt5 GUI (interface/qt/) was removed 2026-08-04; the Qt-free
# interface/ business-logic layer was removed 2026-08-18 (Phase 7).
# These directories held PyInstaller/Nuitka intermediate output. They
# stay ignored so a fresh clone doesn't ship dead build artifacts,
# but they can be safely deleted by anyone with a local clone.
dist/
dist_windows/
dist_linux/
sdist/
outdir/
build/nuitka-wine-dist/
```

**Don't delete** (out of scope):

- `docs/api/` — these are pre-pivot API docs that describe
  `core/domain/models` and `core/domain/services`, which are still
  in active use by `dispatch/`. Phase 8 may want to revise them; not
  Phase 7.
- `interface/qt/` — already removed in 2026-08-04.
- The `dispatch/` tree itself — out of scope per the Phase 7/8 split.
  The "retire dispatch in favor of a webapp-native processor" work
  is its own phase (Phase 8 spec).

### 3.4 Alternatives Considered

| Alternative | Pros | Cons | Why Not Chosen |
|-------------|------|------|----------------|
| Move `_run_current_version_repairs` entirely to `_upgrade_database` (drop the at-version branch) | Simpler — one place that runs migrations | Breaks the documented "schema drift recovery" contract the function was added to provide | The drift-recovery case is real (a hand-edited DB, a backup restored to a different code version); keep the path, gate it on a marker instead |
| Document the re-open workaround in `tests/webapp/AGENTS.md` and move on | Zero code change | The trap waits for the next agent; every future round-trip test pays the comment tax | Cheaper to fix once than to document forever |
| Put the runbook in the existing `DOCUMENTATION.md` | One less file | `DOCUMENTATION.md` is 24 KB of pre-pivot desktop prose; appending makes it harder to find | A standalone `docs/runbook.md` (webapp-scoped, ~150 lines) is more discoverable and matches the existing `docs/architecture/webapp-gap-audit.md` naming |
| Keep `interface/` because *something* might want it | Avoids the deletion | 3,819 lines of dead code is a navigation hazard; future agents will think it's the active code path; the package's own docstring documents that it's orphaned | The decision to drop the desktop version makes the package's existence a contradiction |
| Delete `dispatch/` in Phase 7 too | Big visible win | `dispatch/` is 14,952 lines of actively-used code; deleting it breaks every webapp processing endpoint; it's its own multi-month architectural phase | Scope creep; Phase 8 owns the redesign |

---

## 4. Implementation Plan

### 4.1 Phase 7.1: One-shot current-version repair (Estimated: 0.5 day)

- [ ] Task 7.1.1: Modify `_run_current_version_repairs` in
  `backend/database/database_obj.py` to gate on the
  `schema_repaired_at` marker in `kv_settings`.
- [ ] Task 7.1.2: Add the test fixture for a counting `_migrator_func`
  to `tests/webapp/test_database_repair.py`.
- [ ] Task 7.1.3: Write `tests/webapp/test_database_repair.py` with
  the three cases in §3.3.7.1.
- [ ] Task 7.1.4: Remove the re-open workaround from
  `tests/webapp/test_soft_delete.py` (it's no longer needed);
  add a comment that says "Phase 7.1 made the re-open
  unnecessary."
- [ ] Deliverable: `pytest tests/webapp -q` shows 100% pass;
  `test_soft_delete.py` is simpler; the
  `_run_current_version_repairs` runs at most once per DB lifetime.

### 4.2 Phase 7.2: Operator runbook (Estimated: 1 day)

- [ ] Task 7.2.1: Write `docs/runbook.md` with the six sections
  in §3.3.7.2.
- [ ] Task 7.2.2: Cross-link from `README.md` (Features section)
  and from `docs/architecture/webapp-gap-audit.md §4.1`
  (Phase 6 status).
- [ ] Task 7.2.3: Sanity-check each `curl` example against a running
  `python -m webapp.main` instance to make sure the shapes match
  the actual responses.
- [ ] Deliverable: a new operator has the answer to "where do I
  look?" for the six most common failure modes without reading any
  code.

### 4.3 Phase 7.3: Tree cleanup (Estimated: 0.25 day)

- [ ] Task 7.3.1: Run the verification greps in §3.3.7.3 to
  confirm `interface/` has no live callers. **STOP and report if
  it does** — that's a spec violation, not a cleanup task.
- [ ] Task 7.3.2: `git rm interface/` (16 files). `rm -rf plans/`
  and remove the entry from `.gitignore`. `git rm interface.spec
  launch_interface.sh`. `rm nuitka-crash-report.xml`.
- [ ] Task 7.3.3: Update `.gitignore` per §3.3.7.3 (drop `plans/`
  entry, add the legacy-build-dir comment).
- [ ] Task 7.3.4: `make test` and `ruff check` to confirm nothing
  depended on the deleted paths.
- [ ] Deliverable: `ls` of the repo root is materially cleaner;
  nothing breaks. `dispatch/` and `core/` are untouched.

### 4.4 Phase 7.4 (optional): Update PROJECT_SPEC.md §3.7 (Estimated: 0.25 day)

The §3.7 addendum I wrote in Phase 6 ("webapp deployment model")
recommended the PyQt5 GUI for on-host operators. The 2026-08-18
decision to drop the desktop version rescinds that recommendation.
The addendum needs a follow-on revision:

- Remove the "PyQt5 GUI is still the recommended path for an
  operator who works directly on the host" sentence from §3.7.
- Add a §3.8 (or extend §3.7) capturing "Phase 7: desktop is gone,
  webapp is the only operator surface; the §3.5 release channels
  collapse to two (Docker / source + venv), not three."
- The §3.6 line about rejecting the browser UI alternative is
  historical and stays — it's a record of the reasoning, not a
  binding decision.

### 4.5 Phase 7 ordering

The four tasks (7.1, 7.2, 7.3, 7.4) are independent and can ship in
any order. Recommended:

1. **7.4 first** (the doc-only PROJECT_SPEC.md update) — clarifies
   intent for every subsequent commit message.
2. **7.1 second** (the schema fix) — small, isolated, well-tested.
3. **7.3 third** (the tree cleanup) — removes the dead code that
   distracts from 7.2's runbook narration.
4. **7.2 last** (the runbook) — written after the tree is clean, so
   the runbook only references code that survives.

---

## 5. Database Changes

### 5.1 Schema Changes

None. The `kv_settings` table already exists (created by Phase 4 for
the import's per-DB config). The new key is additive:

```sql
INSERT INTO kv_settings (key, value) VALUES ('schema_repaired_at', '<utcnow>');
```

(Plain `INSERT`, not `INSERT OR IGNORE`, because the gate reads first;
if the gate ever races with itself the second insert raises an
IntegrityError which the `_safe()` wrapper in the caller catches. The
gate is single-threaded in practice — every `open_database()` takes
the process-wide `_DB_LOCK`.)

### 5.2 Migration Strategy

No new migration version. The `_run_current_version_repairs` change
is *behavioral* — it's the gate that runs *around* the existing
migrator, not the migrator itself. Pre-7.1 databases get the repair
run on their next open (existing behavior); the marker is then
written; subsequent opens skip. Post-7.1 fresh databases get the
repair run once on first open, same outcome.

### 5.3 Migration Checklist

- [ ] No `migrations/` version bump.
- [ ] No `core/database/schema.py` change.
- [ ] No `backend/database/sqlite_wrapper.py` change.

---

## 6. Testing Strategy

### 6.1 Test Cases

| Test Case | Type | Description | Expected Result | Phase |
|-----------|------|-------------|-----------------|-------|
| `test_repair_runs_only_once_across_opens` | webapp | Open a fresh DB twice with a counting `_migrator_func`; assert call count is 1 | 1 | 7.1 |
| `test_repair_marker_is_persisted` | webapp | Open DB once, close, open a new `DatabaseObj` on the same file with a counting `_migrator_func`; assert call count is 1 (not 2) | 1 | 7.1 |
| `test_round_trip_stable_without_reopen` | webapp | The Phase 6.4 round-trip pattern (insert, find_one, restore-via-soft-delete) without the re-open workaround in the fixture | passes | 7.1 |
| `test_runbook_endpoints_referenced` | docs | Grep `docs/runbook.md` for every endpoint URL it mentions; assert each one is defined in `webapp/routers/` | 0 missing | 7.2 |
| `test_no_interface_imports_remain` | regression | After Phase 7.3, `grep -rn "from interface\|import interface" webapp/ dispatch/ tests/` returns empty | empty | 7.3 |

### 6.2 Test File Locations

- `tests/webapp/test_database_repair.py` (new) — 7.1's three cases.
- `tests/webapp/test_soft_delete.py` (modified) — drop the re-open
  workaround.
- `tests/webapp/test_runbook.py` (new) — 7.2's endpoint-coverage
  check.
- `tests/webapp/test_tree_cleanup.py` (new) — 7.3's no-`interface`-imports
  check.

### 6.3 Coverage Requirements

- [ ] New code covered by tests (7.1, 7.2, 7.3).
- [ ] Existing tests still pass — baseline 304 webapp python + 116 DOM,
  plus the 5 new tests.
- [ ] `ruff check webapp/ tests/webapp/ backend/database/` clean.
- [ ] `black --check webapp/ tests/webapp/ backend/database/` clean
  on changed files.

---

## 7. Risk Assessment

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| 7.1 marker write happens but a later code path clears `kv_settings` (e.g. a re-import) | Low | Medium (next open re-runs the repair; harmless but noisy) | The marker is a normal key in `kv_settings`; the import's reset path (if any) is documented in `webapp/importer.py` and reviewed before commit. If `kv_settings` reset exists, the marker is preserved by the import (it's not config — it's state). |
| 7.1 custom `_migrator_func` injected by a test fixture doesn't write the marker | Medium | Low (test-only; migrator re-called on every open, same as today) | The gate is a fast-path optimization, not a correctness boundary. The migrator's existing idempotency means repeated calls are safe. |
| 7.2 runbook goes stale as endpoints evolve | Medium | Low (doc-only) | The test in §6.1 (`test_runbook_endpoints_referenced`) catches the common failure mode at CI time. |
| 7.3 `interface/` removal breaks a contributor's local workflow | Very Low | Very Low | The package is orphaned — no callers in `webapp/`, `dispatch/`, or `tests/`. Verified by grep before deletion. |
| 7.3 a CI step depends on `plans/` existing | Very Low | Very Low | `plans/` is gitignored and not referenced by any Makefile, Dockerfile, or CI script (verified by grep). |
| 7.3 `interface.spec` removal breaks a build script | Very Low | Low | The webapp has no build step (it's a `python -m webapp.main` invocation); `interface.spec` is for PyInstaller desktop builds that are no longer happening. |
| 7.4 PROJECT_SPEC.md §3.7 rewrite contradicts an existing reference | Low | Low | The §3.7 addendum I wrote in Phase 6 is the only place recommending the PyQt5 GUI; rewriting it is a clean edit, not a contradiction. |

### 7.1 Rollback Plan

Each phase is a self-contained commit.

- Reverting 7.1 removes the gate; `_run_current_version_repairs` runs
  on every open again (the pre-7.1 behavior). The 7.1 test cases
  stop being meaningful but the migration code path is unchanged.
  The Phase 6.4 test's re-open workaround should be re-added if
  needed.
- Reverting 7.2 deletes `docs/runbook.md` and the README link.
- Reverting 7.3 restores `interface/`, `plans/`, `interface.spec`,
  `launch_interface.sh`, `nuitka-crash-report.xml` from git
  history; reverts the `.gitignore` comment.
- Reverting 7.4 restores the §3.7 PyQt5 recommendation.

---

## 8. Success Criteria

- [ ] `_run_current_version_repairs` runs at most once per DB lifetime
  (verified by `test_repair_runs_only_once_across_opens`).
- [ ] The Phase 6.4 round-trip test
  (`test_soft_delete_restore_round_trip`) passes without the
  re-open workaround in its fixture.
- [ ] `docs/runbook.md` exists, links to every endpoint it mentions
  (verified by `test_runbook_endpoints_referenced`), and has a
  `curl` example for each of the six operator scenarios.
- [ ] `interface/` directory is removed; `grep -rn "from
  interface\|import interface" webapp/ dispatch/ tests/` returns
  empty.
- [ ] `plans/` directory is removed from disk and from `.gitignore`.
- [ ] `interface.spec`, `launch_interface.sh`,
  `nuitka-crash-report.xml` are removed.
- [ ] `.gitignore` has an explanatory comment block for the legacy
  desktop build dirs.
- [ ] `PROJECT_SPEC.md §3.7` no longer recommends the PyQt5 GUI;
  the §3.7 addendum is rewritten to reflect that the webapp is
  the only operator surface.
- [ ] `pytest tests/webapp -q` is 100% green; `ruff check` and
  `black --check` clean on changed files.

---

## 9. Open Questions

1. Should the §3.7 PROJECT_SPEC.md rewrite (4.4) also drop the
   "PyInstaller single-file .exe" line from §3.5 release channels?
   Today §3.5 lists three channels; with the desktop gone, only two
   make sense (Docker + source/venv). **TENTATIVE:** drop the .exe
   line; the operator who wants a single-file distribution can use
   PyInstaller on the webapp source if they really need it, but
   it's not a product commitment.
2. Should the §3.7 addendum's "soft-delete + restore (Phase 6.4)"
   paragraph stay verbatim? It describes the soft-delete feature,
   which is unaffected by the desktop retirement. **TENTATIVE:**
   keep verbatim; it's a separate concern.
3. Does the `dispatch/` tree get any Phase-7 treatment? The spec
   says "no" — the redesign is Phase 8. But the user might want
   a small Phase-7 item like "rename `dispatch/` to
   `webapp/pipeline/` to match the new ownership story" without
   rewriting anything. **TENTATIVE:** defer; the rename is a
   mechanical item that belongs in Phase 8's implementation, not
   in Phase 7's spec.

---

## 10. Appendix

### 10.1 References

- `specs/PROJECT_SPEC.md §3.7` — Phase 6 deployment-model addendum;
  needs a Phase-7 rewrite to remove the PyQt5 recommendation.
- `docs/architecture/webapp-gap-audit.md §4.1` — Phase 6 status;
  §5 — gap-3.x deferred items.
- `backend/database/database_obj.py::_run_current_version_repairs`
  (lines 304-325) — the at-version repair pass that runs on every
  open.
- `migrations/modern_migrations.py::_backfill_defaults` (lines
  412-441) — the side effect the gate in 7.1 fixes.
- `tests/webapp/test_soft_delete.py:30-35` — the workaround Phase
  7.1 removes.
- `webapp/diagnostics.py::collect_diagnostics` (lines 393-470) —
  the diagnostics surface the runbook narrates.
- `webapp/routers/*.py` — every endpoint the runbook references.
- `interface/__init__.py` (docstring) — confirms the `interface/`
  package's intended post-pivot scope.
- `interface/AGENTS.md` — last documentation of the pre-pivot
  layout; deleted in 7.3.

### 10.2 Changelog

| Date | Author | Change |
|------|--------|--------|
| 2026-08-18 | Project Owner | Initial draft — 7.1 (one-shot repair), 7.2 (operator runbook), 7.3 (tree cleanup limited to `plans/` + packaging) |
| 2026-08-18 | Project Owner | Revised — desktop retirement now in scope. 7.3 expanded to include `interface/` deletion; new §4.4 added for the PROJECT_SPEC.md §3.7 rewrite; §9 carries forward the PyQt5-recommendation question as resolved (delete `interface/`). Phase 8 spec split out to a separate document. |
