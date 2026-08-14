# Desktop → Webapp Feature Gap Audit

**Status:** Active gaps after the Qt-to-webapp pivot (`9864dc7e5`, 2026-08-13).
**Method:** Read every `interface/qt/dialogs/*.py` from `9864dc7e5^` and compare
against `webapp/static/index.html` + `webapp/static/app.js`. Anything the
desktop exposed to the operator that the webapp doesn't is listed below.
**Out of scope:** desktop-only build / packaging features (PyInstaller,
Nuitka) and the Qt test surface — both removed by design.

---

## 1. Gaps (operator-visible features in desktop, missing in webapp)

### 1.1 Folder search / filter
- **Desktop** (`interface/qt/window_controller.py:146-167`): `SearchWidget`
  with a free-text filter over alias + path. `_set_folders_filter` updates
  `self._folder_filter` and reloads the list.
- **Webapp** (`webapp/static/index.html:55-79`): folders card has no
  search box. With 530+ folders from a legacy import, scrolling is the
  only way to find one.
- **Fix:** Add `<input id="folder-search">` to the folders card; filter
  client-side by alias / folder_name / resolved_path (cheap, no API
  change needed).

### 1.2 Browse all processed files (search + date range + pagination)
- **Desktop** (`interface/qt/dialogs/resend_dialog.py`): full search text,
  date-range filter (`QDateEdit` with Today button), file-existence worker
  thread, pagination (`_current_offset` / `_total_files`), checkbox to
  select rows for batch resend.
- **Webapp** (`webapp/static/app.js:1189`): only calls
  `/api/processed-files/flagged`. The general
  `GET /api/processed-files` endpoint exists (`webapp/main.py:972`) but
  the frontend never uses it.
- **Fix:** Add a "Processed files" card that lists all recent rows from
  `/api/processed-files` with a search box, folder filter, and
  date-range filter. Add an in-page checkbox column so the same row can
  be flagged for resend from the browse view. Server already returns
  200 rows; pagination is the natural next step if the corpus grows.

### 1.3 `alert_on_failure` toggle (not exposed in the UI)
- **Desktop** (`interface/qt/dialogs/edit_folders_dialog.py`): rendered
  as an `alert_on_failure` checkbox per folder.
- **Webapp** (`webapp/static/app.js:631`): hard-coded `alert_on_failure:
  true` with the comment `// not exposed in the UI yet; default`. The
  schema accepts it (`webapp/folder_schema.py:152`) and the column exists
  in the DB — only the form input is missing.
- **Fix:** Add an `alert_on_failure` checkbox to the folder editor
  Alerting fieldset. Wire through `readFolderPanel` /
  `populateFolderPanel`.

### 1.4 Folder settings copy from another folder
- **Desktop** (`interface/qt/dialogs/edit_folders_dialog.py:90`):
  `on_copy_config=self.handlers.copy_config_from_other` lets the operator
  open the edit panel, click "Copy Config", and pick a source folder to
  copy every setting from (path/alias preserved on the destination).
- **Webapp**: no equivalent. Operators onboading a 50th folder re-enter
  every FTP/email/copy backend manually.
- **Fix:** Add a "Copy from…" button in the folder editor that opens a
  picker (existing `loadFolders()` result is already a list of `{id,
  alias, folder_name, ...}`) and copies the matching backend /
  EDI / UPC / plugin-config blocks into the form. Id / alias /
  folder_name stay local.

### 1.5 Diagnostic / self-test
- **Desktop** (`interface/qt/diagnostics.py`): `run_self_test()` prints
  platform + module-import check + per-component sanity. The GUI test
  enumerates every dialog. CLI flag `-t` / `--self-test` invokes it.
- **Webapp**: no equivalent. The closest is `GET /api/health` (basic
  liveness).
- **Fix:** Add a `GET /api/diagnostics` endpoint that returns
  `{platform, python, db_exists, db_version, watched_count, queue_depth,
  recent_run_failures, ...}` and surface a small "Diagnostics" card.
  Lower priority — most useful for support tickets, not daily operation.

### 1.6 Import progress / cancel
- **Desktop** (`interface/qt/dialogs/database_import_dialog.py:170-220`):
  `QThread` runs the import, progress bar updates, "Cancel" button
  cancels the worker.
- **Webapp** (`webapp/static/app.js:131-162`): button shows "Importing…"
  and disables; no progress feedback, no cancel. A 500-folder legacy
  DB import takes seconds-to-minutes.
- **Fix:** Either run the import on a background task with `/api/import`
  returning a task id that the frontend polls, or at minimum surface
  import stage + duration in the result notice. Lower priority — import
  is a one-time setup action.

### 1.7 Keyboard shortcuts
- **Desktop**: native OS shortcuts (Ctrl+R / F5 to refresh, etc.).
- **Webapp**: none beyond row activation (Enter/Space) and Escape-to-
  close-panel. No way to kick off "Run all folders" without the mouse.
- **Fix:** Add a `keydown` listener on `document` for `Ctrl+Enter` (run),
  `Ctrl+R` (refresh everything), `Ctrl+I` (focus import button), `?`
  (show a small shortcuts modal). Keep it minimal — operators use the
  page often enough that mouse-only is friction.

### 1.8 Resend batch operations
- **Desktop** (`interface/qt/dialogs/resend_dialog.py`): select multiple
  rows + "Resend selected" button.
- **Webapp** (`webapp/main.py:34`): `/api/processed-files/resend-batch`
  endpoint exists but the frontend's flagged-list card has per-row
  checkboxes only — there is no UI for batch flagging.
- **Fix:** Once gap 1.2 lands, the browse view's row checkboxes already
  produce a batch flag.

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

---

## 3. Areas intentionally not ported

- **Native menu bar / status bar** — irrelevant in browser.
- **`-t` self-test CLI flag** — replaced by `/api/health` for the
  browser. A diagnostic endpoint is the modern equivalent (gap 1.5).
- **Folder drag-and-drop onto window** — superseded by the import card
  (file picker).
- **Tray icon / "minimize to tray"** — no equivalent in browser.

---

## 4. Recommended order

1. `alert_on_failure` toggle (gap 1.3) — single-field, ~10 lines of HTML
   + plumbing, unblocks operators who want to suppress noisy alerts.
2. Folder search filter (gap 1.1) — one input + ~20 lines of JS, immediate
   quality-of-life win for 500-folder installs.
3. Browse all processed files (gap 1.2) — wires up an unused endpoint,
   surfaces the 200-row LIMIT the backend already returns.
4. Folder copy/duplicate (gap 1.4) — saves operator time on
   large fleets.
5. Keyboard shortcuts (gap 1.7) — small UX polish.
6. Diagnostics endpoint (gap 1.5) and import progress (gap 1.6) —
   support / setup-time only; defer until needed.

## 5. References

- Commit `9864dc7e5` — pivot commit, dropped `interface/qt/`
- Commit `287015606` — most recent "gap closure" (folder create / delete
  + settings editor + real UPC lookup); explicitly named for that scope.
- Spec: `specs/PROJECT_SPEC.md` §3.2 (capabilities A–E).
