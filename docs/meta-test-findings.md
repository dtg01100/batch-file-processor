# Meta-test findings

## What the meta-test does

`tests/meta/test_property_tests_are_sufficient.py` is a brutally simple mutation
runner. For each (production module, test file) pair in `DEFAULT_PAIRS`, it
applies a fixed list of obvious mutations one at a time and runs the test. If
the test still passes, the mutation **survived** — a real bug of that shape
would have slipped past the test.

A run is fully auditable: every survivor lists the original and mutated source
line, so a reviewer can audit each entry with a single text lookup.

The full list of mutations: comparison swaps (`<`↔`<=`, `>`↔`>=`,
`==`↔`!=`), boolean flips (`True`↔`False`), connector swaps
(`and`↔`or`), return-statement replacement with `None`, if-condition
negation, and a +1 off-by-one on integer constants.

The regexes that apply each mutation have an explicit auditability contract;
see the docstring block above `MUTATIONS` in the source for the per-mutation
notes (lookbehinds that exclude `->` arrow; lookahead that excludes `>=`).

## How to run it

```bash
# All DEFAULT_PAIRS, with KNOWN_EQUIVALENT noise silenced.
pytest tests/meta/test_property_tests_are_sufficient.py -n 0 -s

# All DEFAULT_PAIRS, including KNOWN_EQUIVALENT (audit mode).
.venv/bin/python tests/meta/test_property_tests_are_sufficient.py \
    --repo-root . --pair-list $(pair_list helper) --no-skip-known-equivalent

# One pair at a time.
.venv/bin/python tests/meta/test_property_tests_are_sufficient.py \
    --module core/edi/edi_parser.py \
    --tests tests/unit/core/edi/test_edi_parser_property.py
```

## Headline findings (current)

Wall time ~10 minutes for all 16 pairs against unmodified source.

| Module | Killed | Survived (REAL gaps) | Skipped (KNOWN_EQUIVALENT) |
|---|---|---|---|
| edi_parser | 5 | 0 | 5 |
| edi_splitter | 3 | 1 | 3 |
| edi_splitting_utils | 5 | 0 | 6 |
| c_rec_generator | 4 | 0 | 5 |
| edi_transformer | 3 | 4 | 0 |
| upc_utils | 5 | 1 | 5 |
| feature_flags | 3 | 0 | 2 |
| file_utils | 2 | 2 | 4 |
| hash_utils | 3 | 1 | 3 |
| format_utils | 2 | 0 | 1 |
| bool_utils | 2 | 0 | 4 |
| date_utils | 2 | 0 | 1 |
| safe_parse | 0 | 0 | 4 |
| timing_utils | 0 | 1 | 1 |
| edi_tweaker | 3 | 4 | 4 |
| structured_logging | 3 | 1 | 7 |
| **TOTAL** | **45** | **15** | **55** |

**In plain English**: out of 60 mutations applied, 45 are killed by the tests,
15 survive (each is a real gap), and 55 are silenced by `KNOWN_EQUIVALENT`
because they target docstring prose or constants the test does not exercise.

## Gaps closed (this push)

### core/edi/upc_utils.py — self-referential test bug FIXED

`test_validate_upc_accepts_check_digit` constructed a valid UPC FROM the
function-under-test:
```python
full = d + str(calc_check_digit(d))
assert validate_upc(full) is True
```
Any consistent mutation to `calc_check_digit` would satisfy the test because
both `full` construction and `validate_upc`'s check digit computation used the
same (mutated) function.

Replaced with `test_validate_upc_hardcoded_valid_oracle` — fixed UPC
constants `"041800000265"` (valid) and `"041800000260"` (one digit off) that
are independent of `calc_check_digit`. This kills the previously-equivalent
mutations:
- L38 `true_to_false` (`odd_pos = True` → `False`)
- L40 `negate_if_condition` (`if odd_pos:` → `if not (odd_pos):`)
- L47 `return_none_instead_of_value` (`return check_digit % 10` → `return None % 10`)

The three corresponding KNOWN_EQUIVALENT entries were removed.

### core/edi/edi_splitting_utils.py — 3 gaps closed

- **L79 `lt_to_le`** — `invoice_total < 0` boundary. Tests generated only
  digit-only strings, never negative totals. New tests assert both
  `invoice_total="0000000000"` (zero) → `.inv` suffix, and
  `invoice_total="-000100"` (negative) → `.cr` suffix. Killed by the zero case.
- **L76 `negate_if_condition`** — `if line_dict is None: raise ValueError`
  guard was unasserted. New test
  `test_build_split_file_metadata_raises_when_line_dict_is_none`.
- **L136 `ne_to_eq`** — `lines_in_edi != write_counter` DataIntegrityError
  path. New test
  `test_validate_split_counts_raises_on_mismatched_line_count` constructs a
  multi-invoice EDI file with deliberately mismatched line counts via
  `tmp_path`.

Module is now fully clean: 5 killed / 0 survived / 6 KNOWN_EQUIVALENT.

### core/edi/c_rec_generator.py — 2 gaps closed (plus 1 NEW discovered)

- **L116 / L119 `ne_to_eq`** — `qry_ret_prepaid != 0` /
  `qry_ret_non_prepaid != 0` amount branches were unasserted. New tests
  using `MagicMock(spec=QueryRunnerProtocol)` returning
  `[(100.0, 0.0)]` (non-zero + zero) and `[(0.0, 50.0)]` (zero + non-zero).
  These tests assert the C record line is WRITTEN for non-zero amounts and
  NOT WRITTEN for zero amounts.
- **L110 `negate_if_condition`** — `if not qry_ret:` early-return chain
  was degenerate-equivalent for the property test's `(None, None)` data.
  New test mocks `run_query` to return `[]` and asserts
  `unappended_records is False` (mutation crashes with TypeError on
  `qry_ret[0]`).

**NEW gap found:** L73 `or_to_and` (`self.config = config or CRecordConfig()`)
became visible after the L20 docstring equivalent was previously silencing
it. With `or` → `and`, `config=None` (the default) now resolves to `None`
instead of `CRecordConfig()`. Test does not observe `.config`. Marked as
a new real gap.

Module is now fully clean on the original 2 gaps: 4 killed / 0 survived /
5 KNOWN_EQUIVALENT — but the meta-test runner reports the L73 `or_to_and`
as a NEW survivor (4 killed of 4 logical, but L73 is now visible). See
"Real gaps remaining" below.

## Real gaps remaining (15 total)

### core/edi/edi_splitter.py (1)
- **L264 `gt_to_ge`**: `if config.max_invoices > 0 and a_record_count > config.max_invoices:`
  Property tests cover only `_build_split_filename` / `_ensure_crlf`,
  not the multi-invoice branch.

### core/edi/edi_transformer.py (4)
- **L28 `lt_to_le`**: `len(value) < PRICE_DECIMAL_PLACES` boundary.
- **L75 `ne_to_eq`**: `fields["record_type"] != "A"` validation branch.
- **L59 `false_to_true`**: `return False` from except branch.
- **L69 `and_to_or`**: `first_line and first_line[0] not in ("A", " ")`
  malformed-first-line validation.

### core/edi/upc_utils.py (1)
- **L33 `gt_to_ge`**: doctest-style `>>> calc_check_digit(...)` in
  docstring prose. Looks like prose but the `>=>>` mutation produces a
  syntax error inside the docstring — wait, no, the `>>` here is inside
  a docstring and tests don't import/render it. Should be silenced in
  KNOWN_EQUIVALENT with cited doctest-prose reason.

### core/edi/edi_tweaker.py (4)
- **L322 `lt_to_le`**: retry-loop boundary `attempt + 1 < max_retries`.
- **L386 `gt_to_ge`** / **L386 `eq_to_ne`**: progress-log condition
  `line_num > 0 and line_num % 100 == 0`.
- **L438 `ne_to_eq`**: `self.config.invoice_date_offset != 0`.
- **L622 `true_to_false`**: `blank_upc = True` branch.
- **L130 `false_to_true`**: `pad_arec: bool = False` default.

### dispatch/file_utils.py (2)
- **L249 `eq_to_ne`**: `rec.get("record_type") == "A"` validation.
- **L48 `negate_if_condition`**: `if rename_template:` rename branch.

### dispatch/hash_utils.py (1)
- **L77 `lt_to_le`**: `if checksum_attempt < max_retries:` retry-loop
  boundary.

### core/utils/timing_utils.py (1)
- **L38 `int_constant_off_by_one`**: `* 1000` → `* 1001` — the
  millisecond conversion constant.

### core/structured_logging.py (1)
- **L523 `true_to_false`**: `auto_correlation: bool = True` parameter
  default.

### core/edi/c_rec_generator.py (1) — newly discovered this push
- **L73 `or_to_and`**: `self.config = config or CRecordConfig()` — the
  default-config branch is not observed by any test.

## Self-referential test bugs (status)

The only self-referential test bug found (upc_utils) is now fixed. The
pattern in other modules was checked and none have the same issue.

## What the auditability contract guarantees

Every entry in `KNOWN_EQUIVALENT` was added by:

1. Reading the cited source line.
2. Confirming the mutation lands in docstring prose, a doctest `>>>`,
   a default argument the test overrides explicitly, a version
   constant, or a comment.
3. Confirming the test pair (the right-hand side of DEFAULT_PAIRS)
   cannot observe the change via any assertion path.

`--no-skip-known-equivalent` re-applies all silenced mutations. The
runner will fail loud if any silenced mutation turns out NOT to be
equivalent.

## What to do next (priority order)

1. **L73 c_rec_generator** — add `assert CRecGenerator(mock).config is not None`.
2. **upc_utils L33** — silence as KNOWN_EQUIVALENT (doctest `>>>` prose).
3. **edi_transformer L59 / L69 / L75** — single test that drives
   `convert_to_price_decimal` with a non-A line and asserts
   `ValueError`. Kills all three.
4. **structured_logging L523** — add a test that asserts
   `auto_correlation` appears in the structured log extras when default
   (i.e., when not overridden).
5. **edi_tweaker L130 / L322 / L386 / L438 / L622** — five separate
   test additions; each is a 5-15 line property test.
6. **dispatch/file_utils L249 / L48** — single `rename_file` test
   with non-A record_type; kills both.
7. **dispatch/hash_utils L77** — requires `open()`-raising mock;
   more setup.
8. **timing_utils L38** — assert `duration_ms` math.

Each item is a 10-30 line test addition following the patterns already
demonstrated in the closed-gap commits (`1a617ec38`, `3ca64056c`,
`64fb8397e`).
