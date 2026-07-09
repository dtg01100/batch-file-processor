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

## Test-hygiene meta-test findings (Phase 1, 2026-07-09)

`tests/meta/test_hygiene.py` is a static AST-based linter that scans
every test file under `tests/unit/` for violations of the conventions
documented in `tests/AGENTS.md` and the project root `AGENTS.md`. It
runs in seconds and is safe to parallelize.

### Headline numbers (initial run)

153 test files scanned. **19 real violations across 14 files.**

| Rule | Count | Description |
|---|---|---|
| `bare_except_pass` | 14 | `except: pass` / `except Exception: pass` — silent error swallowing |
| `missing_assert` | 1 | `def test_*` with no `assert` / `pytest.raises` / `pytest.warns` / `pytest.fail` |
| `skip_no_reason` | 3 | `pytest.skip()` with no positional reason and no `reason=` kwarg |
| `single_item_dispatch_root_import` | 1 | `from dispatch import X` (single name) — AGENTS.md convention |
| `bare_magicmock` | 0 | (clean — existing `conftest_magicmock_plugin` enforces) |
| `sleep_call` | 0 | (clean — `patch("time.sleep")` is the project pattern) |
| `unjustified_noqa` | 0 | (clean — every `# noqa` cites a reason) |

### Findings (initial)

**`bare_except_pass` (14)**

| File | Line | Pattern | Notes |
|---|---|---|---|
| `tests/unit/test_build_configuration.py` | 193 | `except ImportError: pass` | optional-dep probe; should use `pytest.importorskip` |
| `tests/unit/test_build_configuration.py` | 195 | `except Exception: pass` | AST parse error swallow; needs logging |
| `tests/unit/test_build_configuration.py` | 298 | `except SyntaxError: pass` | AST parse error swallow |
| `tests/unit/test_build_configuration.py` | 300 | `except Exception: pass` | broad swallow in nested try |
| `tests/unit/test_convert_to_scansheet_type_a.py` | 32 | `except ImportError: pass` | pyzbar optional-dep probe |
| `tests/unit/test_convert_to_simplified_csv.py` | 438 | `except ValueError: pass` | unknown; needs review |
| `tests/unit/test_estore_null_safety.py` | 74 | `except Exception: pass` | broad swallow; needs review |
| `tests/unit/test_golden_output.py` | 315 | `except ImportError: pass` | yaml optional-dep probe |
| `tests/unit/test_golden_output.py` | 324 | `except ImportError: pass` | invoke.vendor.yaml probe |
| `tests/unit/test_pyinstaller_spec.py` | 79 | `except Exception: pass` | AST parse error swallow — real |
| `tests/unit/test_scansheet_type_a.py` | 190 | `except zipfile.BadZipFile: pass` | optional-dep probe |
| `tests/unit/test_scansheet_type_a.py` | 192 | `except Exception: pass` | broad swallow; needs review |
| `tests/unit/test_utils.py` | 1028 | `except Exception: pass` | unknown; needs review |
| `tests/unit/core/utils/test_timing_utils.py` | 96 | `except _TestFailed: pass` | sentinel-catch to test `finally` — legitimate, add to `KNOWN_HYGIENE_VIOLATIONS` when implemented |

**`missing_assert` (1)**

| File | Line | Pattern | Notes |
|---|---|---|---|
| `tests/unit/test_folder_configuration_pydantic.py` | 6 | `test_folder_configuration_pydantic_valid` calls `validate_with_pydantic()` with no positive assertion | Comment says "should not raise" but no `assert` to confirm |

**`skip_no_reason` (3)**

| File | Line | Pattern | Notes |
|---|---|---|---|
| `tests/unit/dispatch_tests/test_legacy_147_routing.py` | 128 | `pytest.skip(` multi-line | needs `reason=` kwarg |
| `tests/unit/dispatch_tests/test_master_routing_matches_147.py` | 166 | `pytest.skip(` multi-line | needs `reason=` kwarg |
| `tests/unit/test_plugins/test_plugin_option_combinations.py` | 409 | `pytest.skip(f"Plugin {format_name} not found")` | has f-string positional; check why flagged |

**`single_item_dispatch_root_import` (1)**

| File | Line | Pattern | Notes |
|---|---|---|---|
| `tests/unit/dispatch/test_feature_flags_property.py` | 11 | `from dispatch import feature_flags` | should be `from dispatch.feature_flags import feature_flags` per AGENTS.md |

### How the runner is structured

`tests/meta/test_hygiene.py` is ~600 lines, single file, no plugin
framework. Seven check functions registered in a `CHECKS` dict, each
returning `list[Violation]`. The pytest wrapper is parametrized over
`(file, check_name)` so `-k missing_assert` or `-k test_db2ssh_connection`
narrow the run. A self-check (`test_hygiene_runner_self_check`) asserts
the runner file itself has no violations of the rules it enforces
(excluding the rules whose description is a literal pattern the file
mentions, e.g. `# noqa`, `MagicMock`, `time.sleep`).

The `bare_magicmock` check delegates to `MagicMockVisitor` and
`_check_file_for_bare_magicmock` from `tests/conftest_magicmock_plugin.py`
to keep a single source of truth. The plugin's runtime autouse fixture
remains in place; the meta-test now provides the static check that
survives the meta-test's subprocess boundary.

### Follow-up work (priority order)

1. **`test_folder_configuration_pydantic_valid:6`** — add
   `assert config.folder_name == "base"` (or similar) to confirm
   construction succeeded, not just absence of raise.
2. **`from dispatch import feature_flags:11`** — change to
   `from dispatch.feature_flags import feature_flags`.
3. **`skip_no_reason` entries (3)** — add `reason=` keyword to each.
4. **`bare_except_pass` `except _TestFailed: pass` in test_timing_utils.py** —
   add `KNOWN_HYGIENE_VIOLATIONS` allowlist entry citing the sentinel
   pattern.
5. **`bare_except_pass` AST/error probes (5)** — convert to
   `pytest.importorskip()` or `try/except` with `logger.debug(..., exc_info=True)`.
6. **`bare_except_pass` unknown/optional-dep probes (5)** — review and
   either convert to `pytest.importorskip()` or justify with
   `KNOWN_HYGIENE_VIOLATIONS`.
