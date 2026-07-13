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
file with `ast.parse` and runs seven checks:

| Rule | Catches |
|---|---|
| `bare_magicmock` | `MagicMock()` without `spec=` (delegates to `conftest_magicmock_plugin.MagicMockVisitor`) |
| `missing_assert` | `def test_*` with no `assert` / `pytest.raises` / `pytest.warns` / `pytest.fail` |
| `sleep_call` | actual `time.sleep(...)` call (not `patch("time.sleep")` or string mention) |
| `skip_no_reason` | `pytest.skip()` with no positional reason and no `reason=` kwarg |
| `bare_except_pass` | `except: pass` / `except Exception: pass` |
| `unjustified_noqa` | `# noqa` without `: CODE — reason` justification |
| `single_item_dispatch_root_import` | `from dispatch import X` (single name) |

The runner is parametrized over `(file, check_name)` so
`pytest tests/meta/test_hygiene.py -k missing_assert -n auto` narrows
the run. A `test_hygiene_runner_self_check` asserts the runner file
itself has no violations of the rules it enforces.

**Headline finding (initial run, 2026-07-09):** 19 violations across
14 files out of 153 scanned. The bare-MagicMock and time.sleep checks
are already clean (enforced by `conftest_magicmock_plugin` and
project-wide conventions respectively); the runner's value is in
surfacing the remaining 4 rules. See
`docs/meta-test-findings.md` for per-violation context.

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
