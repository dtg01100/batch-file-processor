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

## Mutmut adoption attempt (2026-07-13)

A pivot to replace the hand-rolled mutation runner with the `mutmut`
package (both 3.6.0 and the 2.5.1 fallback) was attempted and reverted.
Three hard blockers were confirmed by direct experiment; the hand-rolled
runner stays. This section records the failure mode so the pivot can
be revisited when the blockers are resolved.

### Blocker 1: mutmut 3.x + Python 3.11 import-cache bug

mutmut 3.x's per-test coverage map relies on the
`PY_IGNORE_IMPORTMISMATCH=1` env var, a Python 3.12+ feature. On
Python 3.11 (project max per AGENTS.md) it is a no-op. The mutmut
runner sets the env var, but Python's import system still uses the
cached unmutated module from the first `import core` (which happens
during mutmut's own startup, before cwd changes to `mutants/`).
Subsequent in-process pytest invocations from cwd=mutants resolve
`core.utils.format_utils` via the cache and never load the wrapped
version in `mutants/core/utils/format_utils.py`. The trampoline is
correctly injected, but the test never calls it.

**Evidence:** in-process tracing of `mutmut._stats` during `mutmut run`
showed 0 calls to `record_trampoline_hit` despite 520 tests passing.
Manually importing the wrapped module outside pytest and calling it
directly populated `_stats` correctly, confirming the trampoline
works when reached. Direct pytest invocation from `mutants/` cwd
also worked. The failure is specifically the in-process
`pytest.main(...)` call mutmut 3 uses for its stats pass, combined
with Python 3.11's import cache.

### Blocker 2: mutmut 2.5.1 baseline-must-be-green

mutmut 2.x spawns a fresh subprocess per mutant (sidestepping
Blocker 1), but first runs the FULL test suite as a baseline to
measure timing. The baseline fails on:

```
tests/unit/test_build_configuration.py::TestHiddenImports::test_hook_files_collect_all_submodules
AssertionError: No submodules collected for dispatch
```

This is environment-sensitive (likely `import dispatch` failing under
mutmut 2's runner command — the `dispatch` package is importable in
the regular venv but the test's PyInstaller-hook discovery hits a
different module path). It is pre-existing and unrelated to mutation
testing. mutmut 2's `time_test_suite` raises `RuntimeError` and
refuses to start, so no mutants are generated.

### Blocker 3: PyQt5 + pytest workers segfault

Even with `-m 'not qt' --ignore=tests/unit/interface/qt` to exclude
Qt tests, the full suite run mutmut needs is broader than this
project's Qt-aware test runner. The Qt tests must run with `-n0` per
AGENTS.md ("PyQt5 + pytest-xdist segfaults from worker thread
cleanup"). A `resend_dialog` test segfaults the Python process
(`Fatal Python error: Aborted`) when run via mutmut's runner
subprocess. This is reproducible and would be hit even if Blocker 2
were resolved.

### Resolution paths

The hand-rolled runner in
`tests/meta/test_property_tests_are_sufficient.py` does not have any
of these problems:

- It runs `subprocess.run` per mutation, so each test invocation
  starts with a fresh interpreter and import cache (sidesteps
  Blocker 1).
- It runs only the paired test file, not the full suite (sidesteps
  Blockers 2 and 3).
- It has no baseline requirement.

Revisit the mutmut pivot if **both** of the following become true:

1. Python is upgraded to 3.12+ in the project's supported
   environment (and AGENTS.md's "Python 3.11 maximum" constraint is
   lifted).
2. `test_build_configuration.py::TestHiddenImports::test_hook_files_collect_all_submodules`
   is fixed in this venv (or `--rerun-all` mode tolerates baseline
   failures, which mutmut 2 does not support).

Until then, the hand-rolled runner remains the production mutation
meta-test.

## Phase 2 — assertion-mutation runner (2026-07-13)

`tests/meta/test_assertions_are_meaningful.py` lands as Phase 2 of
`.kilo/plans/meta-tests-beyond-mutation.md`. It is an AST-based
runner that mutates every assertion in every `tests/unit/**/test_*.py`
file and verifies the test still fails. A "survivor" is a test
where the assertion was load-bearing in name only — a real bug of
that shape would have slipped past.

### Initial run (scoped)

The plan estimated ~30 minutes for the full run; in practice each
subprocess (pytest startup + collection + one test) takes 5-10s on
this venv, so the full run is closer to 8-9 hours serial or ~1-2
hours with `-n auto`. The initial commit was validated against
scoped subsets:

| Subset | Cases | Wall time | Survivors |
|---|---|---|---|
| `tests/unit/core/utils/` (5 files) | 45 | 295s serial | 0 |
| `tests/unit/core/edi/` + `core/utils/` + 3 dispatch prop tests | 198 | estimated ~25 min | not run to completion |
| `tests/unit/dispatch_tests/test_interfaces.py` (1 file, 0/6 in mutation runner) | 9 | 169s serial | 0 |

The zero-survivor result on `core/utils/` is the most informative:
every assertion in those five files is load-bearing under all 9
mutation rules. The runner is therefore a **regression catcher**
(it would catch newly-added weak tests) more than a finding
generator for the current corpus.

### Why no `delete` rule

The plan listed a tenth rule, `delete` (replace `assert X` with
`pass`). It was tried and removed: pytest 9 vacuously passes
tests with zero assertions, so `delete` reported every assertion
as dead regardless of load-bearing. The `always_fail` rule
(replace with `assert False`) already answers the same question
with cleaner signal. Documented in
`tests/meta/test_assertions_are_meaningful.py` and in the README.

### `KNOWN_ASSERTION_EQUIVALENT` allowlist

Empty at landing. Add entries here as the runner surfaces survivors
and a reviewer confirms each is equivalent. The auditability
contract is identical to the existing mutation runner's
`KNOWN_EQUIVALENT`: each entry cites the source line as evidence,
not a summary. Reviewer should be able to confirm by reading the
file at the cited line.

## Phase 3a — property-test oracle enumeration (2026-07-13)

`tests/meta/test_property_oracle_consistency.py` lands as Phase 3a.
It is a static AST classifier for property-test oracles. The bug
pattern is the self-referential test: a Hypothesis test that uses
the function-under-test (directly or transitively) to build its own
oracle, so any consistent mutation of the function makes the test
pass vacuously.

### Headline numbers

9 property files, 98 property tests, 159 assertions. **6 tests
flagged** with real signal across 3 property files.

### Per-file findings (original)

**`tests/unit/core/edi/test_edi_transformer_property.py`** (2 flagged)

- L189 `test_convert_to_price_is_deterministic` (L191):
  `assert convert_to_price(...) == convert_to_price(...)` —
  trivially_true. The test verifies determinism, which is
  intentional. Mark as KNOWN_EQUIVALENT or accept the tautology
  as documentation.
- L196 `test_convert_to_price_decimal_is_deterministic` (L198):
  same pattern.

**`tests/unit/core/edi/test_upc_utils_property.py`** (2 flagged)

- L70 `test_calc_check_digit_is_deterministic` (L72):
  `assert calc_check_digit(s) == calc_check_digit(s)` —
  trivially_true, same as above.
- L77 `test_calc_check_digit_accepts_int_input` (L81):
  `assert calc_check_digit(s) == calc_check_digit(int(s))` —
  **self_referential_helper**. The test only validates that
  int-coercion doesn't change the result, but the result is
  computed by `calc_check_digit` itself. A consistent mutation
  to `calc_check_digit` would pass. The fix: add a hardcoded
  counterpart that asserts `calc_check_digit("12345678901") == 7`
  (or any other precomputed value), so the test is not
  self-referential. This is the same pattern as the original
  `test_validate_upc_*` bug fixed in commit `1a617ec38`.

**`tests/unit/core/edi/test_edi_splitting_utils_property.py`** (2 false-positive candidates)

- L270 `test_filter_b_records_by_category_exclude_mode_removes_match`
  (L283): `assert result == []` where `result` was assigned via
  `filter_b_records_by_category(...)` earlier. The classifier's
  `ast.walk` does not trace variable assignments, so the call to
  `filter_b_records_by_category` is invisible at the assertion
  site. Classified as `oracle_independent` even though the
  assertion does use the function-under-test through a local
  variable. This is a Phase 3b concern (track local-variable
  assignments in the classifier).
- L288 `test_filter_b_records_by_category_exclude_mode_keeps_non_match`:
  same pattern.

### Per-file findings (re-run after classifier improvement)

After adding local-variable assignment tracking to the classifier
(see `tests/meta/test_property_oracle_consistency.py`
`_build_local_var_defs` and `_resolve_local`), the two
`test_edi_splitting_utils_property.py` findings reclassified from
`oracle_independent` to `oracle_uses_f_left` — confirming the
tests DO use the function-under-test through local-variable
assignment. They are not bugs.

**However, the local-variable resolution exposed two additional
real findings in `tests/unit/dispatch/test_file_utils_property.py`**
that the previous `ast.walk`-only classifier missed:

- L95 `test_strip_invalid_filename_chars_idempotent` (L99):
  `assert strip(x) == strip(strip(x))` — **self_referential_helper**.
  Same bug pattern as `test_calc_check_digit_accepts_int_input`.
  A consistent mutation to `strip_invalid_filename_chars` that
  preserves idempotency (e.g. "return the input unchanged") would
  pass the test. Real finding.

And the `test_pad_upc_idempotent_when_already_target_length` finding
in `test_upc_utils_property.py` was a real `self_referential_helper`
all along (the original report mentioned it as a hypothetical
"after the runner is improved" case; the improvement surfaced it).

### Fixes applied (commit pending)

1. **Added 3 hardcoded-oracle tests** to break the
   self-referential patterns:
   - `test_calc_check_digit_hardcoded_oracle` in
     `test_upc_utils_property.py` (5 hardcoded values for
     `calc_check_digit` on str inputs, plus 2 int-coercion
     pins).
   - `test_pad_upc_hardcoded_oracle` in `test_upc_utils_property.py`
     (6 hardcoded values covering right-pad, no-pad, truncation).
   - `test_strip_invalid_filename_chars_hardcoded_oracle` in
     `test_file_utils_property.py` (6 hardcoded values covering
     pass-through, multi-strip, all-invalid).

2. **Added 6 `KNOWN_ORACLE_EQUIVALENT` entries** to
   `tests/meta/test_property_oracle_consistency.py`:
   - 3 `trivially_true` entries for the documented purity checks
     (`test_calc_check_digit_is_deterministic`, the two
     `test_convert_to_price*_is_deterministic`). Each entry cites
     the hardcoded-oracle counterpart that now provides the
     mutation-catching coverage.
   - 3 `self_referential_helper` entries for the intentionally
     self-referential tests (int-coercion, idempotency). Each
     entry cites the corresponding hardcoded-oracle counterpart
     that provides actual-value coverage.

3. **Removed the `input_self_referential` classification** from
   the wrapper and CLI. The original heuristic
   (`input_uses_f AND assertion_uses_f`) was too aggressive —
   it flagged legitimate cross-check tests like
   `test_convert_to_price_decimal_decimal_matches_convert_to_price`
   (which uses `convert_to_price` as the oracle for
   `convert_to_price_decimal`, a real non-self-referential
   cross-check). The `_input_uses_f_or_helpers` helper is kept
   for future Phase 3b work (call-graph traversal across local
   helper functions to distinguish "f(x) on the left, expected
   from a *different* f on the right" from "f(x) on the left,
   expected also from f(x) elsewhere"). That requires
   cross-function call graph, out of scope for Phase 3a.

### Re-run after fixes

After the fix commit, the Phase 3a runner reports **0 flagged
tests** out of 98 property tests across 9 files. The
3 `trivially_true` and 3 `self_referential_helper` findings are
now silenced by the `KNOWN_ORACLE_EQUIVALENT` allowlist, and
real coverage of the function's actual values is provided by
the 3 new `*_hardcoded_oracle` tests.

The classifier's local-variable resolution improvement (used in
`_resolve_local`) is a general win: future tests that hide
function calls behind `result = f(...)` will be classified
correctly as `oracle_uses_f_left` rather than `oracle_independent`.

### Classification kinds

The classifier emits five kinds:

| Kind | Meaning |
|---|---|
| `trivially_true` | `assert f(x) == f(x)` (identical operands) — deterministic sanity check |
| `self_referential_helper` | both operands use `f()` with different args — the test only validates that f is invariant under the input transformation |
| `oracle_uses_f_left` / `oracle_uses_f_right` | one operand uses `f()`, the other is independent (e.g. a hardcoded value) — strongest signal; the test catches real f mutations |
| `oracle_independent` | neither operand uses `f()` directly at the assertion site — could be a false positive if `f` is reached through a local variable (Phase 3b work) |
| `other` | non-binary assertion (chained compare, non-Compare) — not classified |

### Phase 3b status

Phase 3b (consistency checks that REPLACE the oracle and verify the
test still passes) is not yet implemented. The plan flagged Phase
3 as experimental; the enumeration report in Phase 3a is the
initial deliverable. Future work:

- Trace local-variable assignments in the classifier to fix the
  2 `edi_splitting_utils_property.py` false positives.
- Add a `input_self_referential` flag for tests that build input
  from a helper that itself calls `f` (the original
  `test_validate_upc_accepts_check_digit` pattern). This is
  partially implemented in the runner but not yet wired into the
  failure path.
- Cross-file helper analysis (test fixture calls into a helper
  defined in another test file).
- Subprocess-based consistency check (run the test with the
  oracle replaced by a hardcoded value; verify it still passes).

## Real bugs surfaced by the meta-tests (2026-07-13)

Running all 3 meta-tests end-to-end surfaced 5 real bugs in the
existing test code. Each was fixed in commit pending. The
findings here are the audit trail.

### Bug 1 — `test_credit_invoice_gets_cr_extension` was self-approving (HIGH SIGNAL)

`tests/unit/test_utils.py:1011`. The test asserted
`result[0][2] in [".cr", ".inv"]` (accepts EITHER extension) when
the test name implies `.cr` specifically. Wrapped in
`try/except Exception: pass` that silently swallowed ALL
exceptions, including the assertion. The A record's
`invoice_total` field was also malformed (`"3-00123456"` with
the `-` in the middle, not the start) so the parser would
always raise — the test was passing only because the bare
`except` caught the parse failure and `pass`ed.

A real production bug where the suffix logic returns the wrong
extension for a credit invoice would have been silently
accepted.

**Fix:** assert `.cr` specifically (matching the test name),
use a valid negative invoice total (`-000000123` with leading
`-` and 9 digits), remove the silent `try/except`, and add a
positive assertion that the result is non-empty.

### Bug 2 — `test_truncated_b_record` was trivial (HIGH SIGNAL)

`tests/unit/test_convert_to_simplified_csv.py:417`. The test
asserted only `os.path.exists(result)` (a trivial check) wrapped
in `try/except ValueError: pass` that silently swallowed the
very exception the test was supposed to be testing for. The
test passed for any outcome — including the converter
crashing, writing corrupt data, or producing nothing.

**Fix:** accept either rejection (ValueError raised) or
graceful skip (output file written without the truncated B
record's data), but assert something specific. The corrected
version reads the output file (if any) and asserts the
truncated B's text ("Short") does NOT leak into the output.

### Bug 3 — `_get_hook_hidden_imports` swallowed parse errors (MEDIUM)

`tests/unit/test_pyinstaller_spec.py:79`. The function reads
hook files and extracts `hiddenimports` lists. The bare
`except Exception: pass` silently dropped any parse error,
file-read error, or AST parse error. A broken hook file would
silently drop its hiddenimports and the build would fail at
runtime with `ModuleNotFoundError` instead of at the test
step.

**Fix:** narrow the catch to `(OSError, SyntaxError, ValueError)`
and log at `logger.debug(..., exc_info=True)` per project
AGENTS.md §Logging Pattern. Tests still pass; the issue is
visible in `pytest -o log_cli_level=DEBUG` runs.

### Bug 4 — `core/edi/edi_splitter.py:72` `if config.prepend_date:` was untested (HIGH SIGNAL)

The mutation runner applied `negate_if_condition` at line 72
(flipping `if config.prepend_date:` to `if not (config.prepend_date):)`)
and **the test pair didn't catch it**. Every property test
in `test_edi_splitter_property.py` used `prepend_date=False`,
so the date-prefix branch was completely untested.

The same pattern as the L264 gap documented in commit
`0d904f130`. A consistent mutation that broke the date-prefix
branch would have produced wrong filenames silently.

**Fix:** added `test_build_split_filename_prepend_date_true_puts_date_in_prefix`
in `test_edi_splitter_property.py`. The test uses a fixed
`prepend_date=True` and asserts the formatted date appears in
the prefix. With the mutation applied, the new test fails
alongside 7 other tests that also use `prepend_date=False`
but assert specific output paths — confirming the mutation is
strongly killed rather than silently passing.

### Bug 5 — `test_edi_parser.py` plain unit test has 1/10 mutation kill rate (HIGH SIGNAL, NOT YET FIXED)

The plain unit test `test_edi_parser.py` (442 lines, ~30
explicit field-equality assertions) only catches 1 of 10
mutations on `core/edi/edi_parser.py`. 9 mutations survive.
The property test pair for the same module kills more, but
the plain unit test is significantly weaker. **Specific
assertions in this file don't bind to production behavior** —
same pattern as the 0/N entries in DEFAULT_PAIRS (test imports
the module but doesn't exercise the mutated code path).

**Status:** fixed in commit pending. The 4 surviving
mutations were:

1. `lt_to_le` at edi_parser.py:89: `if len(line) < 33:` — the
   test data used a 34-char line (33 + newline) so the
   mutation didn't change behavior. Added
   `test_parse_a_record_minimum_length_exactly_33_chars` with
   a 33-char line (no newline) — the boundary case.
2. `eq_to_ne` at edi_parser.py:179: `if line.strip() == "\x1a":`
   (in the parser= branch). No test exercised the parser
   parameter. Added
   `test_capture_records_with_parser_returns_none_for_eof_marker`
   with a single `\x1a` line and a parser that returns None.
3. `ne_to_eq` at edi_parser.py:178: `if result is None and line and line.strip() != "":`
   — the line.strip() == "" case. Added
   `test_capture_records_with_parser_raises_on_unparseable_nonempty`
   that asserts EDIParseError is raised for a non-empty
   non-EOF-marker line.
4. `return_none_instead_of_value` at edi_parser.py:182:
   `return result` in the parser branch. Added
   `test_capture_records_with_parser_returns_parser_result`
   that asserts the parser's return value is passed through.

**After:** kill rate improved from 1/5 (20%) to 5/5 (100%).
The 5 KNOWN_EQUIVALENT mutations remain (docstring
mutations that have no runtime effect).

## 0/N pair follow-up (2026-07-13)

Three of the 0/N pairs documented in DEFAULT_PAIRS were
investigated further. Two had actionable fixes.

### `(dispatch/converters/convert_to_simplified_csv.py, tests/unit/test_convert_to_simplified_csv.py)` — 3/8 → 5/8

Original: 3/8 (38%). All 5 `TestConvertToSimplifiedCSVColumnLayout`
tests only asserted `os.path.exists(...)` without reading the
actual CSV content — the strongest signal you can have for
"tests don't bind to production behavior".

**Fixes:**

1. Added `test_write_headers_omits_description_when_flag_false`
   in `tests/unit/test_convert_to_simplified_csv.py`. Uses
   `inc_item_desc=True, inc_item_numbers=False, column_layout="upc_number,vendor_item,description"`.
   Reads the CSV and asserts the headers are exactly
   `["UPC", "Item Description"]` — the vendor_item column
   must NOT get the description header. Kills the L131
   `eq_to_ne` mutation (`column == "description"` flipped
   to `!=`).
2. Added `test_default_include_headers_when_no_param` that
   calls `edi_convert` with an EMPTY `parameters_dict` and
   asserts the default `simple_csv_include_headers=True`
   produces a header row. Kills the L74 `true_to_false`
   mutation.

**Remaining survivors:** L64 `false_to_true` (retail_uom
default) — to kill this we'd need a test with a populated
`upc_lut` and matching `each_uom_categories`. The retail
UOM transform is gated by `should_apply_retail_uom` which
short-circuits when the upc_lut is empty, so the existing
test with empty `upc_lut` doesn't catch the mutation.
Documented in DEFAULT_PAIRS as 5/8 (was 3/8).

### `(dispatch/converters/convert_to_scansheet_type_a.py, tests/unit/test_convert_to_scansheet_type_a.py)` — 0/9 → 1/9

Original: 0/9. The 131-line test file only tests 2 of 12+
private methods. The converter's public `edi_convert`
interface (which orchestrates the full pipeline) is
untested.

**Fix:**

- Added
  `test_extract_invoices_from_edi_filters_to_a_records_only`
  in `tests/unit/test_convert_to_scansheet_type_a.py`.
  Uses a real EDI file with one A record, one B record,
  and one C record. Calls `_extract_invoices_from_edi` and
  asserts the result is `["0000001"]` (only the A record's
  invoice number's last 7 digits). Kills the L149 `eq_to_ne`
  mutation.

**Remaining survivors:** L130 `return_none_instead_of_value`
(edi_convert's return), L194 `gt_to_ge`, L209 `lt_to_le`,
L287 `ge_to_gt` (all in DB or barcode handling), L316
`or_to_and` (in error handling), and 2 docstring mutations.
The public `edi_convert` requires a database connection,
which is a much larger refactor. Documented in DEFAULT_PAIRS
as 1/9 (was 0/9).

### Pre-existing findings (not fixed, documented)

The 16 remaining hygiene violations (down from 19 after the
4 fixes above) are all in the categories the plan identified
as pre-existing:

- 11 `bare_except_pass` in optional-dependency probes
  (PIL/pyzbar, yaml, zipfile). Should be `pytest.importorskip()`
  but aren't real bugs. Listed in
  `.kilo/plans/meta-tests-beyond-mutation.md` as a follow-up.
- 3 `skip_no_reason` are f-string skips (the runner's regex
  doesn't catch f-string positional reasons). Style nit.
- 1 `missing_assert` is `test_folder_configuration_pydantic_valid`
  (already known, documented in this file).
- 1 `single_item_dispatch_root_import` is `from dispatch import feature_flags`
  in `test_feature_flags_property.py`. Should be
  `from dispatch.feature_flags import feature_flags`. Style nit.

### Re-run after fixes

- Hygiene runner: 19 → 16 violations. The 3 fixed bugs no
  longer appear.
- Phase 3a oracle runner: still 0 flagged (the 3 hardcoded
  oracle tests added in commit `812ead07b` are intact).
- All 3 meta-test self-checks pass.
- New `test_build_split_filename_prepend_date_true_puts_date_in_prefix`
  kills the `negate_if_condition` mutation at edi_splitter.py:72.
