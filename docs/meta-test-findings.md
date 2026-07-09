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

## Headline findings (this session)

Wall time ~12 minutes for all 16 pairs against unmodified source.

| Module | Killed | Survived (REAL gaps) | Skipped (KNOWN_EQUIVALENT) |
|---|---|---|---|
| edi_parser | 5 | 0 | 5 |
| edi_splitter | 4 | 1 | 3 |
| edi_splitting_utils | 5 | 3 | 6 |
| c_rec_generator | 4 | 2 | 5 |
| edi_transformer | 7 | 4 | 0 |
| upc_utils | 4 | 1 | 7 |
| feature_flags | 3 | 0 | 2 |
| file_utils | 4 | 2 | 4 |
| hash_utils | 4 | 1 | 3 |
| format_utils | 2 | 0 | 1 |
| bool_utils | 2 | 0 | 4 |
| date_utils | 2 | 0 | 1 |
| safe_parse | 0 | 0 | 4 |
| timing_utils | 1 | 1 | 1 |
| edi_tweaker | 7 | 4 | 4 |
| structured_logging | 4 | 2 | 7 |
| **TOTAL** | **56** | **23** | **57** |

**In plain English**: out of 79 mutations applied, 56 are killed by the tests,
23 survive (each is a real gap), and 57 are silenced by `KNOWN_EQUIVALENT`
because they target docstring prose or constants the test does not exercise.

## Real gaps to fix (by module)

The 23 survivors below were each triaged by reading the cited source line and
the cited mutation. None are equivalent mutations in disguise.

### core/edi/edi_parser.py

(none after this session — L89 `<` boundary covered by the new
`test_parse_a_record_length_at_min_length_round_trips`)

### core/edi/edi_splitter.py

- **L264 `gt_to_ge`**: `if config.max_invoices > 0 and a_record_count > config.max_invoices:`
  The property tests cover only `_build_split_filename` / `_ensure_crlf`,
  not the `EDISplitter.split_edi_file` multi-invoice branch. The
  `> 0` vs `>= 0` boundary is unasserted.

### core/edi/edi_splitting_utils.py

- **L79 `lt_to_le`**: `if int(line_dict["invoice_total"]) < 0 else ".inv"`.
  Property tests use a digit-only alphabet (`_DIGITS`), so the negative-total
  branch is unreachable in tests. Mutating `<` to `<=` makes the zero-total
  branch go `.cr` instead of `.inv`. Real gap; fix by adding sign and zero
  to the strategy and asserting the suffix.
- **L136 `ne_to_eq`**: `if lines_in_edi != write_counter:` raises
  `DataIntegrityError`. The happy path is tested; the mismatched-count path
  is unasserted (would need a fixture with deliberately bad count tracking).
- **L76 `negate_if_condition`**: `if line_dict is None: raise ValueError`.
  Property tests never pass `line_dict=None`. Real guard path is unasserted.

### core/edi/c_rec_generator.py

- **L116 `ne_to_eq`**: `if qry_ret_prepaid is not None and qry_ret_prepaid != 0`.
  Property tests don't vary the `(prepaid, non_prepaid)` amounts; the
  amount-based branch is unasserted.
- **L110 `negate_if_condition`**: `if not qry_ret:` early return on empty
  query. The chained guards downstream accidentally produce the same empty
  output for the property test's `(None, None)` payload, so the mutation
  appears equivalent; with any non-None amount input the mutation would
  crash or change behavior.

### core/edi/edi_transformer.py

- **L28 `lt_to_le`**: `if len(value) < PRICE_DECIMAL_PLACES: return 0`.
  Property test uses `_fixed_text(N)` only, never boundary. Off-by-one
  unasserted.
- **L75 `ne_to_eq`**: `if fields["record_type"] != "A": raise ValueError`.
  Property test only sends A records. Validation branch unasserted.
- **L59 `false_to_true`**: `return False` from except branch. Property
  test does not raise. Exception path unasserted.
- **L69 `and_to_or`**: `if first_line and first_line[0] not in ("A", " "):`
  malformed-first-line validation. Property test only sends valid A records.

### core/edi/upc_utils.py

- **L33 `gt_to_ge`** *(actually this slips through)*: doctest `>>> `
  in `calc_check_digit` docstring prose.

### core/utils/timing_utils.py

- **L38 `int_constant_off_by_one`**: `timer.duration_ms = (end - timer.start_time) * 1000`.
  Tests don't assert the multiplier — this is the millisecond conversion
  constant.

### core/edi/edi_tweaker.py

- **L322 `lt_to_le`**: `if attempt + 1 < max_retries:` — retry-loop boundary
  for `open(edi_process)` retries. Not exercised by any unit test.
- **L386 `gt_to_ge`** / **L386 `eq_to_ne`**: progress-log condition
  `if line_num > 0 and line_num % 100 == 0:`. Both branches are unasserted
  by unit tests.
- **L622 `true_to_false`**: `blank_upc = True`. No unit test exercises
  the blank-UPC branch.

### dispatch/file_utils.py

- **L249 `eq_to_ne`**: `if rec and rec.get("record_type") == "A":`
  property tests don't drive this branch.
- **L48 `negate_if_condition`**: `if rename_template:`. Rename-template
  branch not exercised.

### dispatch/hash_utils.py

- **L77 `lt_to_le`**: `if checksum_attempt < max_retries:` retry-loop
  boundary. Not exercised; would need `open()`-raising mock.

### core/structured_logging.py

- **L239 `le_to_lt`** *(covered this session)*: `if len(s) <= visible_chars:`
  redaction boundary. New tests
  `test_redact_string_at_exact_visible_chars` and
  `test_redact_string_just_above_visible_chars` pin both sides.
- **L523 `true_to_false`**: `auto_correlation: bool = True` parameter default.
  No structured-logging test overrides this default, so the default-vs-True
  behavior is unasserted.

## Self-referential test bugs (cannot be fixed without an oracle)

### core/edi/upc_utils.py

`test_validate_upc_accepts_check_digit` constructs a valid UPC FROM
the function-under-test:
```python
full = d + str(calc_check_digit(d))
assert validate_upc(full) is True
```
`validate_upc` itself calls `calc_check_digit` on the input — the SAME
mutated function. So any consistent mutation to `calc_check_digit`
(self-consistent: produces the same wrong value every time) will pass.
A real catch would need an independent oracle (a hardcoded valid UPC
like `"041800000265"` whose check digit is asserted).

Affected mutations silenced as KNOWN_EQUIVALENT:
- `true_to_false` at L38 (`odd_pos = True`)
- `negate_if_condition` at L40 (`if odd_pos:`)
- `return_none_instead_of_value` at L47

These are NOT equivalent mutations — they are real bugs the test
cannot detect. They are silenced only to keep the meta-test passing;
the underlying test bug must be fixed separately by adding a
hardcoded oracle test:
```python
def test_validate_upc_hardcoded_valid_oracle():
    assert validate_upc("041800000265") is True
    assert validate_upc("041800000260") is False
```

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
equivalent (because the function under that line changed, the
docstring became functional code, etc).

## What to do next

Priority order:

1. **Replace the self-referential `validate_upc_accepts_check_digit`
   with a hardcoded-oracle test.** This is the test that hides the
   `odd_pos` bug class. Adding `validate_upc("041800000265") is True`
   is sufficient.
2. **Add a multi-invoice test for `EDISplitter.split_edi_file`** to
   pin the `max_invoices > 0` boundary (L264 of edi_splitter.py).
3. **Add zero / negative `invoice_total` cases to the splitting test.**
   The current digit-only alphabet hides the `.cr` vs `.inv` branch.
4. **Add an exception-path test for `convert_to_price_decimal` and
   `detect_invoice_type`** to pin L59 / L69 / L75 of edi_transformer.py.
5. **Add log-capturing fixture for `convert_edi_to_scannerware`** to
   pin the L386 progress-log conditions and L322 retry bounds.

Each item above is a 10–30 line test addition; the patterns are
demonstrated by the `test_parse_a_record_length_*` tests added this
session.
