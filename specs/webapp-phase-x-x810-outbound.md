# Spec: Phase X — x810 Outbound Converter

**Status:** DRAFT
**Author:** Project Owner
**Created:** 2026-09-02
**Updated:** 2026-09-02

> Adds an X12 810 (Invoice) outbound converter to the existing
> dispatcher. Inbound source remains the project's internal
> A/B/C record parser — no X12 envelope parser is added in this
> phase.

---

## 1. Goal

Trading partners that expect a standard X12 810 envelope can now
be configured as a destination in the webapp folder UI. The
converter emits a syntactically valid ASC X12 004010 810 (Invoice)
transaction set from the internal EDI process dict.

## 2. Non-goals

- **No X12 inbound parser.** Phase X generates only. Receiving an
  810 from a partner still goes through whatever process the
  partner requires today.
- **No new backends.** x810 output goes through the existing
  SMTP / FTP / Copy / HTTP backends unchanged.
- **No new schema.** Configuration lives in the existing flat
  `folders` table `parameters` column as JSON-ish key/values.
- **No 810 acknowledgement (997/999) handling.** Out of scope.

## 3. Envelope shape (004010)

```
ISA*00*          *00*          *ZZ*<sender_id_15>*ZZ*<receiver_id_15>*<YYMMDD>*<HHMM>*U*00401*<control_9>*0*P*:~
GS*IN*<sender>*<receiver>*<YYMMDD>*<HHMM>*<gs_ctrl>*X*004010~
ST*810*<st_ctrl>~
BIG*<invoice_date_YYYYMMDD>*<invoice_number>*<po_date_YYYYMMDD>*<po_number>~
N1*BT*<bill_to_name>~
IT1*<line_seq>*<qty>*<unit_measure>*<unit_price>*UP*<upc>*VP*<vendor_item>~
TDS*<total_in_dollars>~
CTT*<line_count>~
SE*<seg_count>*<st_ctrl>~
GE*1*<gs_ctrl>~
IEA*1*<isa_ctrl>~
```

Element separators: `*`. Sub-element separator: `>`. Segment
terminator: `~`.

## 4. Parameters (folder parameters_dict)

| Key | Required | Default | Notes |
|-----|----------|---------|-------|
| `x810_sender_id` | yes | — | 15-char sender ID qualifier |
| `x810_receiver_id` | yes | — | 15-char receiver ID |
| `x810_bill_to_name` | no | `""` | N1*BT entity name |
| `x810_isa_control` | no | timestamp-derived | ISA13, 9 digits |
| `x810_gs_control` | no | same | GS06 |
| `x810_st_control` | no | same | ST02 |
| `x810_force_004010` | no | `True` | set False for 003040 if needed |

Missing required → converter raises `ValueError` with the missing
key name, surfaced through the existing pipeline error path.

## 5. Architecture

- New file `dispatch/converters/convert_to_x810.py`.
- Subclass `BaseEDIConverter`.
- `CONVERTER_METADATA` declares `format_name="x810"`,
  `display_name="X12 810 (Invoice)"`.
- Registry auto-discovery picks it up — no manual list update.
- Webapp `converters_api.py` already calls
  `dispatch.converters.registry.get_all_converters()`, so the new
  format appears in the UI's converter dropdown automatically.

## 6. Mapping (internal A/B/C → x12 810)

| Internal | x12 segment |
|----------|-------------|
| A (header) | `BIG` (invoice_date, invoice_number), `TDS` (total) |
| B (line item) | `IT1` (qty, unit_price, UP=UPC, VP=vendor_item) |
| C (charge) | dropped in this phase (no `SAC` segment yet) |
| Config | `ISA`, `GS`, `ST`, `N1` envelope |

Per-record field derivation:

- `unit_price`: `unit_cost` field on B record, in dollars
  (internal field is in cents; divide by 100).
- `qty`: `qty_of_units * unit_multiplier`, integer.
- `UPC`: `upc_number`. Length-padded to 12 if shorter.

## 7. Error semantics

- Missing required param → `ValueError` with the missing key.
- Internal total not parseable as int → log + use `0`.
- Malformed internal date → log + use today.

These match the existing converter tolerance pattern
(`convert_to_estore_einvoice.py` is the reference).

## 8. Testing

### 8.1 Unit (dispatch_tests/)

`tests/unit/dispatch_tests/test_convert_to_x810.py`:

- golden-file test: input EDI → expected 810 envelope byte-equal.
- param validation: missing `x810_sender_id` raises ValueError.
- multi-line: 3 B records → 3 IT1 segments + correct CTT.
- empty B (header only): 0 IT1 + CTT*0.
- envelope control numbers: configurable override works.

### 8.2 Parity / smoke

`tests/convert_backends/test_x810_smoke.py` — single golden-file
test against `alledi/` corpus if present; skip if not.

### 8.3 Regression

All existing `tests/unit/dispatch_tests/` and
`tests/webapp/test_converters.py` must remain green.

## 9. Effort

~1.5 days focused:

| Task | Effort |
|------|--------|
| Spec (this doc) | done |
| `convert_to_x810.py` implementation | 0.5 day |
| Unit tests + golden fixtures | 0.5 day |
| Parametric override test | 0.25 day |
| Webapp regression check + format appears in registry | 0.25 day |

## 10. Sequencing

This phase is independent of Phase 8/9 (pipeline redesign). It
adds a new converter module; it does not touch the dispatch
package layout. It can land before, during, or after the Phase 9.1
rename — `git mv` will rename the file in flight without changing
its semantics.

It is **not** on the current ROADMAP.md §4 (near-term) sequence.
This spec amends §4 with a Phase X branch:

```
[7b.3 done]  ──►  [Phase X x810]  ──►  [Phase 8 decisions]  ──►  [9.1 rename]  ──► ...
```

The Phase X work fits between 7b.3 and Phase 8 without blocking
either.

## 11. Open decisions

None. The spec is fully resolved as written.

## 12. Exit criteria

- `dispatch/converters/convert_to_x810.py` lands with
  `CONVERTER_METADATA`.
- Webapp `GET /api/converters` returns the new format in its list.
- Unit tests pass.
- `pytest tests/webapp -q` remains green.
- ROADMAP.md §4 is amended to mention Phase X between 7b.3 and 8.
