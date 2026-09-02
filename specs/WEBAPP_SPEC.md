# Spec: Batch File Processor — Webapp Companion

**Status:** DRAFT
**Author:** Project Owner
**Created:** 2026-08-31
**Updated:** 2026-08-31

> **Purpose of this document:** this is the **webapp-focused
> companion spec** to [`specs/PROJECT_SPEC.md`](./PROJECT_SPEC.md).
> The project spec describes *what the product is* — the five
> capabilities (A through E), the non-functional requirements, the
> roadmap, the alternatives. This document describes *what the
> webapp version of the product is today*: the architecture of
> the FastAPI shell, the HTTP API surface, the static SPA, the
> background services, the deployment model, the test surface,
> and the per-feature phase status.
>
> If you are a **new contributor**, read this document first, then
> the project spec. If you are an **operator**, the project spec
> plus [`docs/runbook.md`](../docs/runbook.md) is the actionable
> surface; this doc is the API + architecture reference. If you
> are reviewing a feature change, this doc is the architecture
> section you cite; the project spec is the intent section.
>
> For the *why* behind each phase of the webapp pivot, follow the
> cross-references in §17. For deep design detail (plugin model,
> converter architecture, error handling, etc.) follow the
> project spec's appendix and the per-domain design docs in
> `docs/design/`.

---

## Table of Contents

1. [Summary](#1-summary)
2. [Background](#2-background)
3. [Scope](#3-scope)
4. [Architecture](#4-architecture)
5. [HTTP API Surface](#5-http-api-surface)
6. [Static UI](#6-static-ui)
7. [Configuration & Environment](#7-configuration--environment)
8. [Data Model (webapp-owned tables)](#8-data-model-webapp-owned-tables)
9. [Background Services](#9-background-services)
10. [Authentication & Authorization](#10-authentication--authorization)
11. [Observability](#11-observability)
12. [Deployment](#12-deployment)
13. [Testing Strategy](#13-testing-strategy)
14. [Roadmap & Phase Status](#14-roadmap--phase-status)
15. [Risk Assessment](#15-risk-assessment)
16. [Open Questions](#16-open-questions)
17. [Appendix](#17-appendix)

---

## 1. Summary

> **Internal tool.** One project owner, one workstation, one
> operator role, zero external users. The product exists because
> the project owner needs to process EDI files at runtime without
> writing code for each trading partner. Every other consideration
> is downstream of that. See [ROADMAP.md §1.1](./ROADMAP.md) for
> the full framing.

The **webapp version of the Batch File Processor** is a
**single-host, local-first web application** — a FastAPI HTTP
server backed by a vanilla-JS single-page UI — that wraps the
15-year-old `dispatch/` + `backend/` + `core/` processing
engine with a browser-native operator surface. It was introduced
in 2026-08-04 (commit `9864dc7e5`) and is now the **only**
operator surface for the product.

The webapp exposes:

- a JSON HTTP API (49 endpoints, 11 routers) for folder CRUD,
  processing runs, watcher control, error ledger, processed-files
  management, backups, settings, diagnostics, and a single-server
  bearer-token auth (Phase 6.2);
- a static SPA (`webapp/static/`, ~4,700 lines of JS/CSS/HTML,
  no bundler) that renders the same dashboard;
- three background services — the **run-store worker** (executes
  processing in a thread pool), the **scheduler** (interval-based
  automatic runs), and the **folder-watcher supervisor** (per-folder
  polling tickers);
- one webapp-owned error ledger (`dispatch_errors`) and a soft-delete
  tombstone table (`folders_deleted`) that are the only
  first-class persistence owned by `webapp/`.

The webapp is bound to `127.0.0.1:8000` by default (Phase 6.1),
exposes no inbound surface to the LAN unless the operator
explicitly opts in via `BFS_HOST` or `uvicorn --host 0.0.0.0`,
and adds a long-lived `BFS_API_TOKEN` bearer gate (Phase 6.2) for
the remote-access case. The deployment story is one command
(`docker compose up`) on the same host that owns the data.

| Surface | Layer | Size |
|---------|-------|------|
| HTTP API | `webapp/routers/` + `webapp/main.py` | 11 routers, 49 endpoints, 2,067 LOC |
| Static SPA | `webapp/static/` | 4 files, 4,716 LOC |
| Background services | `webapp/runner.py` + `webapp/scheduler.py` + `webapp/watcher.py` | 1,412 LOC |
| Webapp-owned state | `webapp/errors.py` + soft-delete code in `webapp/routers/folders.py` | 440 + 565 LOC |
| Tests | `tests/webapp/` | 21 Python test files + 4 JS test files |

---

## 2. Background

### 2.1 Origin

Before the webapp pivot, the project shipped a PyQt5 desktop GUI
(`interface/qt/`) that drove the same `dispatch/` engine from a
local workstation. The desktop app had **no inbound network
surface** (per the 2026-07-06 spec §3.4) because the GUI was
local to the operator.

In 2026-08, two changes collided:

1. The desktop GUI was retired by product decision (the desktop
   app's user base had collapsed to zero — the last remaining
   customer had migrated to a hosted solution). The PyQt5
   codebase was the largest single maintenance burden in the
   tree and the only consumer of the desktop-specific
   packaging machinery (PyInstaller, Nuitka, frozen-binary
   builds).
2. Operators wanted **remote access** to the dispatcher from
   their laptop without an X server / RDP session. The natural
   shape is a browser dashboard.

The webapp pivot (commit `9864dc7e5`) was the merge of those two
decisions: drop the desktop GUI, ship a FastAPI + SPA that wraps
the existing engine. The pivot preserved every capability the
desktop app exposed ([`docs/architecture/webapp-gap-audit.md`](../docs/architecture/webapp-gap-audit.md)
§1 confirms operator-visible parity is complete).

### 2.2 What the pivot did not change

- The processing engine (`dispatch/`, `backend/`, `core/edi/`)
  is **unchanged**. `webapp/runner.py` calls
  `dispatch.orchestrator.DispatchOrchestrator` directly inside a
  worker thread. The pipeline stages, the EDI validation rules,
  the 11 converters, the 4 backends, the file-discovery and
  idempotency logic, the structured-logging format — all preserved
  byte-for-byte.
- The database schema and migration policy are unchanged.
  `webapp/importer.py` reads a legacy `folders.db` and the
  migration pipeline still runs on every open. The schema version
  is the same constant in both worlds.
- The plugin model for converters and backends is unchanged.
  Adding a new converter means dropping a file under
  `dispatch/converters/`; the webapp picks it up via
  `webapp/converters_api.py` on the next `GET /api/converters`.

### 2.3 What the pivot added

- **HTTP transport layer.** Every operator action that used to be
  a dialog click is now a JSON request. The router layout
  (one router per domain) was extracted from the original
  monolithic `webapp/main.py` in commit `287015606` so that
  each endpoint lives next to its peer endpoints and the auth
  dependency can be applied per-router.
- **Browser SPA.** The dashboard renders the same 14 cards
  the desktop exposed, with the same keyboard shortcuts, the
  same confirmations, the same diagnostics — but driven by
  `fetch()` against the HTTP API.
- **Run-store singleton.** `webapp/runner.py::RunStore` is a
  thread-safe in-memory record of in-flight and recent runs,
  augmented by the persisted `RunHistory` (SQLite) for the
  long tail. The scheduler and watcher both submit runs through
  the run store so a single `GET /api/runs` returns the merged
  picture.
- **Diagnostics endpoint.** `GET /api/diagnostics` answers
  "is the system healthy right now?" in one round-trip —
  platform info, paths, DB schema version, runtime, recent runs,
  24h failure count, backend reachability (Phase 6.3), and an
  import-check of every Python module the engine needs.

---

## 3. Scope

### 3.1 In scope for this spec

- The webapp layer (everything under `webapp/`).
- The webapp-owned data (`dispatch_errors`, `folders_deleted`,
  `runs` history, `processed_files` queries).
- The static SPA (`webapp/static/`).
- Deployment via Docker and local venv.
- The 21 Python tests and 4 JS tests under `tests/webapp/`.

### 3.2 Out of scope (covered elsewhere)

- The processing engine itself — see
  `docs/design/PROCESSING_PIPELINE.md` and the project spec
  §3.2.3 (the four-stage pipeline contract).
- The plugin model for converters / backends — see
  `docs/design/PLUGIN_API.md`, `docs/PLUGIN_DESIGN.md`, and
  `docs/CONVERTER_OUTPUT_FORMATS.md`.
- The schema design and migration policy — see
  `docs/design/DATABASE_SCHEMA.md` and `docs/MIGRATION_DESIGN.md`.
- The operator workflows ("if X, do Y") — see `docs/runbook.md`.

### 3.3 Intentionally not in scope

These were considered and deferred — see
`docs/architecture/webapp-gap-audit.md` §5 and the project
spec §13:

- TLS termination (Phase 6.1's localhost-by-default makes it
  unnecessary; default recommendation is a reverse proxy in front).
- Multi-user auth (the spec is single-user).
- Mobile-responsive layout (operator persona is at a workstation;
  one `@media` rule for narrow windows is enough).
- Playwright browser smoke tests (JSDOM + python tests cover the
  surface; revisit when the static UI stabilizes).
- Plug-in hot-reload (no third-party plugin authors yet).

---

## 4. Architecture

### 4.1 Layered view

```
+-----------------------------------------------------------------------------+
|                  Operator's browser (single-user)                          |
|  static SPA -- index.html + style.css + app.js (4,716 LOC, no bundler)     |
+-----------------------------------------------------------------------------+
                                  | fetch() with bearer token
                                  v
+-----------------------------------------------------------------------------+
|                    webapp/main.py -- FastAPI app factory                    |
|  lifespan: starts/stops Scheduler, WatcherSupervisor, SoftDeleteTrim        |
|  auth dep: verify_api_token (Phase 6.2) -- applied at router include         |
+-----------------------------------------------------------------------------+
                                  |
        +------------+------------+------------+----------------+
        v            v            v            v                v
  +-----------+ +-----------+ +-----------+ +-----------+ +--------------+
  | system.py | | folders.py| | runs.py   | | errors.py | | processed.py |
  | config.py | | settings  | | schedule  | | backups   | | maintenance  |
  |  health,  | |  folder   | |   runs,   | |   error   | |  processed,  |
  |  diag,    | |  CRUD,    | |  sched,   | |   ledger, | |  resend,     |
  |  preview, | |  soft-    | |  SSE log  | |   backup, | |  bulk ops    |
  |  imports  | |  delete   | |   stream  | |   restore | |              |
  +-----------+ +-----------+ +-----------+ +-----------+ +--------------+
                                  |
                                  v
+-----------------------------------------------------------------------------+
|             webapp-owned services (run store, scheduler, watcher)           |
|                                                                             |
|   runner.py: RunStore (singleton) -- in-flight + recent runs                |
|   scheduler.py: Scheduler -- interval-based automatic runs                  |
|   watcher.py: WatcherSupervisor + FolderWatcher -- per-folder polling       |
|   errors.py: webapp-owned error ledger (dispatch_errors table)               |
|   diagnostics.py: collect_diagnostics() -- single-payload self-test         |
|   importer.py: legacy folders.db import + path rebasing                     |
|   history.py: RunHistory -- SQLite-persisted run history                    |
|   resend.py: list_processed_files + bulk flag / clear                       |
|   preview.py: parse-only EDI preview (no send)                              |
|   maintenance.py: bulk destructive ops + CSV export                         |
|   converters_api.py: dynamic enumeration of dispatch/converters/*           |
|   backup.py: timestamped snapshots + restore + download                     |
|   folder_schema.py: FolderEditSchema (Pydantic) for the editor              |
+-----------------------------------------------------------------------------+
                                  |
                                  v
+-----------------------------------------------------------------------------+
|              dispatch/ + backend/ + core/ (processing engine)               |
|   orchestrator.py -> services/{folder_processor, file_processor}            |
|   pipeline/{validator, splitter, converter, tweaker}                        |
|   converters/ (11 plugins)   send_manager.py   edi_validator.py             |
|   backend/{email, ftp, http, copy}_backend.py   smtp/ftp/http_client.py     |
|   core/{edi/, ports/, utils/, structured_logging, exceptions}               |
|   adapters/{sqlite, db2ssh, inmemory}/ + migrations/                        |
+-----------------------------------------------------------------------------+
```

### 4.2 Process model

The webapp is **one OS process** that owns:

- The asyncio event loop (uvicorn). All HTTP requests run on it.
- A **run-store worker thread** — one thread, started lazily by
  the run store on first `POST /api/run`. Every run (manual
  trigger, scheduler tick, watcher tick, resend) is enqueued on
  this thread and executed serially. The thread is the only
  caller of `dispatch.orchestrator.DispatchOrchestrator`.
- A **scheduler thread** (`Scheduler`) — interval-based loop that
  posts `POST /api/run` equivalent work into the run store.
  Configurable interval (`BFS_SCHEDULE_INTERVAL_SECONDS`,
  default 900). Can be enabled / disabled at runtime via
  `POST /api/schedule`.
- A **folder-watcher supervisor thread** (`WatcherSupervisor`)
  that polls `folders` for `watch_enabled = 1` rows every 30s
  and starts / stops one `FolderWatcher` thread per watched
  folder. Each `FolderWatcher` calls the run store on each tick
  with new files in its input directory.
- A **soft-delete trim supervisor thread** (Phase 6.4) that purges
  `folders_deleted` tombstones older than `FOLDERS_DELETED_TTL_DAYS`
  (default 30) every `FOLDERS_DELETED_TRIM_INTERVAL_SECONDS`
  (default 3600).

All four threads respect a single `_stop` event; the
`webapp/main.py` lifespan handler joins them on shutdown with a
2-second timeout per thread.

### 4.3 State model

| State | Owner | Where it lives | Lifetime |
|-------|-------|----------------|----------|
| Folder configuration | webapp (CRUD via `webapp/routers/folders.py`) | `folders` table (SQLite) | persistent |
| Processed-files ledger | dispatch (`ProcessedFilesTracker`) + webapp reads (`webapp/resend.py`) | `processed_files` table | persistent |
| Run history | webapp (`history.py::RunHistory`) | `runs` table (SQLite, persisted) + `RunStore` (in-memory ring buffer) | mixed |
| Error ledger | webapp (`errors.py::ErrorLedger`) | `dispatch_errors` table | persistent |
| Soft-delete tombstones | webapp (`folders_deleted` table in migrations) | `folders_deleted` table | persistent, TTL'd |
| Run-store singleton | webapp (`runner.py::RunStore`) | in-memory dict + deque | process lifetime |
| Scheduler / watcher / trim supervisor | webapp | thread-local state | process lifetime |
| App settings (email host, FTP default, etc.) | webapp (`webapp/settings_api.py`) | `settings` table (webapp-owned keys) | persistent |

### 4.4 Why the engine is not under `webapp/`

The processing engine (`dispatch/`, `backend/`, `core/`) is the
largest single chunk of battle-tested code in the tree (~25,000
lines across 80+ files). Moving it under `webapp/` is a
**separate, much larger piece of work** tracked by
[`specs/webapp-phase-8-pipeline-redesign.md`](./webapp-phase-8-pipeline-redesign.md).
That spec is a design document, not an implementation plan; it
ends with a numbered list of design decisions that must be made
in order. None of those decisions pre-suppose a particular
outcome; the spec exists so the decisions have a coherent
structure when they are made.

For now, the engine stays where it is. The webapp owns the thin
HTTP / SPA / background-services layer that drives it.


---

## 5. HTTP API Surface

49 endpoints, 11 routers. All endpoints except those in
§5.1 require `Authorization: Bearer <token>` when
`BFS_API_TOKEN` is set.

### 5.1 Unauthenticated endpoints (always reachable)

| Method | Path | Purpose | Owner |
|--------|------|---------|-------|
| `GET` | `/` | Static SPA (browser UI) | `webapp/main.py` |
| `GET` | `/api/health` | Liveness + data-dir summary | `webapp/routers/system.py` |
| `GET` | `/docs` | FastAPI auto-generated docs | FastAPI |
| `GET` | `/openapi.json` | OpenAPI schema | FastAPI |
| `GET` | `/redoc` | ReDoc | FastAPI |

### 5.2 System, config, diagnostics, imports

| Method | Path | Purpose | Phase |
|--------|------|---------|-------|
| `GET` | `/api/config` | base-dir / data-dir / DB path + exists + size | Phase 5 |
| `GET` | `/api/diagnostics` | Full self-test snapshot | Phase 5 / 6.3 |
| `GET` | `/api/preflight` | Validate active folder configs | Phase 5 |
| `POST` | `/api/import` | Upload a legacy `folders.db` + rebasing | Phase 5 |
| `POST` | `/api/preview/edi` | Parse-only EDI preview (no send) | Phase 5 |

### 5.3 Folders (CRUD + soft-delete)

| Method | Path | Purpose | Phase |
|--------|------|---------|-------|
| `GET` | `/api/folders` | List configured folders | Phase 5 |
| `POST` | `/api/folders` | Create a folder | Phase 5 |
| `GET` | `/api/folders/{folder_id}` | One folder (full edit schema) | Phase 5 |
| `PUT` | `/api/folders/{folder_id}` | Save one folder | Phase 5 |
| `DELETE` | `/api/folders/{folder_id}` | Soft-delete | Phase 6.4 |
| `GET` | `/api/folders/deleted` | List soft-deleted tombstones | Phase 6.4 |
| `POST` | `/api/folders/{folder_id}/restore` | Restore a tombstone | Phase 6.4 |
| `POST` | `/api/folders/{folder_id}/run` | Run one folder | Phase 5 |
| `GET` | `/api/converters` | Enumerate 11 converters + config fields | Phase 5 |
| `GET` | `/api/settings` | Editable app settings | Phase 5 |
| `PUT` | `/api/settings` | Replace editable settings | Phase 5 |

### 5.4 Runs, schedule, watcher

| Method | Path | Purpose | Phase |
|--------|------|---------|-------|
| `POST` | `/api/run` | Start a background run (all folders) | Phase 5 |
| `POST` | `/api/resend` | Start a background resend run | Phase 5 |
| `GET` | `/api/runs` | Recent runs (in-memory + persisted) | Phase 5 |
| `GET` | `/api/runs/{run_id}` | One run (poll while running) | Phase 5 |
| `GET` | `/api/runs/{run_id}/log` | SSE stream of run logs | Phase 5 |
| `GET` | `/api/schedule` | Current schedule state | Phase 5 |
| `POST` | `/api/schedule` | Enable / disable the scheduler | Phase 5 |
| `GET` | `/api/watched` | Watched folders + watcher health | Phase 5 |
| `POST` | `/api/watcher/refresh` | Force supervisor re-read | Phase 5 |

### 5.5 Errors ledger

| Method | Path | Purpose | Phase |
|--------|------|---------|-------|
| `GET` | `/api/errors` | Ledger rows + folder counts | Phase 5 |
| `GET` | `/api/errors/file` | Download raw error-text artifact | Phase 5 |
| `GET` | `/api/errors/folder-file` | Download one folder's full error text | Phase 5 |
| `POST` | `/api/errors/clear` | Delete ledger rows (per folder or all) | Phase 5 |

### 5.6 Processed files (browse, flag, resend, bulk)

| Method | Path | Purpose | Phase |
|--------|------|---------|-------|
| `GET` | `/api/processed-files` | Browse with filters + pagination | Phase 5 (1.2) |
| `GET` | `/api/processed-files/flagged` | Same, with resend_flag info | Phase 5 (1.2) |
| `POST` | `/api/processed-files/{id}/resend` | Flag a row for resend | Phase 5 |
| `POST` | `/api/processed-files/resend-batch` | Flag many rows | Phase 5 (1.8) |
| `POST` | `/api/processed-files/clear-flags` | Clear every resend flag | Phase 5 (1.8) |

### 5.7 Maintenance (bulk ops)

| Method | Path | Purpose | Phase |
|--------|------|---------|-------|
| `POST` | `/api/maintenance/clear-processed` | Bulk-delete processed rows | Phase 5 |
| `POST` | `/api/maintenance/mark-processed` | Record a single file | Phase 5 |
| `POST` | `/api/maintenance/set-all-active` | Activate every folder | Phase 5 |
| `POST` | `/api/maintenance/set-all-inactive` | Deactivate every folder | Phase 5 |
| `POST` | `/api/maintenance/clear-queued-emails` | Drop queued report emails | Phase 5 |
| `POST` | `/api/maintenance/remove-inactive` | Delete inactive folders | Phase 5 |
| `POST` | `/api/maintenance/mark-all-processed` | Mark every active folder's files | Phase 5 |
| `POST` | `/api/maintenance/export-processed` | Write a CSV report | Phase 5 |
| `GET` | `/api/maintenance/download` | Download a report | Phase 5 |

### 5.8 Backups

| Method | Path | Purpose | Phase |
|--------|------|---------|-------|
| `GET` | `/api/backups` | List timestamped backup files | Phase 5 |
| `POST` | `/api/backup/create` | Snapshot the active DB | Phase 5 |
| `POST` | `/api/backup/restore` | Restore a named backup | Phase 5 |
| `GET` | `/api/backup/download` | Download a backup file | Phase 5 |

### 5.9 Request conventions

- All `POST` endpoints take arguments as **query parameters** (not
  JSON body), because they mirror the desktop GUI's dialog handlers
  one-for-one and FastAPI's default form encoding is more
  ergonomic for that shape. The SPA serializes `params` into the
  URL in `webapp/static/api.js::api()`.
- Successful `POST` responses are usually `204 No Content` or a
  small `{ok: true, ...}` envelope. `POST /api/import` is the
  one exception — it returns the full import summary
  (`{ok, summary, duration_seconds}`).
- `GET /api/runs/{run_id}/log` is **Server-Sent Events** (text/event-stream),
  not JSON. Each event is `data: {line}\n\n`; the connection
  closes when the run finishes.
- Errors are returned as FastAPI `HTTPException` with a
  `detail` string. The SPA's `api()` wrapper reads
  `body.detail` and re-throws as a JS Error with `.status`.

---

## 6. Static UI

### 6.1 File inventory

| File | Purpose | Size |
|------|---------|------|
| `webapp/static/index.html` | Dashboard shell + 14 cards | 798 lines |
| `webapp/static/style.css` | Theme + responsive rules + dialog styles | 998 lines |
| `webapp/static/app.js` | Renderers + event handlers + state | 2,000+ lines |
| `webapp/static/api.js` | `fetch()` wrapper with bearer-token injection | 143 lines |
| `webapp/static/helpers.js` | Pure helpers (esc, dialogs, formatters) | 220 lines |
| `webapp/static/templates.js` | HTML template fragments for the cards | 313 lines |

Total: **4,716 LOC**, no bundler, no framework, no build step. The
dashboard loads `api.js` then `helpers.js` then `templates.js`
then `app.js` in document order; each defines globals that the
next picks up.

### 6.2 Cards (one per dashboard section)

| Card | Anchor in `index.html` | Owns |
|------|------------------------|------|
| Import configuration | `.import-card` | DB file picker + base-dir input + import button (live timer, Phase 1.6) |
| Configured folders | `.folders-card` | Folder table + filter + add / refresh + Recently deleted (Phase 6.4) |
| Folder editor (modal) | `#folder-modal` | Full `FolderEditSchema` form + per-format plugin UI + "Copy from..." picker (Phase 1.4) |
| Format plugin settings (audit) | `.plugin-audit-card` | Read-only view of every folder's per-format settings |
| Watching | `.watching-card` | Watched folders + last tick / last run / last error per row |
| Errors | `.errors-card` | Ledger table + folder dropdown + clear + raw-file download |
| Processed files | `.processed-files-card` | Search + date range + folder filter + bulk select + Load More + resend flag (Phase 1.2 / 1.8) |
| Runs | `.runs-card` | Recent runs + click-to-poll detail + SSE log stream |
| Schedule | `.schedule-card` | Interval input + enable / disable toggle |
| Maintenance | `.maintenance-card` | 5 bulk ops + confirmation dialogs |
| Settings | `.settings-card` | Editable app settings (email / FTP / reporting / paths) |
| Backups | `.backups-card` | Snapshot list + create / restore / download |
| Diagnostics (modal) | `#diagnostics-modal` | Self-test snapshot with banner + recent runs + Copy JSON (Phase 1.5) |
| Shortcuts help (modal) | `#shortcuts-modal` | Keyboard-shortcut cheat sheet |

### 6.3 Keyboard shortcuts

| Combo | Action |
|-------|--------|
| `Ctrl/Cmd+Enter` | Click **Run all folders** (no-op while a run is in flight) |
| `Ctrl/Cmd+R` | Refresh every card |
| `Ctrl/Cmd+I` | Focus the Import button |
| `Ctrl/Cmd+F` | Focus the Folders search box |
| `Ctrl/Cmd+P` | Focus the Processed-files search box |
| `?` | Open the shortcuts modal |
| `Esc` | Close the open modal (or folder panel) |

Shortcuts that would steal text input (`R`, `I`, `F`, `P`)
are skipped while the event target is an input / textarea /
select / `contentEditable`.

### 6.4 Confirmation dialogs

All destructive actions go through `confirmDialog(message, opts)`
(`webapp/static/helpers.js`) — a Promise-based, non-blocking,
aria-correct replacement for `window.confirm`. The function
honours `globalThis.__bfsTestStubs.confirmDialog` / `.alertDialog`
so JSDOM tests inject their own resolver without rendering an
in-page dialog.

### 6.5 Theming

`webapp/static/style.css` is a single hand-rolled stylesheet with
CSS custom properties for the brand palette. One `@media (max-width:
900px)` rule resizes the layout for narrow windows. No CSS
framework, no preprocessor.

---

## 7. Configuration & Environment

### 7.1 Environment variables

The complete list of env vars the webapp reads (all consumed in
`webapp/config.py::Settings.from_env` unless noted):

| Variable | Default | Purpose | Phase |
|----------|---------|---------|-------|
| `BFS_BASE_DIR` | `./data` | Root that all configured folder paths resolve against | webapp-pivot |
| `BFS_DATA_DIR` | `./data/config` | Where `folders.db` + backups + run logs live | webapp-pivot |
| `BFS_HOST` | `127.0.0.1` | uvicorn bind host (Phase 6.1: localhost by default) | Phase 6.1 |
| `BFS_PORT` | `8000` | uvicorn bind port | webapp-pivot |
| `BFS_API_TOKEN` | (empty) | Bearer token required for every API endpoint when set | Phase 6.2 |
| `BFS_SCHEDULE_INTERVAL_SECONDS` | `900` | Automatic-run interval (15 min) | Phase 5 |
| `FOLDERS_DELETED_TTL_DAYS` | `30` | Soft-delete restore window (clamped 1-365) | Phase 6.4 |
| `FOLDERS_DELETED_TRIM_INTERVAL_SECONDS` | `3600` | Trim-supervisor poll interval | Phase 6.4 |
| `AS400_USERNAME` / `AS400_PASSWORD` / `AS400_ADDRESS` | (empty) | AS400 credentials for db2ssh adapter | legacy |
| `PYTHONUNBUFFERED` | `1` (Dockerfile) | Docker logging flush | Dockerfile |

### 7.2 `webapp/config.py::Settings`

The `Settings` dataclass is the single source of truth for the
webapp's runtime config. `Settings.from_env()` reads the env
above; `webapp/main.py::create_app(settings=...)` accepts an
explicit `Settings` for tests. Fields are typed and validated
(`BFS_PORT` is parsed as `int`, `FOLDERS_DELETED_TTL_DAYS` is
clamped to `[1, 365]`).

### 7.3 `.env.example`

`/.env.example` documents the AS400 credentials used by the
db2ssh adapter for database-dependent converters. `.env` itself
is gitignored; `.env.docker` is a working docker-deploy template
in the same gitignored set.

### 7.4 Docker compose

`docker-compose.yml` mounts `./data` as `/data` (the
`BFS_BASE_DIR` volume), sets `BFS_DATA_DIR=/data/config`, and
binds `127.0.0.1:8000:8000` (Phase 6.1). To enable bearer-token
auth, the operator uncomments the `BFS_API_TOKEN` line and
restarts; to enable remote access, the operator changes the
`ports:` line to `"8000:8000"` and restarts.


---

## 8. Data Model (webapp-owned tables)

The webapp adds three first-class tables to the engine's existing
schema. The migration policy and version scheme are unchanged
(`docs/MIGRATION_DESIGN.md`); each table has its own migration
step.

### 8.1 `dispatch_errors` — the error ledger

**Owner:** `webapp/errors.py::ErrorLedger`
**Migration:** added in the Phase 5 webapp-pivot schema bump.
**Used by:** Phase 5 (ledger write), Phase 5.5 (major/minor
classification), the diagnostics endpoint (24h failure count),
the errors card (browse + filter + clear).

Schema (verified by `webapp/errors.py`):

```sql
CREATE TABLE dispatch_errors (
    id INTEGER PRIMARY KEY,
    folder_id INTEGER,                 -- nullable: pre-config errors
    folder_name TEXT,                 -- resolved at write time
    error_type TEXT,                   -- exception class name
    error_message TEXT,
    stack_trace TEXT,
    severity TEXT,                     -- 'major' | 'minor' (Phase 5.5)
    timestamp TEXT                     -- ISO 8601 UTC
);
CREATE INDEX idx_dispatch_errors_folder ON dispatch_errors(folder_id);
CREATE INDEX idx_dispatch_errors_ts ON dispatch_errors(timestamp);
```

The ledger is populated by `dispatch/error_handler.py::ErrorHandler`,
which the webapp wires into every run via `webapp/runner.py`. The
ledger is deduplicated: consecutive identical `(folder_id,
error_type, error_message)` rows within a short window collapse
into one (`ErrorLedger.record` keeps a fingerprint + last-seen
counter).

### 8.2 `folders_deleted` — soft-delete tombstones

**Owner:** `webapp/routers/folders.py` (`SoftDeleteTrimSupervisor`)
**Migration:** added in Phase 6.4.
**Used by:** Phase 6.4 (DELETE → tombstone + restore window).

Schema:

```sql
CREATE TABLE folders_deleted (
    folder_id INTEGER PRIMARY KEY,    -- original id, preserved on restore
    folder_row TEXT NOT NULL,         -- full JSON snapshot of folders row
    deleted_at TEXT NOT NULL,         -- ISO 8601 UTC
    expires_at TEXT NOT NULL          -- deleted_at + FOLDERS_DELETED_TTL_DAYS
);
CREATE INDEX idx_folders_deleted_expires ON folders_deleted(expires_at);
```

`DELETE /api/folders/{folder_id}` moves the row from `folders`
to `folders_deleted` with the JSON snapshot; the trim supervisor
purges rows where `expires_at < now()` every
`FOLDERS_DELETED_TRIM_INTERVAL_SECONDS`.

### 8.3 `runs` — persisted run history

**Owner:** `webapp/history.py::RunHistory`
**Migration:** added in Phase 5.
**Used by:** `GET /api/runs` (merged with the in-memory ring
buffer in `RunStore`).

Schema:

```sql
CREATE TABLE runs (
    run_id TEXT PRIMARY KEY,          -- UUID v4 string
    started_at TEXT NOT NULL,
    finished_at TEXT,
    duration_seconds REAL,
    status TEXT,                       -- 'running' | 'success' | 'failed' | 'cancelled'
    folders_json TEXT,                -- [{folder_id, alias, status, files_processed, files_failed, error}]
    trigger TEXT                       -- 'manual' | 'schedule' | 'watcher' | 'resend'
);
CREATE INDEX idx_runs_started ON runs(started_at);
```

`RunHistory` persists runs on completion; the in-memory
`RunStore` keeps the last N (default 50) for fast polling while
in flight. The two are merged by `run_id` in
`webapp/routers/runs.py::list_runs`.

### 8.4 Engine tables the webapp reads

The webapp reads from these engine-owned tables but does not
modify their schema:

- `folders` — folder configuration; webapp reads / writes via
  `webapp/folder_schema.py` (Pydantic `FolderEditSchema`) +
  `webapp/routers/folders.py`.
- `processed_files` — the idempotency ledger; webapp reads via
  `webapp/resend.py` for the browse + flag + bulk-clear views,
  and writes the `resend_flag` column (added in a migration
  for Phase 5).

---

## 9. Background Services

### 9.1 `webapp/runner.py::RunStore` (the worker thread)

A thread-safe singleton (`_run_store`) that owns:

- A ring buffer of recent runs (deque of `RunRecord`).
- A dict of in-flight runs keyed by `run_id`.
- A `threading.Thread` started lazily on the first `enqueue`.
- A `threading.Condition` that signals the worker.

Every run (manual trigger via `POST /api/run`, schedule tick,
watcher tick, resend) calls `enqueue(run_request)`. The worker
calls `dispatch.orchestrator.DispatchOrchestrator.process(...)`
inside a try/except, writes the result to `RunHistory`, and
updates the in-memory record. The singleton is intentionally
global so the scheduler and watcher (in their own threads) can
find it.

### 9.2 `webapp/scheduler.py::Scheduler`

Interval-based automatic-run loop. Configuration:

- `interval_seconds` — read from `BFS_SCHEDULE_INTERVAL_SECONDS`,
  default 900.
- `enabled` — read from the `settings` table
  (`schedule_enabled` key); toggleable at runtime via
  `POST /api/schedule`.

When enabled, the loop calls `_run_store.enqueue({"trigger":
"schedule", "scope": "all_folders"})` every interval. The run
record carries the `trigger: "schedule"` tag so `GET /api/runs`
can distinguish operator-triggered runs from automatic ones
(`runs_triggered_today` counter in the diagnostics endpoint).

### 9.3 `webapp/watcher.py::WatcherSupervisor`

One supervisor thread that polls the `folders` table every 30s
for `watch_enabled = 1` rows, and starts / stops one
`FolderWatcher` thread per watched folder. Each
`FolderWatcher`:

- Polls its input directory every `watch_interval_seconds`
  (clamped to a 5-second minimum, per the watching card hint).
- Enumerates candidate files (everything matching the folder's
  extension filter).
- Checks the processed-files ledger for already-processed
  content (`ProcessedFilesTracker`).
- Enqueues a run for the new files via `RunStore.enqueue`
  (`trigger: "watcher"`).
- Records `last_tick_at` / `last_run_id` / `last_error` on
  the folder row (Phase 5).

The supervisor exposes `start()` / `stop()` symmetric with the
lifespan handler in `webapp/main.py`.

### 9.4 `webapp/routers/folders.py::SoftDeleteTrimSupervisor` (Phase 6.4)

A periodic trim job for `folders_deleted` rows. Started in the
lifespan handler when `FOLDERS_DELETED_TRIM_INTERVAL_SECONDS > 0`.
Polls every N seconds (default 3600) and deletes rows where
`expires_at < now()`. Exposes `start()` / `stop()` matching
the watcher supervisor's contract.

---

## 10. Authentication & Authorization

### 10.1 Phase 6.2 — bearer-token auth (single-user)

The webapp uses a single-user bearer-token model that matches the
spec's intent ("single-user local-first" — `PROJECT_SPEC.md`
§3.4). There is **no user table**, **no session store**, **no
JWT**, **no refresh logic** — just a long-lived shared secret read
from the env.

Configuration:

- `BFS_API_TOKEN=...` enables auth.
- `BFS_API_TOKEN=` (empty) disables auth — every endpoint is
  reachable without a header.

Mechanics (`webapp/routers/_deps.py::verify_api_token`):

1. The dependency is applied at the `include_router` layer in
   `webapp/main.py::create_app`. Every router other than the
   static mount carries the dependency.
2. The dependency checks the request path against a hard-coded
   exempt list (`/api/health`, `/docs`, `/openapi.json`,
   `/redoc`). Exempt endpoints pass through without checking
   the header.
3. For all other paths: if `BFS_API_TOKEN` is set, the
   dependency compares the `Authorization: Bearer <token>`
   header to the env value with a constant-time comparison. A
   mismatch returns `401`. An empty / missing header returns
   `401`.

The SPA stores the token in `localStorage["bfs_api_token"]` on
the first 401 (`webapp/static/api.js` listens for the
`bfs:api-401` custom event the fetch wrapper dispatches). A
login prompt in the topbar captures the token and stores it.
The fetch wrapper re-reads `localStorage` on every request.

### 10.2 What's NOT auth

- No CSRF protection. The bearer token is the auth; cross-origin
  requests without the token get 401s.
- No rate limiting. Single-user local-first deployment does not
  need it.
- No audit log. Single operator on a single host; no "who did
  what when" to capture.
- No password rotation flow. The token is rotated by restarting
  the webapp with a new env value.

---

## 11. Observability

### 11.1 Diagnostics endpoint

`GET /api/diagnostics` returns a single payload covering
platform, app, paths, database, runtime, modules, backends,
recent runs, and 24h failure count. The payload shape:

```json
{
  "platform": {"python": "3.12.x", "os": "Linux", "...": "..."},
  "app": {"version": "0.1.0", "title": "Batch File Sender"},
  "paths": {
    "base_dir": "/data",
    "data_dir": "/data/config",
    "database_path": "/data/config/folders.db",
    "database_exists": true,
    "database_size_bytes": 75648000,
    "backups_dir": "/data/config/backups"
  },
  "database": {"version": 51, "schema_repaired_at": "..."},
  "runtime": {
    "active_runs": 0,
    "scheduler_enabled": true,
    "scheduler_interval_seconds": 900,
    "watched_folders": 3,
    "queued_emails": 0
  },
  "backends_health": {
    "smtp": {"ok": false, "latency_ms": 2.0, "error": "..."},
    "ftp": {"ok": true, "latency_ms": 87.3},
    "copy": [{"folder_id": 1, "alias": "ACME", "ok": true, "error": null}]
  },
  "modules": {"imported_ok": 27, "failed": []},
  "recent_runs": [...],
  "recent_run_failures_24h": 1,
  "ok": false,
  "warnings": ["SMTP server unreachable"]
}
```

`ok` is `true` only if **all** of:

- every expected module imports cleanly,
- no run failed in the last 24h,
- no watcher is in a bad state,
- SMTP / FTP probes are either up or "not configured" (down
  with an error is a warning, not a module failure).

`warnings` is the human-readable summary. The SPA's Diagnostics
modal renders a green banner when `ok: true`, amber otherwise.

### 11.2 Per-probe characteristics

| Probe | Method | Timeout | Phase |
|-------|--------|---------|-------|
| Module import | `importlib.import_module` inside `_safe()` | none (each wrapped to swallow import errors) | Phase 5 |
| DB schema version | `SELECT version FROM schema_version` | none | Phase 5 |
| SMTP TCP open | `socket.create_connection` with 2s timeout | 2s | Phase 6.3 |
| FTP TCP open | `socket.create_connection` with 2s timeout | 2s | Phase 6.3 |
| Copy destination | `Path.exists()` + `Path.is_dir()` | none (stat) | Phase 6.3 |
| Recent runs | `RunStore` + `RunHistory` | none | Phase 5 |
| 24h failure count | `SELECT COUNT(*) FROM runs WHERE status='failed' AND finished_at > now - 24h` | none | Phase 5 |

### 11.3 Run log streaming

`GET /api/runs/{run_id}/log` is a Server-Sent Events endpoint
(`text/event-stream`) that streams the structured-logging output
of one in-flight or completed run. Each event is
`data: {line}\n\n`; the connection closes when the run finishes.
The SPA's Runs card renders the stream into a scrolling pane.

### 11.4 Operator-facing runbook

For each of the six most common operator failure modes ("a run
failed", "files aren't being picked up", "SMTP/FTP
unreachable", "I deleted a folder by accident", "how do I
verify the system is healthy", "the database looks weird"),
`docs/runbook.md` gives a 30-second `curl` recipe. The runbook
is exercised by `tests/webapp/test_runbook_endpoints_referenced`
(currently skipped pending this spec's landing — see §16).

---

## 12. Deployment

### 12.1 Docker (canonical)

`docker-compose.yml` builds from `Dockerfile` (python:3.12-slim),
mounts `./data` as `/data`, sets the standard env vars, and
binds `127.0.0.1:8000:8000`. Operators drop incoming files under
`./data/<relative-path>` matching the imported folder layout.

Build + run:

```bash
docker compose up --build      # http://localhost:8000
docker compose down            # stop (data persists in ./data)
```

To enable bearer-token auth, uncomment the `BFS_API_TOKEN` line
in `docker-compose.yml` and restart. To enable remote access,
change `ports: - "127.0.0.1:8000:8000"` to `"8000:8000"` (and
set a token).

### 12.2 Local venv (development)

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
BFS_BASE_DIR=./data python -m webapp.main
# or
BFS_BASE_DIR=./data uvicorn webapp.main:app --host 0.0.0.0 --port 8000
```

`python -m webapp.main` binds `127.0.0.1:8000` (Phase 6.1) and
disables auth (`BFS_API_TOKEN` empty). The `uvicorn` invocation
is the escape hatch for remote access during development.

### 12.3 Reverse-proxy (production remote access)

The recommended shape for non-localhost deployments:

```
nginx / Caddy  -->  http://127.0.0.1:8000 (webapp, bearer-token enabled)
```

The reverse proxy terminates TLS and forwards to the webapp on
localhost. The webapp itself never sees TLS, never exposes
itself directly, and remains bound to localhost on the back end.
BFP does not provide TLS termination itself (deferred per
`docs/architecture/webapp-gap-audit.md` §5.2).

### 12.4 Database path conventions

| Path | Env var | Purpose |
|------|---------|---------|
| `/data/config/folders.db` (container) / `./data/config/folders.db` (host) | `BFS_DATA_DIR` | Active DB |
| `/data/config/backups/...` | derived | Timestamped snapshots |
| `/data/<relative-path>/...` | derived (`BFS_BASE_DIR`) | Imported folder input paths |
| `/data/config/errors/...` | derived | Per-folder raw error-text artifacts |
| `/data/config/logs/...` | derived | Structured-logging files |


---

## 13. Testing Strategy

### 13.1 Test inventory

| Layer | Files | Lines | Marker |
|-------|-------|-------|--------|
| Python webapp tests | 21 files in `tests/webapp/` | ~5,800 | (run with the default pytest) |
| JS unit / DOM tests | 4 files in `tests/webapp/` | ~2,400 | (run with `node --test`) |
| Engine tests (shared regression net) | `tests/unit/dispatch/`, `tests/unit/backend/`, `tests/unit/core/`, `tests/convert_backends/` | ~10,000 | (run with the default pytest) |

The 21 Python files are:

`test_api.py`, `test_auth.py`, `test_backup.py`,
`test_config.py`, `test_converters.py`,
`test_database_repair.py`, `test_diagnostics.py`,
`test_errors.py`, `test_folder_edit.py`, `test_folder_run.py`,
`test_history.py`, `test_importer.py`, `test_maintenance.py`,
`test_paths.py`, `test_preflight.py`, `test_preview.py`,
`test_resend.py`, `test_runner.py`, `test_scheduler.py`,
`test_soft_delete.py`, `test_watcher.py`.

The 4 JS files are:

`api.test.js` (the bearer-token fetch wrapper),
`helpers.test.js` (DOM-free helpers + dialog stubs),
`templates.test.js` (HTML escape + folder-id lookup),
`dom.test.js` (JSDOM rendering for every card + modal +
keyboard-shortcut + bulk-select path).

### 13.2 Running

```bash
# Python webapp tests (run with the rest of the engine suite)
pytest tests/webapp/ -n auto

# JS tests (Node 18+; no bundler, no JSDOM install needed for
# three of the four files; dom.test.js requires JSDOM)
node --test tests/webapp/api.test.js tests/webapp/helpers.test.js tests/webapp/templates.test.js
node --test tests/webapp/dom.test.js

# Full suite
make test-parallel
```

### 13.3 Test conventions

- **No Qt.** PySide6 / PyQt5 references are gone; the webapp's
  test surface is FastAPI's `TestClient` + Node's built-in test
  runner.
- **No bundler.** JS tests run against the source files directly
  via `require()` (`module.exports` at the bottom of each
  static file).
- **JSDOM for DOM tests only.** `api.test.js`, `helpers.test.js`,
  and `templates.test.js` are pure-Node. `dom.test.js` uses
  JSDOM (`package.json` dependency) to render the cards.
- **Spec parity.** Every implementation spec
  (`webapp-phase-{5,6,7}.md`) ships with its own tests and
  marks them off in the spec's §6 (test cases).
- **Runbook parity.** The runbook's endpoints table is
  referenced by a planned `test_runbook_endpoints_referenced`
  test that walks `docs/runbook.md` and asserts every URL is
  defined in `webapp/routers/`. Currently skipped pending this
  spec landing; tracked in §16.

### 13.4 Anti-patterns called out in tests

- **Bare `MagicMock()` without `spec=`** — caught by the
  global test hygiene plugin (`tests/conftest_magicmock_plugin.py`).
- **Silent `except: pass`** — caught by the project-wide grep
  for `except Exception: pass` patterns in CI.
- **Magic padding (`"00" + x`)** — caught by the project-wide
  grep for `zfill` / `f"{x:02d}"` pattern enforcement.

---

## 14. Roadmap & Phase Status

The webapp's lifecycle is broken into five named phases; four are
landed, two are pending.

| Phase | Name | Status | Spec | Landed commit / date |
|-------|------|--------|------|---------------------|
| **Pivot** | webapp-pivot (drop Qt GUI, ship FastAPI + SPA) | Landed | this doc + project spec §3.7 | `9864dc7e5` (2026-08-04) |
| **Roadmap** | Strategic sequencing (near/mid-term, gap-3.x deferred, triggers, open decisions) | Reference | [`ROADMAP.md`](./ROADMAP.md) | — |
| **Phase 5** | Observability (run history, error ledger, diagnostics, processed-files browse, resend, schedule, watcher) | Landed | [`webapp-phase-5-observability.md`](./webapp-phase-5-observability.md) | (multiple, 2026-08-17) |
| **Phase 6** | Production hardening (localhost-by-default, bearer-token, backend health probe, soft-delete) | Landed | [`webapp-phase-6-production-hardening.md`](./webapp-phase-6-production-hardening.md) | (multiple, 2026-08-18) |
| **Phase 7** | Operator confidence + desktop retirement (schema-repair wart fix, runbook, `plans/` + desktop-packaging cleanup) | Landed | [`webapp-phase-7-operator-confidence.md`](./webapp-phase-7-operator-confidence.md) | (multiple, 2026-08-18) |
| **Phase 7b** | `interface/` retirement (delete the 3,819-line Qt-free orphan + the 33,000 lines of dependent tests) | **7b.3 in progress** (7b.1+7b.2 landed) | [`webapp-phase-7b-interface-retirement.md`](./webapp-phase-7b-interface-retirement.md) | `2f29cca57` (7b.2) |
| **Phase 8** | Pipeline redesign (move `dispatch/` under `webapp/`, async-native, drop accreted complexity) | Design spec, pending | [`webapp-phase-8-pipeline-redesign.md`](./webapp-phase-8-pipeline-redesign.md) | TBD |

### 14.1 What's next

The next concrete work is **Phase 7b**, scoped to three commits
each independently revertable. The spec
([`webapp-phase-7b-interface-retirement.md`](./webapp-phase-7b-interface-retirement.md))
captures the file list, the verification commands, and the
rollback story.

Phase 8 is the longer-term redesign. **This spec does not pre-judge
the design decisions** — Phase 8's spec is a design document
that ends with a numbered list of decisions to be made in order;
no decision is pre-made.

### 14.2 What is intentionally deferred

Per `docs/architecture/webapp-gap-audit.md` §5.3:

| Item | Rationale for deferral |
|------|------------------------|
| TLS termination (gap-2.2) | Meaningful only after remote access + bearer-token (already shipped). Default: reverse proxy. |
| Audit log (gap-2.5) | Single-user single-host; no "user" to attribute to. |
| Backup encryption (gap-2.7) | Real risk only if backups are copied off-machine; today they're on the same volume. |
| Mobile responsive (gap-2.8) | Operator persona is at a workstation. |
| Playwright (gap-2.9) | JSDOM + python tests cover the surface; revisit when the static UI stabilizes. |
| Plug-in hot-reload (gap-2.10) | Meaningful when third-party plugin authors exist. |

---

## 15. Risk Assessment

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| **Bearer-token leak via `localStorage`** | Med | Med | XSS in the dashboard would expose the token. Mitigation: no third-party scripts in `index.html`; CSP header recommended (gap-2.5 / 2.10 deferred). |
| **Database corruption mid-run** | Low | High | Phase 5 writes `runs` rows on completion; a crash mid-run leaves the row in `status: 'running'` until the next open + reconcile. Backup / restore workflow covers long-term. |
| **Watcher tick flooding the run store** | Med | Med | Watcher ticks enqueue one run per tick (not one per file); the run store serializes them; `BFS_SCHEDULE_INTERVAL_SECONDS` + `watch_interval_seconds` clamp to 5s minimum. |
| **Scheduler + watcher colliding on the same folder** | Med | Low | Both enqueue via the run store, which serializes; the processed-files ledger prevents double-processing at the file level. |
| **Long-running import blocking the asyncio loop** | Low | Low | Import is a single FastAPI endpoint (`POST /api/import`) that runs synchronously on the event loop; documented in the runbook ("import can take N seconds for large DBs"). Phase 5.7 added `duration_seconds` to the response. |
| **`dispatch/` moving under `webapp/` breaks downstream forks** | Med | High | Phase 8 is a separate, multi-month effort. The webapp's current `webapp/runner.py` integration is a single line (`dispatch.orchestrator.DispatchOrchestrator`); moving it under `webapp/` does not change the call site semantically. |
| **Phase 7b breaks the engine regression net** | Low | High | `tests/unit/interface/` is 25K lines covering engine behaviors already exercised by `tests/unit/dispatch/` + `tests/unit/backend/` + `tests/unit/core/`. Phase 7b's spec enumerates the verification commands that prove no behavior is lost. |
| **Operator forgets to rotate `BFS_API_TOKEN`** | Low | Low | No automated rotation; documented in §10.2. |

---

## 16. Open Questions

1. **Phase 7b sequence.** Does the implementation spec need a
   final review pass before merge? The spec was written
   2026-08-18; the implementation hasn't started yet.
2. **Phase 8 trigger.** Is the pipeline redesign conditional on
   a specific feature request, or is it a proactive
   simplification? The current spec frames it as the latter;
   the design spec doesn't pin a date.
3. **Runbook-parity test.** Should the planned
   `test_runbook_endpoints_referenced` (currently skipped
   pending this spec) be enabled in the same change that
   lands this spec, or as a follow-up?
4. **Static-SPA build step.** Is the no-bundler posture still
   the right tradeoff, or do the cards warrant a lightweight
   templating layer (htmx / Alpine.js / Preact)? The current
   answer is "no, the dashboard is settled"; revisit when
   the static UI starts moving weekly.
5. **Multi-host clustering.** Will the single-host posture ever
   expand to multi-host (e.g. one webapp reading N base-dirs)?
   Today: no. The spec's intent ("single-user local-first")
   precludes it.

---

## 17. Appendix

### 17.1 Cross-references

| Topic | This doc | Primary reference |
|-------|----------|-------------------|
| Product intent (5 capabilities) | §1 | [`PROJECT_SPEC.md` §3.2](./PROJECT_SPEC.md) |
| Non-functional requirements | §3.3, §10, §11 | [`PROJECT_SPEC.md` §3.4](./PROJECT_SPEC.md) |
| Release channels (Docker + venv) | §12 | [`PROJECT_SPEC.md` §3.5](./PROJECT_SPEC.md) |
| Plugin model (converters / backends) | §8.4 | [`docs/design/PLUGIN_API.md`](../docs/design/PLUGIN_API.md), [`docs/PLUGIN_DESIGN.md`](../docs/PLUGIN_DESIGN.md) |
| Pipeline stages (validator → splitter → converter → tweaker → send) | §3.3 | [`docs/design/PROCESSING_PIPELINE.md`](../docs/design/PROCESSING_PIPELINE.md), [`docs/PROCESSING_DESIGN.md`](../docs/PROCESSING_DESIGN.md) |
| Database schema and migrations | §8 | [`docs/design/DATABASE_SCHEMA.md`](../docs/design/DATABASE_SCHEMA.md), [`docs/MIGRATION_DESIGN.md`](../docs/MIGRATION_DESIGN.md) |
| Operator workflows ("if X, do Y") | §11.4 | [`docs/runbook.md`](../docs/runbook.md) |
| Production readiness (gap-2.x) | §3.3, §14.2 | [`docs/architecture/webapp-gap-audit.md`](../docs/architecture/webapp-gap-audit.md) |
| Phase 5 (observability) | §14 | [`specs/webapp-phase-5-observability.md`](./webapp-phase-5-observability.md) |
| Phase 6 (hardening) | §7, §10, §11.1 | [`specs/webapp-phase-6-production-hardening.md`](./webapp-phase-6-production-hardening.md) |
| Phase 7 (operator confidence + desktop retirement) | §14 | [`specs/webapp-phase-7-operator-confidence.md`](./webapp-phase-7-operator-confidence.md) |
| Phase 7b (`interface/` retirement) | §14 | [`specs/webapp-phase-7b-interface-retirement.md`](./webapp-phase-7b-interface-retirement.md) |
| Phase 8 (pipeline redesign) | §4.4, §14 | [`specs/webapp-phase-8-pipeline-redesign.md`](./webapp-phase-8-pipeline-redesign.md) |
| Project-wide conventions (imports, anti-patterns) | §4, §13 | [`AGENTS.md`](../AGENTS.md) |

### 17.2 Glossary

| Term | Meaning |
|------|---------|
| **Webapp** | The FastAPI + static-SPA application under `webapp/`. The only operator surface in the project as of 2026-08-04. |
| **Engine** | The processing code under `dispatch/`, `backend/`, `core/`. Reused unchanged by the webapp. |
| **Run** | One invocation of the processing pipeline for a folder (or all folders); tracked in `runs`. |
| **Tick** | One polling cycle of `FolderWatcher`; enqueues a run if new files are present. |
| **Ledger row** | One row in `dispatch_errors` (or `runs`, or `processed_files`). |
| **Tombstone** | A row in `folders_deleted` representing a soft-deleted folder. |
| **Bearer token** | The long-lived `BFS_API_TOKEN` env-var secret used by Phase 6.2 auth. Not a JWT. |
| **Restore window** | `FOLDERS_DELETED_TTL_DAYS`, default 30; the time a soft-deleted folder can be restored before being purged. |
| **Local-first** | The deployment posture: single host, default bind `127.0.0.1`, no inbound network surface, no cloud sync. |
| **Base-dir** | The `BFS_BASE_DIR` root that all configured folder paths resolve against. Legacy absolute paths are stripped to relative paths at import time. |
| **Processed-files ledger** | The per-(folder, content) idempotency record in `processed_files`. |
| **Golden file** | A recorded expected output used by parity tests to detect regressions. |
| **Phase** | A named scope of work with its own spec. Each implementation spec lands as a series of individually-revertable commits. |

### 17.3 File inventory (single-screen view of `webapp/`)

```
webapp/
|-- __init__.py
|-- main.py                  263  # FastAPI factory + lifespan
|-- config.py                221  # Settings (env-driven)
|-- paths.py                 139  # Path resolution + base-dir semantics
|-- database.py              182  # DB open + schema-version check
|-- history.py               221  # RunHistory (persisted runs)
|-- runner.py                718  # RunStore (singleton + worker thread)
|-- scheduler.py             301  # Scheduler (interval-based runs)
|-- watcher.py               393  # WatcherSupervisor + FolderWatcher
|-- errors.py                440  # ErrorLedger (dispatch_errors)
|-- diagnostics.py              603  # collect_diagnostics()
|-- importer.py              234  # legacy folders.db import + rebasing
|-- converters_api.py        398  # dynamic converter enumeration
|-- resend.py                260  # list_processed_files + bulk flag/clear
|-- preview.py                73  # parse-only EDI preview
|-- maintenance.py           383  # bulk destructive ops + CSV export
|-- settings_api.py          171  # editable settings (settings table)
|-- backup.py                130  # timestamped snapshots + restore + download
|-- folder_schema.py         566  # Pydantic FolderEditSchema
|-- routers/
|   |-- __init__.py           28
|   |-- _deps.py             180  # verify_api_token (Phase 6.2)
|   |-- _helpers.py          158  # shared router helpers
|   |-- system.py            156  # /api/{health,config,diagnostics,preflight,preview/edi}
|   |-- imports.py            93  # /api/import
|   |-- folders.py           565  # /api/folders/* + soft-delete
|   |-- settings_api.py       87  # /api/settings
|   |-- runs.py              191  # /api/{run,resend,runs} + SSE log
|   |-- schedule.py           41  # /api/schedule
|   |-- watcher.py            47  # /api/watched + refresh
|   |-- errors.py            144  # /api/errors/*
|   |-- processed.py         176  # /api/processed-files/*
|   |-- maintenance.py       235  # /api/maintenance/*
|   '-- backups.py            85  # /api/backup/*
'-- static/
    |-- index.html           798  # 14 cards + 2 modals
    |-- style.css            998  # theme + responsive + dialogs
    |-- app.js             ~2000  # renderers + event handlers + state
    |-- api.js               143  # fetch wrapper + bearer token
    |-- helpers.js           220  # esc, folderIdForPath, confirmDialog
    '-- templates.js         313  # HTML fragments per card
```

### 17.4 Version constraints

- **Python:** 3.11+ per `pyproject.toml` `requires-python = ">=3.11"`.
  Dockerfile pins to 3.12.
- **FastAPI:** >= 0.115.0; uvicorn >= 0.30.0.
- **SQLAlchemy:** >= 1.4.49.
- **Node:** 18+ for the JS tests (built-in `node --test`).
- **No Qt.** PySide6 / PyQt5 references in legacy docs are no
  longer applicable.

### 17.5 Changelog

| Date | Author | Change |
|------|--------|--------|
| 2026-08-31 | Project Owner | Initial draft — consolidated webapp companion spec to `PROJECT_SPEC.md`. Captures current state (Phase 5/6/7 landed; Phase 7b and 8 spec'd, pending). 17 sections, ~1,050 lines. |
