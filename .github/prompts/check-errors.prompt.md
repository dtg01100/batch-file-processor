---
description: "Check project for logic errors, code errors, and potential bugs"
argument-hint: "Target (default: entire project, or specify module path)"
agent: "agent"
tools: [search, read_file, run_in_terminal, get_errors]
---

# Project Code Audit

Perform a comprehensive logic and code error audit on the specified target.

## Input

- **Target**: `{argument}` — module path (default: entire project)
- **Code context**: Current file or selection if provided

## Audit Process

### 1. Static Analysis

Run linting and type checking:
```bash
# Lint check
ruff check {target}

# Black formatting check
black --check {target}

# Python syntax validation
.venv/bin/python -m py_compile {target}
```

### 2. Error Collection

Use `get_errors` tool on target files to collect any IDE-reported errors:
- Collect all files with errors
- Group by error type (syntax, type, import, lint)

### 3. Logic Error Detection

Search for common logic errors:

| Pattern | Risk | Search |
|---------|------|--------|
| SQL with f-string interpolation | **Critical** | `grep -rn "execute.*f\""` or `"\.format\(` in SQL context |
| Path construction with f-strings | **High** | `grep -rn 'os\.path\.join.*f"'` or `"\{.*\}/\{.*\}"` for paths |
| Bare `open()` without `with` | **Medium** | `grep -rn "^\s*open("` |
| Silent exception swallowing | **Medium** | `grep -rn "except.*:\s*$"` or `"except.*pass"` |
| Threading without exception capture | **High** | `grep -rn "Thread.*start"` in dispatch/interface |
| Empty `except:` blocks | **Medium** | `grep -rn "except:"` |

### 4. Test Execution

Run targeted tests to catch runtime errors:
```bash
# Unit tests with timeout
.venv/bin/pytest tests/unit/ -q --timeout=30 -x

# Dispatch tests if target includes dispatch/
.venv/bin/pytest tests/dispatch/ -q --timeout=30 -x
```

### 5. Project-Specific Checks

Based on repository conventions:

- **SQL Parameterization**: Verify all `cursor.execute()` uses `%s` or `?` placeholders, not f-strings
- **Path Handling**: Verify `os.path.join()` used instead of `f"{a}/{b}"` path concatenation
- **File Handles**: Verify all `open()` wrapped in `with` statements
- **Thread Safety**: Verify threads capture and re-raise exceptions via `queue.Queue`

## Output Format

```markdown
## Code Audit Report for `{target}`

### Static Analysis Results
| File | Issue | Line | Severity |
|------|-------|------|----------|
| ... | ... | ... | ... |

### Logic Errors Found
| Location | Issue | Risk | Suggestion |
|----------|-------|------|------------|
| ... | ... | ... | ... |

### Test Results
- **Command**: `pytest {target}`
- **Result**: PASS/FAIL
- **Failures**: [list if any]

### Recommendations
1. ...
2. ...
```

## Quality Criteria

- Every error categorized by severity (Critical/High/Medium/Low)
- Each issue includes file:line reference
- Each issue includes actionable fix suggestion
- Critical issues (SQL injection, path traversal) must be flagged prominently

## References

- [AGENTS.md](../AGENTS.md) — project commands and conventions
- [copilot-instructions.md](../.github/copilot-instructions.md) — coding standards
