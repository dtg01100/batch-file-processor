---
description: "Generate edge-case test matrix for dispatch pipeline modules"
argument-hint: "Target module or function (e.g., dispatch/orchestrator.py, convert_to_tweaks)"
agent: "agent"
---

# Dispatch Pipeline Edge-Case Test Case Generator

Generate a comprehensive edge-case test matrix for the specified dispatch pipeline module.

## Input

- **Target**: `{argument}` — module, function, or concept to generate test cases for
- **Code context**: Current file or selection in editor

## Process

1. **Inspect the target module**
   - Read the target file to understand the function signature, inputs, and outputs
   - Identify external dependencies (filesystem, database, network protocols)
   - Map the happy path vs. error handling branches

2. **Generate edge-case matrix**

   Produce a Markdown table with the following columns:

   | Test Case | Input Condition | Expected Behavior | Test Marker | Fixtures |
   |-----------|-----------------|-------------------|-------------|----------|
   | `test_<function>_<case>` | Description of inputs | Expected outcome | `unit`/`dispatch`/`integration` | `tmp_path`, etc. |

3. **Prioritize cases by risk**

   - **Critical**: Empty input, null values, boundary conditions
   - **Error paths**: Exception handling, retry logic, timeout behavior
   - **Edge cases**: Empty files, malformed data, permission errors

## Output Format

```markdown
## Edge-Case Test Matrix for `<target>`

### Critical Path Tests
| Test Case | Input | Expected | Marker | Fixtures |
|-----------|-------|----------|--------|----------|
| ... | ... | ... | ... | ... |

### Error Handling Tests
| Test Case | Input | Expected | Marker | Fixtures |
|-----------|-------|----------|--------|----------|
| ... | ... | ... | ... | ... |

### Suggested Test File
`tests/dispatch/test_<module>.py` or `tests/unit/test_<module>.py`

### Commands to Run
```bash
./.venv/bin/pytest tests/dispatch/test_<module>.py -q --timeout=30
ruff check tests/dispatch/test_<module>.py
```
```

## Quality Criteria

- Each test case has a descriptive name ending with the scenario (e.g., `test_convert_tweaks_empty_input`)
- Fixtures match actual dependencies (no fake Qt widgets, no mocks for internal logic)
- Markers follow repository conventions (`unit`, `dispatch`, `conversion`, `integration`)
- Edge cases cover empty, null, boundary, and malformed inputs

## References

- [test-strategy-wizard skill](../docs/skills/test-strategy-wizard.SKILL.md) — marker and fixture selection
- [dispatch-test-wizard skill](../docs/skills/dispatch-test-wizard.SKILL.md) — dispatch test development pattern
