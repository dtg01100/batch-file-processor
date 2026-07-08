"""Shared fixtures for the legacy 1.47 routing-harness tests.

Scope: only ``tests/unit/dispatch_tests/test_legacy_147_routing.py`` and
``tests/unit/dispatch_tests/test_master_routing_matches_147.py``.

Fixtures provided:

* ``legacy_147_dispatch`` — yields a freshly (re)loaded copy of the vendored
  1.47 ``dispatch`` module with all hard-dependency stubs pre-installed into
  ``sys.modules``. Per-test isolation: reloads the module on every call.
* ``all_anonymized_folder_rows`` — yields the list of folder-row dicts
  committed under ``tests/fixtures/anonymized_folders/folders/*.json``.
  Skips the entire module if no fixtures are committed (to avoid passing
  vacuously).
* ``_install_legacy_147_stubs`` (autouse) — installs the stubs in
  ``sys.modules`` *once per test session* and the ImageOps Py3 alias into
  ``sys.modules`` lazily.

The install order matters: stubs MUST be installed before the vendored
modules are imported, because Python consults ``sys.modules`` first.
"""
from __future__ import annotations

import importlib
import json
import sys
import types
from dataclasses import dataclass, field
from pathlib import Path
from unittest.mock import MagicMock

import pytest

_REPO_ROOT = Path(__file__).resolve().parents[3]
_LEGACY_147_DIR = _REPO_ROOT / "tests" / "fixtures" / "legacy_147"
_LEGACY_147_STUBS_DIR = _LEGACY_147_DIR / "stubs"
_ANON_FOLDERS_DIR = _REPO_ROOT / "tests" / "fixtures" / "anonymized_folders" / "folders"


def _install_legacy_147_stubs_once() -> None:
    """Insert every stubs/*.py file into ``sys.modules`` under its module name.

    Each stub module file is named after the 1.47 module it shadows
    (e.g. ``utils.py`` shadows ``utils``). We do this by importing them via
    their file path rather than via the package, so the install does not
    depend on ``tests.fixtures.legacy_147`` being importable.
    """
    for stub_path in sorted(_LEGACY_147_STUBS_DIR.glob("*.py")):
        if stub_path.name == "__init__.py":
            continue
        module_name = stub_path.stem  # e.g. "utils", "query_runner"
        spec = importlib.util.spec_from_file_location(  # type: ignore[attr-defined]
            f"_legacy_147_stub_{module_name}", str(stub_path)
        )
        if spec is None or spec.loader is None:
            continue
        mod = importlib.util.module_from_spec(spec)  # type: ignore[arg-type]
        # Make sure each subsequent importlib.import_module('utils') returns
        # THIS module. The vendored dispatch imports `utils` (not
        # `stubs.utils`), so we register it under the bare name.
        sys.modules[module_name] = mod
        spec.loader.exec_module(mod)


def _install_image_ops_shim() -> None:
    """Provide a Py2-style ``ImageOps`` alias vendored
    ``convert_to_scansheet_type_a.py`` imports.

    1.47 does ``import ImageOps as pil_ImageOps`` (Py2 style). Under Py3
    the module is ``PIL.ImageOps``. We alias the bare name to the modern
    module so the import resolves cleanly without editing the vendor copy.
    """
    if "ImageOps" in sys.modules:
        return
    try:
        import PIL.ImageOps  # type: ignore[import-not-found]
    except ImportError:
        # PIL is genuinely unavailable — leave the alias absent; tests that
        # need scansheet_type_a will skip via ModuleNotFoundError guard.
        return
    shim = types.ModuleType("ImageOps")
    shim.__dict__.update(PIL.ImageOps.__dict__)
    sys.modules["ImageOps"] = shim


def _ensure_legacy_147_on_sys_path() -> str:
    """Prepend the vendored dir to ``sys.path`` and return the path string."""
    p = str(_LEGACY_147_DIR)
    if p not in sys.path:
        sys.path.insert(0, p)
    return p


@pytest.fixture(scope="session")
def _legacy_147_runtime() -> types.ModuleType:
    """Session-scoped: install stubs, ImageOps shim, sys.path. Return dispatch.

    We reload the vendored ``dispatch`` module on every *test* (see
    ``legacy_147_dispatch``), so this session fixture only gives us the
    one-time harness setup and exposes the dispatch module for reference.
    """
    _install_legacy_147_stubs_once()
    _install_image_ops_shim()
    _ensure_legacy_147_on_sys_path()
    # Importing the vendored dispatch module for the first time.
    importlib.import_module("dispatch")
    # Capture the module for callers that need to reload it per test.
    return sys.modules["dispatch"]


@pytest.fixture
def legacy_147_dispatch(_legacy_147_runtime: types.ModuleType):
    """Yield a freshly reloaded vendored ``dispatch`` module per-test.

    The 1.47 ``dispatch.process()`` mutates module-global state
    (``hash_counter``, ``file_count``, ``parameters_dict_list``,
    ``hash_thread_return_queue``, etc.). Reloading between tests guarantees
    isolation without us having to enumerate every global.

    Returns the reloaded module so tests can call ``dispatch.process(...)``
    directly.
    """
    importlib.reload(_legacy_147_runtime)
    yield _legacy_147_runtime


def _safe_alias_for_filename(name: str) -> str:
    """Sanitize a folder alias for use in an id-parametrize ``ids=`` arg."""
    out = []
    for ch in str(name or ""):
        if ch.isalnum() or ch in "._-":
            out.append(ch)
        else:
            out.append("_")
    return "".join(out) or "row"


def _load_anonymized_rows() -> list[dict]:
    """Read every ``*.json`` file under ``anonymized_folders/folders``.

    Sort by integer id (extracted from filename prefix) for deterministic
    parametrize ordering across machines.
    """
    if not _ANON_FOLDERS_DIR.exists():
        return []
    files = sorted(
        (p for p in _ANON_FOLDERS_DIR.glob("*.json") if p.is_file()),
        key=lambda p: int(p.stem.split("_", 1)[0]),
    )
    rows: list[dict] = []
    for path in files:
        try:
            with path.open("r", encoding="utf-8") as fh:
                rows.append(json.load(fh))
        except (OSError, ValueError):
            # Skip unreadable fixtures — surfaces as a separate test.
            continue
    return rows


@pytest.fixture(scope="session")
def _all_anonymized_folder_rows() -> list[dict]:
    return _load_anonymized_rows()


@pytest.fixture
def all_anonymized_folder_rows(_all_anonymized_folder_rows: list[dict]) -> list[dict]:
    return list(_all_anonymized_folder_rows)


@pytest.fixture
def anonymized_folder_ids(all_anonymized_folder_rows: list[dict]) -> list[str]:
    """Stable ``pytest.mark.parametrize(ids=...)`` labels.

    One per row. Format: ``"{id}-{safe_alias}"`` so failures point to the
    source file and a slug the test log can match to the JSON fixture name.
    """
    return [
        f"{int(row.get('id', idx))}-{_safe_alias_for_filename(row.get('alias', ''))}"
        for idx, row in enumerate(all_anonymized_folder_rows)
    ]


@pytest.fixture
def anonymized_folder_rows_parametrized(all_anonymized_folder_rows, anonymized_folder_ids):
    """Yield ``(row, id_label)`` pairs for the per-row tests.

    Returns the parametrization lists so test files can splat them into
    ``@pytest.mark.parametrize(..., [...], ids=[...])`` style at module
    import time. (We expose as a single fixture that returns a tuple to keep
    import-time ordering deterministic.)
    """
    return list(zip(all_anonymized_folder_rows, anonymized_folder_ids, strict=False))


# ---------------------------------------------------------------------------
# Helpers for the per-row tests
# ---------------------------------------------------------------------------

@pytest.fixture
def make_fake_folders_database():
    """Return a callable that builds a fake ``folders_database`` for one row.

    The fake responds to ``.find(folder_is_active="True", order_by="alias")``
    by yielding ``[parameters_dict]`` once, and to ``.count(...)`` by
    returning 1.
    """

    def _factory(parameters_dict: dict) -> MagicMock:
        db = MagicMock()
        db.find.return_value = iter([parameters_dict])
        db.count.return_value = 1
        # dispatch.process reads parameters_dict.pop('old_id') on line 154;
        # if the row has no old_id it passes via KeyError -> keep id stable.
        return db

    return _factory


@pytest.fixture
def make_fake_processed_files_table():
    """Return a fake processed_files that yields an empty list on find()."""

    def _factory() -> MagicMock:
        t = MagicMock()
        t.find.return_value = iter(())
        t.count.return_value = 0
        return t

    return _factory


# ---------------------------------------------------------------------------
# Per-row routing registry — session-shared between the 1.47 oracle test
# and the master-parity test.
#
# The 1.47 routing test stashes a `Legacy147RoutingResult` keyed by row id;
# the master-parity test reads it to know what 1.47 *actually did* and
# compare against master's behaviour for the same row. This is the lockstep
# mechanism that makes the two tests genuinely *parity* tests rather than
# two independent assertions with similar shape.
# ---------------------------------------------------------------------------


@dataclass
class Legacy147RoutingResult:
    """One row's actual 1.47 routing outcome.

    Attributes:
        row_id: ``parameters_dict['id']`` (int) — the key.
        format_normalized: 1.47's normalization
            (``lower().replace(' ','_').replace('-','_')``).
        format_module_requested: Module name 1.47 attempted to load
            (e.g. ``"convert_to_csv"``). Empty if no conversion.
        converter_called: True if 1.47 reached the converter call.
        converter_input_args: Tuple captured when the converter wrapper was
            invoked. None if not called.
        backend_called: True if any backend's ``do()`` was invoked.
        backend_call_signature: List of ``{backend, filename}`` dicts.
        errors: List of error strings from ``record_error.do``.
        skipped_reason: Why the row was skipped (third-party dep missing).
    """

    row_id: int
    format_normalized: str
    format_module_requested: str
    converter_called: bool
    converter_input_args: tuple | None
    backend_called: bool
    backend_call_signature: list
    errors: list
    skipped_reason: str | None = None
    legacy_process_edi_enabled: bool | None = None
    master_process_edi_enabled: bool | None = None


@dataclass
class Legacy147Registry:
    """Session-shared store of 1.47 oracle results.

    Keyed by integer row id. Populated by the 1.47 per-row test, read by
    the master-parity test. Cleared only at session start.
    """

    results: dict[int, Legacy147RoutingResult] = field(default_factory=dict)

    def record(self, result: Legacy147RoutingResult) -> None:
        self.results[result.row_id] = result

    def get(self, row_id: int) -> Legacy147RoutingResult | None:
        return self.results.get(row_id)

    def all(self) -> list[Legacy147RoutingResult]:
        return list(self.results.values())


@pytest.fixture(scope="session")
def legacy_147_registry() -> Legacy147Registry:
    """Session-scoped registry shared between 1.47 oracle and master parity."""
    return Legacy147Registry()


__all__ = [
    "Legacy147Registry",
    "Legacy147RoutingResult",
    "all_anonymized_folder_rows",
    "anonymized_folder_ids",
    "anonymized_folder_rows_parametrized",
    "legacy_147_dispatch",
    "legacy_147_registry",
    "make_fake_folders_database",
    "make_fake_processed_files_table",
]
