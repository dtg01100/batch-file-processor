# Spec: Phase 11 — Typed Config and Records

**Status:** DRAFT
**Author:** Project Owner
**Created:** 2026-09-02
**Updated:** 2026-09-02

> **Maintainability phase.** Phase 11 replaces dict-as-everything
> with typed dataclasses in the two places that matter most:
> (1) the EDI A/B/C records the pipeline passes between stages,
> and (2) the per-folder configuration every converter reads.
>
> Phase 8/9 cleans up *shape* (where code lives, how it's
> discovered). Phase 11 cleans up *types* (what the data looks
> like in memory). Both are required for a maintainable codebase
> that's also a line-of-business tool.

---

## 1. Goal

Make every line of business logic work on **typed objects**, not
dict-key lookups. A converter reads `record.invoice_number`, not
`record.fields["invoice_number"]`. A folder config reads
`config.sender_id`, not `params["x810_sender_id"]`. Type errors
become import-time / constructor errors, not silent wrong-output
errors at 3 AM.

## 2. Why now

Two pressures, both real:

1. **Maintainability.** The codebase is line-of-business. A typo
   in `record.fields["invoice_numer"]` ships to production as a
   runtime KeyError, not a lint error. Today, the only thing
   catching that is the test suite — which is 1228 tests, all
   *happy path*. An operator adding a new trading partner's
   format touches a converter and learns the field names by
   reading other converters. With typed records, IDE autocomplete
   lists the fields.
2. **It's already half-done.** `core/edi/edi_parser.py` already
   has `ARecord`, `BRecord`, `CRecord` dataclasses
   (`edi_parser.py:13-99`). They aren't used: `capture_records`
   returns `dict`, and 137 string-key accesses in
   `dispatch/converters/` ignore the existing dataclasses. Phase
   11 connects the existing dataclasses to the existing call
   sites.

## 3. Non-goals

- **No schema migration.** The flat `folders` table is unchanged.
  Typed config dataclasses are *read* from the flat rows via an
  adapter (same approach as Phase 8's DECISION 1).
- **No behavior change.** Every golden-file output must be
  byte-equal before and after Phase 11.
- **No new test framework.** Hypothesis + pytest still.
- **No dict-removal in `core/utils/` or `backend/`.** Out of scope.
  Phase 11 is the converter and pipeline boundary only.

## 4. The two surfaces

### 4.1 Surface A — EDI records

Today: `dict[str, str]` with 15 known keys (data above):
`record_type, cust_vendor, invoice_number, invoice_date,
invoice_total, upc_number, description, vendor_item, unit_cost,
unit_multiplier, qty_of_units, suggested_retail_price,
parent_item_number, amount, charge_type`. Accessed by string key
137 times across 12 converters.

Tomorrow: existing `ARecord`, `BRecord`, `CRecord` dataclasses
(already in `core/edi/edi_parser.py`) become the canonical shape.
`EDIRecord` (`dispatch/converters/convert_base.py:77`) becomes:

```python
@dataclass
class EDIRecord:
    record_type: str
    raw_line: str
    fields: ARecord | BRecord | CRecord  # discriminated union
```

Converters read `record.fields.invoice_number` (typed, autocomplete,
refactor-safe).

### 4.2 Surface B — Folder config

Today: every folder has 50+ flat `folders` table columns
(Phase 8 §2.1 enumerates them). Each converter extracts its
slice via `params = context.parameters_dict` and reads
`params.get("calculate_upc_check_digit")`. String keys, defaults
scattered, normalization (`normalize_parameter`) inline.

Tomorrow: one `FolderConfig` dataclass per converter, generated
from `CONVERTER_METADATA`. CSV converter gets
`webapp/converters/csv_config.py::CSVConverterConfig` with
typed fields, defaults in `field(default=...)`, validation in
`__post_init__`. Same for the other 11.

A `webapp/pipeline/config.py::FolderConfigAdapter` reads a flat
folder row and produces the right converter-specific config based
on `convert_to_format`. Phase 8 DECISION 1's adapter, made
concrete.

## 5. Architecture

### 5.1 Module layout (after Phase 11)

```
core/edi/
├── edi_parser.py           # existing dataclasses (unchanged API)
└── ...

webapp/pipeline/           # after Phase 9.1 rename
├── config.py              # FolderConfigAdapter (Phase 8 §4.1)
├── records.py             # EDIRecord wrapper (NEW, Phase 11)
└── ...

webapp/converters/         # after Phase 9.1 rename
├── csv.py
├── csv_config.py          # CSVConverterConfig (NEW, Phase 11)
├── scannerware.py
├── scannerware_config.py
├── x810.py
├── x810_config.py         # X810ConverterConfig (NEW, Phase 11)
└── ...
```

Each converter gets a `_config.py` sibling with one dataclass.
The converter's `__init__` (or `_initialize_output`) takes a
config object, not a dict.

### 5.2 Where the typing boundary lives

```
SQL row ──> FolderConfigAdapter ──> FolderConfig ──> ConverterConfig
                                                          │
                                                          ▼
EDI line ──> capture_records() ──> EDIRecord (typed) ──> Converter.process_b_record(record)
```

**The boundary:** `capture_records()` returns an `EDIRecord`
with a typed `fields` attribute. Everything downstream of that
boundary is typed. `capture_records()` itself stays dict-based
because the parser uses string-key dispatch internally — but its
*return type* is typed.

### 5.3 What stays untyped (deliberately)

- `core/utils/*.py` — internal helpers, low risk, out of scope.
- `backend/*.py` — backends receive a dict (`process_parameters`)
  and don't need typing for the operator-facing fix.
- Test fixtures — they construct dicts to match the SQL schema.
  Typed fixtures come later if at all.
- `parameters_dict` in the *flat-schema adapter* — that's the
  boundary, it has to be dict-shaped because that's what
  `webapp/folder_schema.py` produces today.

## 6. Migration path

### 6.1 Sub-phase ordering

Phase 11 ships in **four sub-phases**, each independently
revertable. Phase 11.4 unblocks Phase 11.1 (records) so the order
is:

```
[11.4 config adapter]  ──►  [11.1 records typed]
                                    │
                              ┌─────┼─────┐
                              ▼     ▼     ▼
                         [11.2 csv] [11.3 scannerware] [11.x remaining]
```

11.4 is small (~1 day) because Phase 8 DECISION 1 already
spec'd it; 11.4 makes the dataclass.

### 6.2 Sub-phase 11.4 — `FolderConfigAdapter`

**Effort:** 1 day.
**Risk:** Low (Phase 8 already spec'd the shape).

1. `webapp/pipeline/config.py::FolderConfigAdapter` reads a flat
   `folders` row dict and produces a `FolderConfig` dataclass
   containing: `folder_id`, `folder_name`, `alias`, `is_active`,
   `convert_to_format`, `process_backends` (typed list, not 4
   booleans), `parameters` (still `dict` — per-converter configs
   come in 11.1+).
2. `webapp/runner.py` constructs an adapter and passes the
   typed config to the pipeline.
3. Existing dict-style access via `folder["folder_name"]` keeps
   working (the dataclass has dict-compatible attribute access
   via `__getitem__`).

**Exit criterion:** one place reads folder config via
`adapter.config.folder_id`; existing call sites still work.

### 6.3 Sub-phase 11.1 — Typed `EDIRecord`

**Effort:** 1 day.
**Risk:** Medium (137 call sites change; refactor surface is wide
but mechanical).

1. `core/edi/edi_parser.py::capture_records()` continues to
   return dicts internally, but a new `capture_records_typed()`
   returns `ARecord | BRecord | CRecord` based on `record_type`.
2. `dispatch/converters/convert_base.py::EDIRecord.fields`
   becomes a typed union. `BaseEDIConverter._dispatch_record`
   constructs the typed record from the parsed dict.
3. Converters migrate *one at a time* in 11.2/11.3/11.x. The base
   class accepts both during the transition via a `record.fields`
   proxy that returns a typed object with dict-fallback attributes.

**Exit criterion:** base class constructs typed records; the
dict-fallback proxy lets any unmigrated converter still compile
and pass tests.

### 6.4 Sub-phase 11.2 — CSV converter migrated

**Effort:** 0.5 day.
**Risk:** Low (smallest converter; golden-file test is the
regression net).

1. `dispatch/converters/csv_config.py::CSVConverterConfig`
   dataclass with the 13 CSV parameters as typed fields with
   defaults.
2. `CSVConverter.__init__` accepts a `CSVConverterConfig`.
3. `webapp/pipeline/config.py::FolderConfigAdapter` constructs
   `CSVConverterConfig` when `convert_to_format == "csv"`.
4. Migrate all `record.fields["..."]` to `record.fields.<attr>`.
5. Golden-file test: `tests/unit/test_convert_to_csv.py` byte-equal
   before/after.

### 6.5 Sub-phase 11.3 — ScannerWare converter migrated

**Effort:** 0.5 day.
**Risk:** Low.

Same pattern as 11.2; chosen second because it has the most
distinct parameter shape (5 params, all defaulted booleans +
strings).

### 6.6 Sub-phase 11.x — Remaining 9 converters

**Effort:** 0.5 day each (~4.5 days total).
**Risk:** Low individually; high if done all at once.

Each converter gets its own `*_config.py` and gets migrated one
at a time. Order is by parameter count, ascending:

- x810 (4 params) → simplified_csv (5) → stewarts_custom (6) →
  jolley_custom (7) → estore_einvoice (8) → estore_einvoice_generic
  (10) → yellowdog_csv (11) → fintech (12) → scansheet_type_a (13).

x810 (just added) is the easiest one to migrate; doing it first
sets the pattern.

### 6.7 Total effort

| Sub-phase | Effort |
|-----------|--------|
| 11.4 adapter | 1 day |
| 11.1 typed records | 1 day |
| 11.2 csv | 0.5 day |
| 11.3 scannerware | 0.5 day |
| 11.x remaining (9 converters × 0.5) | 4.5 days |
| **Total** | **~7.5 days** |

## 7. Testing

### 7.1 Regression net (mandatory)

Every converter has a golden-file test
(`tests/unit/test_convert_to_<format>.py`). Phase 11 commits are
only mergeable if the golden-file output is byte-equal before
and after the migration. The test runs as part of CI today.

### 7.2 New tests

- `tests/unit/test_typed_records.py` — `capture_records_typed()`
  returns the right dataclass for A/B/C records.
- `tests/unit/core/test_folder_config_adapter.py` — adapter
  produces correct typed config from a flat row.
- `tests/unit/test_convert_to_csv_config.py` — CSVConverterConfig
  validation: missing required field raises, wrong type raises.

### 7.3 Type-checking (CI gate)

Phase 11 enables `mypy --strict` on `webapp/pipeline/` and
`webapp/converters/`. The existing `pyproject.toml` ruff config
stays. The CI gate is the first time mypy is enforced; today
my[py] is unconfigured.

## 8. Risks

| Risk | Mitigation |
|------|-----------|
| Typing migration breaks a golden-file test | Revert the sub-phase; the converter keeps dict-based config until the next attempt. The dict-fallback proxy in 11.1 means a partial migration is a valid intermediate state. |
| `mypy --strict` reveals dozens of pre-existing issues | Phase 11 enables mypy on the *new* code path only. Pre-existing issues get filed as separate issues; they don't block Phase 11. |
| The adapter tax (Phase 8's concern) becomes painful here | The adapter is the same code path. If the dataclass surface grows faster than the migration, the adapter itself becomes typed — Phase 12 work, not Phase 11. |
| Typed records break the `mixins.py` code that accesses `record.fields["..."]` | `mixins.py` is migrated as part of 11.x — same `*_config.py` per-converter pattern. The 4 mixins get rewritten as composition (`self.db.query_customer(...)`) not inheritance; that's Phase 12. |
| Operator's domain logic changes (e.g., new field) | Adding a new field to the dataclass is a one-line change with type-checker feedback. Adding it to the dict is a search-and-replace with no safety net. Phase 11 reduces future risk. |

## 9. Sequencing vs Phase 8/9

```
[7b.3 done]  ──►  [X done]  ──►  [Phase 8 decisions]  ──►  [Phase 9.1-9.5 rename + simplify]
                                                                │
                                                                ▼
                                                       [Phase 9.6-9.8 docs/fixtures]
                                                                │
                                                                ▼
                                                  [Phase 11.4 adapter]
                                                                │
                                                                ▼
                                                  [Phase 11.1 typed records]
                                                                │
                                                                ▼
                                                  [Phase 11.2-11.x per-converter migrations]
                                                                │
                                                                ▼
                                                  [Phase 12 mixins → composition]
```

Phase 11 starts **after** Phase 9 lands. Two reasons:

1. The rename (`dispatch/ → webapp/pipeline/`) is mechanical and
   benefits from a clean baseline. Doing the rename and the
   typing migration together risks conflating two failure modes
   when bisecting a regression.
2. Phase 9.4 (registry discovery) is a prerequisite for 11.4's
   adapter: the adapter needs to know which `*_config.py` to
   load based on `convert_to_format`, and Phase 9.4 is what
   makes that discovery automatic.

## 10. What this is **not**

- **Not a rewrite.** The operators' domain logic is preserved
  verbatim; only the type annotations change.
- **Not a new ORM.** The folders table stays flat; the adapter
  reads it. No SQLAlchemy, no dataclass-as-DB-layer.
- **Not a "Phase 8 redo."** Phase 8 was about *where code lives*.
  Phase 11 is about *what types the data has*.

## 11. Exit criteria

- `mypy --strict webapp/pipeline/ webapp/converters/` passes.
- All 11 converters migrated; `dispatch/converters/` no longer
  contains `record.fields["..."]` accesses (or, after the rename,
  `webapp/converters/` no longer does).
- Golden-file tests byte-equal for all 11 converters.
- `pytest tests/webapp tests/unit/dispatch_tests tests/unit/test_convert_to_* -q`
  green.
- `webapp/pipeline/AGENTS.md` documents the typed-record
  contract for future converter authors.

## 12. Open questions

1. **Does Phase 11 also type the backends?** Today's backends take
   `process_parameters: dict` and `settings_dict: dict`. They're
   smaller surface area (4 backends, ~25 calls total) and lower
   risk (the backends are well-tested). **TENTATIVE:** out of
   scope for Phase 11; a Phase 13 if the typing payoff is clear
   after Phase 11.
2. **Does the `core/utils/utils.py` legacy module get cleaned up
   in 11.4?** **TENTATIVE:** yes — `core/utils/utils.py` is two
   functions that duplicate what `core/edi/retail_uom.py`
   already provides. Deleting it is mechanical; included in 11.4.
3. **Should `capture_records` be renamed `parse_edi_line`?** The
   current name was inherited from a 2010-era codebase and is
   non-standard for a Python parser. **TENTATIVE:** rename in
   11.1 along with the typed return.

## 13. Changelog

| Date | Author | Change |
|------|--------|--------|
| 2026-09-02 | Project Owner | Initial draft. Sub-phases 11.1-11.4 + 11.x. ~7.5 days total. Sequenced after Phase 9 lands. |
