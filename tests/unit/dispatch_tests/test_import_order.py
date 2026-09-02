"""Regression tests for the webapp.pipeline import cycle.

The webapp.pipeline.results -> webapp.pipeline.services ->
webapp.pipeline.pipeline -> webapp.pipeline.results cycle was
introduced when the dispatch package was refactored into the
webapp-owned pipeline (Phase 9.1, 2026-09-02). The tests below
exercise that each submodule imports cleanly in a fresh
interpreter; they would catch a cycle being re-introduced.

The cycle is order-dependent: the same code that imports fine in tests can raise
``ImportError: cannot import name 'X' from partially initialized module`` when a
different module is imported FIRST in a fresh process.

These tests import each entry point as the *first* import in a subprocess, which
is the only reliable way to catch a reintroduced cycle. See
docs/IMPORT_ARCHITECTURE.md for the full diagram and rules.
"""

import subprocess
import sys
from pathlib import Path

import pytest

pytestmark = [pytest.mark.unit, pytest.mark.dispatch]

# Every entry point that must survive being the first import in a fresh process.
# Importing any of these used to crash before the results.py fix (2026-08-09).
CRITICAL_FIRST_IMPORTS = [
    "webapp.pipeline",
    "webapp.pipeline.pipeline",
    "webapp.pipeline.results",
    "webapp.pipeline.orchestrator",
    "webapp.pipeline.services",
    "webapp.pipeline.services.file_processor",
    "webapp.pipeline.send_manager",
    "webapp.main",
    "webapp.runner",
]

PROJECT_ROOT = Path(__file__).resolve().parents[3]


@pytest.mark.parametrize("module", CRITICAL_FIRST_IMPORTS)
def test_module_imports_first_in_fresh_interpreter(module: str) -> None:
    """``import <module>`` must succeed as the first import of a fresh process."""
    proc = subprocess.run(
        [sys.executable, "-c", f"import {module}"],
        cwd=PROJECT_ROOT,
        capture_output=True,
        text=True,
        timeout=120,
    )
    assert proc.returncode == 0, (
        f"import {module} failed as a first import — an import cycle has been "
        f"reintroduced. See docs/IMPORT_ARCHITECTURE.md.\n"
        f"stderr:\n{proc.stderr}"
    )
