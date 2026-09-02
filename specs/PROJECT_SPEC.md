# Spec: Batch File Processor — Canonical Project Specification

**Status:** APPROVED (this is the canonical project spec)
**Author:** Project Owner
**Created:** 2026-07-06 (initial), 2026-08-21 (rewritten post-webapp-pivot)
**Updated:** 2026-08-21

> **Purpose of this document:** this is the **canonical project
> spec** — what the Batch File Processor *is today*, how it is built
> today, and what it is trying to become. It supersedes the prior
> 2026-07-06 "intent-only" draft and consolidates the §3.7 / §3.8
> addenda into the main body.
>
> For *implementation tasks*, see the per-phase specs in
> `specs/webapp-phase-N-*.md` derived from this one. For deep design
> detail, follow the cross-references in §14.

---

## Table of Contents

1. [Summary](#1-summary)
2. [Background](#2-background)
3. [Design](#3-design)
4. [Components](#4-components)
5. [Data Model](#5-data-model)
6. [HTTP API Surface](#6-http-api-surface)
7. [Configuration & Environment](#7-configuration--environment)
8. [Security & Privacy](#8-security--privacy)
9. [Operator Workflows](#9-operator-workflows)
10. [Testing Strategy](#10-testing-strategy)
11. [Roadmap & Phase Status](#11-roadmap--phase-status)
12. [Risk Assessment](#12-risk-assessment)
13. [Open Questions](#13-open-questions)
14. [Appendix](#14-appendix)

---

## 1. Summary

> **Internal tool.** One project owner, one workstation, one
> operator role, zero external users. The product exists because
> the project owner needs to process EDI files at runtime without
> writing code for each trading partner. See
> [ROADMAP.md §1.1](./ROADMAP.md) for the full framing.

The Batch File Processor (**BFP**) is a **single-host, local-first web
application** (FastAPI + static SPA) that watches local folders for
incoming EDI (Electronic Data Interchange) files, validates and
reshapes them through a configurable pipeline, converts them into
one of many business-specific output formats, and delivers the result
to one or more configured destinations (FTP, SMTP, HTTP, local copy).
All configuration, processing history, and operator state persist in
a single SQLite database through a versioned schema.

The product's defining characteristic is that **the pipeline is
fully user-configurable at runtime** — folders, converters, backends,
parameters, and delivery settings are all edited through the browser
UI without code changes, restarts, or operator shell access.

The webapp was introduced in 2026-08-04 (commit `9864dc7e5`) and is
now the **only** operator surface. The prior PyQt5 desktop GUI was
removed in the same pivot; the Qt-free business-logic orphan
(`interface/`) is being deleted in Phase 7b (in progress).

---

## 2. Background

### 2.1 Problem Statement

Operators in retail / distribution businesses receive EDI feeds
(typically A / B / C "Three-Letter" record-based formats with custom
record layouts) from trading partners that must be reshaped into
retailer-specific formats (CSV, Excel, Fintech, E-Store, Scannerware,
etc.) and delivered to each retailer's required destination (their
FTP drop, their email intake, their internal share). Each trading
partner has a unique combination of:

- input record layout
- split rules (split by a field value, or emit N records per output)
- output format
- delivery destination and credentials
- tweak rules (post-conversion record rewrites)

Doing this by hand — or with bespoke cron jobs and shell scripts —
is brittle, un-auditable, and requires a developer for every new
trading partner.

### 2.2 Motivation

A single operator-facing tool should let a non-developer:

1. Point the app at a folder.
2. Describe the file format (or select from a library of known EDI
   formats).
3. Pick an output format.
4. Pick one or more destinations.
5. Walk away.

…and have every file that lands in the folder be processed,
delivered, and logged, without anyone touching a shell. New trading
partners are onboarded in minutes, not days. Failures are visible.
Re-processing after a destination outage is one click.

The webapp pivot made this **remotely accessible** without changing
the operator workflow: a single-user bearer token + reverse proxy is
the canonical "operator on a different machine" shape, but
single-host-local-first remains the default deployment.

### 2.3 Prior Art

The project is the single line of descent from the original desktop
app. The `dispatch/`, `backend/`, and `core/` trees are the
battle-tested processing engine; the webapp is the new operator
shell. Existing in-tree documentation that informs this spec:

| Document | What it covers |
|----------|----------------|
| `docs/ARCHITECTURE.md` | Original as-built system architecture (PyQt5-era; partially stale) |
| `docs/PROCESSING_PIPELINE.md` | End-to-end pipeline behavior |
| `docs/PROCESSING_DESIGN.md` | Pipeline internals (validator, splitter, converter, tweaker, sender) |
| `docs/PLUGIN_DESIGN.md` / `docs/PLUGIN_DEVELOPER_GUIDE.md` | How converters and backends are added |
| `docs/PLUGIN_ARCHITECTURE.md` | Plugin discovery model |
| `docs/DATABASE_DESIGN.md` | Schema, migrations, repository pattern |
| `docs/STRUCTURED_LOGGING.md` | Logging conventions |
| `docs/MIGRATION_DESIGN.md` | Schema migration policy |
| `docs/runbook.md` | Operator workflows (`curl`-ready) |
| `docs/architecture/webapp-gap-audit.md` | Production-readiness gap analysis |
| `AGENTS.md` | Project-wide technical reference (architecture, imports, anti-patterns) |
| `DOCUMENTATION.md` | Long-form developer / user guide |
| `specs/README.md`, `specs/TEMPLATE.md` | Existing spec workflow this document follows |
| `specs/webapp-phase-{5,6,7,7b,8}-*.md` | The work this spec describes |
| `README.md` | Operator-facing quick-start |

Out of scope for this spec (managed elsewhere):

- Single-feature implementation specs (`specs/<feature>.md`)
- `openspec/changes/` change-set proposals
- Bug-hunting audits (`CODE_AUDIT_FINDINGS.md`, `BUGFIX_SUMMARY.md`)
- The legacy `dispatch/` migration spec (`specs/dispatch-migration.md`,
  `specs/refactor-dispatch-simplification.md` — pre-pivot artifacts)

---

## 3. Design

### 3.1 Architecture Overview

The webapp is a thin HTTP layer over the existing processing engine.
The engine lives in `dispatch/` and `backend/` and is reused
unchanged by the webapp via `webapp/runner.py` wrapping
`dispatch.orchestrator.DispatchOrchestrator` in a worker thread.

```
┌─────────────────────────────────────────────────────────────────────────┐
│                       Operator (browser, single-user)                    │
└─────────────────────────────────────────────────────────────────────────┘
                                   │
                          HTTP (FastAPI + static SPA)
                                   │
                                   ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                          webapp/ (FastAPI shell)                         │
│  ┌─────────────┐  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐  │
│  │ main.py     │  │ routers/*    │  │ runner.py    │  │ watcher.py   │  │
│  │ (app        │  │ (13 routers  │  │ (background  │  │ (folder      │  │
│  │  factory,   │  │  split out   │  │  run         │  │  polling     │  │
│  │  lifespan)  │  │  of main.py) │  │  worker)     │  │  supervisor) │  │
│  └──────┬──────┘  └──────┬───────┘  └──────┬───────┘  └──────┬───────┘  │
│         │                │                  │                  │         │
│         ▼                ▼                  ▼                  ▼         │
│  ┌─────────────┐  ┌──────────────┐  ┌──────────────────────────────┐     │
│  │ config.py   │  │ diagnostics  │  │ errors.py (webapp-owned      │     │
│  │ settings    │  │ importer     │  │  error ledger + soft-delete) │     │
│  └─────────────┘  └──────────────┘  └──────────────────────────────┘     │
└────────────────────────────────────┬────────────────────────────────────┘
                                     │
                                     ▼
┌─────────────────────────────────────────────────────────────────────────┐
│           dispatch/ (processing engine — being moved under webapp/)      │
│   orchestrator.py → services/folder_processor.py → services/file_processor.py │
│   pipeline/{validator, splitter, converter, tweaker}                    │
│   converters/ (11 plugins)   send_manager.py   edi_validator.py         │
└────────────────────────────────────┬────────────────────────────────────┘
                                     │
                                     ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                          backend/ (delivery plugins)                     │
│   ftp_backend.py   email_backend.py   http_backend.py   copy_backend.py │
│   + {smtp,ftp,http}_client.py (with timeouts, retries)                   │
└────────────────────────────────────┬────────────────────────────────────┘
                                     │
                                     ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                  core/  +  adapters/ +  migrations/                      │
│   structured_logging, exceptions, EDI parsing, SQLite adapters, schema   │
└─────────────────────────────────────────────────────────────────────────┘
```

### 3.2 The Five Capabilities (Contract for the System)

These are the user-visible capabilities the rest of the architecture
must serve. They are unchanged from the 2026-07-06 spec because they
describe the *product*, not the implementation.

#### 3.2.1 Capability A — Folder-bound processing

The operator defines a **folder** with:

- a watched input directory (resolved against `BFS_BASE_DIR` at
  runtime; stored as a relative path in the DB)
- one or more converters to apply
- one or more destinations to ship the result to
- optional split and tweak steps
- per-format parameter overrides
- enable / disable and schedule

**Contract:** add, edit, or remove a folder through the UI without
restarting the webapp, watcher, or any worker. Changes take effect on
the next watcher tick or the next `POST /api/run`.

#### 3.2.2 Capability B — File discovery with idempotency

For every enabled folder, the app must:

1. Enumerate candidate files in the input directory.
2. Filter out files already processed (by content checksum and / or
   `mtime + size`, per folder config).
3. Process each remaining file through the pipeline.
4. Mark it processed only on successful delivery to **all** required
   backends (failure policy is user-configurable per folder).

**Contract:** a file is processed exactly once per (folder, content).
Replacing a file with different content re-triggers processing.
Restarting the app mid-run must not duplicate-process nor
silently-drop a file.

#### 3.2.3 Capability C — Pipeline as four ordered stages

Each file flows through, in order:

```
Validator  →  Splitter  →  Converter(s)  →  Tweaker(s)  →  Send
```

- **Validator** (`dispatch/edi_validator.py`) rejects malformed EDI
  before any work is done. Phase 5.5 classifies errors as
  `major` / `minor` for the error ledger.
- **Splitter** (`dispatch/pipeline/splitter.py` +
  `core/edi/edi_splitter.py`) segments multi-record files into one
  or many output files.
- **Converter(s)** (`dispatch/converters/`) transform EDI into the
  target business format. Multiple converters in series are allowed
  per folder.
- **Tweaker(s)** (`dispatch/converters/convert_to_tweaks.py`) apply
  post-conversion record-level rewrites (lookup substitutions,
  padding fixes, header tweaks).
- **Send** (`dispatch/send_manager.py` + `backend/`) is the delivery
  step after the chain completes.

**Contract:** each stage has a single, documented
`PipelineStep.execute()` interface
(`dispatch/pipeline/interfaces.py`). A stage that succeeds must not
be re-run when a downstream stage fails — checkpointing is per-stage,
not whole-file.

#### 3.2.4 Capability D — Multi-destination delivery

A folder ships its output to N destinations. Each destination is a
backend instance (FTP, SMTP, local copy, HTTP). The user picks:

- which backends to use (an ordered list),
- per-backend credentials,
- per-backend retry policy,
- whether a failure in any backend blocks the others (default: do
  not block),
- whether a failure in all backends rolls the file back to
  "unprocessed" so it is retried on the next tick.

**Contract:** no backend is hard-coded as "the" destination. New
backends are added by dropping a `*_backend.py` module into `backend/`
and following the documented
`do(process_parameters, settings_dict, filename, disable_retry) -> bool`
signature (per `docs/PLUGIN_DESIGN.md`). The four backends shipped
today are `ftp_backend`, `email_backend`, `http_backend`,
`copy_backend`.

#### 3.2.5 Capability E — Operator observability

The operator must always be able to answer, from the browser:

- What folders exist and are enabled / disabled?
- What is each folder's current state (idle, processing, error)?
- What files were processed when, with what status, to which
  destinations?
- What errors occurred, for which file, with what stack trace?
- What is in the current tick's work queue?
- Are the configured backends reachable *right now*? (Phase 6.3)

**Contract:** all of the above is queryable from the dashboard and
persisted to SQLite for after-the-fact review. Errors are recorded to
a dedicated `dispatch_errors` table via `webapp/errors.py` (which
`dispatch/error_handler.py` writes through). No error is swallowed
silently — enforced by the AGENTS.md anti-pattern rules.

### 3.3 Deployment Model

#### 3.3.1 Posture

**Single-host, single-operator, local-first.** A fresh
`python -m webapp.main` binds `127.0.0.1:8000` (Phase 6.1) — no
inbound network surface. Remote access is an explicit opt-in via
`BFS_HOST=0.0.0.0` and `BFS_API_TOKEN=<secret>` (Phase 6.2). The
bearer-token is a long-lived env-var secret, not a JWT — the spec is
single-user, so refresh flows would add ceremony for zero operational
benefit.

TLS termination is deliberately out of scope: an operator who wants
to expose the dashboard remotely puts nginx or Caddy in front, and
the bearer-token + nginx-TLS pairing is the documented canonical
remote-access shape.

#### 3.3.2 Threat model

| Concern | Treatment |
|---------|-----------|
| Credentials in DB | Stored only in `folders.db` (SQLite); never logged; never sent off-machine except to configured destinations |
| Inbound network | Default bind is `127.0.0.1`; remote access requires explicit `BFS_HOST=0.0.0.0` + `BFS_API_TOKEN`; bearer-token is the only auth gate |
| API exposure | When token is set, every endpoint except `/`, `/api/health`, `/docs`, `/openapi.json`, `/redoc` requires `Authorization: Bearer <token>` |
| Container escape | The Docker compose file binds `127.0.0.1:8000:8000`; operator opts in to expose by changing the bind line |
| DB integrity | WAL mode + transactions; automatic pre-migration backup (`webapp/backup.py`) |
| CORS / CSRF | Same-origin only; no CORS configured; bearer-token stored in `localStorage` (UI), attached as `Authorization` header on every `fetch` |
| Log redaction | Process parameters (credentials) are not logged; log filters redact known sensitive keys |

### 3.4 What the Product Is Not

Stating non-goals is part of the spec. The product is explicitly
**not**:

- **Not a cloud service.** No SaaS tier, no hosted backend. All data
  stays on the operator's machine.
- **Not an EDI format converter toolkit.** It is an *operator-facing*
  configuration product that *uses* converters. Authors of new
  converters interact with the Python API; operators interact with
  the UI.
- **Not a real-time / streaming system.** Folder polling is the
  model. Files are entire before processing begins.
- **Not a multi-tenant product.** One SQLite database per host. No
  shared central server, no user table.
- **Not a desktop application.** The PyQt5 GUI was removed in the
  2026-08-04 webapp-pivot; the Qt-free `interface/` orphan is being
  deleted in Phase 7b. The webapp is the only operator surface.

### 3.5 Release Channels

The product ships as:

1. **Docker Compose** (primary) — `docker compose up -d` binds
   `127.0.0.1:8000:8000`, mounts `./data` as `/data`, stores the DB
   in `./data/config`. Operator edits the `ports:` line to expose.
2. **Source + venv** — `pip install -r requirements.txt` +
   `python -m webapp.main` for developer / fallback install.
3. **Uvicorn direct** — `uvicorn webapp.main:app --host 0.0.0.0
   --port 8000` for explicit remote-access deployments.

The PyInstaller single-file `.exe` (which was the original
desktop-era distribution) is no longer a product commitment. An
operator who wants a single-file distribution can build one against
the webapp source with PyInstaller; it is not maintained or
documented as a first-class channel.

Headless / automatic mode (the desktop app's `-a` flag) is subsumed
by the webapp's scheduler endpoint (`POST /api/schedule`).

### 3.6 Non-Functional Requirements

| Category | Requirement | Source of truth |
|----------|-------------|-----------------|
| Portability | Single-user, single-host, works offline | Local SQLite + local filesystem |
| Reliability | App crash during processing must not corrupt the DB | WAL mode + transactions |
| Safety | Re-running must not double-process or re-deliver a file | Per-folder processed-files ledger |
| Reversibility | Schema evolution is forward-only with automatic backups before each migration | `migrations/` |
| Testability | Every plugin and every stage has a unit test; pipeline end-to-end has integration tests; UI flows have smoke tests | `docs/TESTING_DESIGN.md` |
| Logging | Structured logging with `folder_alias`, `file_path`, `stage` context on every record | `docs/STRUCTURED_LOGGING.md`, `AGENTS.md` |
| Observability | Errors recorded to DB even when logging fails | `webapp/errors.py` + `dispatch/error_handler.py` |
| Performance | Single file processed in under 5 s on a modern desktop; backlog drained in foreground or worker thread | Out of scope to over-optimize |
| Security | Credentials stored only in the local SQLite DB; never logged; never sent off-machine except to configured destinations | Implicit; no inbound network surface by default |

### 3.7 Alternatives Considered

| Alternative | Pros | Cons | Why Not Chosen |
|-------------|------|------|----------------|
| Browser-based web UI (originally rejected 2026-07-06) | Easier distribution, no Qt | Requires a server; cross-platform desktop parity lost | **Reversed 2026-08-04** — webapp-pivot shipped; PyQt5 GUI removed 2026-08-18 |
| PyQt5 desktop GUI (the prior art) | Powerful widgets; offline by default; no inbound surface | Cross-platform packaging pain; Windows-only at deployment; no remote access | **Reversed 2026-08-04** — see §3.4 |
| Per-folder YAML / JSON config files | GitOps, version controllable | Brittle for operators; schema migrations get ugly; loses the GUI value proposition | SQLite + webapp remains canonical |
| AsyncIO pipeline end-to-end | Modern concurrency; native to FastAPI | Incompatible with the current `ThreadPoolExecutor`-driven `dispatch/` engine; rewrite cost | Phase 8 plans this for the webapp-native pipeline (§11) |
| Hard-coded converters | Faster MVP | Defeats the operator-onboarding-in-minutes value prop | Plugin discovery remains canonical |
| Cloud-hosted config sync | Multi-machine operators | Privacy / connectivity / compliance concerns; out of scope for local-first product | Optional later |
| PyInstaller single-file `.exe` | Familiar Windows distribution | Stale; webapp is the only operator surface | Removed from release channels (§3.5) |
| JWT-based auth with refresh | Industry-standard, scales to multi-user | Ceremony for zero operational benefit (single-user) | Long-lived bearer-token is the canonical Phase 6.2 shape |

---

## 4. Components

This section is the as-built map. Every module is annotated with its
role and its current status in the Phase 7/7b/8 cleanup arc.

### 4.1 `webapp/` — Operator Surface (FastAPI + Static SPA)

**Role:** the only operator surface. Owns the HTTP API, the
background run worker, the folder watcher, the error ledger, the
diagnostics card, and the soft-delete / restore lifecycle.

| Module | Role | Notes |
|--------|------|-------|
| `main.py` | FastAPI app factory + lifespan; uvicorn entry point; static-files mount; token gate | Houses `Settings` factory + `RunStore` / `Scheduler` singletons; delegates all endpoint logic to `webapp/routers/` |
| `config.py` | `Settings` dataclass + `from_env()` loader | Phase 6 added `host`, `port`, `api_token`, `folders_deleted_ttl_days`, `folders_deleted_trim_interval_seconds` |
| `runner.py` | `RunStore` with `start_run` / `wait_run`; background worker thread that wraps `dispatch.orchestrator.DispatchOrchestrator.process()` | The bridge between FastAPI and the synchronous dispatch engine |
| `watcher.py` | Folder-watcher supervisor with health columns (`last_tick_at`, `last_run_id`, `last_error`) | Started by `main.py::_lifespan` |
| `scheduler.py` | Periodic-run scheduler | Started by `main.py::_lifespan`; exposed via `/api/schedule` |
| `errors.py` | `dispatch_errors` table + `insert_error()` + consecutive-failure dedupe | Webapp-owned; the `dispatch/error_handler.py` adapter writes through this |
| `diagnostics.py` | Self-test snapshot for the Diagnostics card | Phase 6.3 added `backends_health` (SMTP / FTP / copy probes) |
| `importer.py` | Legacy `folders.db` importer with base-dir rebasing | Strips absolute paths to relative paths against `BFS_BASE_DIR` |
| `folder_schema.py` | Typed folder-edit schema + per-folder validation | |
| `converters_api.py` | 11-converter registry metadata for the folder editor's per-format UI | Currently hardcodes the 11 keys; Phase 8 plans to make this registry-driven |
| `settings_api.py` | Editable global settings (`kv_settings`) | |
| `history.py` | Run history rows + `MAX_HISTORY_ROWS` cap | |
| `maintenance.py` | Bulk operations: clear-processed, mark-processed, export-CSV, set-all-active, etc. | |
| `resend.py` | Resend-flag + resend-run orchestration | |
| `backup.py` | Snapshot / restore / list / download of `folders.db` | |
| `preview.py` | Parse-only EDI preview for `/api/preview/edi` | |
| `paths.py` | Path resolution against `BFS_BASE_DIR` | |
| `database.py` | `folders_deleted` table DDL (Phase 6.4) + helpers | |
| `routers/` | 13 `APIRouter` modules split out of `main.py` (Phase 5 refactor) | `_deps.py`, `_helpers.py`, `backups.py`, `errors.py`, `folders.py`, `imports.py`, `maintenance.py`, `processed.py`, `runs.py`, `schedule.py`, `settings_api.py`, `system.py`, `watcher.py` |
| `static/` | Browser SPA (`index.html`, `app.js`, etc.) | One-page app; per-page cards for folders, runs, processed files, errors, diagnostics, backups |

**Entry points:**

```bash
# Default
BFS_BASE_DIR=./data python -m webapp.main

# Remote access
uvicorn webapp.main:app --host 0.0.0.0 --port 8000

# Docker
docker compose up -d   # binds 127.0.0.1:8000:8000
```

### 4.2 `dispatch/` — Processing Engine (Phase 8+ Retirement Target)

**Role:** the EDI processing pipeline. Today this is the only code
that processes files; the webapp wraps it in a worker thread. Phase 8
plans to move the surviving code under `webapp/pipeline/` and
`webapp/converters/`, leaving `dispatch/` empty.

| Module | Role | Phase 8 status |
|--------|------|----------------|
| `orchestrator.py` | `DispatchOrchestrator.process()` — the main coordinator | Will move to `webapp/pipeline/orchestrator.py` |
| `services/folder_processor.py` | `FolderPipelineExecutor` — per-folder processing | Will move to `webapp/pipeline/folder_executor.py` |
| `services/file_processor.py` | `FileProcessor` — per-file processing | Will move to `webapp/pipeline/file_processor.py` |
| `services/folder_discovery.py` | Folder enumeration | Will move to `webapp/pipeline/discovery.py` |
| `services/database_connector.py` | DB access abstraction | Will be absorbed into webapp DB layer |
| `services/progress_reporter.py` + `services/progress_reporting.py` | Two parallel progress-reporting implementations | **Phase 8 §3.1 #1:** collapse to one (delete `progress_reporting.py`) |
| `services/{upc,customer_lookup,uom_lookup}_service.py` | Lookup abstractions | Stay where they are (webapp keeps delegating) |
| `services/{item_processing,file_filter}.py` | Line-item filtering | |
| `pipeline/{validator,splitter,converter,tweaker}.py` | Per-stage pipeline abstraction | Will move to `webapp/pipeline/stages/` |
| `pipeline/factory.py` | `create_standard_pipeline()` wires the standard set | |
| `pipeline/interfaces.py` | `PipelineStep` protocol | |
| `converters/` | 11 converter plugins under `BaseEDIConverter` (`csv`, `estore_einvoice`, `estore_einvoice_generic`, `fintech`, `jolley_custom`, `scannerware`, `scansheet_type_a`, `simplified_csv`, `stewarts_custom`, `tweaks`, `yellowdog_csv`) + `convert_base.py`, `registry.py` | Will move to `webapp/converters/` |
| `send_manager.py` | `SendManager` + `BackendFactory` — multi-channel delivery | Will move to `webapp/pipeline/backends.py` |
| `error_handler.py` | Error-capture adapter | Will be absorbed by `webapp/errors.py` |
| `edi_validator.py` | EDI A/B/C record validation with major/minor classification | Will move to `webapp/pipeline/edi.py` |
| `preflight_validator.py` | Config validation | Will move to `webapp/pipeline/preflight.py` |
| `interfaces.py`, `file_utils.py`, `hash_utils.py`, `file_system.py`, `processed_files_tracker.py`, `log_sender.py`, `results.py`, `feature_flags.py` | Supporting modules | Various Phase 8 targets; see `specs/webapp-phase-8-pipeline-redesign.md` |
| `observability/` | Alert dispatcher, queue, audit logger, background writer | Stays (cross-cutting) |

**Anti-targets for Phase 8:**

- The 11 converters do **not** change *semantically*. Operator
  domain logic ("convert this EDI to CSV with these columns") is
  preserved. Only the plumbing moves.
- No behavior change ships in Phase 8 itself. Phase 8 produces a
  decision document; Phase 9+ ships the code.

### 4.3 `backend/` — Delivery Plugins

**Role:** send a file to an external destination.

| Module | Role |
|--------|------|
| `__init__.py` | Package marker; no public API |
| `backend_base.py` | `BaseSendBackend` ABC + shared retry / timeout helpers |
| `copy_backend.py` | Local-filesystem copy destination |
| `email_backend.py` | SMTP delivery; delegates to `smtp_client.py` |
| `ftp_backend.py` | FTP delivery; delegates to `ftp_client.py` (paramiko-based) |
| `http_backend.py` | HTTP POST/PUT delivery; delegates to `http_client.py` |
| `smtp_client.py` | SMTP client with TLS, retries, timeouts |
| `ftp_client.py` | FTP / SFTP client with retries, timeouts |
| `http_client.py` | HTTP client with retries, timeouts |
| `file_operations.py` | Shared filesystem operations (atomic rename, copy) |
| `protocols.py` | Type protocols for backend parameters |
| `database/` | `database_obj.py`, `sqlite_wrapper.py` — legacy DB wrappers (kept for compatibility) |

**Contract** (per `docs/PLUGIN_DESIGN.md`):

```python
def do(
    process_parameters: dict,  # Backend-specific config
    settings_dict: dict,      # Global settings
    filename: str,            # File to send
    disable_retry: bool = False,
) -> bool:
    """Send a file via backend.

    Returns:
        True if successful.
    """
```

### 4.4 `core/` — Shared Utilities

| Module | Role |
|--------|------|
| `structured_logging.py` | The canonical structured logger; per-record context (`folder_alias`, `file_path`, `stage`); correlation IDs |
| `logging_config.py` | Root logger configuration |
| `constants.py` | Project-wide constants |
| `exceptions.py` | Custom exception hierarchy |
| `utils/` | Misc helpers (e.g., `folder_utils.build_effective_folder`, `normalize_bool`) |
| `edi/` | EDI parsing primitives (`edi_parser.py`, `edi_splitter.py`, `edi_tweaker.py`) |
| `database/` | Framework-agnostic DB layer (`connection.py`, `manager.py`, `schema.py`, `query_runner.py`, `c_record_generator.py`) |
| `ports/` | Port-and-adapter interfaces |
| `domain/` | Domain dataclasses |

### 4.5 `adapters/` — Database Adapter Strategy

Three adapters ship today:

| Adapter | Role |
|---------|------|
| `adapters/sqlite/` | The SQLite adapter used by the webapp |
| `adapters/db2ssh/` | DB2-over-SSH (production-era alternative to SQLite) |
| `adapters/inmemory/` | In-memory adapter for tests |

The webapp currently uses only the SQLite adapter; the others are
kept for the legacy desktop-era deployment shape.

### 4.6 `migrations/` — Schema Evolution

| File | Role |
|------|------|
| `folders_database_migrator.py` | The sequential migration script (v5 → v40+) |
| `legacy_migrations.py` | Pre-v5 migrations |
| `modern_migrations.py` | Post-v5 migrations |
| `migration_helpers.py` | Shared migration utilities |
| `add_plugin_config_column.py` | One-off migration helper |
| `fix_missing_columns.py` | One-off repair helper |

**Migration discipline** (from `docs/MIGRATION_DESIGN.md`,
endorsed by this spec):

- Forward-only. No down-migrations.
- Automatic pre-migration backup (`webapp/backup.py`).
- Each migration has a corresponding test in
  `tests/integration/database_schema_versions.py`.
- A failed migration leaves the DB at the pre-migration version on
  disk and reports failure in the UI.

### 4.7 `tests/` — Test Suite

| Subdirectory | Role | Marker |
|--------------|------|--------|
| `tests/unit/` | Fast unit tests | `unit` |
| `tests/integration/` | DB + dispatch integration | `integration` (heavily reduced post-Phase 7b) |
| `tests/webapp/` | Webapp-specific (importer rebasing, runner, API, soft-delete, diagnostics) | `webapp` |
| `tests/convert_backends/` | Converter parity tests (golden-file comparison) | `conversion` |
| `tests/fixtures/` | Shared test fixtures |
| `tests/golden_files/` | Recorded expected outputs for parity tests |
| `tests/meta/` | Meta-tests (hygiene, marker placement, module coverage) | meta |

**Markers** (canonical set per `docs/TESTING_DESIGN.md`):

- `unit` — fast unit tests
- `integration` — DB + dispatch integration
- `qt` — UI tests (legacy, removed in Phase 7b)
- `conversion` — converter parity tests
- `backend` — backend behavior tests
- `webapp` — webapp-specific
- `meta` — meta-tests

**Qt test rule (legacy):** Qt tests must run single-threaded
(`pytest -n0`) due to PySide6 / pytest-xdist segfaults. N/A
post-Phase 7b — no Qt code remains.

### 4.8 What is being removed (Phase 7b in progress)

The git working tree (branch `webapp-pivot`, ahead of
`origin/webapp-pivot` by 24 commits) shows the active Phase 7b
deletion list:

- `interface/` — Qt-free business-logic orphan (3,819 lines, 16 files,
  no callers in `webapp/` or `dispatch/`)
- `tests/integration/test_*.py` — the desktop-era integration tests
  that exercise the deleted `interface/` layer (~30 files)

The webapp-pivot branch's purpose is the Phase 7 → 8 arc; once
shipped, the only processing-engine code will live under `webapp/`.

---

## 5. Data Model

The canonical database layer is documented in
`docs/DATABASE_DESIGN.md` and `docs/MIGRATION_DESIGN.md`. As a
*project* spec, this document concerns itself only with
schema-intent rules, not column lists.

### 5.1 Schema Categories (Intent)

The schema carries four kinds of information:

1. **Application settings** — global config (paths, defaults).
   Lives in the `kv_settings` table; new keys must follow the
   `webapp.<key>` naming convention.
2. **Folder definitions** — every configured folder and its pipeline
   configuration. Lives in the `folders` table. The 50+ flat
   `folder_*` columns are documented in
   `docs/architecture/DATABASE_COLUMN_READ_MAP.md`.
3. **Processed-file ledger** — one row per (folder, file content)
   the system has handled; the canonical idempotency record. Lives
   in `processed_files`.
4. **Error ledger** — every captured error with full context,
   queryable from the dashboard. Lives in `dispatch_errors`
   (webapp-owned; consecutive-failure dedupe in `webapp/errors.py`).

These four kinds **must not share a table**. Cross-joins are
forbidden. New tables belong to exactly one of these categories.

The Phase 6.4 addition of `folders_deleted` (the soft-delete
tombstone) is a fifth category: *recovery metadata*. It belongs
with folder definitions conceptually but is physically separate so a
trim job can purge expired rows without touching the live `folders`
table.

### 5.2 Migration Discipline (Intent)

- Forward-only. No down-migrations.
- A backup is taken before every migration, in a folder the operator
  can locate.
- Each migration has a corresponding test in
  `tests/integration/database_schema_versions.py`.
- A failed migration leaves the DB at the pre-migration version on
  disk and reports failure in the UI.

These rules are non-negotiable per the existing
`docs/MIGRATION_DESIGN.md`. This spec endorses them.

### 5.3 Schema Changes Required by This Spec

This spec itself **introduces no schema change**. Schema changes
belong in the feature specs (`specs/<feature>.md`) and migration
files (`migrations/`) that implement the phases in §11.

Phase 8 *plans* a typed `folder_config` object (replacing the
50+ flat columns) but the implementation path (JSON-in-one-column
vs child table) is an open design question (§13).

---

## 6. HTTP API Surface

The complete endpoint list (consolidated from `webapp/main.py`'s
docstring and `README.md`). All endpoints live under
`webapp/routers/`; each router module owns its slice.

### 6.1 Liveness & Configuration

| Endpoint | Method | Auth (Phase 6.2) | Notes |
|----------|--------|-----------------|-------|
| `/` | GET | exempt | Static SPA mount |
| `/api/health` | GET | exempt | Liveness + paths |
| `/api/diagnostics` | GET | required if token set | Self-test snapshot; includes `backends_health` (Phase 6.3) |
| `/api/config` | GET | required if token set | `base_dir`, `data_dir`, DB status, counts |
| `/api/preflight` | GET | required if token set | Validate active folder configs |

### 6.2 Import & Preview

| Endpoint | Method | Auth | Notes |
|----------|--------|------|-------|
| `/api/import` | POST | required if token set | Multipart upload of legacy `folders.db` (+ optional `base_dir`, `platform`) |
| `/api/preview/edi` | POST | required if token set | Parse-only EDI classification |

### 6.3 Folders (CRUD + Lifecycle)

| Endpoint | Method | Auth | Notes |
|----------|--------|------|-------|
| `/api/folders` | GET | required if token set | Configured folders (relative + resolved paths) |
| `/api/folders` | POST | required if token set | Create a folder row |
| `/api/folders/{id}` | GET | required if token set | One folder (full edit schema) |
| `/api/folders/{id}` | PUT | required if token set | Save one folder |
| `/api/folders/{id}` | DELETE | required if token set | **Soft-delete** (Phase 6.4); moves row to `folders_deleted`; returns `{deleted, expires_at}` |
| `/api/folders/deleted` | GET | required if token set | List non-expired soft-deleted folders; sorted by `expires_at` ascending |
| `/api/folders/{id}/restore` | POST | required if token set | Restore a soft-deleted folder; re-inserts original row with original `id`; 409 on id-reuse, 410 on expired |

### 6.4 Converters & Settings

| Endpoint | Method | Auth | Notes |
|----------|--------|------|-------|
| `/api/converters` | GET | required if token set | 11 convert formats + per-format config fields |
| `/api/settings` | GET | required if token set | Editable app settings (from `kv_settings`) |
| `/api/settings` | PUT | required if token set | Replace editable settings |

### 6.5 Runs

| Endpoint | Method | Auth | Notes |
|----------|--------|------|-------|
| `/api/run` | POST | required if token set | Start a background processing run |
| `/api/resend` | POST | required if token set | Start a background resend run |
| `/api/folders/{id}/run` | POST | required if token set | Run a single folder |
| `/api/runs` | GET | required if token set | Recent runs |
| `/api/runs/{run_id}` | GET | required if token set | Run detail (poll while running; includes duration + throughput) |
| `/api/runs/{run_id}/log` | GET | required if token set | SSE stream of per-folder logs |

### 6.6 Processed Files & Resend

| Endpoint | Method | Auth | Notes |
|----------|--------|------|-------|
| `/api/processed-files` | GET | required if token set | Recently processed (filters, total, offset) |
| `/api/processed-files/flagged` | GET | required if token set | Processed files with resend-flag info |
| `/api/processed-files/{id}/resend` | POST | required if token set | Flag a row for resend |
| `/api/processed-files/resend-batch` | POST | required if token set | Flag many rows |
| `/api/processed-files/clear-flags` | POST | required if token set | Clear every resend flag |

### 6.7 Maintenance

| Endpoint | Method | Auth | Notes |
|----------|--------|------|-------|
| `/api/maintenance/clear-processed` | POST | required if token set | Bulk-delete processed rows |
| `/api/maintenance/mark-processed` | POST | required if token set | Record a single file as processed |
| `/api/maintenance/set-all-active` | POST | required if token set | Activate every folder |
| `/api/maintenance/set-all-inactive` | POST | required if token set | Deactivate every folder |
| `/api/maintenance/clear-queued-emails` | POST | required if token set | Drop queued report emails |
| `/api/maintenance/remove-inactive` | POST | required if token set | Delete inactive folders |
| `/api/maintenance/mark-all-processed` | POST | required if token set | Mark every active folder's files |
| `/api/maintenance/export-processed` | POST | required if token set | Write a CSV report |
| `/api/maintenance/download` | GET | required if token set | Download a previously-written report |

### 6.8 Schedule & Watcher

| Endpoint | Method | Auth | Notes |
|----------|--------|------|-------|
| `/api/schedule` | GET | required if token set | Current scheduler state + runs triggered |
| `/api/schedule` | POST | required if token set | Enable / disable scheduler + set interval |
| `/api/watched` | GET | required if token set | Watched folders + live watcher health (`last_tick`, `last_run`, `last_error`) |
| `/api/watcher/refresh` | POST | required if token set | Force the watcher supervisor to re-read the watch list |

### 6.9 Errors

| Endpoint | Method | Auth | Notes |
|----------|--------|------|-------|
| `/api/errors` | GET | required if token set | Error-ledger rows + per-folder counts |
| `/api/errors/file` | GET | required if token set | Download a raw error-text artifact |
| `/api/errors/folder-file` | GET | required if token set | Download one folder's full error text |
| `/api/errors/clear` | POST | required if token set | Delete error-ledger rows (optionally per folder) |

### 6.10 Backups

| Endpoint | Method | Auth | Notes |
|----------|--------|------|-------|
| `/api/backups` | GET | required if token set | List timestamped backup files |
| `/api/backup/create` | POST | required if token set | Snapshot the active DB |
| `/api/backup/restore` | POST | required if token set | Restore a named backup as the active DB |
| `/api/backup/download` | GET | required if token set | Download a backup file |

### 6.11 API Conventions

- All JSON, UTF-8.
- Auth (when `BFS_API_TOKEN` is set): `Authorization: Bearer <token>`.
  401 on missing / wrong; 503 when server token is missing (fail
  closed).
- 409 on id-reuse, 410 on expired (Phase 6.4 soft-delete).
- Errors are returned with `{detail: "..."}` or the route's error
  shape; no silent failures.

---

## 7. Configuration & Environment

### 7.1 Environment Variables

| Variable | Default | Purpose |
|----------|---------|---------|
| `BFS_BASE_DIR` | `./data` | Base directory that configured folder paths resolve against |
| `BFS_DATA_DIR` | `<base_dir>/config` | Where `folders.db` lives |
| `BFS_HOST` | `127.0.0.1` | Interface uvicorn binds (Phase 6.1; opt in to remote access with `0.0.0.0`) |
| `BFS_PORT` | `8000` | TCP port uvicorn binds |
| `BFS_API_TOKEN` | *(unset)* | Phase 6.2 single-user bearer-token. When set, every API endpoint except `/`, `/api/health`, `/docs`, `/openapi.json`, `/redoc` requires `Authorization: Bearer <token>`. The static UI prompts for the token on the first 401 and stores it in `localStorage` under `bfs_api_token`. Rotate by restarting with a new value. |
| `FOLDERS_DELETED_TTL_DAYS` | `30` | Phase 6.4 soft-delete restore window in days, clamped `[1, 365]`. After this many days a soft-deleted folder is purged by the hourly trim job. |
| `FOLDERS_DELETED_TRIM_INTERVAL_SECONDS` | `3600` | How often the soft-delete trim job runs. Set to `0` to disable. |

### 7.2 Base-dir Rebasing (Importer)

The legacy desktop app stored absolute paths (e.g.,
`C:\Data\Incoming\X`). The webapp strips these to relative paths
(`Data/Incoming/X`) at import time and resolves them against
`BFS_BASE_DIR` at run time. This makes the import portable across
machines (Windows → Linux container) and makes the Docker mount
straightforward.

The `importer.py` module is the single point of truth for this
rebasing. The `kv_settings` table persists `webapp.base_directory`
(the rebased root) and `webapp.source_platform` (Windows / Linux)
as import provenance.

### 7.3 Feature Flags

`dispatch/feature_flags.py` exposes runtime configuration via
environment variables; see `get_feature_flags()` /
`set_feature_flag()`. Flags are read once at process start; the
webapp does not yet expose flag-toggling through the UI.

### 7.4 Docker

```yaml
# docker-compose.yml
services:
  bfs:
    build: .
    ports:
      - "127.0.0.1:8000:8000"  # opt in to LAN exposure by removing the bind
    volumes:
      - ./data:/data
    environment:
      BFS_BASE_DIR: /data
      BFS_DATA_DIR: /data/config
```

---

## 8. Security & Privacy

### 8.1 Authentication

- **Default (no token):** auth disabled; webapp behaves as it did
  pre-Phase 6.2.
- **`BFS_API_TOKEN` set:** every endpoint except `/`, `/api/health`,
  `/docs`, `/openapi.json`, `/redoc` requires
  `Authorization: Bearer <token>`. Wrong / missing token → 401;
  server unconfigured → 503.
- The static UI reads the token from `localStorage` (key
  `bfs_api_token`) and attaches it as a header on every `fetch`.
  No CSRF — same-origin only (no CORS configured), and the token is
  never sent in URLs or logged.

### 8.2 Credential Storage

- All credentials (SMTP passwords, FTP passwords, HTTP API tokens)
  live only in `folders.db` (SQLite). They are loaded into memory
  only at the moment of `do()`; they are not persisted to logs.
- `process_parameters` is never logged. The structured-logging
  context includes `folder_alias`, `file_path`, `stage` — never
  credentials.
- No outbound network calls happen except to the configured
  destinations. There is no telemetry, no analytics, no auto-update
  channel that would push data off-machine.

### 8.3 Network Posture

- Default bind: `127.0.0.1:8000` (Phase 6.1).
- Docker compose binds `127.0.0.1:8000:8000`.
- Remote access requires *two* explicit operator actions:
  - `BFS_HOST=0.0.0.0` (or `--host 0.0.0.0`)
  - `BFS_API_TOKEN=<secret>`
- TLS termination is out of scope; the canonical remote-access
  shape is `nginx` / `Caddy` in front + bearer-token auth.

### 8.4 Database Integrity

- SQLite WAL mode + transactions.
- Automatic pre-migration backup (`webapp/backup.py`).
- Soft-delete is reversible within `FOLDERS_DELETED_TTL_DAYS`
  (default 30).
- Error ledger is durable across crashes (WAL mode).

### 8.5 Anti-Patterns Enforced

Per `AGENTS.md`:

- No silent `except: pass` — always `logger.debug(..., exc_info=True)`.
- No `MagicMock()` without `spec=` in tests.
- No `getattr` on unknown objects without `hasattr` check.
- No magic padding (`"00" + x`) — use `x.zfill(2)` / `f"{x:02d}"`.
- No business logic in UI / router handlers — delegate to
  `webapp/` operations modules.

---

## 9. Operator Workflows

The authoritative runbook is `docs/runbook.md`. This section is the
short summary; cross-reference for the canonical `curl` examples.

### 9.1 "A run failed"

1. `GET /api/runs` — list recent runs.
2. `GET /api/runs/{run_id}` — pull one run's per-folder breakdown.
3. `GET /api/runs/{run_id}/log` (SSE) — stream the per-folder log.
4. `GET /api/errors?folder_id={id}` — drill into the error ledger.
5. `GET /api/errors/file?folder={alias}` — download the raw error
   artifact.

### 9.2 "Files aren't being picked up"

1. `GET /api/watched` — verify the folder is being watched and the
   watcher is healthy (`last_tick_at`).
2. `GET /api/folders/{id}` — verify `folder_is_active = 1`.
3. `GET /api/diagnostics` — check `backends_health` (Phase 6.3).
4. `POST /api/watcher/refresh` — force the supervisor to re-read.

### 9.3 "SMTP / FTP unreachable"

1. `GET /api/diagnostics` — `backends_health.smtp` / `.ftp` shows
   reachable / not, with error message.
2. Verify credentials in the folder's edit schema.
3. Test from the host directly (curl / openssl s_client).

### 9.4 "I deleted a folder by accident"

1. `GET /api/folders/deleted` — list soft-deleted folders.
2. `POST /api/folders/{id}/restore` — restore within
   `FOLDERS_DELETED_TTL_DAYS` (default 30). 410 if expired.

### 9.5 "The database looks weird"

1. `GET /api/config` — verify `data_dir` and DB existence.
2. `GET /api/backups` — list available backups.
3. `POST /api/backup/create` — snapshot before any recovery action.
4. `POST /api/backup/restore` — restore a named backup.
5. If the DB is corrupt at the schema level, the migration error is
   visible in the UI and the DB is left at the pre-migration
   version on disk.

---

## 10. Testing Strategy

Refer to `docs/TESTING_DESIGN.md` for full coverage of markers and
conventions. As a *project* spec:

### 10.1 Test Layers

| Layer | Marker | Covers |
|-------|--------|--------|
| Unit | `unit` | Pipeline stages, converter / output generation, validators, backend `do()` |
| Integration | `integration` | End-to-end folder → pipeline → backend with in-memory DB |
| Webapp | `webapp` | Importer rebasing, runner, soft-delete, diagnostics, API contracts |
| Backend parity | `backend` | Backend behavior equivalence with golden files |
| Conversion parity | `conversion` | Each converter's output compared to a recorded golden file |
| Meta | `meta` | Test hygiene, marker placement, module coverage |

### 10.2 Intent-Level Invariants

These must hold for every release:

- A folder with a single valid file and a single working backend
  ends in exactly one row in the processed-files ledger.
- A folder with a working input file but a failing backend does
  *not* add a processed-files row.
- Killing the app mid-pipeline and restarting does not produce
  duplicate downstream deliveries.
- Every discovered converter module produces a non-empty output
  for at least one golden EDI input.
- Every discovered backend module has at least one test that
  asserts the `do()` contract.
- A soft-deleted folder restored within `FOLDERS_DELETED_TTL_DAYS`
  reappears with the original `id` and identical configuration.
- An expired soft-delete restore returns 410 (Phase 6.4).

### 10.3 Coverage Requirements

| Code Area | Minimum Coverage |
|-----------|------------------|
| `dispatch/` (orchestration + pipeline stages) | 85% lines |
| `dispatch/converters/` (per-converter) | 80% lines, with golden-file parity test |
| `backend/` (per-backend) | 80% lines, with at least one harness test that exercises `do()` |
| `core/database/` | 90% lines (high-risk layer) |
| `webapp/` (routers, runner, watcher, errors, diagnostics) | 80% lines; smoke test per router |

These minima are enforced by CI once that exists (see §11).

---

## 11. Roadmap & Phase Status

The roadmap is a sequence of phase specs, each of which is itself
an implementation spec (with a status, an author, and an explicit
scope). This project-level roadmap groups them; per-phase detail
lives in the linked spec.

### 11.1 Phase 5 — Observability — ✅ COMPLETE

`specs/webapp-phase-5-observability.md` (2026-08-13)

> **See `specs/ROADMAP.md` for the strategic sequencing of all phases, including near-term (next 30 days), mid-term (next 90 days), gap-3.x deferred items, and trigger conditions.**

- Error ledger wired into the runner (`webapp/errors.py`).
- Consecutive-failure dedupe.
- Severity classification (`major` / `minor` for EDI validation).
- Run history with `MAX_HISTORY_ROWS` cap.
- Diagnostics card.
- Search filter on the folders card.
- `alert_on_failure` toggle exposed in folder editor.
- SSE stream of per-folder run logs.
- Resend-flag workflow.
- Soft-delete groundwork laid (implementation in 6.4).
- 1,350-line `main.py` split into 13 routers.

### 11.2 Phase 6 — Production Hardening — ✅ COMPLETE

`specs/webapp-phase-6-production-hardening.md` (2026-08-18)

- 6.1 — Default bind `127.0.0.1`.
- 6.2 — Single-user bearer-token auth (`BFS_API_TOKEN`).
- 6.3 — Backend health probe (SMTP / FTP / copy).
- 6.4 — Soft-delete with restore window (`FOLDERS_DELETED_TTL_DAYS`).

### 11.3 Phase 7 — Operator Confidence & Desktop Retirement — ✅ PARTIALLY COMPLETE

`specs/webapp-phase-7-operator-confidence.md` (2026-08-18)

- Operator runbook (`docs/runbook.md`).
- Schema-repair wart fix (`schema_repaired_at` marker).
- PyQt5 desktop packaging machinery deleted.
- `plans/` stale refactoring plans deleted.

### 11.4 Phase 7b — `interface/` Retirement — 🚧 IN PROGRESS

`specs/webapp-phase-7b-interface-retirement.md` (2026-08-19)

- Delete `interface/` (Qt-free orphan, 3,819 lines, 16 files).
- Delete the `tests/integration/test_*.py` desktop-era tests that
  exercise `interface/`.
- Update CI / Makefile / `pyproject.toml`.

### 11.5 Phase 8 — Pipeline Redesign — 📝 DESIGN ONLY

`specs/webapp-phase-8-pipeline-redesign.md` (2026-08-18)

Phase 8 is a *design* spec, not an *implementation* spec. Its
deliverable is "the next agent knows what to build," not "the next
agent has built it." Targets:

- **Ownership clarity** — every line of processing code lives
  under `webapp/`; the top-level `dispatch/` package is removed.
- **Async-native** — the pipeline is designed around the FastAPI
  async model, not around the desktop Qt thread-per-folder model.
- **Honest complexity** — code that exists because "the desktop
  app needed it once" is removed; code that exists because the
  *operator* needs it today is preserved with a clear name.

Open design questions are tracked in §13.

### 11.6 Phase 9+ — Implementation of Phase 8's Decisions — ⏳ PLANNED

Will be broken into small implementation specs in the same shape
as Phases 5–7b. Each ships independently, behind a feature flag
where possible.

### 11.7 Long-Range Wishlist (Beyond Phase 9)

- Async end-to-end (`asyncio.Task` groups replacing the worker
  thread).
- Typed `folder_config` (JSON-in-one-column vs child table — open).
- Registry-driven converter discovery (one file to add the 12th
  converter).
- Unified error / run-history / progress timeline.
- Optional read-only cloud sync (explicit operator opt-in).

---

## 12. Risk Assessment

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| A new converter returns a non-UTF-8 file and downstream backends choke | Med | Med | Encoding contract enforced by `do()` wrapper; validator catches malformed output |
| Backend credentials leak via logs | Med | High | Credentials loaded only at the moment of send; log filters redact; `process_parameters` never logged |
| Long-running pipeline holds the runner thread | Med | Med | Runner runs in `ThreadPoolExecutor` worker; UI remains responsive; cancellation signal supported |
| Operator deletes a folder mid-process | Low | Med | Phase 6.4 soft-delete with 30-day restore window |
| New EDI format added but no converter exists | Med | Med | Format library in `edi_formats/` is documentation, not contract; unknown formats fail validation with clear message |
| Migrations on a corrupted DB brick the install | Low | High | Automatic pre-migration backup + integrity check before applying (per `docs/MIGRATION_DESIGN.md`) |
| Plugin added at runtime with a broken signature crashes the webapp | Low | High | Plugin discovery wrapped in isolated importer that quarantines broken modules |
| Bearer-token leaks via browser `localStorage` | Low | High | Token never sent in URLs; never logged; same-origin only; rotate by restart |
| Phase 8's pipeline move breaks an untested code path | Med | High | Phase 9+ ships behind a feature flag; golden-file parity tests run both old and new paths during transition |
| The two parallel progress-reporting modules (`progress_reporter.py`, `progress_reporting.py`) drift further | Med | Med | Phase 8 §3.1 #1 collapses to one; tracked in `specs/webapp-phase-8-pipeline-redesign.md` |

### 12.1 Rollback Plan

A webapp release is a `git pull` + container restart (or
`pip install -r requirements.txt` + restart for source installs).
The SQLite DB lives next to the webapp; replacing the binary does
not touch the DB. Schema migrations are forward-only — if v40
fails on an operator's machine, the operator reverts to the v39
build, restores from the auto-backup taken just before the
migration, and continues. Migrations from v40 onward can be
re-attempted after a fix.

Phase 8's planned file moves are reversible via `git revert` per
implementation spec.

---

## 13. Open Questions

1. **Typed folder config — JSON or child table?** (Phase 8 §4.1).
   JSON-in-one-column preserves migration simplicity but loses
   per-column indexing; a child `folder_config` table is the
   reverse. Deferred until Phase 9 starts.
2. **Phase 8's move order.** Does the webapp first depend on a
   shim in `dispatch/` that re-exports from `webapp/pipeline/`, or
   is the webapp cut over to `webapp/pipeline/` directly? Deferred.
3. **The 50+ flat folder columns — bulk-rename or live-with-it
   during the move?** Bulk-renaming inside the migration is a
   one-time operator pain; leaving them is a permanent
   readability cost. Deferred.
4. **Maximum reasonable folder count for a single host.**
   Unknown; monitor in the field. If exceeded, profile splitting
   is a long-range concern.
5. **Should Phase 9+ ship behind a feature flag, or all-at-once?**
   The Phase 8 spec leans toward feature-flagged gradual rollout.
   Final decision deferred to each Phase 9 sub-spec.
6. **Mobile responsive UI?** Deferred (operator persona is
   desktop-first). Listed in `docs/architecture/webapp-gap-audit.md`
   §5 (gap-3.x).
7. **TLS termination in the webapp itself?** Out of scope per
   §3.3.1; nginx / Caddy remains the canonical remote-access shape.

---

## 14. Appendix

### 14.1 Cross-Reference

| Topic | This Spec | Canonical Doc |
|-------|-----------|---------------|
| Architecture overview | §3.1, §4 | `docs/ARCHITECTURE.md` (stale; use §4 as the truth today) |
| Pipeline stages | §3.2.3 | `docs/PROCESSING_DESIGN.md`, `docs/PROCESSING_PIPELINE.md` |
| Plugin model | §3.2.3, §3.2.4 | `docs/PLUGIN_DESIGN.md`, `docs/PLUGIN_DEVELOPER_GUIDE.md`, `docs/PLUGIN_API_REFERENCE.md`, `docs/CONVERTER_OUTPUT_FORMATS.md`, `docs/CONVERTER_PLUGIN_GUIDE.md` |
| Database | §5 | `docs/DATABASE_DESIGN.md`, `docs/MIGRATION_DESIGN.md`, `docs/architecture/DATABASE_COLUMN_READ_MAP.md` |
| GUI flows | §3.4, §4.1 | (legacy) `docs/GUI_DESIGN.md`, `docs/UI_LAYOUTS.md`; (current) `webapp/static/` |
| Error handling | §3.2.5, §4.1 | `docs/ERROR_HANDLING_DESIGN.md`, `webapp/errors.py` |
| Logging | §3.6, §8.2 | `docs/STRUCTURED_LOGGING.md`, `AGENTS.md` |
| Testing | §10 | `docs/TESTING_DESIGN.md` |
| Build / distribution | §3.5 | `Makefile`, `Dockerfile`, `docker-compose.yml` |
| Operator workflows | §9 | `docs/runbook.md` |
| Production readiness | §3.3, §8 | `docs/architecture/webapp-gap-audit.md` |
| Webapp companion spec (architecture, API, UI, deployment) | companion | `specs/WEBAPP_SPEC.md` |
| Roadmap (sequencing, triggers, deferred items) | companion | `specs/ROADMAP.md` |
| Phase implementation specs | §11 | `specs/webapp-phase-{5,6,7,7b,8}-*.md` |
| API surface | §6 | `webapp/main.py` docstring, `README.md` |
| Configuration | §7 | `webapp/config.py` |
| Validation rules | §3.2.3 | `docs/VALIDATION_DESIGN.md`, `docs/EDI_FORMAT_DESIGN.md` |

### 14.2 Glossary

| Term | Meaning |
|------|---------|
| **Folder** | One configured input directory plus its pipeline + destinations (the unit of work in the UI). |
| **EDI** | Electronic Data Interchange — here, A/B/C "Three-Letter" record-based feeds from trading partners. |
| **Converter** | A plugin that takes parsed EDI + an EDI process dict and produces a target-format file. |
| **Backend** | A plugin that takes a filename and ships it to an external destination. |
| **Tweaker** | Optional post-conversion stage that rewrites records (substitutions, padding). |
| **Tick** | One polling cycle of the folder watcher (`WatcherSupervisor`). |
| **Stage** | One of Validator → Splitter → Converter(s) → Tweaker(s). Not including Send. |
| **Golden file** | A recorded expected-output used by parity tests to detect regressions. |
| **Base-dir** | The `BFS_BASE_DIR` root that all configured folder paths resolve against. Legacy absolute paths are stripped to relative paths at import time. |
| **Bearer token** | The long-lived `BFS_API_TOKEN` env-var secret used by Phase 6.2 auth. Not a JWT. |
| **Soft-delete** | Phase 6.4 — a delete that moves the row to a `folders_deleted` tombstone for `FOLDERS_DELETED_TTL_DAYS` instead of permanently removing it. |
| **Local-first** | The deployment posture: single host, default bind `127.0.0.1`, no inbound network surface, no cloud sync. |
| **Run** | One invocation of the processing pipeline for a folder (or all folders); tracked in `RunStore`. |
| **Processed-files ledger** | The per-(folder, content) idempotency record. The query that prevents duplicate processing. |
| **Error ledger** | The `dispatch_errors` table; webapp-owned; consecutive-failure dedupe; severity classification (`major` / `minor`). |

### 14.3 Version Constraints

- **Python:** 3.11+ (per `pyproject.toml` `requires-python = ">=3.11"`).
- **Web framework:** FastAPI ≥ 0.115.0; uvicorn ≥ 0.30.0.
- **DB driver:** SQLAlchemy ≥ 1.4.49.
- **No Qt.** PyQt5 was removed in the webapp-pivot; PySide6 references
  in legacy docs are no longer applicable.

### 14.4 Changelog

| Date | Author | Change |
|------|--------|--------|
| 2026-07-06 | Project Owner | Initial draft — project intent spec derived from existing `docs/` and `specs/` workflow. PyQt5 GUI canonical. |
| 2026-08-04 | Project Owner | §3.7 addendum — webapp-pivot shipped (commit `9864dc7e5`). PyQt5 GUI source tree removed; webapp is the only operator surface. |
| 2026-08-18 | Project Owner | §3.8 addendum — desktop retirement decision. `interface/` Qt-free orphan marked for deletion in Phase 7. Phase 6 (production hardening) added. |
| 2026-08-21 | Project Owner | Full rewrite post-Phase 7b. This document is now the canonical project spec. Addenda §3.7 / §3.8 collapsed into the main body. Pipeline redesign §3.1 diagram updated to reflect the 2026-08-21 source tree. Phase 5/6/7/7b/8 status brought current. |
