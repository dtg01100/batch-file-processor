---
applyTo: '**/*.py'
description: 'Guidelines for managing Python dependencies in the Batch File Processor project'
---

# Dependency Management

## Core Principles

- **Pin critical dependencies** to avoid breaking changes
- **Use the virtual environment exclusively** — never install globally
- **Separate runtime and dev dependencies** clearly
- **Audit dependencies regularly** for security vulnerabilities
- **Document why each dependency is needed**

## Dependency Files

### `requirements.txt` — Runtime Dependencies

Contains all packages needed to **run** the application:

- PyQt5 for the GUI
- SQLAlchemy for database access
- paramiko for SSH/SFTP
- requests for HTTP operations
- pytest and pytest-qt (needed for test imports in runtime code)
- All other libraries used by the application

### `requirements-dev.txt` — Development Dependencies

Contains packages needed for **development and testing**:

```
black==26.3.1              # Code formatter
ruff>=0.15.8               # Fast linter
isort==5.12.0              # Import sorter
pytest==7.4.3              # Test framework
pytest-cov==4.1.0          # Coverage reporting
pytest-timeout>=2.2.0      # Test timeout enforcement
pytest-xdist>=3.5.0        # Parallel test execution
hypothesis>=6.100.0        # Property-based testing
pydantic>=2.10.0           # Data validation (dev/testing)
```

## Adding a New Dependency

### Step 1: Determine the Category

Ask: **Is this needed at runtime or only for development?**

- **Runtime**: Application won't work without it → `requirements.txt`
- **Development**: Testing, linting, formatting, analysis → `requirements-dev.txt`

### Step 2: Choose the Right Version Constraint

```txt
# Pin exact version for critical/stable packages
package==1.2.3

# Allow patch updates for bug fixes
package>=1.2.0

# Allow minor updates for new features
package>=1.2,<2.0

# Latest version (use sparingly, only for fast-moving dev tools)
package
```

**Guidelines:**
- Pin **exact versions** (`==`) for packages that have caused breaking changes before
- Use **minimum versions** (`>=`) for stable packages where patches are safe
- Use **upper bounds** (`<`) when major versions might break compatibility
- Avoid bare package names (no version constraint) except for very stable packages

### Step 3: Install in the Virtual Environment

```bash
# Activate the virtual environment first
source .venv/bin/activate

# Install the package
pip install <package>

# Or install from requirements file
pip install -r requirements.txt
pip install -r requirements-dev.txt
```

### Step 4: Update the Requirements File

Add the package to the appropriate requirements file with a comment explaining **why** it's needed:

```txt
# requirements.txt
requests>=2.32.2          # HTTP client for API integrations
paramiko>=3.0.0           # SSH/SFTP client for file transfers

# requirements-dev.txt
pytest-xdist>=3.5.0       # Parallel test execution for faster CI
```

### Step 5: Verify Installation

```bash
# Verify the package is installed
pip show <package>

# Test that it imports correctly
python -c "import <package>; print(<package>.__version__)"

# Run relevant tests
pytest tests/ -x --timeout=30 -q
```

## Removing a Dependency

### Step 1: Verify It's Actually Unused

```bash
# Search for imports of the package
grep -r "import <package>" --include="*.py" .
grep -r "from <package>" --include="*.py" .

# Check if it's a transitive dependency (needed by another package)
pip show <package> | grep "Required-by"
```

### Step 2: Remove from Requirements File

Delete the line from `requirements.txt` or `requirements-dev.txt`.

### Step 3: Uninstall from Virtual Environment

```bash
source .venv/bin/activate
pip uninstall <package>
```

### Step 4: Verify Nothing Breaks

```bash
# Run the full test suite
pytest tests/ -x --timeout=30 -q

# Run the linter
ruff check .

# Try running the application
./.venv/bin/python interface/main.py
```

## Upgrading Dependencies

### When to Upgrade

- **Security vulnerabilities**: Upgrade immediately
- **Bug fixes**: Upgrade when the bug affects you
- **New features**: Upgrade when you need the feature
- **Major versions**: Upgrade carefully, test thoroughly

### Safe Upgrade Process

```bash
# 1. Check for outdated packages
source .venv/bin/activate
pip list --outdated

# 2. Upgrade a single package
pip install --upgrade <package>

# 3. Update the requirements file with the new version
# Edit requirements.txt or requirements-dev.txt

# 4. Run tests to verify nothing breaks
pytest tests/ -x --timeout=30 -q

# 5. If tests fail, pin to the last working version
# <package>=<last_working_version>
```

### Bulk Upgrade (Use with Caution)

```bash
# Upgrade all packages (risky — test thoroughly!)
pip install --upgrade -r requirements.txt
pip install --upgrade -r requirements-dev.txt

# Run full test suite
pytest tests/ --timeout=30 -q
```

## Security Auditing

### Regular Audits

```bash
# Check for known vulnerabilities
pip audit

# Or use safety (alternative tool)
pip install safety
safety check -r requirements.txt
safety check -r requirements-dev.txt
```

### When Vulnerabilities Are Found

1. **Assess severity**: Critical/High → fix immediately, Medium/Low → schedule
2. **Check for updates**: `pip install --upgrade <vulnerable-package>`
3. **Test thoroughly**: Run full test suite after upgrade
4. **Update requirements file**: Pin to the fixed version
5. **Document the fix**: Add a comment explaining the security fix

## Using uv for Faster Dependency Management

If `uv` is available (faster alternative to pip):

```bash
# Install dependencies (much faster than pip)
uv pip install -r requirements.txt
uv pip install -r requirements-dev.txt

# Upgrade a package
uv pip install --upgrade <package>

# Sync environment to match requirements files exactly
uv pip sync requirements.txt
```

## Common Issues and Solutions

### Issue: Conflicting Dependencies

```bash
# Problem: pip reports dependency conflicts
# Solution: Identify the conflict
pip install <package>  # Read the error message carefully

# Check which packages require conflicting versions
pip show <package1> <package2>

# Resolve by finding compatible versions or removing one
```

### Issue: Package Not Found After Installation

```bash
# Verify you're in the right environment
which python
# Should be: /path/to/project/.venv/bin/python

# Reinstall if needed
pip uninstall <package>
pip install <package>
```

### Issue: Import Error After Upgrade

```bash
# Check if the package structure changed
python -c "import <package>; print(dir(<package>))"

# Pin to the last working version
pip install <package>==<last_working_version>

# Update requirements file accordingly
```

## Best Practices

1. **Always activate the venv** before installing or removing packages
2. **Keep requirements files up to date** — they are the source of truth
3. **Pin versions that matter** — don't pin everything, but pin what breaks
4. **Test after every dependency change** — run the relevant test suite
5. **Document why** — add comments for non-obvious dependencies
6. **Audit regularly** — check for vulnerabilities monthly
7. **Use exact pins for critical packages** — especially GUI frameworks and database drivers
8. **Never install globally** — always use the virtual environment

## Project-Specific Notes

### Critical Pinned Dependencies

These packages are pinned to exact versions due to compatibility requirements:

- `PyQt5==5.15.10` — GUI framework, major version changes break UI code
- `urllib3==2.6.3` — Pinned due to requests compatibility
- `pytest==7.4.3` — Test framework, ensure consistent behavior
- `black==26.3.1` — Code formatter, version affects formatting output

### Optional Dependencies

Some packages are optional and only needed for specific features:

- `pytest-xdist` — Speeds up test runs (parallel execution)
- `hypothesis` — Property-based testing (advanced test coverage)
- `pydantic` — Data validation (used in some converters)

### Transitive Dependencies

Many packages are pulled in as dependencies of other packages. Don't remove these from `requirements.txt` unless you're certain they're not needed directly.

## CI/CD Integration

The dependency installation should be part of the CI/CD pipeline:

```bash
# In CI/CD script
source .venv/bin/activate
pip install -r requirements.txt
pip install -r requirements-dev.txt
pytest tests/ --timeout=30
ruff check .
black --check .
```

This ensures the application works with the pinned dependencies and catches issues before they reach production.
