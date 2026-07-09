# Meta-test findings

## What the meta-test does

`tests/meta/test_property_tests_are_sufficient.py` is a brutally simple mutation
runner. For each (production module, property test file) pair, it applies a
fixed list of obvious mutations one at a time and runs the property test. If
the test still passes, the mutation **survived**: a real bug of that shape
would have slipped past the test.

The full list of mutations: comparison swaps (`<`↔`<=`, `>`↔`>=`,
`==`↔`!=`), boolean flips (`True`↔`False`), connector swaps
(`and`↔`or`), return-statement replacement with `None`, `if`-condition
negation, and a +1 off-by-one on integer constants.

## How to run it

```bash
# All 9 default property-test pairs.
pytest tests/meta/test_property_tests_are_sufficient.py -n 0 -s

# Or as a CLI.
.venv/bin/python tests/meta/test_property_tests_are_sufficient.py \
    --module core/edi/edi_parser.py \
    --tests tests/unit/core/edi/test_edi_parser_property.py
```

## First run: what was found

Wall time ~4 minutes for all 9 pairs. The result: **34 of 80 mutations
were killed, 46 survived**.

### The headline finding

The meta-test surfaced a real test bug in the splitter property tests.
`SplitConfig.prepend_date` defaults to `True`. The existing property tests
construct `SplitConfig(output_directory="/tmp/out", filename_stem="...")`
without specifying `prepend_date`, so the production code calls
`parse_edi_date` on the strategy-generated `invoice_date`. The strategy
`st.text(alphabet=_DIGITS, min_size=6, max_size=6)` produced the string
`"000000"`, which `parse_edi_date` rejects (month 00). The test only
appeared to pass because the Hypothesis example database had cached
passing examples from earlier runs.

Fix: add `prepend_date=False` to every `SplitConfig(...)` construction in
`tests/unit/core/edi/test_edi_splitter_property.py`. After the fix, the
property test runs in 1.3s, down from "infinite hang on clean cache".

### Per-module kill rate

| Module | Killed | Total | Kill rate |
|---|---|---|---|
| edi_parser | 5 | 10 | 50% |
| edi_splitter | 4 | 7 | 57% |
| edi_splitting_utils | 3 | 11 | 27% |
| c_rec_generator | 1 | 7 | 14% |
| edi_transformer | 3 | 7 | 43% |
| upc_utils | 4 | 11 | 36% |
| feature_flags | 4 | 6 | 67% |
| file_utils | 3 | 9 | 33% |
| hash_utils | 4 | 8 | 50% |

The c_rec_generator result is suspicious — only 1 of 7 mutations killed.
The survivors cluster on the `QueryRunnerProtocol` (sentinel runner path)
and the `CRecordConfig` defaults, which the test does not exercise.

## Survivor triage

The full list of 46 survivors is in the run output. They split into three
buckets:

### Bucket 1: equivalent mutations (no test should catch these)

These are mutations that change code in a way the test cannot observe:

- `and_to_or` / `or_to_and` at low line numbers (1, 3, 5, 6): the
  mutation lands inside a module docstring ("...variables or database
  settings..."). The test does not parse the docstring, so the change
  has no observable effect.
- `int_constant_off_by_one` at lines like 6, 15, 22: these are version
  numbers, `__all__` lengths, or constant table sizes that the test
  does not depend on.
- `true_to_false` / `false_to_true` at lines like 27, 38, 100, 128: in
  some cases these land in docstrings ("True if DISPATCH_DEBUG_MODE is
  'true'"), in other cases on default values that the test overrides
  anyway.

### Bucket 2: real test gaps (write stronger property tests)

- `edi_parser.lt_to_le` at line 89: `if len(line) < EDI_A_RECORD_MIN_LENGTH`.
  The current property tests use `_fixed_text(N)` which generates strings
  of exactly length N, so the boundary at N is not exercised. A test
  that uses `min_size=N-1, max_size=N+1` would catch the off-by-one.
- `edi_parser.ge_to_gt` at line 93: a debug-log format string. The test
  does not assert on log output. Either: add a log-capturing fixture, or
  document the mutation as not-our-concern.
- `edi_splitting_utils.lt_to_le` at line 79: the `_col_to_excel` function.
  The current tests assert length-1 for n in [1, 26] but not the exact
  result for boundary values like 26, 27.
- `c_rec_generator.int_constant_off_by_one` at line 126: the fixed
  output length is 9; the test asserts the field length but not the
  exact integer.
- `c_rec_generator.return_none` at line 20: an `__init__` arg branch.
  The test does not exercise the missing-`config` path.

### Bucket 3: test setup bugs (similar to the splitter one)

None of the remaining survivors look like this; the splitter fix
resolved the one I found in this run.

## What to do next

The meta-test framework is in place. Two follow-ups, in priority order:

1. **Lock the equivalent mutations as such.** Add a `KNOWN_EQUIVALENT`
   list to the runner — `(module, line, mutation_name)` triples that
   the runner should skip. This is a brutal simple change: a `set` of
   tuples, a `continue` in the loop. Roughly 30 of the 46 survivors
   are equivalent and would be silenced by this.
2. **Add meta-test coverage for non-property tests.** Every test file
   that exercises a single production module should have a pair in
   `DEFAULT_PAIRS`. The list will grow; the runner will not.

The user explicitly asked for the simplest possible approach. The
runner is already that: a fixed mutation list, a `subprocess.run`,
and a printed report. Any "improvement" beyond that should be
rejected on auditability grounds.
