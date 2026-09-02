# Spec: Phase 12 — Mixins to Composition (Completion)

**Status:** DRAFT
**Author:** Project Owner
**Created:** 2026-09-02
**Updated:** 2026-09-02

> **Completion phase.** Phase 11 gave us typed data. Phase 12
> finishes the composition refactor that was always the
> end-state: replace the legacy converter mixins with explicit
> service composition. Most of the work was already done
> during Phase 8/9; this phase verifies nothing was missed
> and retires the dead code.

---

## 1. Goal

Eliminate the four converter mixins in
`webapp/pipeline/converters/mixins.py` and route every
converter through the explicit service composition that
`stewarts_custom` and `jolley_custom` already use. Once
nothing imports those mixins, retire the file.

Two distinct mixin concerns in the codebase:

- **Converter mixins** (`mixins.py`): shared DB-backed logic
  for converters that need AS400 lookups.
- **Pipeline-step mixin** (`ErrorRecordingMixin` in
  `pipeline/interfaces.py`): shared error-recording for
  pipeline steps. Different module, different purpose.
  **Not in scope** — see §6.

## 2. Why now

The mixins-vs-services decision was made in the 2026-04-20
solid-refactoring plan (`docs/superpowers/plans/2026-04-20-solid-refactoring.md`).
Services were extracted to
`webapp/pipeline/services/` and stewarts_custom + jolley_custom
were migrated to use them. The remaining consumer
(`convert_to_tweaks.py`) was left using `DatabaseConnectionMixin`
because the migration was not driven by an immediate
converter bug.

The mixins still ship in the codebase but nothing in
production uses them. The mixins themselves are now dead
code that:

1. Create two parallel APIs for the same operations
   (mixin methods vs service methods).
2. Confuse new contributors ("should I use the mixin or
   the service?").
3. Distort `convert_to_x810.py`-style type signatures
   with mixed-in attributes (`query_object: QueryRunner | None`
   as a class annotation, even when the class doesn't use it).

## 3. Architecture (current state)

### 3.1 Converter mixins (`webapp/pipeline/converters/mixins.py`)

| Mixin | Service replacement |
|-------|---------------------|
| `DatabaseConnectionMixin` | `webapp.pipeline.services.database_connector.DatabaseConnector` |
| `CustomerLookupMixin` | `webapp.pipeline.services.customer_lookup_service.CustomerLookupService` |
| `UOMLookupMixin` | `webapp.pipeline.services.uom_lookup_service.UOMLookupService` |
| `ItemProcessingMixin` (static methods) | `webapp.pipeline.services.item_processing.ItemProcessor` |

| `build_jolley_header_dict` | `convert_to_jolley_custom.py` (only) | Move to `webapp/pipeline/converters/jolley_header_builder.py`. Update the single import. |
| `CUSTOMER_QUERY_SQL_TEMPLATE`, `BASIC_CUSTOMER_QUERY_SQL`, `STEWARTS_CUSTOMER_QUERY_SQL` | N/A — already moved to `customer_queries.py` | `customer_queries.py` already defines these (lines 8, 119, 120). `convert_to_stewarts_custom.py` and `convert_to_jolley_custom.py` already import from there. `mixins.py` still has its own copies (lines 335-448) — delete those (after confirming no other consumers via `grep`). |

### 4.1 Audit (today)


Find every consumer of the four converter mixins and the
helper data exports in ``mixins.py``:

| Symbol | Consumer | Action |
|--------|----------|--------|
| `DatabaseConnectionMixin` | `convert_to_tweaks.py` | Migrate to `DatabaseConnector` (matches `convert_to_stewarts_custom.py` pattern). |
| `DatabaseConnectionMixin` | `tests/unit/core/database/test_query_runner.py` (lines 315, 356, 369) | Backward-compat test. Retarget at `DatabaseConnector` or keep the mixin as a one-line back-compat shim that delegates. |
| `CustomerLookupMixin` | none | No active consumers. |
| `UOMLookupMixin` | none | No active consumers. |
| `ItemProcessingMixin` | none | No active consumers. |
| `build_jolley_header_dict` | `convert_to_jolley_custom.py` (single import) | Move to a dedicated `webapp/pipeline/converters/jolley_header_builder.py`. Update the one import. |
| `CUSTOMER_QUERY_SQL_TEMPLATE`, `BASIC_CUSTOMER_QUERY_SQL`, `STEWARTS_CUSTOMER_QUERY_SQL` | `customer_queries.py` already has them; `mixins.py` lines 335-448 are now duplicates | Delete the duplicates from `mixins.py` once the move is confirmed via `grep`. |

**Sub-phase 12.1 — migrate `convert_to_tweaks.py`**

`convert_to_tweaks.py` is the only production consumer of
`DatabaseConnectionMixin`. Replace its mixin usage with
explicit `DatabaseConnector` instantiation (same pattern
as `convert_to_stewarts_custom.py` lines 64-66):

```python
# Before
class TweaksConverter(BaseEDIConverter, DatabaseConnectionMixin):
    def __init__(self):
        super().__init__()
        self._init_db_connection(...)

# After
class TweaksConverter(BaseEDIConverter):
    def __init__(self):
        super().__init__()
        self._db_connector = DatabaseConnector()
        self._db_connector.init_connection(...)
        self._tweaker = EDITweaker(self._db_connector.query_runner, config)
```

Update the `_initialize_output` flow to match. Existing
integration tests for tweaks should pass unchanged.

**Sub-phase 12.2 — retire `CustomerLookupMixin`, `UOMLookupMixin`, `ItemProcessingMixin`**

These have no active consumers. Confirm with a project-wide
grep; if clean, remove the class definitions and the
`from webapp.pipeline.converters.mixins import ...` lines
from `convert_to_tweaks.py` (if 12.1 leaves any).

**Sub-phase 12.3 — move constants to `customer_queries.py`**

`CUSTOMER_QUERY_SQL_TEMPLATE`, `BASIC_CUSTOMER_QUERY_SQL`,
`STEWARTS_CUSTOMER_QUERY_SQL` move to
`webapp/pipeline/converters/customer_queries.py` (which
already exists and is imported by `convert_to_jolley_custom.py`
and `convert_to_stewarts_custom.py`). Re-export from
`mixins.py` for backward compat with `tests/unit/dispatch/`
if anything still references them.

**Sub-phase 12.4 — extract `build_jolley_header_dict`**

Move to `webapp/pipeline/converters/jolley_header_builder.py`.
Update `convert_to_jolley_custom.py` import.

**Sub-phase 12.5 — back-compat tests**

`tests/unit/core/database/test_query_runner.py` has
backward-compat tests against `DatabaseConnectionMixin`
(lines 315, 356, 369). Decide:

- (a) retarget them at `DatabaseConnector` directly.
- (b) leave the mixin as a one-line back-compat shim
  (`class DatabaseConnectionMixin: def __init__(self): ...`)
  that delegates to `DatabaseConnector`, and update the
  tests to assert the delegation.

(b) is the conservative choice — keeps the public surface
stable, and any other un-discovered consumer (e.g. a
plugin or a downstream fork) keeps working. Plan to do
(b) initially; revisit when 100% of the codebase is
migrated.

**Sub-phase 12.6 — retire `mixins.py` (optional)**

If all consumers are migrated and all data exports move
out, the file can be deleted. But many callers may still
import from it for back-compat. Recommendation: leave the
file with re-exports only, document it as deprecated in
the module docstring, and plan removal in a future
release.

### 4.3 Effort

| Sub-phase | Effort |
| 12.1 tweaks migration | 1 hour |
| 12.2 retire unused mixin classes | 15 min |
| 12.3 delete duplicate SQL constants | 5 min |
| 12.4 extract `build_jolley_header_dict` | 15 min |
| 12.5 back-compat tests | 30 min (option b — keep shim) |
| 12.6 retire file (deferred) | — |
| **Total** | **~2 hours** |

## 5. Test plan

- All existing tweaks integration tests pass unchanged
  (the migration preserves behaviour).
- Back-compat tests pass (option b above).
- Full unit + webapp suite green.
- Project-wide grep for the four mixin class names returns
  no production references (only the back-compat tests).

## 6. Out of scope

- `ErrorRecordingMixin` in `pipeline/interfaces.py` — lives
  on the pipeline step hierarchy, not the converter
  hierarchy. Different concern, different consumers
  (`EDIConverterStep`, `EDISplitterStep`). Worth a parallel
  Phase 12b if the duplication grows, but no current
  pain.
- `core/edi/edi_tweaker.py`'s `EDITweaker` and
  `TweakerConfig` — these are not mixins. They are
  service objects that `convert_to_tweaks.py` composes.
  Out of scope.

## 7. Open questions

1. **Should we keep `mixins.py` as a back-compat shim
   indefinitely, or plan a hard removal?** Affects
   sub-phase 12.6. Recommendation: indefinite shim,
   docstring-deprecated.
2. **Do any webapp plugins import the converter mixins?**
   Need to grep `interface/plugins/` and any third-party
   integration points. (Phase 7b.3 deleted `interface/`
   so this is probably empty.)
3. **Is `ErrorRecordingMixin` worth a parallel
   Phase 12b?** It has only 2 consumers. Punt.

## 8. Changelog

| Date | Author | Change |
|------|--------|--------|
| 2026-09-02 | Session | Initial draft. Confirms services exist, stewarts_custom/jolley_custom migrated, only convert_to_tweaks.py and back-compat tests remain. Effort ~3.5 hours. |
