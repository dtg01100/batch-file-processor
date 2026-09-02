# Roadmap: Batch File Processor — Webapp

**Status:** DRAFT
**Author:** Project Owner
**Created:** 2026-08-31
**Updated:** 2026-08-31

> **Purpose of this document:** this is the **strategic roadmap**
> for the webapp version of the Batch File Processor. Where the
> [project spec](./PROJECT_SPEC.md) is *intent*, the
> [webapp spec](./WEBAPP_SPEC.md) is *current state*, and the
> per-phase specs are *implementation narratives*, this document
> is *sequencing*: what work is queued, in what order, with what
> dependencies, what effort, and what triggers would change the
> plan.
>
> The roadmap is **living** — it changes when the product
> changes. The current view (2026-08-31) is captured in §2;
> the near-term plan is §4; the mid-term plan is §5; the
> deferred-but-not-dropped list is §6; the open decisions
> that gate future work are §7; the trigger conditions that
> would re-prioritize the roadmap are §8.
>
> For per-phase implementation detail (file lists, test plans,
> success criteria), follow the cross-references in §10.

---

## Table of Contents

1. [Vision](#1-vision)
2. [Current State (2026-08-31)](#2-current-state-2026-08-31)
3. [Strategic Priorities](#3-strategic-priorities)
4. [Near-Term: Next 30 Days](#4-near-term-next-30-days)
5. [Mid-Term: Next 90 Days](#5-mid-term-next-90-days)
6. [Long-Range / Defensive (gap-3.x)](#6-long-range--defensive-gap-3x)
7. [Open Decisions That Gate Future Work](#7-open-decisions-that-gate-future-work)
8. [Trigger Conditions](#8-trigger-conditions)
9. [Effort & Risk Calibration](#9-effort--risk-calibration)
10. [Cross-References](#10-cross-references)

---

## 1. Vision

This is an **internal tool**. One project owner, one workstation
(or one Docker host), one operator role, zero external users.
The product exists because the project owner needs to process
EDI files in a runtime-configurable way without writing code
for each trading partner. Every other consideration is
downstream of that.

The webapp version of the Batch File Processor will become
**the single, well-bounded, single-host operator tool** for
that workload: a non-developer configures folders, picks
converters and destinations, and the system runs. The
product's defining property — *runtime-configurable pipeline
without code changes* — stays. The defining costs of the
current state — *engine code living under a top-level `dispatch/`
package that exists only because the desktop app used to import
it; a flat-bag configuration schema; two parallel progress
reporters; no structured error timeline* — get paid down over
time.

### 1.1 What "internal tool" means here

The internal-tool framing is **load-bearing**, not cosmetic. It
determines what gets built, what gets deferred, and what gets
rejected outright:

| Question | External-product answer | Internal-tool answer |
|----------|-------------------------|---------------------|
| Who uses it? | Customers with SLAs | The project owner |
| What features get prioritized? | Customer demand | Project-owner workflow |
| What's the cost of a regression? | Lost customer trust | Project-owner time |
| What's the cost of a missing feature? | Churn risk | Project-owner annoyance |
| Is "we'll add it when someone asks" OK? | Yes (SaaS) | No — there is no "someone" |
| Is "we'll never need this" OK? | Risky (might lose deals) | Often the right call |

The downstream effect of the internal-tool framing:

- **Many "defensive" gap-3.x items are moot, not just deferred.**
  Mobile layout, plugin hot-reload, third-party API, public
  audit log — these are N/A when there's one operator on one
  host. Section 6 lists them as "rejected outright," not "parked
  indefinitely."
- **The project owner is the only customer signal.** "Will this
  be useful?" is the question; "what's the demand?" isn't.
- **Defensive engineering has a higher bar.** A multi-user
  deployment needs TLS, audit, encryption even if "no one
  asked for it yet" because the threat model exists. An
  internal tool with one operator on one workstation doesn't
  have that threat model — the host's full-disk encryption
  covers the realistic risks.
- **Roadmap triggers are project-owner-driven, not
  market-driven.** Section 8's triggers reference the project owner's
  own decisions, not hypothetical external users.

### 1.2 Three north-stars

1. **One process, one tree.** Every line of processing code lives
   under `webapp/`. The top-level `dispatch/`, `backend/`,
   and `core/` packages either move under `webapp/` or shrink
   to true shared utilities. No code "happens to be" outside
   the webapp. (For an internal tool, this matters *more* than
   for an external product: there's no team to spread the
   context across, so the codebase has to be navigable by one
   person.)
2. **One configuration shape.** The `folders` table either
   stays flat (with a typed adapter) or moves to a structured
   `folder_config` table — but it doesn't keep both shapes in
   the codebase forever. The choice is made once and documented.
3. **One error timeline.** A failing run produces a single,
   queryable, mergeable sequence of events (errors, retries,
   progress, per-folder status) — not three separate persistence
   paths. The project owner with a failing run reads one
   timeline and fixes it.

### 1.3 What the product is **not** heading toward

The single-user local-first posture
(PROJECT_SPEC.md section 3.4) is the fixed point
everything else rotates around. Specifically:

- Not multi-host. Not multi-user. Not cloud-synced.
- Not a public API. Not third-party plugin authors. Not a
  marketplace.
- Not mobile-first. Not a tablet app. Not a phone notification
  service.
- Not SOC 2 / HIPAA / PCI compliant (the host's compliance
  posture covers it; the webapp itself doesn't need its own).
- Not a customer-facing product with SLAs, support contracts,
  or onboarding flows.

The shape the product is heading toward is **"a really good
shell script that has a web UI and survives restarts."** The
project owner runs it on their workstation, points it at the
data volume, and forgets about it until something breaks.


---

## 2. Current State (2026-08-31)

Snapshot of the working tree at `webapp-pivot` branch head
(`2f29cca57`).

### 2.1 Phases

| Phase | Status | Last commit | Days since |
|-------|--------|-------------|-----------|
| **Pivot** (drop Qt GUI, ship FastAPI + SPA) | Landed | `9864dc7e5` (2026-08-04) | 27 |
| **5** (Observability) | Landed | `80ef8951c` (2026-08-17) | 14 |
| **6** (Production hardening) | Landed | `9ee5b0daa` (2026-08-18) | 13 |
| **7** (Operator confidence + desktop retirement partial) | Landed | `64f4db1fc` (2026-08-18) | 13 |
| **7b.1** (drop `interface/` imports from surviving tests) | Landed | `64e7c6236` (2026-08-19) | 12 |
| **7b.2** (delete `tests/unit/interface/`) | Landed | `2f29cca57` (2026-08-19) | 12 |
| **7b.3** (delete `interface/` + `tests/integration/`) | **Staged, not committed** | — | working tree |
| **8** (Pipeline redesign — design spec) | **Approved** | `a4642f29f` (2026-08-18) | 13 |
| **9+** (Phase 8 implementation) | Not started | — | — |

### 2.2 Code shape

| Tree | Purpose | Lines | Notes |
|------|---------|-------|-------|
| `webapp/` | HTTP layer, SPA, background services | 7,899 | 11 routers, 49 endpoints, 3 background threads |
| `webapp/static/` | SPA source | 4,716 | no bundler, no framework |
| `tests/webapp/` | Webapp tests | ~5,800 | 21 Python + 4 JS test files |
| `dispatch/` | Processing engine (pre-pivot) | 14,952 | 55 files; the Phase 8 target |
| `backend/` | Delivery plugins | ~5,000 | 4 backends + 3 client modules |
| `core/` | Shared utilities + EDI parsing | ~8,000 | stable, not in scope for restructuring |
| `interface/` | **DELETION STAGED** (Phase 7b.3) | 0 effective | 16 files marked `D` in `git status` |
| `tests/integration/` | **DELETION STAGED** (Phase 7b.3) | 0 effective | 37 files marked `D` in `git status` |
| `tests/unit/interface/` | **DELETED** (Phase 7b.2) | 0 | 13 files removed in commit `2f29cca57` |

### 2.3 What's *not* in the tree yet (gap-3.x deferred)

Per [docs/architecture/webapp-gap-audit.md §5.3](../docs/architecture/webapp-gap-audit.md):

- 2.2 TLS termination
- 2.5 Configuration-change audit log
- 2.7 Backup encryption
- 2.8 Mobile-responsive layout
- 2.9 Playwright browser smoke tests
- 2.10 Plug-in hot-reload

Each is defensible to defer; see §6 for the rationale per item.

---

## 3. Strategic Priorities

Ordered by *value per unit of risk*:

1. **Land the in-progress work.** Phase 7b.3 is staged; committing
   it is a 5-minute action that delivers the largest single
   reduction in tree clutter the project has seen. Do this first.
2. **Make the Phase 8 design decisions.** Without decisions, Phase 9
   can't start. Decisions are cheap (reading + writing), high-leverage
   (they gate a multi-month effort), and *time-sensitive* (the
   design spec is now 13 days old and the rationale is freshest
   in mind). Do this in week 2.
3. **Ship Phase 9.1 (rename + minimal-touch move).** The lowest-risk
   piece of Phase 8 implementation; ownership clarity with zero
   behavior change. Roughly 1-2 days of focused work.
4. **Ship Phase 9.2-9.5 (targeted simplifications).** These are
   the structural wins that justified the rename: one progress
   module, async boundary, converter registry, direct error-ledger
   integration. Each is small and independently revertable.
6. **Decide whether to take Candidate C (full async + JSON config).**
   The answer depends on whether Phase 9's adapter-based config
   becomes painful within the first quarter. *This is a
   re-decision, not a pre-decision.*
7. **Defensive gap-3.x work is opportunistic, not pre-planned.**
   Each item gets picked up only when an operator signal
   (a real failure mode, a real deployment scenario, a real
   feature request) makes the cost worth paying.

What is **not** a priority:

- Adding new product capabilities. The webapp has feature parity
  with the desktop ([docs/architecture/webapp-gap-audit.md §2](../docs/architecture/webapp-gap-audit.md));
  new capabilities belong in a follow-on roadmap cycle.
- Re-platforming the webapp framework (FastAPI → something else).
  FastAPI is the right choice; the rewrite cost would be enormous
  for no gain.
- Building multi-host / multi-user features. The product posture
  is fixed at single-host single-user.


---

## 4. Near-Term: Next 30 Days

Concrete, sequenced, with effort estimates. Each item links to the
spec that scopes it. Effort estimates assume one focused
contributor.

### 4.1 Phase 7b.3 — Commit the staged deletions

**Effort:** 0.1 day (≤ 1 hour).
**Owner:** current working-tree author.
**Risk:** Low (the deletions are mechanical; the regression net
is already exercised by 7b.1 + 7b.2).

**Tasks:**

1. `git status` confirms `interface/` + `tests/integration/`
   are deleted (`D` lines).
2. `pytest tests/webapp -q` — confirm the webapp test suite
   is 100% green on the staged deletions.
3. `grep -rn "from interface\|import interface" webapp/ core/
   backend/ dispatch/ tests/` — confirm zero hits in source
   code.
4. `find interface -name "*.py"` — confirm empty.
5. `find tests/integration -name "*.py"` — confirm empty.
6. Commit: `chore: delete interface/ + tests/integration/ (Phase 7b.3)`.
7. Update [docs/architecture/webapp-gap-audit.md §4.2](../docs/architecture/webapp-gap-audit.md)
   to note `interface/` is now gone (rather than pending).

**Exit criterion:** the working tree is clean; `interface/` and
`tests/integration/` are gone; webapp test suite green; the gap
audit reflects reality.

### 4.2 Phase 8 — Decision document

**Effort:** 2-3 days.
**Risk:** Low (decisions are documentation; no code changes).
**Blocker for:** Phase 9 (any commit).

Phase 8's design spec ([webapp-phase-8-pipeline-redesign.md](./webapp-phase-8-pipeline-redesign.md))
already enumerates 10 design decisions in §4 that need answers.
This sub-phase **makes those decisions** (with rationale) and
records them, either in-place in the §4 table or split out into
a sibling decisions file (§9 Open Question #4 of the Phase 8 spec).

**Tasks:**

1. Pick the architecture (Phase 8 spec recommends Candidate B —
   rename + targeted simplifications). Document why.
2. Answer each of the 10 design decisions in Phase 8 §4.1-4.10.
3. Order Phase 9 commits (Phase 8 §6.2 is empty; this fills it).
4. Decide: keep the decisions in §4 or split into
   `docs/architecture/webapp-phase-8-decisions.md`.
5. Update [PROJECT_SPEC.md §11.5](./PROJECT_SPEC.md) and the
   Phase 8 spec's status line to `APPROVED` (from `DRAFT`).

**Exit criterion:** every decision in Phase 8 §4 has an answer
and a rationale; the Phase 9 commit order is recorded; the spec
status reflects reality.

### 4.3 Phase 9.1 — Rename + minimal-touch move

**Effort:** 1-2 days.
**Risk:** Low (no behavior changes; just file moves + import
updates). The three importers (`webapp/runner.py:23`,
`webapp/errors.py:31`, `webapp/routers/system.py:17`) get
updated; everything else stays.
**Depends on:** Phase 8 decisions (specifically DECISION 1 — the
path becomes `webapp/pipeline/` or `webapp/dispatch/`).

**Tasks:**

1. `git mv dispatch/ webapp/pipeline/` (or whatever the
   Phase 8 decision settles on).
2. Update the three importer sites.
3. `grep -rn "from dispatch\|import dispatch" webapp/` —
   confirm zero remaining.
4. `pytest tests/webapp -q` — confirm 100% green.
5. Update `dispatch/AGENTS.md` → `webapp/pipeline/AGENTS.md`.

**Exit criterion:** no `dispatch.*` import in the source tree;
`webapp/pipeline.*` is the canonical path; webapp test suite
green.

### 4.4 Phase 9.2 — Two-progress-reporter merge

**Effort:** 0.5 day.
**Risk:** Medium (need to verify the Qt-friendly reporter has
zero callers after the desktop retirement).
**Depends on:** Phase 9.1 (need the new path first).

**Tasks:**

1. `grep -rn "ProgressReporter" webapp/ tests/webapp/` —
   confirm the SSE path uses `progress_reporting.py` only.
2. Delete the unused reporter module.
3. Consolidate the surviving reporter's interface.
4. `pytest tests/webapp/ -q` — green.

**Exit criterion:** one progress module; no callers of the
deleted one.

### 4.5 Phase 9.3 — Async boundary change

**Effort:** 1 day.
**Risk:** Medium (boundary change touches the lifecycle; needs
cancellation-path coverage).
**Depends on:** Phase 9.1.

**Tasks:**

1. Replace `webapp/runner.py::_worker` thread with
   `asyncio.run_in_executor` calls.
2. Add `asyncio.wait_for` cancellation on operator-initiated
   stop.
3. Cover with `tests/webapp/test_runner.py` cases that
   exercise: in-flight run, cancelled run, timeout run.
4. `pytest tests/webapp/ -q` — green.

**Exit criterion:** the pipeline runs on the FastAPI event
loop's executor pool; cancellation is bounded; tests cover
the edge cases.

### 4.6 Phase 9.4 — Converter registry discovery

**Effort:** 0.5 day.
**Risk:** Low (registry is additive; old hardcoded list can
coexist as a fallback).
**Depends on:** Phase 9.1.

**Tasks:**

1. Add `webapp/converters/registry.py::discover_converters()`
   that scans `webapp/converters/` for `CONVERTER_METADATA`.
2. Add a `CONVERTER_METADATA` attribute to each of the 11
   converter modules.
3. Make `webapp/converters_api.py::all_converter_specs()` a
   thin wrapper.
4. `pytest tests/webapp/test_converters.py -q` — green; the
   registry returns exactly 11 specs.

**Exit criterion:** adding a 12th converter is a one-file change.

### 4.7 Phase 9.5 — Direct error-ledger integration

**Effort:** 0.5 day.
**Risk:** Low (the dispatcher was already webapp-owned via the
adapter; this drops the adapter).
**Depends on:** Phase 9.1.

**Tasks:**

1. Replace `dispatch/error_handler.py::ErrorHandler` calls
   with `webapp/errors.insert_error()` direct calls.
2. Delete `dispatch/error_handler.py` (now `webapp/pipeline/error_handler.py`
   or removed entirely).
3. Verify consecutive-failure dedupe still works.
4. `pytest tests/webapp/test_errors.py tests/webapp/test_runner.py -q`
   — green.

**Exit criterion:** the pipeline writes errors directly to the
webapp ledger; the adapter layer is gone.

### 4.8 Phase 9 sequencing (near-term)

Order matters:

```
[7b.3 commit]  ──►  [Phase 8 decisions]  ──►  [9.1 rename]
                                                  │
                              ┌───────────────────┼───────────────────┐
                              ▼                   ▼                   ▼
                            [9.2 progress]      [9.3 async]       [9.4 registry]
                              │                   │                   │
                              └───────────────────┼───────────────────┘
                                                  ▼
                                            [9.5 errors]
                                                  │
                                                  ▼
                                            [9.6-9.8 mid-term]
```

9.2, 9.3, and 9.4 are **independent** of each other — they can
ship in any order after 9.1. 9.5 depends on the rename only.
9.6-9.8 are mid-term (§5).

---

## 5. Mid-Term: Next 90 Days

After the near-term commits ship and bake, the mid-term queue
opens. Each item is sequenced behind the near-term and behind
its own dependencies.

### 5.1 Phase 9.6 — Watcher integration direct call

**Effort:** 0.5 day.
**Risk:** Low.
**Depends on:** Phase 9.1 + Phase 9.3 (async boundary).

The watcher (`webapp/watcher.py::WatcherSupervisor`) currently
calls `dispatch/orchestrator.DispatchOrchestrator` via
`webapp/runner.py` indirection. After 9.3, the indirection
disappears: the watcher calls `webapp/pipeline/orchestrator.PipelineOrchestrator`
directly via `run_in_executor`.

### 5.2 Phase 9.7 — Test fixture updates

**Effort:** 1 day.
**Risk:** Low (mechanical import path updates).
**Depends on:** Phase 9.1.

Update test fixtures that mock the pipeline to point at the new
import paths. `tests/webapp/conftest.py` gets a
`make_folder_row(...)` factory that knows both the old and new
shapes, so future tests don't hand-roll the 50-column insert.

### 5.3 Phase 9.8 — Documentation

**Effort:** 0.5 day.
**Risk:** Low.
**Depends on:** Phase 9.1.

Write `webapp/pipeline/AGENTS.md` modeled on the existing
`dispatch/AGENTS.md`, but updated to reflect: async-aware
orchestrator, single progress module, registry-driven
converter discovery.

### 5.4 Phase 10 — Decision checkpoint (Candidate C?)

**Effort:** 0 (decision only).
**Risk:** None at this stage; the decision determines whether
Phase 10 implementation is needed at all.
**Trigger:** see §8.

After ~90 days with the Phase 9 tree, re-evaluate the
adapter-based config. If the adapter tax is manageable (≤1
schema addition per quarter), stay on Candidate B. If it's
not, schedule Phase 10 = Candidate C = full async pipeline +
JSON config column.

### 5.5 Mid-term sequencing

```
[9.1+9.3 done]  ──►  [9.6 watcher]
[9.1 done]      ──►  [9.7 fixtures]
[9.1 done]      ──►  [9.8 docs]
[9.1-9.8 done]  ──►  [Phase 10 decision checkpoint]
```

9.6, 9.7, and 9.8 can run in parallel. The Phase 10 checkpoint
is gated on all of them.


---

## 6. Long-Range / Defensive (gap-3.x)

These are the deferred items from
docs/architecture/webapp-gap-audit.md section 5.3. For an **internal tool**
(section 1.1), the right framing for most of them is **"rejected outright,
not just deferred"** — there is no external customer whose needs would
ever justify the work. A small set remain genuinely "parked" because
they're cheap to keep on the radar.

### 6.1 Rejected outright (not on the roadmap)

These items are N/A for an internal tool. They're listed here so
a future contributor can confirm the rationale and move on.

| # | Item | Why rejected for an internal tool |
|---|------|------------------------------------|
| **2.5** | Configuration-change audit log | One operator on one host. "Who changed what when" has zero value when there's exactly one "who." The host's filesystem audit (if enabled) covers any real forensic need. |
| **2.7** | Backup encryption | Backups live in `BFS_DATA_DIR/backups/` on the same volume as the active DB. The realistic threat model is host loss / disk failure / accidental deletion — host full-disk encryption covers all three. Encryption-of-backups-only adds complexity without addressing the threat. |
| **2.8** | Mobile-responsive layout | Operator uses a workstation. Tablet / phone is not a real workflow. The one `@media (max-width: 900px)` rule covers "browser resized small," which is enough. |
| **2.10** | Plug-in hot-reload | The project owner is the only plugin author. `uvicorn` restarts are a 5-second cost; hot-reload would save ~5 seconds per plugin addition (which happens maybe twice a year). Net negative on complexity. |

### 6.2 Parked (genuinely deferred)

These items have a small chance of becoming useful for an
internal tool — usually because the project owner's own
workflow changes. Each has a concrete trigger in section 8.

| # | Item | Why parked | Trigger to re-evaluate |
|---|------|------------|-----------------------|
| **2.2** | TLS termination | The webapp itself doesn't need TLS — reverse proxy covers it. But if the project owner ever wants to expose the webapp *directly* on the LAN (e.g., for a second machine to drive the same dispatch volume), TLS becomes a self-contained option instead of a reverse-proxy concern. | section 8 trigger "expose the webapp without a reverse proxy." |
| **2.9** | Playwright browser smoke tests | JSDOM + python tests cover the surface today. Playwright becomes worth it when the static UI moves weekly and JSDOM misses a CSS or focus-trap bug. | section 8 trigger "CSS regression or focus-trap bug that JSDOM misses." |

### 6.3 What is not on this list

Items that *sound* like deferred work but are actually rejected
without needing a separate row:

- **Multi-user auth.** The webapp's single-user bearer token
  (Phase 6.2) is the right answer; "real" multi-user auth is
  out of scope per PROJECT_SPEC.md section 3.4.
- **Cloud sync / remote control.** The single-host posture is
  the fixed point.
- **A customer-facing support / onboarding flow.** There are no
  customers.

Each of these belongs in PROJECT_SPEC.md's "Alternatives
considered" section (section 3.6), not on a roadmap of work to do.


---

## 7. Open Decisions That Gate Future Work

These are the decisions the roadmap cannot make *for* future
contributors — they require judgment calls based on operator
signals, deployment shape, or technical preference. Each is
captured here so the roadmap is honest about what's decided and
what's not.

### 7.1 Phase 8 design decisions (gating Phase 9)

The Phase 8 spec
([webapp-phase-8-pipeline-redesign.md §4](./webapp-phase-8-pipeline-redesign.md))
enumerates 10 design decisions (4.1 through 4.10). §4.2 of this
roadmap scopes the work of making those decisions; the
decisions themselves remain open until Phase 8's decision
document lands.

The most consequential open decisions:

- **DECISION 1** — config object shape. Adapter dataclass
  (Candidate B's path) vs. new JSON column / child table
  (Candidate C's path). The recommendation is adapter; the
  re-decision point is the Phase 10 checkpoint (§5.4).
- **DECISION 2** — which progress reporter survives. The
  recommendation is the SSE-aware one; verification is
  straightforward (§4.4).
- **DECISION 5** — error-ledger integration path. The
  recommendation is to delete the `ErrorHandler` adapter and
  write directly. The decision is straightforward but the
  verification (consecutive-failure dedupe still works) needs
  coverage.
- **DECISION 9** — no `dispatch/` shim. The recommendation is
  hard-cut. The trade-off is *forcing* downstream forks to
  update on a fixed schedule.

### 7.2 Roadmap-level decisions

- **Candidate B vs. Candidate C now.** Candidate B is the
  recommended path (§4.2). Candidate C is the right answer if
  the operator's domain logic changes drastically in the next
  6 months; we don't expect that, so B is the plan.
- **Where the converter registry lives.** Phase 8 §3.5
  recommends `webapp/converters/registry.py`; this is the
  Phase 9.4 scope (§4.6). No alternatives are on the table.
- **Whether to commit to a no-bundler SPA forever.** Today's
  static-SPA shape is the right call while the dashboard is
  settled. The decision point is "when does the dashboard
  start moving weekly" — likely not in the next 6 months.

---

## 8. Trigger Conditions

A trigger is a real-world event that re-prioritizes the roadmap.
The triggers below are explicit so a future contributor can
re-read this document and immediately see whether the plan has
shifted. Because this is an internal tool (section 1.1), **triggers are
project-owner-driven**, not market-driven.

### 8.1 Re-prioritization triggers

| Trigger | Re-prioritization |
|---------|-------------------|
| **The project owner reports the 5-second minimum watcher interval is too slow for their workflow** | Add a Phase X (configurable lower bound, with a safety clamp) to near-term. |
| **The project owner wants to expose the webapp without a reverse proxy** | Promote gap-3.x #2.2 (TLS) to near-term. Add a self-signed cert flow. |
| **A 12th converter needs to be added (e.g., a new trading partner's format)** | If Phase 9.4 (converter registry) is not yet shipped, the work exposes the hardcoded-list debt — accelerate Phase 9.4. |
| **The project owner wants to use the webapp from a phone or tablet for a one-off task** | One-off: resize the browser window, use the existing layout. If "one-off" becomes "regular," promote gap-3.x #2.8 (mobile) — but probably don't, since the project owner is at a workstation 99% of the time. |
| **A platform deprecation (Python 3.11, FastAPI, SQLite version, etc.)** | Schedule a maintenance window in the near-term. Unrelated to roadmap sequencing. |
| **Phase 9.1-9.5 cause regressions that the webapp test suite doesn't catch** | Pause Phase 9; add a regression test that fails on the staged tree; revisit the Phase 8 decision document. |
| **Schema migrations become more frequent than 1/quarter** | Schedule Phase 10 (Candidate C) to remove the adapter tax. |
| **A CSS regression or focus-trap bug slips through JSDOM** | Promote gap-3.x #2.9 (Playwright) to mid-term; add the browser test that would have caught it. |

### 8.2 Triggers that re-open the spec (very rare)

These are the only triggers that would re-open
PROJECT_SPEC.md (the product intent) rather
than just re-prioritize the roadmap. They're listed so a future
contributor knows what *not* to assume is stable.

| Trigger | What re-opens |
|---------|---------------|
| **The project owner acquires a second operator** (e.g., brings on a part-time admin) | Re-evaluate single-user posture: bearer-token (Phase 6.2) might become "user accounts"; audit log (gap-3.x #2.5) becomes meaningful. |
| **The project owner acquires a second host** (e.g., moves from one workstation to two that need to coordinate) | Re-evaluate single-host posture: this is the trigger that would re-open PROJECT_SPEC.md section 3.4 (the security model) and section 3.5 (release channels). |
| **The project owner takes on a customer** (i.e., ships the tool to someone else) | The whole product framing changes from internal tool to external product. Multi-user auth, SLA, support flow, mobile responsive, third-party plugin API, audit log — all become "parked, not rejected." This is the trigger that re-opens section 1.1 (this section). |

### 8.3 What is **not** a trigger

These events *look* like they should re-prioritize the roadmap
but shouldn't, for an internal tool:

- "We might want this someday." — No. Sometime-never is the
  same as never.
- "Best practice says we should have X." — Only if X addresses
  a real risk the project owner actually faces.
- "An external user might want this." — There are no external
  users (section 1.1).
- "Industry trend is toward Y." — Irrelevant; the project
  owner's workflow doesn't change because of industry trends.

The default answer to "should we add this?" is **no** for an
internal tool. The burden of proof is on the addition, not on
the status quo.


---

## 9. Effort & Risk Calibration

Cross-cutting calibration of the work in §4 and §5.

### 9.1 Effort estimates

All estimates assume one focused contributor, working in a
clean tree, with the existing test suite as the regression net.

| Item | Effort | Confidence |
|------|--------|-----------|
| Phase 7b.3 commit | 0.1 day | High (mechanical) |
| Phase 8 decisions | 2-3 days | High (documentation only) |
| Phase 9.1 rename | 1-2 days | High (mechanical + import updates) |
| Phase 9.2 progress merge | 0.5 day | Medium (need to verify zero callers of the deleted reporter) |
| Phase 9.3 async boundary | 1 day | Medium (cancellation paths need coverage) |
| Phase 9.4 converter registry | 0.5 day | High (additive; old list can coexist) |
| Phase 9.5 error-ledger direct | 0.5 day | High (drop a known adapter) |
| Phase 9.6 watcher integration | 0.5 day | High (post-9.3, mechanical) |
| Phase 9.7 fixture updates | 1 day | High (import path renames) |
| Phase 9.8 docs | 0.5 day | High |
| **Total near + mid-term** | **~8-10 days** | |

That fits comfortably in 30-90 calendar days at one focused
day per working day, or in 2-3 weeks at two focused days per
working day.

### 9.2 Risk calibration

| Risk class | Items | Mitigation |
|------------|-------|------------|
| **Mechanical-only** | 7b.3, 9.1, 9.4, 9.7, 9.8 | Revert on `git revert`; existing tests are the regression net. |
| **Behavioral** | 9.2, 9.5 | Phase 8 spec's "golden file" pattern (per-converter output stability) catches drift; per-decision verification step in §4. |
| **Concurrency** | 9.3, 9.6 | Phase 8 §3.4 (DECISION 3) commits to `run_in_executor` (proven pattern); cancellation bounded by `asyncio.wait_for`. |
| **Documentation-only** | Phase 8 decisions, 9.8 | No code; review by reading. |
| **Long-tail correctness** | 9.7 fixture updates | A test that worked before must work after; if it doesn't, that's a hidden behavioral change surfaced by the rename — investigate before continuing. |

### 9.3 What is *not* in the calibration

- The cost of NOT doing the work (continuing to carry the
  `dispatch/` package as legacy code, the adapter tax on every
  schema addition, the two-progress-reporters drift). This is a
  real cost but it's amortized across the lifetime of the
  product, not any single day.
- The cost of doing the work *poorly* (rewriting a converter
  during the move, changing the folder schema in 9.1). The
  mitigations are explicit: 9.1 is "move only, no rewrite";
  Phase 8 commits to no-schema-change in 9.1-9.5; golden-file
  tests catch any converter drift.

---

## 10. Cross-References

| Topic | This doc | Primary reference |
|-------|----------|-------------------|
| Product intent (5 capabilities, NFRs) | §1 | [PROJECT_SPEC.md](./PROJECT_SPEC.md) |
| Current state of the webapp (architecture, API, deployment) | §2 | [WEBAPP_SPEC.md](./WEBAPP_SPEC.md) |
| Operator workflows ("if X, do Y") | §3, §8 | [docs/runbook.md](../docs/runbook.md) |
| Phase 7b (interface/ retirement) | §4.1 | [webapp-phase-7b-interface-retirement.md](./webapp-phase-7b-interface-retirement.md) |
| Phase 7 (operator confidence + partial desktop retirement) | §2.1 | [webapp-phase-7-operator-confidence.md](./webapp-phase-7-operator-confidence.md) |
| Phase 8 (pipeline redesign — design spec) | §4.2, §7.1 | [webapp-phase-8-pipeline-redesign.md](./webapp-phase-8-pipeline-redesign.md) |
| Phase 6 (production hardening) | §2.1, §3 | [webapp-phase-6-production-hardening.md](./webapp-phase-6-production-hardening.md) |
| Phase 5 (observability) | §2.1, §3 | [webapp-phase-5-observability.md](./webapp-phase-5-observability.md) |
| Gap-2.x (production hardening — landed) | §2.1 | [docs/architecture/webapp-gap-audit.md §5](../docs/architecture/webapp-gap-audit.md) |
| Gap-3.x (deferred items) | §6 | [docs/architecture/webapp-gap-audit.md §5.3](../docs/architecture/webapp-gap-audit.md) |
| Project conventions (imports, anti-patterns) | §9 | [AGENTS.md](../AGENTS.md) |

### 10.1 Glossary

| Term | Meaning |
|------|---------|
| **Roadmap** | This document — the strategic sequencing of phases and decisions. |
| **Phase** | A named scope of work with its own spec. Each implementation spec lands as a series of individually-revertable commits. |
| **Candidate A / B / C** | The three architecture options from Phase 8 §3.3. B is the recommended path. |
| **Adapter tax** | The cost of reading config through both a typed dataclass and the flat underlying schema. Today: small. Triggers Phase 10 if it grows. |
| **Trigger** | A real-world event that would re-prioritize the roadmap (§8). |
| **Gap-3.x** | The set of deferred items from the gap-audit §5.3. |
| **Local-first** | The deployment posture: single host, default bind `127.0.0.1`, no inbound network surface, no cloud sync. |
| **Internal tool** | The product framing (§1.1): one project owner, zero external users. Determines what gets built, what gets deferred, and what gets rejected outright. The default answer to "should we add this?" is **no**; the burden of proof is on the addition. |

### 10.2 Changelog

| Date | Author | Change |
|------|--------|--------|
| 2026-08-31 | Project Owner | Initial draft — strategic roadmap for the webapp version. 10 sections, ~500 lines. Sequenced Phase 7b.3 (in-progress), Phase 8 (decision document), Phase 9.1-9.8 (rename + targeted simplifications), Phase 10 (re-decision checkpoint), and the gap-3.x deferred items. |

