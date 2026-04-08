---
description: "Use when: modifying Python version requirements, Qt/PyQt dependencies, or suggesting upgrades to Qt6/newer Python. Qt5 and Python 3.11 are intentional constraints for target system compatibility — do not suggest or implement upgrades."
applyTo: "**/*.py"
---

# Qt5 and Python 3.11 Intentional Constraints

## Critical Constraint

**Qt5 (PyQt5) and Python 3.11 are intentional, non-negotiable requirements.**

This project targets a specific system environment that requires:
- **Python 3.11+** (tested with 3.13, but 3.11 is the minimum baseline)
- **PyQt5** (NOT PyQt6 or PySide6)

## Agent Guidelines

### DO NOT:
- Suggest upgrading to PyQt6, PySide6, or any Qt6-based framework
- Suggest upgrading Python requirements beyond what's compatible with the target system
- "Modernize" code by replacing PyQt5 imports with Qt6 equivalents
- Change `PyQt5` to `PyQt6` in imports, requirements, or documentation
- Update `python_requires` in pyproject.toml/setup.py to exclude 3.11
- Remove or modify version pins for PyQt5 in requirements files

### DO:
- Respect existing PyQt5 imports and patterns
- Maintain Python 3.11 compatibility in any new code
- Use Python 3.11+ features only (no 3.12+ or 3.13+ specific syntax unless already in use project-wide)
- Follow existing PyQt5 patterns for UI components, signals/slots, and event handling
- Document any workarounds needed for Qt5 limitations with `TODO: Qt5 limitation — <reason>`

## Where This Comes From

The target deployment system has specific library and Python version constraints that cannot be changed. Attempting to "upgrade" these dependencies will break compatibility with the production environment.

## Code Examples

```python
# ✅ GOOD: Respecting Qt5 constraint
from PyQt5.QtWidgets import QApplication, QMainWindow
from PyQt5.QtCore import Qt, pyqtSignal

# ❌ BAD: Attempting Qt6 upgrade
from PyQt6.QtWidgets import QApplication, QMainWindow  # DO NOT DO THIS
```

```python
# ✅ GOOD: Python 3.11 compatible
from typing import Optional, List

def process(items: Optional[List[str]] = None) -> dict:
    ...

# ❌ BAD: Python 3.12+ only syntax (if not already used project-wide)
def process[T](items: T) -> dict:  # Type parameter syntax is 3.12+
    ...
```

## References

- See `copilot-instructions.md` — "PyQt5 desktop application (project is intentionally Qt5)"
- See `requirements.txt` — PyQt5 version pins
- See `pyproject.toml` — Python version requirements
