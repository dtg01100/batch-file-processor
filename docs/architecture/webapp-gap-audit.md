# Desktop → Webapp Feature Gap Audit

**Status:** Re-checked 2026-08-18 against the current working tree
after closing all gap-1.x items (2026-08-17) and the router split
(2026-08-18). Operator-visible feature parity is complete; §6 adds a
new gap-2.x track for production hardening.
**Method (gap-1.x):** Read every `interface/qt/dialogs/*.py` from
`9864dc7e5^` and compare against `webapp/static/index.html` +
`webapp/static/app.js`. Anything the desktop exposed to the operator
that the webapp doesn't is listed below.
**Method (gap-2.x):** Read `specs/PROJECT_SPEC.md` §3.4 (Non-Functional
Requirements), §3.5 (Release Channels), §3.6 (Alternatives) and grade
each candidate against the spec's stated security model — single-user,
local-first, no inbound network surface — to find where the webapp
diverges from the intent.
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

## 4. Remaining work (gap-1.x)

None. All gap-1.x items are resolved.

### 4.1 Phase 6 status (2026-08-18)

All four gap-2.x picks (2.1 bearer-token, 2.3 localhost, 2.4 backend
health probe, 2.6 soft-delete) are landed on the `webapp-pivot`
branch. The webapp is now safe-by-default (binds `127.0.0.1`), supports
opt-in remote access (bearer-token), exposes live backend health in
the diagnostics card, and recovers from accidental folder deletion
through the "Recently deleted" collapsible section with per-row
Restore. Phase 6.4's `FOLDERS_DELETED_TTL_DAYS` env var (default 30,
clamped `[1, 365]`) controls the restore window; the trim job
(`SoftDeleteTrimSupervisor`) purges expired tombstones every hour.

---

## 5. Gap-2.x — Production hardening (new track)

**Context:** The webapp pivot (commit `9864dc7e5`) built exactly the
"Browser-based web UI" alternative that §3.6 rejected for *"complicating
single-user local-first story"*. The audit gap-1.x closed operator-visible
parity; gap-2.x closes the production-readiness gap that comes with
having an inbound network surface that the spec never sanctioned.

### 5.1 Candidates (graded)

| # | Item | Spec ref | Effort | Phase 6? | Why |
|---|------|----------|--------|----------|-----|
| 2.1 | Single-user bearer-token auth (`BFS_API_TOKEN` env var) | §3.4 Security | M | ✅ | The webapp defaults to `host="0.0.0.0"` (verified — `webapp/main.py:173`, `Dockerfile` exposes 8000). Any machine on the LAN can hit every endpoint. Bearer-token is the simplest match for the spec's "single-user" constraint. |
| 2.2 | TLS termination (TLS cert + key) | §3.4 Portability | M | ❌ defer | Meaningful only after 2.1 exists *and* the operator opts into remote exposure. Default recommendation is "put nginx / Caddy in front" — keep the webapp plain HTTP. |
| 2.3 | Bind to `127.0.0.1` by default; require explicit opt-in for remote | §3.4 Portability | S | ✅ | 3-line change. Prevents the entire exposure problem class before it starts. Matches the spec's "no inbound network surface" intent verbatim. |
| 2.4 | Backend health probe (TCP-open SMTP/FTP, copy-path exists) | §3.4 Observability | M | ✅ | Operator's #1 question after a failed run is *"is the SMTP server actually reachable right now?"*. The Diagnostics card is the natural home — the current `collect_diagnostics` only checks config existence, not reachability. |
| 2.5 | Configuration-change audit log (who changed what when) | §3.4 (implicit) | M | ❌ defer | Meaningful only after 2.1 lands; until then there's no "user" to attribute changes to. Also conflicts with the spec's "single-machine local-only" — there's typically one human on the box. |
| 2.6 | Soft-delete with restore window (deleted folders → `folders_deleted` for N days) | §3.4 Safety | L | ✅ | Current DELETE is permanent (verified — `webapp/routers/folders.py::api_delete_folder` removes the row + its processed-files; the only recovery is from backup, which is heavyweight for "I clicked Delete by accident"). Soft-delete is small, isolated, and removes a real foot-gun. |
| 2.7 | Backup encryption (credentials in `folders.db` are cleartext) | §3.4 Security | M | ❌ defer | Real risk only if the operator copies backup tarballs off-machine; today's deployment is a single local volume. Defensible to defer until 2.6 lands and a backup-of-backups workflow exists. |
| 2.8 | Mobile / responsive layout (one `@media` rule today) | §3.4 (implicit) | L | ❌ defer | Operator persona is at a workstation; the existing `@media (max-width: 900px)` rule covers "browser resized small". Tablet/phone isn't an immediate user. |
| 2.9 | Playwright real-browser smoke tests | §3.4 Testability | M | ❌ defer | The 24 jsdom DOM tests + 265 python tests cover the existing surface well. Real-browser tests catch CSS regressions and focus-trap bugs that JSDOM doesn't. Worth doing once the static UI stops moving weekly. |
| 2.10 | Plug-in hot-reload (no uvicorn restart for new converters) | §3.1 Pluggable | M | ❌ defer | Today the operator is the only plugin author and knows to restart uvicorn. Becomes meaningful when third-party plugins exist. |

### 5.2 Phase 6 picks

Phase 6 ships the four ✅ items: 2.3, 2.1, 2.4, 2.6. Ordered by
risk reduction (smallest, broadest-impact first):

1. **2.3 localhost-by-default** — 3-line fix, eliminates the entire
   network-exposure problem class. ✅ Landed (`06aa7dea7`).
2. **2.1 bearer-token auth** — opens the door to safe remote exposure;
   without it, 2.3 leaves a one-host-only webapp, which is correct
   for the spec but limiting. ✅ Landed (`d96d876f3`).
3. **2.4 backend health probe** — operator-facing observability win,
   no security implications. ✅ Landed (`9ee5b0daa`).
4. **2.6 soft-delete with restore window** — removes the
   permanent-delete foot-gun. ✅ Landed (Phase 6.4 commit on this
   branch).

### 5.3 Deferred (gap-3.x candidates)

The remaining six items (2.2, 2.5, 2.7, 2.8, 2.9, 2.10) are deferred
to a future audit cycle. Each is defensible today:

- **2.2 TLS / 2.5 audit log / 2.7 backup encryption** — meaningful only
  if the deployment model expands beyond single-host single-user.
- **2.8 mobile responsive** — operator persona doesn't require it.
- **2.9 Playwright** — JSDOM + python tests cover the surface; revisit
  when the static UI stabilizes.
- **2.10 plugin hot-reload** — meaningful when there are external
  plugin authors, not today.

### 5.4 Spec delta required

The webapp-pivot creates a real divergence from `PROJECT_SPEC.md` §3.4
(security model: *"no inbound network surface"*) and §3.6 (the spec
explicitly rejected the web-UI alternative the webapp-pivot built).
Phase 6 should include a small §3.7 addendum to the project spec
capturing the new deployment model and the rationale for the
single-user bearer-token design.

---

## 6. References

- Commit `9864dc7e5` — pivot commit, dropped `interface/qt/`
- Commit `287015606` — most recent "gap closure" (folder create / delete
  + settings editor + real UPC lookup); explicitly named for that scope.
- Commits `e0729e88e` (1.1), `d7ac64ea0` (1.3), `8de4d4476` (bulk
  "mark all processed"), `0326ae246` (per-format plugin UIs),
  `c4a20bc49` (async dialogs).
- Phase-5 spec: `specs/webapp-phase-5-observability.md` (the established
  template Phase 6 follows).
- Phase-6 spec: `specs/webapp-phase-6-production-hardening.md`.
- Spec: `specs/PROJECT_SPEC.md` §3.2 (capabilities A–E), §3.4 (NFRs),
  §3.5 (release channels), §3.6 (alternatives).
