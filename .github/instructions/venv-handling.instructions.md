---
applyTo: '**/*.py'
description: 'Instructions for handling Python virtual environment issues - always recreate the venv instead of falling back to host Python. Never use host/system Python directly.'
---

# Python Virtual Environment Handling

## Core Principle

**NEVER bypass the project's virtual environment.** The host/system Python is forbidden for project work, debugging, testing, or analysis. If `.venv/` is missing or broken, recreate it before doing anything else.

## Required Behavior

- Always use `.venv/bin/python`, `.venv/bin/pip`, or `./.venv/bin/pytest`.
- Do not use `python`, `python3`, `pip`, `pip3`, or system package installations for this repository.
- If the venv is broken, recreate it. Do not continue with the host Python.
- If a tool or environment asks for a Python interpreter, choose `.venv/bin/python`.

## When to Recreate the Virtual Environment

Recreate the virtual environment when you encounter:
- missing package errors for dependencies listed in `requirements.txt`
- import errors for installed packages
- version conflicts between installed or required packages
- corrupted or incomplete `.venv` (missing `pip`, `python`, or `activate`)
- shell/IDE integration using host Python instead of `.venv`

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
pip install -r requirements-dev.txt

# 6. Verify installation
pip list
python -c "import pytest; print(pytest.__version__)"
```

### If `uv` is available

```bash
rm -rf .venv
uv venv .venv
source .venv/bin/activate
uv pip install -r requirements.txt
uv pip install -r requirements-dev.txt
```

## What NOT to Do

### ❌ NEVER use host/system Python
```bash
python3 script.py
python3 -m pytest tests/
pip3 install <package>
```

### ❌ NEVER install packages globally
```bash
sudo pip install <package>
pip3 install --user <package>
```

### ❌ NEVER bypass `.venv` with environment hacks
```bash
export PYTHONPATH=/usr/lib/python3/site-packages:$PYTHONPATH
.venv/bin/python3 -c "import sys; sys.path.insert(0, '/usr/lib/python3')"
```

## Verification Steps

After recreating or activating the virtual environment:

1. **Verify the interpreter path**:
   ```bash
   which python
   # Must output: /path/to/project/.venv/bin/python
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

### Missing `python` executable in `.venv/bin`
```bash
rm -rf .venv
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### Package installation fails
```bash
rm -rf .venv
python3 -m venv .venv
source .venv/bin/activate
pip cache purge
pip install --upgrade pip
pip install -r requirements.txt
```

### Import errors after package installation
```bash
source .venv/bin/activate
pip list | grep <package_name>

pip uninstall <package_name>
pip install <package_name>

# If the issue persists, recreate the venv
rm -rf .venv
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## Project-Specific Notes

For this Batch File Processor project:
- The venv is at `.venv/` in the project root.
- Use `./.venv/bin/python` for direct execution without activation.
- Use `./.venv/bin/pytest` for tests.
- Do not use host or system Python for any repository task.

## Testing After Venv Recreation

Always verify the venv works correctly:

```bash
./.venv/bin/pytest tests/unit/test_file.py -x --timeout=30
./.venv/bin/python -c "from dispatch.orchestrator import Orchestrator; print('OK')"
QT_QPA_PLATFORM=offscreen ./.venv/bin/pytest tests/qt/test_widget.py -x --timeout=30
```

## Reminder

**The virtual environment is non-negotiable.** It guarantees:
- reproducible builds
- correct dependency versions
- isolation from system Python
- consistent behavior across development and CI

If anything in the workflow tries to use host Python, stop and fix the `.venv` first.
