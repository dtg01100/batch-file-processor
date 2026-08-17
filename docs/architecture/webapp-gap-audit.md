# Desktop → Webapp Feature Gap Audit

**Status:** Re-checked 2026-08-17 against the current working tree
after closing gaps 1.2, 1.5, 1.6, and 1.7. All gap-1.x items are
now resolved.
**Method:** Read every `interface/qt/dialogs/*.py` from `9864dc7e5^` and compare
against `webapp/static/index.html` + `webapp/static/app.js`. Anything the
desktop exposed to the operator that the webapp doesn't is listed below.
**Out of scope:** desktop-only build / packaging features (PyInstaller,
Nuitka) and the Qt test surface — both removed by design.

---

## Status summary (2026-08-17, all gaps resolved)

| # | Gap | Status |
|---|-----|--------|
| 1.1 | Folder search / filter | ✅ Landed (`e0729e88e`) |
| 1.2 | Browse all processed files | ✅ Landed (2026-08-17) |
| 1.3 | `alert_on_failure` toggle | ✅ Landed (`d7ac64ea0`) |
| 1.4 | Folder settings copy from another folder | ✅ Landed (2026-08-17) |
| 1.5 | Diagnostic / self-test | ✅ Landed (2026-08-17) |
| 1.6 | Import progress / cancel | ✅ Landed (2026-08-17) |
| 1.7 | Keyboard shortcuts | ✅ Landed (2026-08-17) |
| 1.8 | Resend batch operations | ✅ Landed (with 1.2's browse view) |

---

## 1. Gaps (operator-visible features in desktop, missing in webapp)

### 1.1 Folder search / filter — ✅ LANDED
- **Desktop** (`interface/qt/window_controller.py:146-167`): `SearchWidget`
  with a free-text filter over alias + path. `_set_folders_filter` updates
  `self._folder_filter` and reloads the list.
- **Webapp**: `#folders-search` input added to the folders card head
  (`e0729e88e`); `_renderFolders()` filters client-side by alias / path on
  every `input` event. No further work.

### 1.2 Browse all processed files (search + date range + pagination) — ✅ LANDED (2026-08-17)
- **Desktop** (`interface/qt/dialogs/resend_dialog.py`): full search text,
  date-range filter (`QDateEdit` with Today button), file-existence worker
  thread, pagination (`_current_offset` / `_total_files`, "Showing N files"
  + "Load More"), checkbox to select rows, bulk **Select All** /
  **Clear Selection** / **Mark Selected for Resend** / **Clear Resend Flags**.
- **Webapp**:
  - **Server:** `webapp/resend.py` exposes `list_processed_files` +
    `count_processed_files` sharing one WHERE-builder. `GET
    /api/processed-files` accepts `folder_id` / `search` / `date_from` /
    `date_to` / `limit` (cap 10000) / `offset` (cap 10000) and returns
    `{count, total, limit, offset, files}`.
  - **UI:** the processed-files card now has every piece of desktop
    parity — folder dropdown (mirror of the errors-filter dropdown,
    rebuilds on folder-set change but preserves selection), search input,
    date inputs with **Today** buttons on each, **Clear** button,
    **Select all** + **Clear selection** bulk toggles, a head-of-table
    checkbox that tracks tri-state, **Load More** button (visible while
    `offset < total`), and a "Showing N of M" count line.
  - **Tests:** `tests/webapp/test_resend.py` covers `offset`/`total`
    round-trip + `count_processed_files`. `tests/webapp/dom.test.js`
    covers folder-dropdown narrowing, Today buttons, bulk selection
    (incl. tri-state), and Load-More pagination over a synthetic 250-row
    fixture.

### 1.3 `alert_on_failure` toggle — ✅ LANDED
- **Desktop** (`interface/qt/dialogs/edit_folders_dialog.py`): rendered
  as an `alert_on_failure` checkbox per folder.
- **Webapp**: `alert_on_failure` checkbox added to the folder editor's
  Alerting fieldset (`d7ac64ea0`), wired through `readFolderPanel` /
  `populateFolderPanel`. No further work.

### 1.4 Folder settings copy from another folder — ✅ LANDED (2026-08-17)
- **Desktop** (`interface/qt/dialogs/edit_folders_dialog.py:90`):
  `on_copy_config=self.handlers.copy_config_from_other` lets the operator
  open the edit panel, click "Copy Config", and pick a source folder to
  copy every setting from (path/alias preserved on the destination).
- **Webapp**: "Copy from…" button in the folder panel head opens a picker
  dialog (every folder except the one being edited), fetches the source's
  full edit schema, and seeds the form — backends, EDI, UPC, A-record,
  invoice-date, CSV, vendor-specific and per-format plugin config — while
  id / alias / path / active state stay on the destination. A note under
  the panel head confirms the copy. See `pickCopySource` /
  `copyFolderSettings` in `webapp/static/app.js` and the
  "copy from…" DOM test in `tests/webapp/dom.test.js`.

### 1.5 Diagnostic / self-test — ✅ LANDED (2026-08-17)
- **Desktop** (`interface/qt/diagnostics.py`): `run_self_test()` prints
  platform + module-import check + per-component sanity. The GUI test
  enumerates every dialog. CLI flag `-t` / `--self-test` invokes it.
- **Webapp**:
  - **Server:** `webapp/diagnostics.py::collect_diagnostics()` builds the
    snapshot. Every probe is wrapped in `_safe()` so a missing table /
    mid-import kv_settings read can never 500 the endpoint.
    `GET /api/diagnostics` returns `{platform, app, paths, database,
    runtime, modules, ok, warnings}` plus a recent-runs list (merged
    in-memory + persisted `RunHistory`) and a 24h failure count.
    Module import check covers the same workhorses the desktop
    exercised minus the Qt-only entries.
  - **UI:** a `diag` button in the topbar opens a `<dialog
    id="diagnostics-modal">` with a state banner (green when clean,
    amber when warnings), a per-field table (platform, Python, DB
    version, folders/processed/errors/queued-emails counts, active
    runs, scheduler, watched folders, backups, module summary), a
    collapsible recent-runs list, a Raw JSON block, and a Copy JSON
    button (Clipboard API + `execCommand` fallback for non-secure
    contexts).
  - **Tests:** `tests/webapp/test_diagnostics.py` covers the endpoint,
    the no-DB early-boot path, the recent-failure warning path, and
    the expected-modules contract. `tests/webapp/dom.test.js` covers
    the open-from-button + render path + Esc close + clean vs warning
    banner.

### 1.6 Import progress / cancel — ✅ LANDED (2026-08-17)
- **Desktop** (`interface/qt/dialogs/database_import_dialog.py:170-220`):
  `QThread` runs the import, progress bar updates, "Cancel" button
  cancels the worker.
- **Webapp**:
  - **Server:** `/api/import` now measures wall-clock duration with
    `time.perf_counter()` and adds `duration_seconds` to the response
    payload alongside the existing summary. No Cancel endpoint —
    threading a cancel through FastAPI's request lifecycle would add a
    lot of code for a one-time setup action, so the audit-doc "stage
    + duration" option is the chosen fix.
  - **UI:** while the request is in flight, the Import button shows a
    live elapsed timer ("Importing… 12.3s") that ticks every 100ms.
    On success, the result notice appends `(N.NNs)` so a 500-folder
    import that took 28.4s now says "Imported 500 folder(s) … in
    (28.40s)" instead of an opaque spinner.
  - **Tests:** `tests/webapp/test_api.py` asserts `duration_seconds`
    is present and non-negative. `tests/webapp/dom.test.js` covers
    the live timer (label changes over time) and the duration in
    the result notice.

### 1.7 Keyboard shortcuts — ✅ LANDED (2026-08-17)
- **Desktop**: native OS shortcuts (Ctrl+R / F5 to refresh, etc.).
- **Webapp**: a single `keydown` listener on `document` handles:
  - `Ctrl/Cmd+Enter` — click the **Run all folders** button (no-op while
    a run is in flight, mirroring the disabled-button state).
  - `Ctrl/Cmd+R` — refresh every card (`refreshConfig` + `loadFolders` +
    `loadWatched` + `loadErrors` + `loadRuns` + `loadProcessed` +
    `loadBackups` + `loadSettings`).
  - `Ctrl/Cmd+I` — focus the Import button.
  - `Ctrl/Cmd+F` — focus the Folders search box.
  - `Ctrl/Cmd+P` — focus the Processed-files search box.
  - `?` — open a `<dialog id="shortcuts-modal">` cheat sheet
    (Esc / backdrop / × button all close it).
  - `Esc` — close the modal first, otherwise close the folder panel.
  - Shortcuts that would steal text input (R / I / F / P) are skipped
    while the event target is an input/textarea/select/contentEditable.
- The footer hints "Press `?` for keyboard shortcuts." and a topbar "?"
  button both open the modal. Tests: `tests/webapp/dom.test.js` covers
  the modal open/close + Ctrl+Enter / Ctrl+R / Ctrl+F / Ctrl+P paths.

### 1.8 Resend batch operations — ✅ LANDED
- **Desktop** (`interface/qt/dialogs/resend_dialog.py`): select multiple
  rows + "Resend selected" button.
- **Webapp**: per-row checkboxes on the processed-files card set/reset
  `resend_flag` via `POST /api/processed-files/{id}/resend`; "Resend
  flagged (N)" posts to `/api/resend` and polls the run; "Clear all
  flags" bulk-clears. Bulk **Select All** / **Clear Selection** buttons
  landed with gap 1.2.

---

## 2. Areas the webapp matches or exceeds the desktop

For completeness — these were parity-checked, no gap.

| Area | Webapp | Desktop |
|------|--------|---------|
| Import configuration | multipart upload + base-dir rebasing | file picker + path override |
| Folder CRUD | full create / edit / delete with plugin-config UI | full create / edit / delete |
| Folder-level plugin config | per-format UI for all 11 converters | per-format UI |
| Maintenance | all 5 destructive ops with confirm + clear-queued-emails | all 5 destructive ops |
| Run + preflight + log | background run with SSE log streaming | synchronous with progress |
| Schedule | interval + enable/disable + runs-triggered count | interval toggle |
| Watcher | per-folder enable + interval + last tick / last run / last error | basic on/off |
| Errors ledger | DB-backed + raw download + folder filter | file-based viewer |
| Settings | email / AS400 / backups / reporting / paths | same fields |
| Backup / restore | timestamped snapshots + download | same |
| Processed-files report | per-folder "Export CSV report" in the folder panel | `processed_files_dialog` report export |
| Processed-files browse | search + date-range + folder filter + Today + Load More + bulk select | same fields, Qt-native |
| Keyboard shortcuts | Ctrl+Enter/R/I/F/P + ? modal | OS-native |
| Self-test / diagnostics | `GET /api/diagnostics` + Diagnostics modal (banner, table, recent runs, Copy JSON) | `run_self_test()` CLI (`-t`) + Qt dialog |
| Import progress | live elapsed timer on the button + `duration_seconds` in the result notice | QThread + progress bar + Cancel |

---

## 3. Areas intentionally not ported

- **Native menu bar / status bar** — irrelevant in browser.
- **`-t` self-test CLI flag** — replaced by `/api/health` for the
  browser. A diagnostic endpoint is the modern equivalent (gap 1.5).
- **Folder drag-and-drop onto window** — superseded by the import card
  (file picker).
- **Tray icon / "minimize to tray"** — no equivalent in browser.

---

## 4. Remaining work

None. All gap-1.x items are resolved. Any further parity work belongs
in new audit cycles (e.g. comparing a future desktop feature against
the webapp once it's built).

## 5. References

- Commit `9864dc7e5` — pivot commit, dropped `interface/qt/`
- Commit `287015606` — most recent "gap closure" (folder create / delete
  + settings editor + real UPC lookup); explicitly named for that scope.
- Commits `e0729e88e` (1.1), `d7ac64ea0` (1.3), `8de4d4476` (bulk
  "mark all processed"), `0326ae246` (per-format plugin UIs),
  `c4a20bc49` (async dialogs).
- Spec: `specs/PROJECT_SPEC.md` §3.2 (capabilities A–E).
