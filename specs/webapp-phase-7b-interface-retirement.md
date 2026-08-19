# Spec: Webapp Phase 7b — interface/ Retirement

**Status:** DRAFT (2026-08-18)
**Author:** Project Owner
**Created:** 2026-08-18
**Updated:** 2026-08-18

> **Origin:** Phase 7's `specs/webapp-phase-7-operator-confidence.md §3.3 (7.3)`
> claimed the `interface/` package had no callers. Verification at
> commit time (2026-08-18) proved the claim false: `interface/` is
> called from 13 test files totaling ~7,500 lines of code, including
> the entire 25,372-line `tests/integration/` directory. Phase 7.3
> shipped without `interface/` (commit `4a4240306` covers only the
> safe deletions). This spec scopes the follow-on work: delete
> `interface/` *and* every test that imports it.

---

## 1. Summary

Retire the Qt-free `interface/` package (16 files, 3,819 lines) by
deleting it together with every test that imports it: the entire
`tests/integration/` directory (37 files, 25,372 lines) plus
`tests/unit/interface/` (~13 files, ~3,111 lines) plus small edits
in `tests/conftest.py` (425 lines), `tests/unit/dispatch/test_converters_registry.py`,
`tests/unit/test_folder_configuration_pydantic.py`, and
`tests/unit/test_settings_validation.py`. Total: ~33,000 lines of
test code deleted alongside the 3,819 lines of source code.

The webapp test suite (`tests/webapp/`, 310 tests passing as of
2026-08-18) becomes the regression net going forward. No source
code under `webapp/`, `core/`, `backend/`, `dispatch/` depends on
`interface/`; deleting it does not affect any production code path.

---

## 2. Background

### 2.1 Problem Statement

`interface/` is the Qt-free business-logic layer that the pre-pivot
desktop app used to share between the GUI and the runner. It
exposes folder CRUD, processed-files management, and validation
helpers. The webapp-pivot (2026-08-04) deleted the GUI (`interface/qt/`),
and Phase 7's desktop retirement (§3.8 addendum, 2026-08-18)
ruled out ever reviving it.

After Phase 7.1's verification grep — which checked only
`webapp/` and `dispatch/` — the Phase 7.3 spec assumed `interface/`
had no callers. The commit-time verification grep, run against
`tests/`, proved that wrong: `interface/` is imported from
**13 test files**, totaling ~7,500 lines of code. The bulk is
`tests/integration/` (37 files, 25,372 lines) — the entire
end-to-end integration test suite.

This spec captures the explicit scope of the `interface/`
retirement, separate from the now-shipped Phase 7.3 partial.

### 2.2 Inventory

**To delete (`interface/`):**

| File | Lines | Purpose |
|------|-------|---------|
| `interface/__init__.py` | (small) | Package marker; documents that Qt UI was removed |
| `interface/AGENTS.md` | (~30) | Pre-pivot layout doc |
| `interface/interfaces.py` | (?) | Protocols / dependency-injection seams |
| `interface/ports.py` | (?) | Port definitions |
| `interface/models/folder_configuration.py` | (?) | Folder config dataclass |
| `interface/operations/folder_data_extractor.py` | (?) | Path normalization |
| `interface/operations/folder_manager.py` | (?) | Folder CRUD |
| `interface/operations/processed_files.py` | (?) | Processed-files ops |
| `interface/services/customer_lookup_service.py` | (?) | Customer lookup |
| `interface/services/ftp_service.py` | (?) | FTP backend wrapper |
| `interface/services/progress_service.py` | (?) | Progress reporter |
| `interface/services/reporting_service.py` | (?) | Reporting |
| `interface/services/resend_service.py` | (?) | Resend |
| `interface/services/smtp_service.py` | (?) | SMTP backend wrapper |
| `interface/validation/email_validator.py` | (?) | Email validation |
| `interface/validation/folder_settings_validator.py` | (?) | Settings validation |
| **Total** | **3,819** | (per `find interface -name "*.py" -exec wc -l {} +`) |

**To delete (`tests/`):**

| Path | Files | Lines | Notes |
|------|-------|-------|-------|
| `tests/integration/` (whole dir) | 37 | 25,372 | Tracked in git. Includes `tests/integration/conftest.py`, `tests/integration/option_matrix.py`, and 35 test_*.py files. |
| `tests/unit/interface/` (whole dir) | 13 | ~3,111 | Untracked. Tests for `interface/` modules directly. |
| **Subtotal (whole dirs)** | **50** | **~28,500** | |

**To edit (small imports in non-`interface/` tests):**

| File | Lines affected | Import to remove |
|------|---------------|------------------|
| `tests/conftest.py` | 2 lines | `from interface.ports import ...`, `from interface.services.resend_service import ...` |
| `tests/unit/dispatch/test_converters_registry.py` | 2 lines | `from interface.models.folder_configuration import ConvertFormat` |
| `tests/unit/test_folder_configuration_pydantic.py` | 3 lines | Same `ConvertFormat` import (used 3x) |
| `tests/unit/test_settings_validation.py` | 1 line | `from interface.validation.folder_settings_validator import ...` |
| **Subtotal** | **~8 lines** | |

**Total scope: ~33,000 lines deleted across ~67 files (50 untracked, 37 tracked).**

### 2.3 Why delete the integration tests outright

`tests/integration/` tests the end-to-end flow of
`FolderManager.process_folder()` against an in-memory adapter. The
test surface duplicates what `tests/webapp/` already covers at a
higher level (HTTP endpoints + DB + threading) and at a lower
level (`tests/unit/` for individual modules).

The webapp test suite (310 passing tests) covers every HTTP
endpoint, every router, every DB schema addition, every Phase 6
behavior (soft-delete, diagnostics, bearer-token, soft-delete trim).
Removing the integration suite does not lose test coverage that
the webapp suite doesn't already cover at the integration level.

For modules where `interface/` was the only test coverage
(`tests/unit/interface/`), the corresponding webapp equivalents
either exist (`webapp/routers/folders.py` is tested by
`tests/webapp/test_folder_edit.py`, etc.) or are themselves
dead code (no caller — no need to test a module nothing uses).

### 2.4 What we explicitly do NOT lose

- **HTTP endpoint coverage**: every webapp endpoint stays tested
  by `tests/webapp/`.
- **Pipeline behavior**: `dispatch/orchestrator.py` is tested by
  `tests/webapp/test_runner.py` (via `webapp/runner.py`).
- **Database behavior**: every schema migration is exercised by
  `tests/webapp/test_database_repair.py`, `test_soft_delete.py`,
  and the implicit `open_database()` calls in every webapp test.
- **Converter behavior**: `tests/unit/dispatch/` covers the 11
  converter plugins; `tests/webapp/test_converters.py` covers the
  API surface; golden-file tests (Phase 5) cover output stability.

### 2.5 Prior art

- Phase 7.1 commit `64f4db1fc` — already ships the schema-repair
  gate; this spec does not touch source code outside the deletions.
- Phase 7.3 commit `4a4240306` — already shipped the safe
  deletions (plans/, launch_interface.sh, packaging artifacts).
- 2026-08-18 user decision: "Path B: delete `interface/` + its
  dependent tests (5K lines) — webapp test suite becomes the
  regression net." Subsequent re-count put the dependent-test
  scope at ~33,000 lines, not 5,000; this spec scopes that.
- `interface/__init__.py` (pre-pivot docstring) — the package's
  own documentation says *"the former Qt UI layer was removed in
  the webapp pivot"*; the Qt-free remainder is an artifact of
  incomplete cleanup, not an active design choice.

---

## 3. Design

### 3.1 Architecture Alignment

- [x] Reviewed `docs/ARCHITECTURE.md` — `interface/` is documented
  as the "non-UI service layer" that the webapp reuses; the
  webapp-pivot commit (`9864dc7e5`) *intended* to share it, but
  in practice the webapp reimplemented the same logic via
  `webapp/routers/folders.py`, `webapp/folder_schema.py`, etc.
  This spec acknowledges the original intent failed and finalizes
  the divergence.
- [x] Reviewed `docs/DATABASE_DESIGN.md` — `interface/`'s
  `FolderConfiguration` model is the pre-pivot shape; the webapp
  uses `webapp/folder_schema.py::FolderEditSchema` instead. Both
  read the same SQLite columns; the dataclass is dead-code.
- [x] Reviewed `docs/TESTING_DESIGN.md` — no test layer is being
  added; this spec *removes* a test layer (the integration suite
  that depended on `interface/`).
- [x] Reviewed `AGENTS.md` — no silent `except: pass`; deletions
  are mechanical `git rm` / `rm`, no error handling needed.
- [x] Reviewed `specs/PROJECT_SPEC.md §3.8` (the Phase 7 desktop
  retirement addendum) — this spec is the follow-on that scopes
  the missing piece.

### 3.2 Components affected

**Deleted outright:**

- `interface/` — the entire package.
- `tests/integration/` — the entire directory.
- `tests/unit/interface/` — the entire directory.

**Edited (remove `interface.*` imports):**

- `tests/conftest.py` — remove 2 lines.
- `tests/unit/dispatch/test_converters_registry.py` — remove 2 lines.
- `tests/unit/test_folder_configuration_pydantic.py` — remove 3 lines.
- `tests/unit/test_settings_validation.py` — remove 1 line.

**Untouched:**

- `webapp/`, `core/`, `backend/`, `dispatch/` — verified
  `grep -rn "from interface\|import interface"` returns empty
  for these directories.
- `tests/webapp/` — no imports of `interface/` (verified).

### 3.3 Technical approach per item

The work is mechanical. Three commits in order:

**Commit 7b.1: Edit small test imports.**

Edit the four test files that import from `interface/` but live
outside `tests/integration/` and `tests/unit/interface/`. After
edits, `pytest tests/unit/dispatch/test_converters_registry.py`,
`pytest tests/unit/test_folder_configuration_pydantic.py`,
`pytest tests/unit/test_settings_validation.py`, and
`pytest tests/conftest.py` (the conftest pytest import) must all
import cleanly.

The edits are:

- `tests/conftest.py`: delete lines 19-20 (the two `from interface.*`
  imports). Verify that no other line in the file references
  the imported symbols (`ProgressServiceProtocol`, `UIServiceProtocol`,
  `ResendService`).
- `tests/unit/dispatch/test_converters_registry.py`: delete the
  inline `from interface.models.folder_configuration import
  ConvertFormat` (line ~141). Verify the test still passes
  (the import is in a test that checks the dispatch-side registry,
  not the interface-side model — `ConvertFormat` is likely
  re-exported or duplicated in `dispatch/`).
- `tests/unit/test_folder_configuration_pydantic.py`: delete the
  three `from interface.models.folder_configuration import
  ConvertFormat` lines. Same verification.
- `tests/unit/test_settings_validation.py`: delete the
  `from interface.validation.folder_settings_validator import
  FolderSettingsValidator` line. Same verification.

If any of these edits breaks a test (i.e., `interface.*` was
the *only* source of a class the test depends on), that class
must be either (a) re-implemented in `tests/webapp/` (preferred —
keeps the regression net honest) or (b) ported from
`interface/` to a temporary test-only location. (b) is a smell;
(a) is the right answer.

**Commit 7b.2: Delete `tests/unit/interface/`.**

This is the directory that tests `interface/` modules directly.
Once `interface/` is gone, this directory has nothing left to
test. `git rm -r tests/unit/interface/`.

**Commit 7b.3: Delete `interface/` and `tests/integration/`.**

`git rm -r interface/ tests/integration/`. This is the bulk of
the deletion. After this commit, the webapp test suite
(`tests/webapp/`) is the sole regression net.

### 3.4 Alternatives considered

| Alternative | Pros | Cons | Why not chosen |
|-------------|------|------|----------------|
| Re-point integration tests to webapp/ equivalents | Preserves the test surface | 25K lines of test code would need editing; high risk of subtle behavior changes; the test files test pre-pivot desktop behavior that doesn't map to the webapp | Per user call: "webapp test suite becomes the regression net" |
| Keep interface/, just stop using it from webapp | Lower-risk | 3,819 lines of dead code stays; future agents will think it's active and try to import from it | The 2026-08-18 desktop retirement is explicit; keeping the orphan contradicts §3.8 |
| Migrate interface/ to core/ or webapp/ | Preserves the data models | The webapp has its own equivalent models (`webapp/folder_schema.py`, etc.); the conversion is risky and the spec was clear that desktop is gone | Out of scope per §3.8 |
| Delete interface/ but keep tests as broken | Smallest change | `pytest` fails on import | Non-option |

---

## 4. Implementation Plan

### Phase 7b.1: Edit small test imports (Estimated: 0.25 day)

- [ ] Task 7b.1.1: Edit `tests/conftest.py` — delete the two
  `from interface.*` lines. Run `pytest tests/conftest.py` to
  verify the conftest still imports cleanly (pytest doesn't
  *run* it, but importing it surfaces symbol errors).
- [ ] Task 7b.1.2: Edit `tests/unit/dispatch/test_converters_registry.py`
  — delete the inline import. Run
  `pytest tests/unit/dispatch/test_converters_registry.py` to
  verify.
- [ ] Task 7b.1.3: Edit `tests/unit/test_folder_configuration_pydantic.py`
  — delete the three imports. Run
  `pytest tests/unit/test_folder_configuration_pydantic.py`.
- [ ] Task 7b.1.4: Edit `tests/unit/test_settings_validation.py` —
  delete the import. Run
  `pytest tests/unit/test_settings_validation.py`.
- [ ] Deliverable: all four edited tests still pass; no
  `interface.*` references remain in the surviving test files.

### Phase 7b.2: Delete `tests/unit/interface/` (Estimated: 0.05 day)

- [ ] Task 7b.2.1: `git rm -r tests/unit/interface/`.
- [ ] Task 7b.2.2: Run `pytest tests/` (excluding
  `tests/integration/`) — verify the webapp suite + the surviving
  unit tests still pass.
- [ ] Deliverable:13 files, ~3,111 lines deleted; full
  `tests/unit/` + `tests/webapp/` still 100% green.

### Phase 7b.3: Delete `interface/` and `tests/integration/` (Estimated: 0.05 day)

- [ ] Task 7b.3.1: `git rm -r interface/ tests/integration/`.
- [ ] Task 7b.3.2: Run `pytest tests/webapp/` — verify the webapp
  suite is 100% green. This is the new regression baseline.
- [ ] Task 7b.3.3: Run `grep -rn "from interface\|import interface" .`
  — verify the only remaining matches are in `docs/` (the
  Phase 7 spec and gap audit reference the package historically).
- [ ] Deliverable: ~29,000 lines deleted; webapp test suite
  green; no source-code references to `interface/` remain.

---

## 5. Database Changes

None. The schema is unchanged.

---

## 6. Testing Strategy

### 6.1 Test Cases

This phase *removes* tests, doesn't add them. The success
criterion is "the surviving test suite is green." Per the spec's
rollback, reverting 7b commits restores everything.

| Test | Type | Description | Expected | Phase |
|------|------|-------------|----------|-------|
| `pytest tests/webapp -q` | regression | Webapp suite stays 100% green | 310 pass | 7b.2 / 7b.3 |
| `pytest tests/unit -q` | regression | Surviving unit tests stay 100% green | 100% | 7b.2 / 7b.3 |
| `grep -rn "from interface\|import interface" webapp/ core/ backend/ dispatch/ tests/` | structural | No production code or surviving test references `interface/` | empty | 7b.3 |

### 6.2 Test File Locations

No new test files. The four edits in 7b.1 are line deletions
in existing files.

### 6.3 Coverage Requirements

- [ ] Existing tests still pass — baseline 310 webapp python +
  surviving unit tests.
- [ ] `ruff check` clean on the four edited files.
- [ ] No file under `interface/` exists. Verified by
  `find interface -name "*.py"` returning empty.
- [ ] No file under `tests/integration/` exists. Verified by
  `find tests/integration -name "*.py"` returning empty.
- [ ] No file under `tests/unit/interface/` exists. Verified by
  `find tests/unit/interface -name "*.py"` returning empty.

---

## 7. Risk Assessment

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| 7b.1 edit breaks a test because the only source of a class is `interface.*` | Medium | Medium | Per 7b.1 plan: re-implement in `tests/webapp/` (preferred) or port to a test-only location. The four edited files are small; the verification step is per-file pytest. |
| 7b.3 deletion surfaces a behavior the webapp tests didn't catch | Low | High | The webapp test suite (310 tests) covers every HTTP endpoint, the schema-repair gate (Phase 7.1), soft-delete, diagnostics, the bearer-token gate, and the trim supervisor. The integration suite's coverage was redundant with the webapp suite. |
| A test in `tests/integration/` was the only coverage for a subtle bug class | Low | Medium | Reverting the commit restores the test. The behavior is in git history; the test can be ported to `tests/webapp/` as a follow-on if it ever bit us. |
| 7b.3 deletion uncovers that the webapp's `FolderEditSchema` is missing a field the integration tests exercised | Very Low | Low | `webapp/folder_schema.py::FolderEditSchema` is tested by `tests/webapp/test_folder_edit.py` (the soft-delete round-trip test in particular). The webapp test surface is the canonical mapping; the integration tests were testing the pre-pivot model. |

### 7.1 Rollback Plan

Each commit is self-contained.

- Reverting 7b.1 restores the four edited test files to their
  pre-edit state.
- Reverting 7b.2 restores `tests/unit/interface/`.
- Reverting 7b.3 restores `interface/` and `tests/integration/`.

After revert, `pytest` should be back to its pre-7b baseline.

---

## 8. Success Criteria

- [ ] `interface/` directory is removed; `find interface -name "*.py"`
  returns empty.
- [ ] `tests/integration/` directory is removed.
- [ ] `tests/unit/interface/` directory is removed.
- [ ] `tests/conftest.py`, `tests/unit/dispatch/test_converters_registry.py`,
  `tests/unit/test_folder_configuration_pydantic.py`,
  `tests/unit/test_settings_validation.py` no longer import from
  `interface/`.
- [ ] `grep -rn "from interface\|import interface" webapp/ core/
  backend/ dispatch/ tests/` returns empty (or matches only in
  `docs/`).
- [ ] `pytest tests/webapp -q` is 100% green.
- [ ] `pytest tests/unit -q` is 100% green (the surviving unit
  tests).
- [ ] `ruff check` clean on the four edited files.

---

## 9. Open Questions

1. Should the four edited test files retain any of their
   imports if removing them causes `NameError`? **TENTATIVE:**
   per 7b.1's plan, re-implement in `tests/webapp/` if a class
   is needed; otherwise delete the line. Don't port to a
   test-only location (smell).
2. Should this spec update `docs/architecture/webapp-gap-audit.md
   §4.2` to note that `interface/` is now deleted (rather than
   pending)? **TENTATIVE:** yes; add a §4.3 entry once 7b ships.
3. Should the gap audit's reference to `interface/` (in the
   "Out of scope: desktop-only build / packaging features" line
   near the top) be updated to reflect that it's now also gone?
   **TENTATIVE:** yes, in the same commit as 7b.3.

---

## 10. Appendix

### 10.1 References

- `specs/webapp-phase-7-operator-confidence.md` — the Phase 7 spec
  that scoped 7.3 with incomplete verification.
- `specs/PROJECT_SPEC.md §3.8` — the desktop retirement addendum
  (2026-08-18).
- Commit `64f4db1fc` — Phase 7.1 schema-repair gate.
- Commit `4a4240306` — Phase 7.3 partial (plans/, packaging).
- Commit `eadf05ac9` — Phase 6.3 backend health probes.
- Commit `9864dc7e5` — the 2026-08-04 webapp-pivot that started the
  divergence.
- `interface/__init__.py` — pre-pivot docstring documenting that
  the Qt UI was removed.

### 10.2 Changelog

| Date | Author | Change |
|------|--------|--------|
| 2026-08-18 | Project Owner | Initial draft — three-commit scope (7b.1 edits, 7b.2 delete unit/interface/, 7b.3 delete interface/ + tests/integration/) |