# tests/meta — tests for our tests

This directory contains meta-tests: tests that probe the test suite itself.

The point is simple. As the property tests in `tests/unit/**/*_property.py` get
tighter, we expect bugs to surface. The meta-test is what surfaces them.

## What is here

### `test_property_tests_are_sufficient.py`

A brutally simple mutation runner. For each (production module, property test
file) pair, it:

1. Applies a small fixed list of mutations to the module source — comparison
   swaps, boolean flips, connector swaps, return-statement changes, integer
   off-by-one, etc.
2. For each mutation, runs the property test once. If the test still passes,
   the mutation **survived**: the test would have missed that real bug.
3. Prints a per-module report. Survivors are listed by file, line, and
   mutation name. The runner exits non-zero if any survivor exists.

The runner is intentionally simple. It uses `subprocess.run` and a fixed
mutation list. It does NOT use a mutation-testing framework (mutmut, cosmic
ray, etc.) — those are great, but they come with plugin systems, config
files, and opinions we do not need. The whole file is < 400 lines.

### `DEFAULT_PAIRS`

The 9 default (module, test) pairs. To extend, add a line to the list and
the wrapper picks it up.

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
```

The pytest wrapper prints survivors inline; the CLI prints the same plus an
overall summary.

## Interpreting survivors

A surviving mutation is one of:

1. **Real gap.** The test does not exercise the mutated code path. Fix: write
   a stronger property test that covers the boundary / branch.
2. **Equivalent mutation.** The change has no observable effect. Document it
   inline at the test site with a comment, and either (a) extend the
   mutation list to skip that exact line, or (b) accept the survivor.
3. **Test bug.** The mutation surfaced a real bug in the test setup, e.g.
   missing argument, default value clash, or flaky strategy. Fix the test.

When the meta-test first ran, it surfaced a real bug in the splitter
property tests: the test constructed `SplitConfig(...)` without specifying
`prepend_date`, which defaults to `True`, and the `_INVOICE_DATE_STRINGS`
strategy could produce `"000000"` — which crashes `parse_edi_date` inside
the production code. The test only appeared to pass because the Hypothesis
example database had cached passing examples from earlier runs. The fix:
add `prepend_date=False` to every `SplitConfig(...)` in the property tests.

That is exactly the kind of bug this meta-test is for.

## When to re-run

- After tightening a property test.
- After a refactor that changes control flow in any module under test.
- Periodically as a smoke test in CI. Long wall time is acceptable: the
  runner reports a per-mutation progress line.

## Why a hand-rolled runner, not mutmut?

The user asked for the simplest possible meta-test. mutmut is a great tool
but it carries a trampoline plugin, a configuration file, a coverage setup,
a Textual TUI, and a multi-process worker model. For our purposes, a
`subprocess.run` + regex + a fixed mutation list is enough. We can switch
later if the hand-rolled runner starts hiding bugs.
