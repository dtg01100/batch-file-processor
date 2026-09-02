"""Helpers shared between the 1.47 oracle and master-parity tests.

Objects exported here:

* ``Legacy147ModuleLoader`` — a ``ModuleLoaderProtocol``-compatible loader
  that resolves ``convert_to_<format>`` to the *vendored* 1.47 module living
  under ``tests/fixtures/legacy_147/``. Used to prove master can drive the
  exact same converter code as 1.47 (no divergence in module behaviour)
  end-to-end. Keeps the swap point in one place.

* ``MasterRoutingRecorder`` — utility that drives ``EDIConverterStep`` once
  against a row's ``parameters_dict`` with a custom
  ``MockModuleLoader`` pre-populated with vendored modules. Records:

  * whether master would run a converter (precheck chain)
  * which module name it would load (concrete string)
  * the inputs it would pass (per-arg tuple, surfaced for input-shape
    parity with the 1.47 capture)
  * whether master would error

* ``MasterMockModuleLoader`` — module loader that holds a registry of
  ``MasterMockConverter``s by name and records every load_module call.
  Mirrors the shape of the existing ``MockModuleLoader`` in
  ``test_pipeline_converter.py`` but with a richer recorder API.

This module is intentionally side-effect free so it can be imported from
both the 1.47 oracle and the master parity test without any test-order
dependency on globals.
"""

from __future__ import annotations

import importlib
import sys
from dataclasses import dataclass
from pathlib import Path
from types import ModuleType
from typing import Any
from unittest.mock import MagicMock

_REPO_ROOT = Path(__file__).resolve().parents[2]
_VENDORED_DIR = _REPO_ROOT / "tests" / "fixtures" / "legacy_147"


# ---------------------------------------------------------------------------
# Legacy147ModuleLoader — load vendored 1.47 modules through the same
# interface the master pipeline expects.
# ---------------------------------------------------------------------------


class Legacy147ModuleLoader:
    """Module loader that resolves ``convert_to_<format>`` to vendored 1.47 modules.

    The vendored 1.47 ``dispatch.py`` builds a module name like
    ``convert_to_csv`` (bare, with ``convert_to_`` prefix); the master
    pipeline builds ``dispatch.converters.convert_to_csv``. Both names
    resolve through this loader.

    Each call records the lookup so a master-parity test can prove master
    *actually* called the same vendored module the oracle did.
    """

    def __init__(self) -> None:
        self.loaded: list[str] = []

    def _resolve(self, module_name: str) -> ModuleType:
        # Strip a "webapp.pipeline.converters." prefix if present so a master
        # call can be redirected to vendored 1.47 code without rewriting
        # the master's formatter.
        bare = module_name
        if bare.startswith("webapp.pipeline.converters."):
            bare = bare[len("webapp.pipeline.converters.") :]
        path = _VENDORED_DIR / f"{bare}.py"
        if not path.exists():
            raise ImportError(f"no vendored 1.47 module at {path}")
        spec = importlib.util.spec_from_file_location(bare, str(path))  # type: ignore[attr-defined]
        if spec is None or spec.loader is None:
            raise ImportError(f"could not build spec for {bare}")
        mod = importlib.util.module_from_spec(spec)  # type: ignore[arg-type]
        sys.modules[bare] = mod
        spec.loader.exec_module(mod)
        return mod

    def load_module(self, module_name: str) -> Any:
        self.loaded.append(module_name)
        return self._resolve(module_name)

    def module_exists(self, module_name: str) -> bool:
        bare = module_name
        if bare.startswith("webapp.pipeline.converters."):
            bare = bare[len("webapp.pipeline.converters.") :]
        return (_VENDORED_DIR / f"{bare}.py").exists()


# ---------------------------------------------------------------------------
# Master-side helpers.
# ---------------------------------------------------------------------------


@dataclass
class MasterRoutingOutcome:
    """Concrete per-row outcome from running real master code.

    Populated by ``drive_master_converter_step``. Used by
    ``test_master_routing_matches_147.py`` to assert parity with the 1.47
    oracle.
    """

    would_run_converter: bool
    would_error: bool
    module_requested: str | None
    module_loaded: str | None
    converter_inputs: tuple | None  # args tuple passed to edi_convert
    format_used: str
    success: bool
    bucket: str  # "noop" | "disabled" | "run" | "error" | "import_error"
    failure_reason: str | None = None
    output_path: str | None = None


@dataclass
class MasterRecorderModule:
    """Stand-in for a vendored converter; records the args master passes."""

    def __init__(self, name: str, missing_dep: str | None = None) -> None:
        self.name = name
        self.missing_dep = missing_dep
        self.call_args: list[tuple] = []

    def edi_convert(
        self,
        edi_process,
        output_filename,
        settings,
        parameters,
        upc_dict,
    ) -> str:
        self.call_args.append(
            (
                str(edi_process),
                str(output_filename),
                id(settings),
                id(parameters),
                id(upc_dict),
            )
        )
        if self.missing_dep:
            raise ModuleNotFoundError(self.missing_dep)
        # Mirror the real converter contract: return the output path.
        return str(output_filename)


class MasterMockModuleLoader:
    """Module loader that resolves every ``convert_to_<fmt>`` look to a
    recorder module and tracks every ``load_module`` call.

    Drops through to ``Legacy147ModuleLoader`` for any module that has not
    been pre-registered and that the vendored dir provides — this lets
    master drive vendored 1.47 modules directly when we *want* real
    converter semantics, not a recorder stub.
    """

    def __init__(self) -> None:
        self._modules: dict[str, MasterRecorderModule] = {}
        self.calls: list[str] = []

    def register(
        self, module_name: str, missing_dep: str | None = None
    ) -> MasterRecorderModule:
        recorder = MasterRecorderModule(module_name, missing_dep)
        self._modules[module_name] = recorder
        return recorder

    def load_module(self, module_name: str) -> Any:
        self.calls.append(module_name)
        if module_name in self._modules:
            return self._modules[module_name]
        # Otherwise try to load the vendored 1.47 module verbatim.
        return Legacy147ModuleLoader()._resolve(module_name)

    def module_exists(self, module_name: str) -> bool:
        if module_name in self._modules:
            return True
        bare = module_name
        if bare.startswith("webapp.pipeline.converters."):
            bare = bare[len("webapp.pipeline.converters.") :]
        return (_VENDORED_DIR / f"{bare}.py").exists()


def drive_master_converter_step(
    row: dict,
    *,
    tmp_path: Path | None = None,
    render_real_converter: bool = False,
) -> MasterRoutingOutcome:
    """Run ``EDIConverterStep.convert`` once for a row.

    Uses a ``MasterMockModuleLoader`` that records each converter attempt.

    Args:
        row: Folder row dict (anonymized JSON).
        tmp_path: Where to stage the input EDI file. Defaults to ``/tmp``.
        render_real_converter: When True, prefer the vendored 1.47 module
            via ``Legacy147ModuleLoader`` so the test runs real converter
            code. Default is False (recorder stub only).

    Returns:
        ``MasterRoutingOutcome`` with full diagnostics.
    """
    from core.utils.bool_utils import normalize_bool  # type: ignore
    from core.utils.format_utils import normalize_convert_to_format  # type: ignore
    from webapp.pipeline.pipeline.converter import EDIConverterStep  # type: ignore

    raw_format = row.get("convert_to_format") or ""
    fmt = normalize_convert_to_format(raw_format)
    process_edi = normalize_bool(row.get("process_edi", False))

    loader = MasterMockModuleLoader()
    # Pre-register a recorder for the concrete module master would build.
    module_name = f"webapp.pipeline.converters.convert_to_{fmt}"
    if fmt:
        recorder = loader.register(module_name)

    fs = MagicMock()
    fs.dir_exists.return_value = True

    if tmp_path is None:
        tmp_path = Path("/tmp")
    step = EDIConverterStep(module_loader=loader, file_system=fs)

    # Stage a placeholder input/output dir.
    input_basename = "input.edi"
    out_dir = str(tmp_path / "out")
    input_path = str(tmp_path / input_basename)

    # Drive the actual precheck chain by calling .convert().
    try:
        result = step.convert(
            input_path,
            out_dir,
            dict(row),
            {},
            {},
        )
    except Exception as exc:  # pragma: no cover - defensive
        return MasterRoutingOutcome(
            would_run_converter=False,
            would_error=True,
            module_requested=module_name if fmt else None,
            module_loaded=None,
            converter_inputs=None,
            format_used=fmt,
            success=False,
            bucket="error",
            failure_reason=str(exc),
        )

    # Resolve which bucket this outcome falls into.
    if not fmt:
        bucket = "noop"
        would_run = False
        would_error = False
        converter_inputs = None
        loaded_module = None
    elif not process_edi:
        bucket = "disabled"
        would_run = False
        would_error = False
        converter_inputs = None
        loaded_module = None
    elif result.success and (result.output_path != input_path):
        bucket = "run"
        would_run = True
        would_error = False
        converter_inputs = recorder.call_args[-1] if recorder.call_args else None
        loaded_module = loader.calls[-1] if loader.calls else None
    elif result.success and (result.output_path == input_path):
        # success but no conversion -> either format unsupported and we
        # silently passed through, or we fell into the unsupported-format
        # branch which the master pipeline records via _record_error.
        unsupported = any("Unsupported" in e for e in result.errors)
        bucket = "error" if unsupported else "noop"
        would_run = False
        would_error = unsupported
        converter_inputs = None
        loaded_module = loader.calls[-1] if loader.calls else None
    else:
        bucket = "error"
        would_run = False
        would_error = True
        converter_inputs = recorder.call_args[-1] if recorder.call_args else None
        loaded_module = loader.calls[-1] if loader.calls else None

    return MasterRoutingOutcome(
        would_run_converter=would_run,
        would_error=would_error,
        module_requested=module_name if fmt else None,
        module_loaded=loaded_module,
        converter_inputs=converter_inputs,
        format_used=fmt,
        success=result.success,
        bucket=bucket,
        failure_reason=result.errors[0] if result.errors else None,
        output_path=result.output_path,
    )


__all__ = [
    "Legacy147ModuleLoader",
    "MasterMockModuleLoader",
    "MasterRecorderModule",
    "MasterRoutingOutcome",
    "drive_legacy_147_for_row",
    "drive_master_converter_step",
]


# ---------------------------------------------------------------------------
# 1.47 oracle driver — shared between the 1.47 routing test and master-parity
# test so neither one depends on the other running first.
# ---------------------------------------------------------------------------


def drive_legacy_147_for_row(row: dict, tmp_path, monkeypatch, dispatch_module):
    """Run the vendored 1.47 ``dispatch.process`` for one row.

    Returns a tuple of:
        Legacy147RoutingResult — the observed outcome, ready to be stashed
                                 into ``legacy_147_registry``.
        list — capture of converter calls (each entry: ``(input,
                output, settings_dict, parameters_dict, upc_lookup)``).
        list — capture of backend calls (each entry: ``{backend, filename}``).

    The function mutates ``sys.modules`` (registers backend recorder
    modules) but does so via ``monkeypatch`` so teardown is automatic.

    NOTE: This was extracted from
    ``test_legacy_147_routing.test_legacy_147_routing_per_row`` and mirrors
    that body but is decoupled from pytest-style record-on-instance
    storage. The two test files now both go through this helper so
    neither depends on the other running first.
    """
    import io
    import sys as _sys
    from types import SimpleNamespace
    from unittest.mock import MagicMock as _MagicMock

    from tests.fixtures.legacy_147.stubs import record_error as record_error_stub

    # Imported lazily so the helpers module remains importable in isolation
    # (Legacy147RoutingResult is defined in the dispatch_tests conftest).
    from tests.unit.dispatch_tests.conftest import Legacy147RoutingResult

    record_error_stub.reset()
    captured_converters: dict[str, list[tuple]] = {}
    backend_calls: list[dict] = []

    # ---- normalize parameters_dict with safe defaults ---------------------
    parameters_dict = dict(row)
    parameters_dict.setdefault("id", int(row.get("id", 0)))
    parameters_dict.setdefault("alias", str(row.get("alias", "")))
    parameters_dict.setdefault("process_edi", row.get("process_edi", "False"))
    parameters_dict.setdefault("tweak_edi", row.get("tweak_edi", "False"))
    parameters_dict.setdefault("split_edi", row.get("split_edi", "False"))
    parameters_dict.setdefault(
        "force_edi_validation", row.get("force_edi_validation", "False")
    )
    parameters_dict.setdefault("rename_file", row.get("rename_file", ""))
    parameters_dict.setdefault(
        "process_backend_copy", row.get("process_backend_copy", "True")
    )
    parameters_dict.setdefault(
        "process_backend_ftp", row.get("process_backend_ftp", "False")
    )
    parameters_dict.setdefault(
        "process_backend_email", row.get("process_backend_email", "False")
    )
    parameters_dict.setdefault("copy_to_directory", row.get("copy_to_directory", ""))
    parameters_dict.setdefault("ftp_server", row.get("ftp_server", ""))
    parameters_dict.setdefault("ftp_folder", row.get("ftp_folder", ""))
    parameters_dict.setdefault("ftp_port", row.get("ftp_port", 21))
    parameters_dict.setdefault("ftp_username", row.get("ftp_username", ""))
    parameters_dict.setdefault("ftp_password", row.get("ftp_password", ""))
    parameters_dict.setdefault("email_to", row.get("email_to", ""))
    parameters_dict.setdefault(
        "split_edi_include_credits", row.get("split_edi_include_credits", 1)
    )
    parameters_dict.setdefault(
        "split_edi_include_invoices", row.get("split_edi_include_invoices", 1)
    )
    parameters_dict["convert_to_format"] = row.get("convert_to_format", "") or ""

    # Fold the row's folder_name into tmp_path.
    safe_alias = (
        "".join(
            ch if (ch.isalnum() or ch in "._-") else "_"
            for ch in str(parameters_dict["alias"])
        )
        or "row"
    )
    parameters_dict["folder_name"] = str(tmp_path / safe_alias)
    (tmp_path / safe_alias).mkdir(parents=True, exist_ok=True)
    input_path = tmp_path / safe_alias / "input.edi"
    input_path.write_text(
        "AVENDOR00000000010101250000100000\n"
        "B01234567890Test Item Description    1234560001000100000100010991001000000\n"
        "CTABSales Tax                      000010000\n",
        encoding="utf-8",
    )

    # ---- compute legacy/master split for process_edi ----------------------
    legacy_enabled = parameters_dict.get("process_edi") == "True"
    master_enabled = _normalize_truthy(parameters_dict.get("process_edi"))

    fmt = (
        (parameters_dict.get("convert_to_format") or "")
        .strip()
        .lower()
        .replace(" ", "_")
        .replace("-", "_")
    )
    format_module = f"convert_to_{fmt}" if fmt else ""

    # ---- replace threading backends with non-forking, deterministic ones ----
    import concurrent.futures as _futures

    class _InlineThreadPool(_futures.Executor):
        def submit(self, fn, *args, **kwargs):
            fut = _futures.Future()
            try:
                fut.set_result(fn(*args, **kwargs))
            except Exception as e:  # pragma: no cover
                fut.set_exception(e)
            return fut

        def map(self, fn, *iterables, **kwargs):
            _ = kwargs
            iters = [iter(it) for it in iterables]
            done = []
            while True:
                try:
                    a = [next(it) for it in iters]
                except StopIteration:
                    break
                done.append(fn(*a))
            return iter(done)

    monkeypatch.setattr(_futures, "ThreadPoolExecutor", _InlineThreadPool)
    # ProcessPoolExecutor must be patched too: the vendored 1.47 dispatch
    # uses it at dispatch.py:165 for md5 hashing, and the forked worker
    # process tries to ``import doingstuffoverlay`` (etc.) which is only
    # registered in the parent's ``sys.modules``. The worker dies with
    # ModuleNotFoundError on first task, the pool becomes Broken, and the
    # main thread blocks forever on ``hash_thread_return_queue.get()``
    # because the hash thread never puts its result. Running inline
    # avoids the fork entirely.
    monkeypatch.setattr(_futures, "ProcessPoolExecutor", _InlineThreadPool)

    # ---- capture converter invocations through a wrapper ------------------
    if format_module:
        try:
            original_module = importlib.import_module(format_module)
        except (ImportError, ModuleNotFoundError):
            original_module = None

        if original_module is not None and hasattr(original_module, "edi_convert"):

            def wrapped(
                edi_process, output_filename, settings_dict, parameters_dict, upc_lookup
            ):
                tup = (
                    edi_process,
                    output_filename,
                    id(settings_dict),
                    id(parameters_dict),
                    id(upc_lookup),
                )
                captured_converters.setdefault(format_module, []).append(tup)
                try:
                    return original_module.__wrapped_edi_convert__(
                        edi_process,
                        output_filename,
                        settings_dict,
                        parameters_dict,
                        upc_lookup,
                    )
                except (ImportError, ModuleNotFoundError):
                    return edi_process
                except Exception:
                    return edi_process

            wrapped.__wrapped__ = original_module.edi_convert
            wrapped.__wrapped_edi_convert__ = original_module.edi_convert
            monkeypatch.setattr(original_module, "edi_convert", wrapped)

    # ---- patch backend do() to record calls --------------------------------
    def _make_recorder(name):
        def _do(parameters, settings_dict, filename):
            backend_calls.append({"backend": name, "filename": str(filename)})
            return True

        return _do

    for backend_name in ("copy_backend", "ftp_backend", "email_backend"):
        if backend_name in _sys.modules:
            continue
        mod = type(_sys)(backend_name)
        mod.do = _make_recorder(backend_name)
        monkeypatch.setitem(_sys.modules, backend_name, mod)

    # ---- invoke vendored dispatch.process ---------------------------------
    folders_db = _MagicMock()
    folders_db.find.return_value = iter([parameters_dict])
    folders_db.count.return_value = 1

    processed_files = _MagicMock()
    processed_files.find.return_value = iter(())
    processed_files.count.return_value = 0
    processed_files.insert_many.return_value = None

    run_log = io.BytesIO()
    args = SimpleNamespace(automatic=True)
    root = _MagicMock()
    root.update = _MagicMock()
    reporting = {"enable_reporting": "False", "report_edi_errors": True}
    errors_folder = {"errors_folder": str(tmp_path / "errors")}
    settings = {
        "as400_username": "test",
        "as400_password": "test",
        "as400_address": "test.as400",
        "odbc_driver": "{IBM i Access ODBC Driver}",
    }

    try:
        _, _summary = dispatch_module.process(
            database_connection=_MagicMock(),
            folders_database=folders_db,
            run_log=run_log,
            emails_table=_MagicMock(),
            run_log_directory=str(tmp_path),
            reporting=reporting,
            processed_files=processed_files,
            root=root,
            args=args,
            version="1.47.0",
            errors_folder=errors_folder,
            settings=settings,
            simple_output=None,
        )
    except Exception as exc:
        # ``dispatch.process`` runs inner dispatchers and may raise
        # unrelated errors from the row's parameters (e.g. file-name
        # sanitization). Capture so the assertions don't blow up the
        # whole suite.
        backend_calls.append({"backend": "exception", "filename": str(exc)})

    converter_calls = (
        list(captured_converters.get(format_module, [])) if format_module else []
    )
    converter_args: tuple | None = converter_calls[0] if converter_calls else None

    result = Legacy147RoutingResult(
        row_id=int(row.get("id", 0)),
        format_normalized=fmt,
        format_module_requested=format_module,
        converter_called=bool(converter_calls),
        converter_input_args=converter_args,
        backend_called=bool(backend_calls),
        backend_call_signature=list(backend_calls),
        errors=list(record_error_stub.recorded_errors),
        legacy_process_edi_enabled=legacy_enabled,
        master_process_edi_enabled=master_enabled,
    )
    return result, converter_calls, backend_calls


def _normalize_truthy(value):
    """Reduced normalize_bool — matches master boolean semantics."""
    if value is True or value is False:
        return value
    if isinstance(value, int):
        return bool(value)
    if isinstance(value, str):
        return value.strip().lower() in ("true", "yes", "on", "1")
    return False
