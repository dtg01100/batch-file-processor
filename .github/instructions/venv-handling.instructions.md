---
applyTo: '**/*.py'
description: 'Instructions for handling Python virtual environment issues - always recreate the venv instead of falling back to host Python'
---

# Python Virtual Environment Handling

## Core Principle

**NEVER bypass the project's virtual environment.** When encountering venv issues, always recreate or fix the virtual environment rather than falling back to the host Python interpreter.

## When to Recreate the Virtual Environment

Recreate the virtual environment when you encounter:
- Missing package errors that should be installed
- Import errors for dependencies listed in `requirements.txt`
- Version conflicts between installed packages
- Corrupted or incomplete venv (missing `pip`, `python` executable, etc.)
- Any indication that the venv is not properly configured

## How to Recreate the Virtual Environment

### Standard Recreation Process

```bash
# 1. Remove the existing venv
rm -rf .venv

# 2. Create a fresh virtual environment
python3 -m venv .venv

# 3. Activate the new environment
source .venv/bin/activate

# 4. Upgrade pip
pip install --upgrade pip

# 5. Install dependencies
pip install -r requirements.txt
pip install -r requirements-dev.txt  # if applicable

# 6. Verify installation
pip list
python -c "import <key_package>; print(<key_package>.__version__)"
```

### Using uv (if available)

```bash
# 1. Remove existing venv
rm -rf .venv

# 2. Create with uv (faster)
uv venv .venv

# 3. Activate
source .venv/bin/activate

# 4. Install dependencies (much faster than pip)
uv pip install -r requirements.txt
uv pip install -r requirements-dev.txt
```

## What NOT to Do

### ❌ BAD: Using host Python directly
```bash
# NEVER do this, even if venv is broken
python3 script.py
python3 -m pytest tests/
pip3 install <package>  # without activating venv first
```

### ❌ BAD: Installing packages globally
```bash
# NEVER install packages globally to fix venv issues
sudo pip install <package>
pip3 install --user <package>
```

### ❌ BAD: Workarounds that bypass the venv
```bash
# DON'T manipulate PYTHONPATH to use system packages
export PYTHONPATH=/usr/lib/python3/site-packages:$PYTHONPATH

# DON'T use system Python while pretending to use venv
.venv/bin/python3 -c "import sys; sys.path.insert(0, '/usr/lib/python3')"
```

## Verification Steps

After recreating the virtual environment:

1. **Verify Python executable**:
   ```bash
   which python
   # Should output: /path/to/project/.venv/bin/python
   ```

2. **Verify key packages**:
   ```bash
   python -c "import pytest; print(f'pytest {pytest.__version__}')"
   python -c "import PyQt6; print(f'PyQt6 {PyQt6.QtCore.PYQT_VERSION_STR}')"
   ```

3. **Run a quick test**:
   ```bash
   pytest tests/unit/test_something.py -x --timeout=30
   ```

## Common Venv Issues and Solutions

### Issue: Missing `python` executable in .venv/bin
```bash
# Solution: Recreate the venv
rm -rf .venv
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### Issue: Package installation fails
```bash
# Solution: Clear pip cache and reinstall
rm -rf .venv
python3 -m venv .venv
source .venv/bin/activate
pip cache purge
pip install --upgrade pip
pip install -r requirements.txt
```

### Issue: Import errors after package installation
```bash
# Solution: Verify package is actually installed
source .venv/bin/activate
pip list | grep <package_name>

# If not listed, reinstall
pip uninstall <package_name>
pip install <package_name>

# If still failing, recreate entire venv
```

### Issue: pytest marker not recognized
```bash
# Solution: Ensure test dependencies are installed
source .venv/bin/activate
pip install -r requirements-dev.txt

# Verify markers are registered
pytest --markers | grep <marker_name>
```

## Project-Specific Notes

For this Batch File Processor project:
- The venv is located at `.venv/` in the project root
- Use `./.venv/bin/python` for direct execution without activation
- Main dependencies: PyQt6, pytest, pytest-qt, pytest-timeout
- Development dependencies include: pytest-xdist, coverage, ruff, black

## Testing After Venv Recreation

Always verify the venv is working correctly:

```bash
# 1. Run a single unit test
./.venv/bin/pytest tests/unit/test_file.py -x --timeout=30

# 2. Check import of main modules
./.venv/bin/python -c "from dispatch.orchestrator import Orchestrator; print('OK')"

# 3. Verify Qt is working (for UI tests)
QT_QPA_PLATFORM=offscreen ./.venv/bin/pytest tests/qt/test_widget.py -x --timeout=30
```

## Reminder

**The virtual environment is non-negotiable.** It ensures:
- Reproducible builds
- Correct dependency versions
- Isolation from system Python
- Consistent behavior across development and CI

When in doubt, recreate the venv. It's faster than debugging a broken environment and guarantees a clean state.
