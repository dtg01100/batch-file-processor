# Spec: Batch File Sender — Project Intent

**Status:** DRAFT
**Author:** Project Owner
**Created:** 2026-07-06
**Updated:** 2026-07-06

> **Purpose of this document:** This is a *forward-looking intent spec* — what the Batch File Sender is trying to be. For *what currently exists* and *how it is built today*, see the linked design docs throughout. For *implementation tasks*, see `specs/<feature-name>.md` documents derived from this one.

---

## 1. Summary

Batch File Sender is a desktop application that watches local folders for incoming EDI (Electronic Data Interchange) files, validates and reshapes them through a configurable pipeline, converts them into one of many business-specific output formats, and delivers the result to one or more configured destinations (FTP, email, local copy, HTTP). All configuration, processing history, and operator state persist in a local SQLite database through a versioned schema.

The product's defining characteristic is that **the pipeline is fully user-configurable at runtime** — folders, converters, backends, parameters, and delivery settings are all edited through the GUI without code changes or restarts.

---

## 2. Background

### 2.1 Problem Statement

Operators in retail/distribution businesses receive EDI feeds (typically A/B/C "Three-Letter" format with custom record layouts) from trading partners that must be reshaped into retailer-specific formats (CSV, Excel, Fintech, E-Store, Scannerware, etc.) and delivered to each retailer's required destination (their FTP drop, their email intake, their internal share). Each trading partner has a unique combination of:

- input record layout
- split rules (split by some field value, or emit N records per output)
- output format
- delivery destination and credentials
- tweak rules (post-conversion record rewrites)

Doing this by hand — or with bespoke cron jobs and shell scripts — is brittle, un-auditable, and requires a developer for every new trading partner.

### 2.2 Motivation

A single operator-facing tool should let a non-developer:

1. Point the app at a folder.
2. Describe the file format (or select from a library of known EDI formats).
3. Pick an output format.
4. Pick a destination.
5. Walk away.

…and have every file that lands in the folder be processed, delivered, and logged, without anyone touching a shell. New trading partners are onboarded in minutes, not days. Failures are visible. Re-processing after a destination outage is one click.

### 2.3 Prior Art

In-tree documentation that informs this spec:

| Document | What it covers |
|----------|----------------|
| `docs/ARCHITECTURE.md` | Current as-built system architecture |
| `docs/PROCESSING_PIPELINE.md` | End-to-end pipeline behavior |
| `docs/PROCESSING_DESIGN.md` | Pipeline internals (validator, splitter, converter, tweaker, sender) |
| `docs/PLUGIN_DESIGN.md` / `docs/PLUGIN_DEVELOPER_GUIDE.md` | How converters and backends are added |
| `docs/PLUGIN_ARCHITECTURE.md` | Plugin discovery model |
| `docs/DATABASE_DESIGN.md` | Schema, migrations, repository pattern |
| `docs/GUI_DESIGN.md` / `docs/UI_LAYOUTS.md` | Qt UI structure and layouts |
| `docs/TESTING_DESIGN.md` | Test layering and markers |
| `docs/CONVERTER_OUTPUT_FORMATS.md` | Output format compatibility matrix |
| `docs/ERROR_HANDLING_DESIGN.md` | Error capture, retries, alerting |
| `docs/STRUCTURED_LOGGING.md` | Logging conventions |
| `docs/MIGRATION_DESIGN.md` | Schema migration policy |
| `AGENTS.md` | Project-wide technical reference (architecture, imports, anti-patterns) |
| `DOCUMENTATION.md` | Long-form developer/user guide |
| `specs/README.md`, `specs/TEMPLATE.md` | Existing spec workflow this document follows |

Out of scope for this spec (managed elsewhere):

- Single-feature specs in `specs/<feature>.md` (e.g., new converter onboarding).
- `openspec/changes/` change-set proposals.
- Bug-hunting audits (`CODE_AUDIT_FINDINGS.md`, `BUGFIX_SUMMARY.md`).

---

## 3. Design

### 3.1 Architecture Alignment

This spec **endorses** the architecture documented in `docs/ARCHITECTURE.md` rather than replacing it. The product intent maps to architecture as follows:

| Intent (this spec) | Realized in |
|--------------------|-------------|
| Folder-driven, automatic processing | `dispatch/orchestrator.py` + `dispatch/services/folder_processor.py` |
| Validation, splitting, conversion, tweaks as discrete stages | `dispatch/pipeline/{validator,splitter,converter,tweaker}.py` |
| Many output formats, none hard-coded | `dispatch/converters/convert_to_*.py` (17 plugins) |
| Many delivery destinations, none hard-coded | `backend/{email,ftp,copy,http}_backend.py` |
| Pluggable without restart | Filesystem-based plugin discovery |
| Persistent configuration | SQLite via `core/database/` framework-agnostic layer |
| Versioned schema evolution | `migrations/` + `folders_database_migrator.py` |
| Operator-facing UI | `interface/qt/` PyQt5 widgets, dialogs, theming |
| Auditable processing | `dispatch/error_handler.py`, structured logging |

This means: **changes that contradict the patterns documented in `docs/` are out of scope until this spec is amended.**

### 3.2 The Product as Five Capabilities

The product's intent reduces to five user-visible capabilities. Each one is a contract for the rest of the system.

#### 3.2.1 Capability A — Folder-bound processing

The operator defines a **folder** with:

- a watched input directory,
- one or more converters to apply,
- one or more destinations to ship the result to,
- optional split and tweak steps,
- per-format parameter overrides,
- enable/disable and schedule.

**Intent contract:** Adding, editing, or removing a folder must be possible through the GUI without restarting the application, daemon, or any worker process. Changes take effect on the next polling tick (see 3.2.5).

#### 3.2.2 Capability B — File discovery with idempotency

For every enabled folder, the app must:

1. Enumerate candidate files in the input directory.
2. Filter out files already processed (by content checksum or mtime+size, per folder config).
3. Process each remaining file through the pipeline.
4. Mark it processed only on successful delivery to **all** required backends (failure policy is user-configurable per folder — see 3.2.4).

**Intent contract:** A file is processed exactly once per (folder, content). Replacing a file with different content re-triggers processing. Restarting the app mid-run must not duplicate-process nor silently-drop a file.

#### 3.2.3 Capability C — Pipeline as four ordered stages

Each file flows through, in order:

```
Validator  ->  Splitter  ->  Converter(s)  ->  Tweaker(s)  ->  Send
```

- **Validator** rejects malformed EDI before any work is done (see `docs/PROCESSING_DESIGN.md`).
- **Splitter** segments multi-record files into one-or-many output files.
- **Converter(s)** transform EDI into the target business format. Multiple converters in series are allowed per folder.
- **Tweaker(s)** apply post-conversion record-level rewrites (lookup substitutions, padding fixes, header tweaks).
- **Send** is not a pipeline stage but the delivery step after the chain completes.

**Intent contract:** Each stage has a single, documented `PipelineStep.execute()` interface (per `dispatch/pipeline/interfaces.py`). A stage that succeeds must not be re-run when a downstream stage fails — checkpointing is per-stage, not whole-file.

#### 3.2.4 Capability D — Multi-destination delivery

A folder ships its output to N destinations. Each destination is a backend instance (FTP, SMTP, local copy, HTTP). The user picks:

- which backends to use (an ordered list),
- per-backend credentials,
- per-backend retry policy,
- whether a failure in any backend blocks the others (default: do not block),
- whether a failure in all backends rolls the file back to "unprocessed" so it is retried on the next tick.

**Intent contract:** No backend is hard-coded as "the" destination. New backends are added by dropping a `*_backend.py` module into `backend/` and following the documented `do(process_parameters, settings_dict, filename, disable_retry) -> bool` signature (per `docs/PLUGIN_DESIGN.md`).

#### 3.2.5 Capability E — Operator observability

The operator must always be able to answer, without leaving the app:

- What folders exist and are enabled/disabled?
- What is each folder's current state (idle, processing, error)?
- What files were processed when, with what status, to which destinations?
- What errors occurred, for which file, with what stack trace?
- What is in the current tick's work queue?

**Intent contract:** All of the above is queryable from the main window and persisted to the SQLite database for after-the-fact review. Errors are recorded to a dedicated `errors` table via `dispatch/error_handler.py`. No error is swallowed silently (enforced by AGENTS.md anti-pattern rules).

### 3.3 What the Product Is Not

Stating non-goals is part of the spec. The product is explicitly **not**:

- **Not a cloud service.** No SaaS tier, no hosted backend. All data stays on the operator's machine. (Future: optional read-only cloud sync is *allowed*; anything that pushes data off-box as a default behavior is not.)
- **Not an EDI format converter toolkit.** It is an *operator-facing* configuration product that *uses* converters. Authors of new converters interact with the Python API; operators interact with the GUI.
- **Not a real-time / streaming system.** Folder polling is the model. Files are entire before processing begins.
- **Not a multi-tenant product.** One SQLite database per Windows user profile. No shared central server.
- **Not Python-3.12+ or Qt6.** Hard-pinned to Python 3.11 and PyQt5 5.15 (per AGENTS.md version constraints — these are deployment realities, not preferences).

### 3.4 Non-Functional Requirements

| Category | Requirement | Source of truth |
|----------|-------------|-----------------|
| Portability | Single-user, single-machine, works offline | Distribution is a Windows .exe (PyInstaller) or local Python venv |
| Reliability | App crash during processing must not corrupt the DB (WAL mode + transactions) | `core/database/connection.py` |
| Safety | Re-running must not double-process or re-deliver a file | Per-folder processed-files table |
| Reversibility | Schema evolution is always forward-only with automatic backups before each migration | `migrations/` |
| Testability | Every plugin and every stage has a unit test; pipeline end-to-end has integration tests; UI flows have smoke tests | `docs/TESTING_DESIGN.md` |
| Logging | Structured logging with `folder_alias`, `file_path`, `stage` context on every record | `docs/STRUCTURED_LOGGING.md` |
| Observability | Errors recorded to DB even when logging fails | `dispatch/error_handler.py` |
| Performance | Single file processed in under 5 s on a modern Windows desktop; backlog drained in foreground or worker thread | Out of scope to over-optimize |
| Security | Credentials stored only in the local SQLite DB; never logged; never sent off-machine except to configured destinations | Implicit; no inbound network surface |

### 3.5 Release Channels

The product ships as:

1. **PyInstaller single-file Windows .exe** — primary production distribution (`build_windows.sh`, `main_interface.spec`).
2. **Source + venv** — developer / fallback install (`pip install -r requirements.txt`; `python main_qt.py`).
3. **Headless / automatic mode** — same codebase, `-a` flag for scheduled runner mode (folder watcher runs, no Qt window shown).

### 3.6 Alternatives Considered

| Alternative | Pros | Cons | Why Not Chosen |
|-------------|------|------|----------------|
| Browser-based web UI | Easier distribution, no Qt | Requires a server; cross-platform desktop parity lost; complicates single-user local-first story | Keep PyQt5; per AGENTS.md |
| Per-folder YAML/JSON config files | GitOps, version controllable | Brittle for operators; schema migrations get ugly; loses the GUI value proposition | SQLite + GUI remains canonical |
| AsyncIO pipeline | Modern concurrency | Not compatible with PyQt5 worker-thread model used today; rewrite cost | Keep `ThreadPoolExecutor` for now |
| Hard-coded converters | Faster MVP | Defeats the operator-onboarding-in-minutes value prop | Plugin discovery remains canonical |
| Cloud-hosted config sync | Multi-machine operators | Privacy / connectivity / compliance concerns; out of scope for local-first product | Optional later |

---

## 3.7 Addendum (2026-08-18) — Webapp Deployment Model

The webapp-pivot (commit `9864dc7e5`) reversed the §3.6 rejection of a
browser-based UI and ships FastAPI + a static SPA in the same repo as
the dispatch engine. This addendum captures the new deployment model
and the security posture it requires.

**Deployment posture:** single-host, single-operator, local-first. A
fresh `python -m webapp.main` binds `127.0.0.1:8000` (Phase 6.1) — no
inbound network surface. Remote access is an explicit opt-in via
`BFS_HOST=0.0.0.0` and `BFS_API_TOKEN=<secret>` (Phase 6.2). The
bearer-token is a long-lived env-var secret, not a JWT — the spec is
single-user, so refresh flows would add ceremony for zero operational
benefit. TLS termination is deliberately out of scope: an operator
who wants to expose the dashboard remotely puts nginx or Caddy in
front, and the bearer-token + nginx-TLS pairing is documented as the
canonical remote-access shape.

**Why this is consistent with §3.4 ("no inbound network surface"):**
the default bind makes that statement literally true on a fresh
install. Remote access is the explicit exception that requires two
deliberate operator actions (env var + flag), each documented in the
README. The threat model is unchanged: credentials remain in the
local SQLite DB; the bearer-token is an authentication gate, not a
credential store.

**Why this changes §3.5 (release channels):** the webapp replaces the
"source + venv" distribution shape with `docker compose up -d` or
`uvicorn webapp.main:app`. The PyInstaller single-file .exe remains
the primary production distribution; the webapp is a parallel option
for operators who want remote access from a different machine. The
two share the same SQLite-backed `dispatch/` engine, so a single
configuration carries across both.

**Why the spec still rejects the §3.6 alternative wholesale:**
the original rejection was about *the desktop app existing at all*
in a world where a single-user local-first product could be served
by a single binary. The webapp-pivot (2026-08-04) removed the
PyQt5 GUI source tree; the 2026-08-18 desktop-retirement decision
removes the rest. The webapp is now the **only** operator surface.
The §3.6 reasoning remains in this document as a record of the
architectural choice; it does not bind future work.

**Soft-delete + restore (Phase 6.4):** the desktop GUI's permanent
delete was a known foot-gun; the webapp ships soft-delete with a
configurable restore window (`FOLDERS_DELETED_TTL_DAYS`, default 30
days, clamped `[1, 365]`). The implementation lives in
`webapp/routers/folders.py::api_delete_folder` (moves the row to a
`folders_deleted` tombstone) + `api_restore_folder` (re-inserts with
the original id, 409 on id-reuse, 410 on expired). The trim job
(`SoftDeleteTrimSupervisor`) is a daemon thread started by the
FastAPI lifespan; `interval_seconds=0` is the synchronous-test
override. The spec's release-channel rationale (§3.5) covers why the
trim defaults to 1 h rather than running on every delete.

---

## 3.8 Addendum (2026-08-18) — Desktop Retirement

The 2026-08-18 decision to **completely drop the desktop version**
supersedes §3.7's "PyQt5 GUI is still the recommended path for an
operator who works directly on the host" carve-out. Two layers of
desktop-era code remain after the §3.7 addendum:

1. The PyQt5 GUI source tree (`interface/qt/`) — already removed
   in the 2026-08-04 webapp-pivot.
2. The Qt-free `interface/` business-logic layer (16 files,
   3,819 lines) — orphaned; verified no callers in `webapp/` or
   `dispatch/` before Phase 7's deletion.

Both deletions are tracked in `specs/webapp-phase-7-operator-confidence.md §3.3`.

**Release channels (§3.5) collapse from three to two:**

- ~~PyInstaller single-file Windows .exe~~ — removed. The webapp's
  distribution shape is `docker compose up -d` or `uvicorn webapp.main:app`.
  An operator who wants a single-file distribution can build one
  with PyInstaller against the webapp source; it's not a product
  commitment.
- Source + venv — still supported. `pip install -r requirements.txt`
  + `python -m webapp.main`.
- Headless / automatic mode — subsumed by the webapp's scheduler
  endpoint (`POST /api/schedule`). The `-a` flag is no longer
  applicable to a webapp deployment.

The webapp is the only operator surface going forward. Future
specs (Phase 8+) operate on the assumption that there is no
desktop alternative.

---

## 4. Implementation Plan

> **This is the product-level roadmap, not a feature spec.** Each phase corresponds to a deliverable the operator can see. Individual feature specifications live in `specs/<name>.md`.

### Phase 1 — Solidify the foundation (in progress / completed)

- [x] Core pipeline orchestrator (`dispatch/orchestrator.py`)
- [x] Plugin discovery for converters and backends
- [x] SQLite-backed configuration and processed-files tracking
- [x] Versioned migrations v5 to v40
- [x] PyQt5 main window with folder list, processing dialog, error viewer

### Phase 2 — Operator polish

- [ ] Per-folder retry / rollback policy UI
- [ ] Drag-and-drop file-onto-window to add a new folder
- [ ] Inline diff view of converter parameter changes
- [ ] Plugin status panel: show discovered converters and backends, their parameter schemas, and "last loaded" version

### Phase 3 — Reliability hardening

- [ ] Crash-safe processing: atomic rename of in-flight files
- [ ] Per-tick metrics: files/second, average pipeline latency, error rate
- [ ] Configurable dead-letter destination (per folder)
- [ ] End-to-end smoke harness usable from CI

### Phase 4 — Distribution

- [ ] Signed Windows installer (currently single-file .exe)
- [ ] Auto-update channel (read from a local-only manifest)
- [ ] Headless automatic mode run as Windows Scheduled Task by default

### Phase 5 — Optional conveniences

- [ ] Local read-only web status page (`http://127.0.0.1:port/status`)
- [ ] Config export/import for moving folder setups between machines
- [ ] Pluggable UPC lookup tables sourced from CSV at runtime

---

## 5. Database Changes

The canonical database layer is documented in `docs/DATABASE_DESIGN.md` and `docs/MIGRATION_DESIGN.md`. As a *product* spec, this document concerns itself only with schema-intent rules, not column lists.

### 5.1 Schema Discipline (Intent)

The schema carries four kinds of information:

1. **Application settings** — global config (paths, defaults).
2. **Folder definitions** — every configured folder and its pipeline configuration.
3. **Processed-file ledger** — one row per (folder, file content) the system has handled; the canonical idempotency record.
4. **Error ledger** — every captured error with full context, queryable from the GUI.

These four kinds **must not share a table**. Cross-joins are forbidden. New tables belong to exactly one of these categories.

### 5.2 Migration Discipline (Intent)

- Migration is forward-only. No down-migrations.
- A backup is taken before every migration, in a folder the operator can locate.
- Each migration has a corresponding test in `tests/integration/database_schema_versions.py`.
- A failed migration leaves the DB at the pre-migration version on disk and reports failure in the UI.

These rules are non-negotiable per the existing `docs/MIGRATION_DESIGN.md`. This spec endorses them.

### 5.3 Schema Changes Required by This Spec

This spec itself **introduces no schema change**. Schema changes belong in the feature specs (`specs/<feature>.md`) and migration files (`migrations/`) that implement the phases above.

---

## 6. Testing Strategy

### 6.1 Testing Layers

Refer to `docs/TESTING_DESIGN.md` for full coverage of markers and conventions. As an *intent* spec:

| Layer | Marker | Covers |
|-------|--------|--------|
| Unit | `unit` | Pipeline stages, converter/output generation, validators, backend `do()` |
| Integration | `integration` | End-to-end folder -> pipeline -> backend with in-memory DB |
| Backend parity | `backend` | Backend behavior equivalence with golden files |
| Conversion parity | `conversion` | Each converter's output compared to a recorded golden file |
| UI smoke | `qt` | Dialog open/close, form validation, signals emitted (`-n0`, single-threaded) |

### 6.2 Intent-Level Test Invariants

These invariants must hold for every release regardless of what feature work is in progress:

- A folder with a single valid file and a single working backend ends in exactly one row in the processed-files ledger.
- A folder with a working frontend file but a failing backend does *not* add a processed-files row.
- Killing the app mid-pipeline and restarting does not produce duplicate downstream deliveries.
- Every discovered converter module produces a non-empty output for at least one golden EDI input.
- Every discovered backend module has at least one test that asserts the `do()` contract.

### 6.3 Coverage Requirements

| Code Area | Minimum Coverage |
|-----------|------------------|
| `dispatch/` (orchestration + pipeline stages) | 85% lines |
| `dispatch/converters/` (per-converter) | 80% lines, with golden-file parity test |
| `backend/` (per-backend) | 80% lines, with at least one harness test that exercises `do()` |
| `core/database/` | 90% lines (high-risk layer) |
| UI dialogs (`interface/qt/dialogs/`) | Smoke test per dialog (open, fill, accept, cancel) |

These minima are enforced by CI once that exists (see Phase 4 in §4).

---

## 7. Risk Assessment

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| A new converter returns a non-UTF-8 file and downstream backends choke | Med | Med | Encoding contract enforced by `do()` wrapper; validator catches malformed output |
| Backend credentials leak via logs | Med | High | Credentials loaded only at the moment of send; log filters redact; no log of `process_parameters` |
| Long-running pipeline holds the GUI thread | Med | High | Pipeline runs in `ThreadPoolExecutor` worker; UI remains responsive; cancellation signal supported |
| Operator deletes a file mid-process | Low | Med | Atomic rename-in-progress pattern (Phase 3); file open with `O_EXCL`-style check where supported |
| New EDI format added but no converter exists | Med | Med | Format library in `edi_formats/` is documentation, not contract; unknown formats fail validation with clear message |
| Migrations on a corrupted DB brick the install | Low | High | Automatic pre-migration backup + integrity check before applying (per `docs/MIGRATION_DESIGN.md`) |
| Plugin added at runtime with a broken signature crashes the daemon | Low | High | Plugin discovery wrapped in isolated importer that quarantines broken modules |
| Auto-update channel pushes a bad build | Med | High | Out of scope today; Phase 4 will require signed manifests and human approval gate |

### 7.1 Rollback Plan

Every release is a single-file .exe that can be replaced with the previous one. The SQLite DB lives next to the exe; replacing the exe does not touch the DB. Schema migrations are forward-only — if v40 fails on a customer's machine, the operator reverts the .exe to the v39 build, restores from the auto-backup taken just before the migration, and continues. Migrations from v40 onward can be re-attempted after a fix.

---

## 8. Success Criteria

The spec is "implemented" when **all** of the following are true:

- [x] An operator can define a folder, attach a converter + an FTP backend, drop a file in the watched directory, and see the converted file appear on the FTP server within one polling tick. *Achieved today.*
- [x] Every processing attempt is reflected in the database with status, destination, and timestamp. *Achieved today.*
- [ ] All five capabilities in §3.2 are documented as GUI flows in `docs/UI_LAYOUTS.md` with screenshots. *Partial today.*
- [ ] Every Phase 2 / Phase 3 item in §4 has a corresponding `specs/<feature>.md` ready for implementation.
- [ ] The product ships as a signed installer; auto-update channel reads a local-only manifest.
- [ ] No item in §3.3 is violated by any shipped feature.
- [ ] No silent error swallowing anywhere in `dispatch/` or the plugin layer (enforced by AGENTS.md).

---

## 9. Open Questions

1. Should the headless / automatic mode inherit GUI folder definitions from the same DB, or use a separate "runner" DB? (Decision: same DB; resolved at auto-mode launch by reading folders marked `auto_run=true`.)
2. Does the app own the FTP/email threadpool, or does each backend manage its own? (Decision: app owns, via `SendManager`, to make global retry policy uniform.)
3. What is the maximum reasonable folder count for a single operator profile? (Unknown; monitor in the field. If exceeded, profile splitting is a Phase 5+ concern.)
4. Is there a customer requirement for an HTTP webhook destination alongside FTP/email/copy? (Today: yes, `backend/http_backend.py` exists; spec already names it under Capability D.)
5. Should Phase 4's auto-update require administrator elevation on Windows, or run as the current user? (Undecided; defer until Phase 4 starts.)
6. Are UPC lookup tables always static for a given customer, or do they change monthly? (Affects Phase 5 "pluggable UPC lookup tables from CSV" — defer until Phase 5.)

---

## 10. Appendix

### 10.1 Cross-Reference

| Topic | This Spec | Canonical Doc |
|-------|-----------|----------------|
| Architecture overview | §3.1 | `docs/ARCHITECTURE.md` |
| Pipeline stages | §3.2.3 | `docs/PROCESSING_DESIGN.md`, `docs/PROCESSING_PIPELINE.md` |
| Plugin model | §3.2.3, §3.2.4 | `docs/PLUGIN_DESIGN.md`, `docs/PLUGIN_DEVELOPER_GUIDE.md`, `docs/PLUGIN_API_REFERENCE.md`, `docs/CONVERTER_OUTPUT_FORMATS.md`, `docs/CONVERTER_PLUGIN_GUIDE.md` |
| Database | §5 | `docs/DATABASE_DESIGN.md`, `docs/MIGRATION_DESIGN.md` |
| GUI flows | §3.2, §3.5 | `docs/GUI_DESIGN.md`, `docs/UI_LAYOUTS.md` |
| Error handling | §3.2.5 | `docs/ERROR_HANDLING_DESIGN.md` |
| Logging | §3.4 | `docs/STRUCTURED_LOGGING.md`, `AGENTS.md` |
| Testing | §6 | `docs/TESTING_DESIGN.md` |
| Build / distribution | §3.5 | `Makefile`, `build_windows.sh`, `main_interface.spec`, `Dockerfile*` |
| Version constraints | §3.3 | `AGENTS.md` (Python 3.11, PyQt5 5.15) |
| API surface | §3.2.2, §3.2.3, §3.2.4 | `docs/API_SUMMARY.md`, `docs/COMPONENT_COMMUNICATION_TEST_MATRIX.md` |
| Configuration | §5 | `docs/CONFIGURATION_DESIGN.md` |
| Validation rules | §3.2.3 | `docs/VALIDATION_DESIGN.md`, `docs/EDI_FORMAT_DESIGN.md` |

### 10.2 Glossary

| Term | Meaning |
|------|---------|
| **Folder** | One configured input directory plus its pipeline + destinations (the unit of work in the GUI). |
| **EDI** | Electronic Data Interchange — here, A/B/C "Three-Letter" record-based feeds from trading partners. |
| **Converter** | A plugin that takes parsed EDI + an EDI process dict and produces a target-format file. |
| **Backend** | A plugin that takes a filename and ships it to an external destination. |
| **Tweaker** | Optional post-conversion stage that rewrites records (substitutions, padding). |
| **Tick** | One polling cycle of the folder watcher (`FolderProcessor` per folder). |
| **Polling tick** | The cadence at which the app re-enumerates input folders. Configurable globally; default from `interval_seconds` on the folder. |
| **Stage** | One of Validator → Splitter → Converter(s) → Tweaker(s). Not including Send. |
| **Golden file** | A recorded expected-output used by parity tests to detect regressions. |

### 10.3 Change Log

| Date | Author | Change |
|------|--------|--------|
| 2026-07-06 | Project Owner | Initial draft — project intent spec derived from existing `docs/` and `specs/` workflow. |

