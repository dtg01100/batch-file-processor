# tests/meta — tests for our tests

This directory contains meta-tests: tests that probe the test suite itself.

The point is simple. As the property tests in `tests/unit/**/*_property.py`
get tighter, we expect bugs to surface. The meta-test is what surfaces them.

## What is here

### `test_property_tests_are_sufficient.py`

A brutally simple mutation runner. For each (production module, test
file) pair in `DEFAULT_PAIRS`, it:

1. Applies a small fixed list of mutations to the module source — comparison
   swaps, boolean flips, connector swaps, return-statement changes, integer
   off-by-one, etc.
2. For each mutation, runs the test once. If the test still passes,
   the mutation **survived**: the test would have missed that real bug.
3. Prints a per-module report. Survivors are listed by file, line,
   mutation name, and the original/mutated source lines so a reviewer
   can audit each one by sight.
4. The runner exits non-zero if any survivor exists.

The runner is intentionally simple. It uses `subprocess.run` and a fixed
mutation list. It does NOT use a mutation-testing framework (mutmut, cosmic
ray, etc.) — those are great, but they come with plugin systems, config
files, and opinions we do not need. The whole file is one screenful.

### `test_hygiene.py` (added 2026-07-09)

A static AST-based linter that scans every test file under `tests/unit/`
for violations of the conventions documented in `tests/AGENTS.md` and
the project root `AGENTS.md`. Unlike the mutation runner it does no
subprocess, no fixture setup, no module imports — it parses each test
file with `ast.parse` and runs checks:

| Rule | Catches |
|---|---|
| `bare_magicmock` | `MagicMock()` without `spec=` (delegates to `conftest_magicmock_plugin.MagicMockVisitor`) |
| `missing_assert` | `def test_*` with no `assert` / `pytest.raises` / `pytest.warns` / `pytest.fail` |
| `sleep_call` | actual `time.sleep(...)` call (not `patch("time.sleep")` or string mention) |
| `skip_no_reason` | `pytest.skip()` with no positional reason and no `reason=` kwarg |
| `bare_except_pass` | `except: pass` / `except Exception: pass` |
| `unjustified_noqa` | `# noqa` without `: CODE — reason` justification |
| `single_item_dispatch_root_import` | `from dispatch import X` (single name) |
| `assert_is_bool_comparison` | `assert X is True` / `assert X is False` (tautology) |
| `magic_padding` | `"00" + x` zero-padding concatenation (AGENTS.md anti-pattern; use `f"{x:02d}"` or `x.zfill(N)`) |
| `tuple_subscript_trick` | `(expr, None)[1]` obfuscation (AGENTS.md anti-pattern) |
| `nested_try_pyramid` | try/except nested 3+ levels deep (AGENTS.md anti-pattern; use a `stage` variable) |

The runner is parametrized over `(file, check_name)` so
`pytest tests/meta/test_hygiene.py -k missing_assert -n auto` narrows
the run. A `test_hygiene_runner_self_check` asserts the runner file
itself has no violations of the rules it enforces.

**Headline finding (initial run, 2026-07-09):** 19 violations across
14 files out of 153 scanned. bare-MagicMock and time.sleep checks
are already clean (enforced by `conftest_magicmock_plugin` and
project-wide conventions respectively); the runner's value is in
surfacing the remaining 4 rules. See
`docs/meta-test-findings.md` for per-violation context.

**Headline finding (2026-07-14, layer expansion):** 208 files scanned
(unit + integration + qt, see ``_layers.py``). 16 entries in
``KNOWN_HYGIENE_VIOLATIONS`` silence intentional exceptions
(sentinel catches, optional-dep probes, polling-helper sleep calls).
The runner reports **9 real findings across 6 files** in production
test code; all are tracked in ``docs/meta-test-findings.md`.

Re-validate the allowlist with::

    python tests/meta/test_hygiene.py --no-skip-known-hygiene-violations

### `test_assertions_are_meaningful.py` (added 2026-07-13)

An AST-based assertion-mutation runner. For every test file under
`tests/unit/`, it parses the file with `ast`, finds every
`ast.Assert` node, and applies a set of targeted mutations using a
`NodeTransformer`:

| Rule | Mutation |
|---|---|
| `polarity_flip` | `assert X` -> `assert not (X)` |
| `equality_flip` | `assert X == Y` -> `assert X != Y` |
| `inequality_flip` | `assert X != Y` -> `assert X == Y` |
| `membership_flip` | `assert X in Y` -> `assert X not in Y` |
| `identity_flip` | `assert X is Y` -> `assert X is not Y` |
| `gt_lt_flip` | `assert X > Y` -> `assert X < Y` |
| `ge_le_flip` | `assert X >= Y` -> `assert X <= Y` |
| `bool_literal_flip` | `assert X is True` <-> `assert X is False` |
| `always_fail` | `assert X` -> `assert False` |

The plan also listed a `delete` rule (replace with `pass`). It was
tried and removed: in pytest 9, a test with zero assertions vacuously
passes, so `delete` produced the same "all assertions are dead" signal
regardless of load-bearing. `always_fail` already answers the same
question with cleaner signal.

For each mutation, the runner loads the mutated source into a fresh
in-process module namespace, walks every `test_*` function (top-level
and class methods), and runs each. A mutation "kills" the test if any
test function raises. **Default execution path is in-process** (see
`tests/meta/test_assertions_are_meaningful.py`'s `_run_mutated_tests_inprocess`).

**Cost (in-process, default):** 208 files × 9 rules × ~7ms per
mutation = ~13s serial; ~3min for the full sweep. Measured 145x
speedup over the legacy subprocess path (1.07s/mutation).
**Cost (subprocess, opt-in via `TAM_USE_SUBPROCESS=1`):** same as
prior, ~1.07s per mutation; ~33min for the full sweep on -n auto.

The in-process runner provides minimal stand-ins for the standard
pytest fixtures the project uses (`tmp_path`, `tmpdir`, `caplog`,
`capfd`, `capsys`, `monkeypatch`). Tests that depend on other
fixtures (`qtbot`, real `tmpdir` paths consumed by subprocess) may
see a `TypeError` from the missing arg, which the runner treats as
a kill. This is the safer wrong answer for a meta-test (a missing
fixture always means the assertion is load-bearing, by definition).
See `docs/meta-test-findings.md` for the parity verification
(`test_structured_logging.py`: 82/82 kills match; integration
`test_mock_automatic_run.py`: same finding reproduces).

The runner is parametrized over `(file, rule_name)`. A
`KNOWN_ASSERTION_EQUIVALENT` allowlist cites the source line as
evidence when a survivor is judged equivalent. A self-check asserts
the runner file itself has no dead assertions.

### `test_property_oracle_consistency.py` (added 2026-07-13)

A static AST classifier for property-test oracles. The bug pattern
this catches is the **self-referential test**: a test that uses the
function-under-test (directly or transitively) to build its own
oracle, so any consistent mutation of the function makes the test
pass vacuously.

The existing mutation runner already caught one such bug
(`test_validate_upc_accepts_check_digit` constructed its input from
`calc_check_digit`; the fixed version uses hardcoded oracles). This
runner automates the hunt.

For every `tests/**/*_property.py` file, the runner:

1. Walks every `@given` test.
2. Resolves the **function-under-test** by matching the test name
   against the file's `from X import Y` statements (longest prefix
   wins).
3. For each `assert` in the test, classifies the assertion:
   - `trivially_true` — both operands are the same `f(x)` call
   - `self_referential_helper` — both operands use `f()` with
     different args
   - `oracle_uses_f_left` / `oracle_uses_f_right` — one operand
     uses `f()`, the other is independent
   - `oracle_independent` — neither side uses `f()`
4. Flags tests where the input is built from a call to `f` AND an
   assertion checks `f` (the "input-construction helper uses f"
   pattern that hid the original `test_validate_upc_*` bug).
5. Emits a per-file report; the pytest wrapper fails on
   `trivially_true`, `self_referential_helper`, or input-construction
   patterns.

**Initial run (2026-07-13):** 9 property files, 98 property tests,
159 assertions. **6 tests flagged** with real signal:

- 3 `trivially_true` (`test_calc_check_digit_is_deterministic`,
  `test_convert_to_price_is_deterministic`,
  `test_convert_to_price_decimal_is_deterministic`) — these are
  intentional sanity checks that f is pure; documented but not
  fixed.
- 1 `self_referential_helper` (`test_calc_check_digit_accepts_int_input`)
  — the test only validates that int-coercion doesn't change the
  result, but the result is computed by f itself; a consistent
  mutation to f would pass. Real finding; needs a hardcoded oracle
  counterpart.
- 2 false-positive candidates (the
  `test_filter_b_records_by_category_*` tests) — the runner
  classifies them as `oracle_independent` because the function
  call is hidden behind a `result =` assignment that the
  classifier's `ast.walk` doesn't trace. Phase 3b work.

Phase 3b (consistency checks) is not yet implemented; the current
deliverable is the enumeration report. The plan flagged Phase 3
as experimental.

### `test_module_coverage.py` (added 2026-07-16)

Surfaces production modules that no test file imports. A module
without any test reference is a silent refactor risk: a change to
its behavior can break production without any test failing.

**Detection strategy:**
1. Walk every production root (`core/`, `dispatch/`, `backend/`,
   `interface/`, `adapters/`, `batch_file_processor/`, `scripts/`)
   and build the set of module dotted names.
2. Walk every test file under `tests/` (excluding `tests/meta/`),
   parse every `Import` and `ImportFrom`, and also extract dotted
   module paths from `patch("...")` / `monkeypatch.setattr("...")`
   string arguments (those are runtime imports that don't show up
   as AST imports).
3. A module is "covered" if any test imports its exact dotted path
   OR a longer path that starts with it (e.g. `from foo.bar.baz
   import X` covers `foo.bar.baz`).

**Why this rule (no parent-package matching):** Python does not
auto-load submodules when a parent package is imported. `from
foo import bar` only loads `foo/bar.py` if `foo/__init__.py` eagerly
re-exports it. Most `__init__.py` files in this project do not, so
parent-package matching would over-credit coverage. The strict rule
(direct or longer-prefix match) accepts false positives (saying
uncovered when the module is loaded by an eager `__init__.py`) in
exchange for never missing a real gap.

**Initial run (2026-07-16):** 185 production modules scanned, 37
uncovered. All 37 are intentional:
- 4 `adapters/inmemory/*` — in-memory adapter not used in production
  (db2ssh is the production adapter).
- 5 `core/*` — utility helpers (CSV, folder-path, generic `utils`).
- 6 `dispatch/*` — converters imported only via `patch()` string
  references, and pipeline factory that is constructed inline.
- 9 `interface/*` — Qt form/window helpers exercised via dialog
  smoke tests, not direct imports.
- 13 `scripts/*` — CLI utilities invoked manually, not library code.

The full allowlist is in `KNOWN_UNCOVERED` with one-line citations
for each entry. Re-validate with::

    python tests/meta/test_module_coverage.py --no-skip-known-uncovered

### `test_marker_placement.py` (added 2026-07-16)

Catches the case where a test file's `@pytest.mark.X` decorator
doesn't match its directory convention. AGENTS.md says `@unit`
tests live under `tests/unit/`, `@integration` under
`tests/integration/`, etc. A marker that conflicts with the
directory is a layering smell: a `-m unit` selector silently
excludes an integration test, or vice versa.

**Detection strategy:**
1. Walk every `test_*.py` under `tests/` (excluding `tests/meta/`).
2. For each file, extract every `@pytest.mark.<name>` decorator
   from functions, classes, and module-level `pytestmark = [...]`
   lists.
3. Look up each marker in `MARKER_TO_DIRECTORIES` and compare to
   the file's actual directory.

**Initial run (2026-07-16):** 216 test files scanned, 8
misplacements detected. All 8 are intentional cross-layer tests
(Qt-in-integration, integration-in-unit-for-pre-split-tests, etc.)
and live in `KNOWN_MARKER_MISPLACEMENT` with cited reasons.

Re-validate with::

    python tests/meta/test_marker_placement.py --no-skip-known-marker-misplacement

### `DEFAULT_PAIRS`

The 16 default (module, test) pairs. To extend, add a line to the list
and the wrapper picks it up.

### `KNOWN_EQUIVALENT`

A list of (module_relpath, mutation_name, line_number, reason) tuples
that silence mutations which cannot produce observable behavior change
— typically they land in a docstring, a comment, a default-argument
value the test overrides, or a version constant.

The reason is the cited source evidence at that line, not a summary.
A typo fails closed: an unknown (module, mutation, line) tuple does
NOT match the skip lookup, and the mutation is applied normally.

The runner exposes `--no-skip-known-equivalent` so the list itself is
auditable: a previously-equivalent mutation that has since become
observable (because a docstring became code, a constant became used,
etc.) is detected as a survivor, and the test fails.

## Running

```bash
# Run all default pairs.
pytest tests/meta/test_property_tests_are_sufficient.py -n 0 -s

# Run a single pair via CLI.
.venv/bin/python tests/meta/test_property_tests_are_sufficient.py \
    --module core/edi/edi_parser.py \
    --tests tests/unit/core/edi/test_edi_parser_property.py

# Run multiple pairs via CLI.
.venv/bin/python tests/meta/test_property_tests_are_sufficient.py \
    --pair-list core/edi/edi_parser.py:tests/unit/core/edi/test_edi_parser_property.py \
    --pair-list core/edi/upc_utils.py:tests/unit/core/edi/test_upc_utils_property.py

# Audit KNOWN_EQUIVALENT itself: run ALL mutations including silenced.
.venv/bin/python tests/meta/test_property_tests_are_sufficient.py \
    --pair-list core/edi/upc_utils.py:tests/unit/core/edi/test_upc_utils_property.py \
    --no-skip-known-equivalent
```

The pytest wrapper prints survivors inline; the CLI prints the same
plus an overall summary.

## Interpreting survivors

A surviving mutation is one of:

1. **Real gap.** The test does not exercise the mutated code path. Fix:
   write a stronger test (often a property test using broader strategy
   alphabets, a hardcoded oracle, or a log-capturing fixture).
2. **Equivalent mutation.** The change has no observable effect. The
   `KNOWN_EQUIVALENT` list documents these with cited evidence; the
   `--no-skip-known-equivalent` flag lets you re-validate the list.
3. **Test bug.** The mutation surfaced a real bug in the test setup,
   e.g. missing argument, default value clash, or — more subtly — a
   self-referential test that uses the function-under-test to build
   its own oracle. Fix the test (see "Self-referential test bugs"
   in `docs/meta-test-findings.md`).

When the meta-test first ran it surfaced a real bug in the splitter
property tests: the test constructed `SplitConfig(...)` without
specifying `prepend_date`, which defaults to `True`, and the
`_INVOICE_DATE_STRINGS` strategy could produce `"000000"` — which
crashes `parse_edi_date` inside the production code. The test only
appeared to pass because the Hypothesis example database had cached
passing examples from earlier runs. The fix: add `prepend_date=False`
to every `SplitConfig(...)` in the property tests.

That is exactly the kind of bug this meta-test is for.

## When to re-run

- After tightening a property test.
- After a refactor that changes control flow in any module under test.
- After any change to a docstring or default value cited in
  `KNOWN_EQUIVALENT` (re-validate the auditability claim).
- Periodically as a smoke test in CI. Long wall time is acceptable:
  the runner reports a per-mutation progress line.

## Why a hand-rolled runner, not mutmut?

The user asked for the simplest possible meta-test. mutmut is a great tool
but it carries a trampoline plugin, a configuration file, a coverage setup,
a Textual TUI, and a multi-process worker model. For our purposes, a
`subprocess.run` + regex + a fixed mutation list is enough. We can switch
later if the hand-rolled runner starts hiding bugs.

### Re-evaluation: 2026-07-13

A pivot attempt to replace this runner with `mutmut` failed. Three
hard blockers were confirmed by direct experiment — see
`docs/meta-test-findings.md` § "Mutmut adoption attempt" for the full
trace logs. The blockers are:

1. **mutmut 3.x + Python 3.11 import-cache bug.** mutmut 3's per-test
   coverage map depends on `PY_IGNORE_IMPORTMISMATCH=1`, which is a
   Python 3.12+ env var. On Python 3.11 (project max per AGENTS.md), the
   first `import core` from project root caches the unmutated module in
   `sys.modules`; the in-process pytest never re-imports from
   `mutants/`, so the trampoline is never entered and the coverage map
   is empty. mutmut reports "could not find any test case for any
   mutant" and exits 1.

2. **mutmut 2.5.1 baseline-must-be-green.** mutmut 2 spawns a fresh
   subprocess per mutant, which sidesteps (1), but first runs the FULL
   test suite as a baseline. The baseline fails on
   `tests/unit/test_build_configuration.py::TestHiddenImports::test_hook_files_collect_all_submodules`
   ("No submodules collected for dispatch") in this environment. mutmut
   2 raises `RuntimeError` and refuses to start. The test is
   environment-sensitive (likely module-discovery in the venv), not
   related to mutation testing.

3. **PyQt5 + pytest workers segfault.** Project AGENTS.md requires Qt
   tests run with `-n0`; the full suite run mutmut needs segfaults in
   a `resend_dialog` test. Workaround (`-m 'not qt' --ignore=...`) is
   available but moot given (2).

The hand-rolled runner does not have any of these issues. It runs
`subprocess.run` per mutation, so each test invocation starts with a
fresh interpreter and import cache; it runs the paired test file (not
the full suite) so Qt tests are not exercised unless the pair itself is
a Qt pair; and it does not require a green baseline. Revisit the
mutmut pivot if (a) Python is upgraded to 3.12+ (lift AGENTS.md
constraint and update the toolchain), or (b) the build-configuration
baseline test is fixed in this environment.
