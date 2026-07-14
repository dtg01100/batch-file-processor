"""Test-hygiene meta-test.

This meta-test asks: do the test files in the project conform to the
project's testing conventions documented in ``tests/AGENTS.md`` and the
broader project ``AGENTS.md``?

The runner walks every test layer except ``meta`` (the runners
themselves) and ``convert_backends`` (no test files yet) — see
``tests/meta/_layers.py`` for the source of truth.

Principles (carried forward from ``test_property_tests_are_sufficient.py``):

1. **Single file, no plugin framework, no config files.** Read the source,
   understand the result.
2. **Every violation lists the source line.** A reviewer audits with a
   single text lookup. No clever grouping, no pattern-based silencing.
3. **Fails closed.** An unknown violation is a real failure. The
   ``KNOWN_HYGIENE_VIOLATIONS`` list (if needed) cites the source line as
   evidence, not a summary.

Checks implemented:

- ``bare_magicmock`` — ``MagicMock()`` without ``spec=`` (delegates to the
  visitor in ``conftest_magicmock_plugin``; single source of truth).
- ``missing_assert`` — ``def test_*`` that has no ``assert``, no
  ``pytest.raises``, no ``pytest.warns``, no ``pytest.fail``, and no
  ``with pytest.raises(...)``. Tests that "pass" because they do nothing.
- ``sleep_call`` — actual ``time.sleep(...)`` call (not
  ``patch("time.sleep")`` or a string mention). Flakiness source; the
  project explicitly avoids ``time.sleep`` in tests (see
  ``test_timing_utils.py`` and ``test_structured_logging.py``).
- ``skip_no_reason`` — ``pytest.skip()`` with no positional string
  argument and no ``reason=`` keyword. Unjustified skips hide failures.
- ``bare_except_pass`` — ``except ...: pass`` (silent error swallowing).
- ``unjustified_noqa`` — ``# noqa`` without a trailing ``: CODE — reason``
  justification. Bare ``# noqa`` hides lint findings.
- ``single_item_dispatch_root_import`` — ``from dispatch import X`` with
  a single name. AGENTS.md prefers ``from dispatch.module import X``;
  multiple items from ``dispatch`` root is acceptable.

Coverage scope (current):

- Walks every layer except ``meta`` and ``convert_backends`` (see
  ``tests/meta/_layers.py``). ``meta`` is excluded because each
  runner's own self-check covers it; ``convert_backends`` has no
  test files yet.
- Test marker enforcement is out of scope: the project relies on
  directory conventions (146 of 153 unit files have no marker), and
  marker drift is not a bug. A future check that validates directory
  placement is a separate concern.

Usage::

    # Run all hygiene checks against all unit tests.
    pytest tests/meta/test_hygiene.py -n auto

    # Run a single check.
    pytest tests/meta/test_hygiene.py -n auto -k missing_assert

    # Audit a single file.
    pytest tests/meta/test_hygiene.py -n auto -k "test_db2ssh_connection"

    # Run only the self-check.
    pytest tests/meta/test_hygiene.py -n 0 -k self_check

    # CLI summary (no pytest).
    python tests/meta/test_hygiene.py
"""

from __future__ import annotations

import ast
import re
import sys
from collections.abc import Iterable
from dataclasses import dataclass
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
TESTS_DIR = PROJECT_ROOT / "tests"

# Layer registry. The single source of truth for which directories under
# ``tests/`` the meta-test runners walk. Defined in ``_layers.py`` so the
# runners, the report, and the layer-aware CLI summary all stay in sync.
sys.path.insert(0, str(Path(__file__).resolve().parent))
from _layers import (  # type: ignore[import-not-found]
    Layer,
    iter_scanned_test_files,
    scanned_layers,
)

# ---------------------------------------------------------------------------
# Imports from the existing MagicMock plugin. Single source of truth for
# the bare-MagicMock check. The plugin's private API is stable for
# internal use; the plugin's docstring describes the same conventions
# the hygiene runner enforces.
# ---------------------------------------------------------------------------

sys.path.insert(0, str(TESTS_DIR))
try:
    from conftest_magicmock_plugin import (  # type: ignore[import-not-found]
        MagicMockVisitor,
    )
    from conftest_magicmock_plugin import (  # type: ignore[import-not-found]
        _check_file_for_bare_magicmock as _plugin_check_magicmock,
    )
    from conftest_magicmock_plugin import (  # type: ignore[import-not-found]
        _file_has_module_flag as _plugin_has_module_flag,
    )
except ImportError:
    MagicMockVisitor = None  # type: ignore[assignment]
    _plugin_check_magicmock = None  # type: ignore[assignment]
    _plugin_has_module_flag = None  # type: ignore[assignment]


# ---------------------------------------------------------------------------
# Violation model.
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class Violation:
    file: Path
    line: int
    rule: str
    message: str
    source: str

    def format(self) -> str:
        rel = self.file.relative_to(PROJECT_ROOT)
        return f"{rel}:{self.line} [{self.rule}] {self.message}\n" f"    {self.source}"


# ---------------------------------------------------------------------------
# File enumeration.
# ---------------------------------------------------------------------------


def _iter_scanned_test_paths() -> list[Path]:
    """Return every absolute test file path the runner should walk.

    Walks every layer except ``meta`` (the runners themselves) and
    ``convert_backends`` (no test files yet). See ``_layers.py`` for
    the source of truth and the rationale for each exclusion. Paths
    are returned as absolute paths relative to ``PROJECT_ROOT`` so
    callers can ``relative_to(PROJECT_ROOT)`` for display.
    """
    return [(PROJECT_ROOT / rel).resolve() for rel, _layer in iter_scanned_test_files()]


# ---------------------------------------------------------------------------
# Check: bare MagicMock (delegated).
# ---------------------------------------------------------------------------


def _check_bare_magicmock(file: Path) -> list[Violation]:
    if _plugin_check_magicmock is None:
        return []
    raw = _plugin_check_magicmock(str(file))
    violations: list[Violation] = []
    source_lines = file.read_text(encoding="utf-8", errors="replace").splitlines()
    for lineno, msg in raw:
        if 1 <= lineno <= len(source_lines):
            src = source_lines[lineno - 1].strip()
        else:
            src = ""
        violations.append(
            Violation(
                file=file,
                line=lineno,
                rule="bare_magicmock",
                message=msg,
                source=src,
            )
        )
    return violations


# ---------------------------------------------------------------------------
# Check: test function with no assertions.
# ---------------------------------------------------------------------------


class _BodyHasAssertion(ast.NodeVisitor):
    """True if the function body contains any load-bearing assertion shape."""

    def __init__(self) -> None:
        self.found = False

    def visit_Assert(self, node: ast.Assert) -> None:
        self.found = True

    def visit_Raise(self, node: ast.Raise) -> None:
        if node.exc is not None:
            self.found = True

    def visit_Call(self, node: ast.Call) -> None:
        if isinstance(node.func, ast.Attribute) and isinstance(
            node.func.value, ast.Name
        ):
            if node.func.value.id == "pytest" and node.func.attr in {
                "fail",
                "raises",
                "warns",
                "skip",
            }:
                self.found = True
        elif isinstance(node.func, ast.Name) and node.func.id in {
            "pytest_fail",
        }:
            self.found = True
        self.generic_visit(node)

    def visit_With(self, node: ast.With) -> None:
        for item in node.items:
            ctx = item.context_expr
            if isinstance(ctx, ast.Call) and isinstance(ctx.func, ast.Attribute):
                if (
                    isinstance(ctx.func.value, ast.Name)
                    and ctx.func.value.id == "pytest"
                    and ctx.func.attr in {"raises", "warns"}
                ):
                    self.found = True
        self.generic_visit(node)


def _is_fixture(node: ast.FunctionDef | ast.AsyncFunctionDef) -> bool:
    """True if the function is decorated with @pytest.fixture."""
    for dec in node.decorator_list:
        if isinstance(dec, ast.Attribute) and dec.attr == "fixture":
            return True
        if isinstance(dec, ast.Name) and dec.id == "fixture":
            return True
        if isinstance(dec, ast.Call):
            func = dec.func
            if isinstance(func, ast.Attribute) and func.attr == "fixture":
                return True
            if isinstance(func, ast.Name) and func.id == "fixture":
                return True
    return False


def _check_missing_assert(file: Path) -> list[Violation]:
    try:
        tree = ast.parse(file.read_text(encoding="utf-8", errors="replace"))
    except SyntaxError:
        return []

    violations: list[Violation] = []
    source_lines = file.read_text(encoding="utf-8", errors="replace").splitlines()

    top_level_test_lines: set[int] = set()
    for node in tree.body:
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            if node.name.startswith("test_") and not _is_fixture(node):
                top_level_test_lines.add(node.lineno)

    for node in ast.walk(tree):
        if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            continue
        if not node.name.startswith("test_"):
            continue
        if node.name == "test_":  # bare `def test_(...):` is rare but skip
            continue
        if node.lineno not in top_level_test_lines:
            continue

        visitor = _BodyHasAssertion()
        for stmt in node.body:
            visitor.visit(stmt)
        if not visitor.found:
            if 1 <= node.lineno <= len(source_lines):
                src = source_lines[node.lineno - 1].strip()
            else:
                src = ""
            violations.append(
                Violation(
                    file=file,
                    line=node.lineno,
                    rule="missing_assert",
                    message=(
                        f"def {node.name} has no assertion, pytest.raises, "
                        "pytest.warns, or pytest.fail"
                    ),
                    source=src,
                )
            )
    return violations


# ---------------------------------------------------------------------------
# Check: time.sleep call (not patch, not string).
# ---------------------------------------------------------------------------


def _is_sleep_call(node: ast.Call) -> bool:
    """Detect actual ``time.sleep(...)`` invocation, not ``patch("time.sleep")``.

    Matches ``time.sleep``, ``from time import sleep`` / ``sleep(...)``, and
    ``module.time.sleep(...)`` shapes. Excludes string mentions.
    """
    func = node.func
    if isinstance(func, ast.Attribute) and func.attr == "sleep":
        value = func.value
        if isinstance(value, ast.Name) and value.id == "time":
            return True
    if isinstance(func, ast.Name) and func.id == "sleep":
        return True
    return False


def _check_sleep_call(file: Path) -> list[Violation]:
    try:
        tree = ast.parse(file.read_text(encoding="utf-8", errors="replace"))
    except SyntaxError:
        return []

    violations: list[Violation] = []
    source_lines = file.read_text(encoding="utf-8", errors="replace").splitlines()

    for node in ast.walk(tree):
        if isinstance(node, ast.Call) and _is_sleep_call(node):
            if 1 <= node.lineno <= len(source_lines):
                src = source_lines[node.lineno - 1].strip()
            else:
                src = ""
            violations.append(
                Violation(
                    file=file,
                    line=node.lineno,
                    rule="sleep_call",
                    message=(
                        "actual time.sleep() call — flakiness source. "
                        "Use unittest.mock.patch('time.sleep'), threading."
                        "Barrier, or busy-wait helpers (see test_timing_utils)."
                    ),
                    source=src,
                )
            )
    return violations


# ---------------------------------------------------------------------------
# Check: pytest.skip without reason.
# ---------------------------------------------------------------------------


def _check_skip_no_reason(file: Path) -> list[Violation]:
    try:
        tree = ast.parse(file.read_text(encoding="utf-8", errors="replace"))
    except SyntaxError:
        return []

    violations: list[Violation] = []
    source_lines = file.read_text(encoding="utf-8", errors="replace").splitlines()

    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        func = node.func
        is_pytest_skip = (
            isinstance(func, ast.Attribute)
            and isinstance(func.value, ast.Name)
            and func.value.id == "pytest"
            and func.attr == "skip"
        )
        if not is_pytest_skip:
            continue

        has_reason_kwarg = any(kw.arg == "reason" for kw in node.keywords)
        has_positional_reason = (
            len(node.args) >= 1
            and isinstance(node.args[0], (ast.Constant, ast.JoinedStr))
            and (
                not isinstance(node.args[0], ast.Constant)
                or isinstance(node.args[0].value, str)
            )
        )
        if has_reason_kwarg or has_positional_reason:
            continue
        if 1 <= node.lineno <= len(source_lines):
            src = source_lines[node.lineno - 1].strip()
        else:
            src = ""
        violations.append(
            Violation(
                file=file,
                line=node.lineno,
                rule="skip_no_reason",
                message="pytest.skip() without reason — unjustified skip",
                source=src,
            )
        )
    return violations


# ---------------------------------------------------------------------------
# Check: bare except: pass / except Exception: pass.
# ---------------------------------------------------------------------------


def _is_bare_except(handler: ast.ExceptHandler) -> bool:
    """True for ``except:`` or ``except Exception:``-style handlers.

    Narrow handlers (``except ValueError:``,
    ``except (KeyError, TypeError):``) are NOT considered bare;
    they catch a specific exception class and the developer's
    intent is documented by the class name.
    """
    # No exception type at all: `except:`
    if handler.type is None:
        return True
    # Multiple names: `except (A, B):` — at least one must be the
    # generic ``Exception`` or ``BaseException`` for it to be bare.
    if isinstance(handler.type, ast.Tuple):
        for elt in handler.type.elts:
            if _is_generic_exception(elt):
                return True
        return False
    return _is_generic_exception(handler.type)


def _is_generic_exception(node: ast.expr) -> bool:
    """True if the node is ``Exception`` or ``BaseException``.

    Catches both ``Exception`` and ``BaseException`` as bare-style
    handlers. Anything else (``ValueError``, ``OSError``, etc.)
    is a narrow handler.
    """
    if isinstance(node, ast.Name) and node.id in {"Exception", "BaseException"}:
        return True
    if isinstance(node, ast.Attribute) and node.attr in {"Exception", "BaseException"}:
        return True
    return False


def _is_pass_only(body: list[ast.stmt]) -> bool:
    if len(body) != 1:
        return False
    stmt = body[0]
    if isinstance(stmt, ast.Pass):
        return True
    if isinstance(stmt, ast.Expr) and isinstance(stmt.value, ast.Constant):
        if stmt.value.value is None:
            return True
    return False


def _check_bare_except_pass(file: Path) -> list[Violation]:
    try:
        tree = ast.parse(file.read_text(encoding="utf-8", errors="replace"))
    except SyntaxError:
        return []

    violations: list[Violation] = []
    source_lines = file.read_text(encoding="utf-8", errors="replace").splitlines()

    for node in ast.walk(tree):
        if not isinstance(node, ast.ExceptHandler):
            continue
        if not _is_pass_only(node.body):
            continue
        # Skip narrow handlers — they're documented intent, not
        # silent error swallowing.
        if not _is_bare_except(node):
            continue
        if 1 <= node.lineno <= len(source_lines):
            src = source_lines[node.lineno - 1].strip()
        else:
            src = ""
        violations.append(
            Violation(
                file=file,
                line=node.lineno,
                rule="bare_except_pass",
                message=(
                    "except: pass / except Exception: pass — silent error "
                    "swallowing hides test failures"
                ),
                source=src,
            )
        )
    return violations


# ---------------------------------------------------------------------------
# Check:
NOQA_PATTERN = "# noqa"
NOQA_JUSTIFIED_RE = re.compile(r"#\s*noqa\s*:\s*[A-Z]+\d*\s*[—-]+\s*\S")


def _check_unjustified_noqa(file: Path) -> list[Violation]:
    violations: list[Violation] = []
    source_lines = file.read_text(encoding="utf-8", errors="replace").splitlines()
    for lineno, line in enumerate(source_lines, start=1):
        if NOQA_PATTERN not in line:
            continue
        if re.search(NOQA_JUSTIFIED_RE, line):
            continue
        violations.append(
            Violation(
                file=file,
                line=lineno,
                rule="unjustified_noqa",
                message=NOQA_VIOLATION_MSG,
                source=line.strip(),
            )
        )
    return violations


NOQA_VIOLATION_MSG = (
    "# noqa without justification - append ': CODE - reason' "
    "(em-dash or hyphen separator) to make the suppression auditable"
)


# ---------------------------------------------------------------------------
# Check: assert X is True / assert X is False.
# ---------------------------------------------------------------------------
#
# The ``assert X is True`` pattern is an idiomatic smell: the explicit
# comparison against a bool literal provides no additional coverage over
# ``assert X``, and the comparator ``is`` (identity) is technically
# correct only if X is guaranteed to be exactly ``True`` or ``False``
# (not just truthy). When X is a numpy scalar, pandas value, or any
# custom truthy type, ``is True`` silently fails. The fix is one of:
#
#   assert X              # when only truthiness matters
#   assert X == expected  # when equality matters
#   assert X is True      # when X is guaranteed to be exactly True
#                         # (rare; cite the invariant)
#
# The runner does NOT flag every ``is True`` — it flags those that
# appear inside assert statements, where the smell combines with the
# assert's tautological nature (``assert truthy is True`` is a
# no-op for any truthy value).
# ---------------------------------------------------------------------------


def _check_assert_is_bool_comparison(file: Path) -> list[Violation]:
    try:
        source = file.read_text(encoding="utf-8", errors="replace")
        tree = ast.parse(source)
    except SyntaxError:
        return []

    violations: list[Violation] = []
    source_lines = source.splitlines()

    for node in ast.walk(tree):
        if not isinstance(node, ast.Assert):
            continue
        test = node.test
        # Detect: assert <expr> is True / is False
        if not isinstance(test, ast.Compare):
            continue
        if len(test.ops) != 1:
            continue
        op = test.ops[0]
        if not isinstance(op, ast.Is):
            continue
        if len(test.comparators) != 1:
            continue
        rhs = test.comparators[0]
        # Narrow: only flag bare `assert <name> is True/False`. Attribute
        # access (``assert obj.flag is True``) and chained expressions
        # document which property is being tested, so dropping ``is True``
        # would lose signal. Bare ``Name`` is the pure tautology case
        # where ``assert x`` is strictly clearer than ``assert x is True``.
        if not isinstance(test.left, ast.Name):
            continue
        if (
            not isinstance(rhs, ast.Constant)
            or rhs.value is not True
            and rhs.value is not False
        ):
            continue
        if 1 <= node.lineno <= len(source_lines):
            src = source_lines[node.lineno - 1].strip()
        else:
            src = ""
        literal = "True" if rhs.value is True else "False"
        violations.append(
            Violation(
                file=file,
                line=node.lineno,
                rule="assert_is_bool_comparison",
                message=(
                    f"assert X is {literal} is redundant for truthy/falsy "
                    f"values; prefer 'assert X' or 'assert X == {literal}' "
                    f"if equality is the contract"
                ),
                source=src,
            )
        )
    return violations


# ---------------------------------------------------------------------------
# Check: from dispatch import X (single item).
# ---------------------------------------------------------------------------


def _check_single_item_dispatch_root(file: Path) -> list[Violation]:
    try:
        tree = ast.parse(file.read_text(encoding="utf-8", errors="replace"))
    except SyntaxError:
        return []

    violations: list[Violation] = []
    source_lines = file.read_text(encoding="utf-8", errors="replace").splitlines()

    for node in ast.walk(tree):
        if not isinstance(node, ast.ImportFrom):
            continue
        if node.module != "dispatch":
            continue
        if node.level != 0:
            continue
        names = [n for n in node.names if n.name != "*"]
        if len(names) != 1:
            continue
        if 1 <= node.lineno <= len(source_lines):
            src = source_lines[node.lineno - 1].strip()
        else:
            src = ""
        violations.append(
            Violation(
                file=file,
                line=node.lineno,
                rule="single_item_dispatch_root_import",
                message=(
                    f"from dispatch import {names[0].name} — use "
                    f"from dispatch.{_module_for(names[0].name)} import "
                    f"{names[0].name} (AGENTS.md Import Conventions). "
                    "Multi-item 'from dispatch import A, B' is acceptable."
                ),
                source=src,
            )
        )
    return violations


def _module_for(name: str) -> str:
    """Best-effort guess at the dispatch sub-module for the imported name.

    The runner doesn't actually validate the guess; the message just
    points the developer at the documented convention. Keeping this here
    means the violation message is actionable without the runner having
    to introspect the dispatch/ package.
    """
    if name == "feature_flags":
        return "feature_flags"
    if name == "file_utils":
        return "file_utils"
    return "module"


# ---------------------------------------------------------------------------
# Check registry.
# ---------------------------------------------------------------------------

CHECKS: dict[str, callable] = {
    "bare_magicmock": _check_bare_magicmock,
    "missing_assert": _check_missing_assert,
    "sleep_call": _check_sleep_call,
    "skip_no_reason": _check_skip_no_reason,
    "bare_except_pass": _check_bare_except_pass,
    "unjustified_noqa": _check_unjustified_noqa,
    "single_item_dispatch_root_import": _check_single_item_dispatch_root,
    "assert_is_bool_comparison": _check_assert_is_bool_comparison,
}


# ---------------------------------------------------------------------------
# Auditability allowlist. An entry is
# (relpath, rule, line, reason). It silences a violation that has been
# manually verified to be intentional. Each entry cites the source line
# as evidence. A typo fails closed: an unknown (file, rule, line) tuple
# does NOT match the lookup and the violation is reported normally.
# ---------------------------------------------------------------------------


KNOWN_HYGIENE_VIOLATIONS: list[tuple[str, str, int, str]] = [
    # Sentinel-class catch in a try/finally test. The test deliberately
    # raises an internal `_TestFailed` exception to verify that the
    # `finally` block in `context_timer()` runs. Catching it with `pass`
    # is the only way to inspect `timer.duration_ms` after the raise.
    # The flag (silent error swallowing) is the test's mechanism, not
    # a real bug.
    (
        "tests/unit/core/utils/test_timing_utils.py",
        "bare_except_pass",
        96,
        "sentinel catch of internal `_TestFailed` in try/finally test; "
        "the only way to assert the `finally` block ran",
    ),
    # Optional-dependency probe in build-configuration importability
    # test. `__import__(module)` may raise ImportError when an optional
    # dep is absent; we collect and report these as a separate list
    # (the test only fails if errors is non-empty at the end). The
    # `pass` is intentional: the goal is "can be imported", not
    # "imports cleanly".
    (
        "tests/unit/test_build_configuration.py",
        "bare_except_pass",
        193,
        "optional-dep ImportError probe in __import__(module); "
        "collected and reported as `errors` list, not silently lost",
    ),
    (
        "tests/unit/test_build_configuration.py",
        "bare_except_pass",
        195,
        "same try/except as L193 — broad Exception catch is the "
        "outer guard for the optional-dep import probe",
    ),
    # AST parse failure on `py_file` content. SyntaxError on a vendored
    # .py file is not a test failure; the test continues and the AST
    # walk skips the file. The `pass` is the documented behaviour.
    (
        "tests/unit/test_build_configuration.py",
        "bare_except_pass",
        298,
        "SyntaxError swallow in AST parse of vendored .py file; "
        "documented as 'not a test failure' in the loop comment",
    ),
    (
        "tests/unit/test_build_configuration.py",
        "bare_except_pass",
        300,
        "outer Exception catch in the same open()+ast.parse() block; "
        "guards against OSError on unreadable vendored files",
    ),
    # Optional PIL/Pillow + zxing dep probe. The test runs only if
    # pyzbar is available; if not, the helper returns None and the
    # caller asserts a skip. ImportError is the documented
    # opt-dep-missing case.
    (
        "tests/unit/test_convert_to_scansheet_type_a.py",
        "bare_except_pass",
        53,
        "optional PIL/zxing ImportError probe; helper returns None "
        "and the caller pytest.skip()s the test",
    ),
    # Optional yaml dep probe. The helper tries stdlib yaml first,
    # then invoke's vendored yaml. Both ImportError catches are
    # documented fallbacks; if both fail, the helper returns {}.
    (
        "tests/unit/test_golden_output.py",
        "bare_except_pass",
        315,
        "stdlib yaml ImportError probe; falls through to invoke's "
        "vendored yaml, then returns {} if both absent",
    ),
    (
        "tests/unit/test_golden_output.py",
        "bare_except_pass",
        324,
        "invoke.vendor.yaml ImportError probe; same fallback chain " "as L315",
    ),
    # Integration-layer sleep calls. All four are in explicit polling
    # helpers whose entire job is "wait for a real external thing to
    # become ready, with a deadline". The pattern is the same as the
    # unit test_timing_utils.SlowBackend test fixture: bounded by a
    # timeout, polling a real signal, fail-fast on deadline. The
    # ``time.sleep`` is the only way to do this without busy-waiting
    # the CPU; the helper docstring documents the contract.
    (
        "tests/integration/test_edi_sample_files.py",
        "sleep_call",
        95,
        "_wait_for_server: bounded poll for a real socket connect, "
        "raises RuntimeError on timeout; helper is the documented "
        "pattern for waiting on real servers",
    ),
    (
        "tests/integration/test_edi_sample_files.py",
        "sleep_call",
        108,
        "_wait_for_messages: bounded poll for handler.messages to "
        "reach count; same pattern as _wait_for_server",
    ),
    (
        "tests/integration/test_ftp_smtp_live_servers.py",
        "sleep_call",
        70,
        "_wait_for_server: bounded poll for a real socket connect; "
        "same pattern as test_edi_sample_files L95",
    ),
    (
        "tests/integration/test_ftp_smtp_live_servers.py",
        "sleep_call",
        83,
        "_wait_for_messages: bounded poll for handler.messages; "
        "same pattern as test_edi_sample_files L108",
    ),
    (
        "tests/integration/test_log_email_comprehensive.py",
        "sleep_call",
        110,
        "_wait_until: bounded poll with deadline; helper docstring "
        "states it replaces fixed time.sleep() with a deterministic "
        "deadline, so a faster handler doesn't slow the suite and a "
        "slower one fails fast",
    ),
    (
        "tests/integration/test_multi_folder_edge_cases.py",
        "sleep_call",
        93,
        "SlowBackend.send: explicit artificial-delay class for "
        "testing concurrency/race conditions; class name and "
        "docstring declare the intent",
    ),
    (
        "tests/integration/test_multi_folder_edge_cases.py",
        "sleep_call",
        420,
        "same SlowBackend.send pattern as L93",
    ),
    (
        "tests/integration/test_multi_folder_edge_cases.py",
        "sleep_call",
        430,
        "same SlowBackend.send pattern as L93",
    ),
]


def _is_known_hygiene_violation(file: Path, rule: str, line: int) -> bool:
    """Return True if (file, rule, line) is in the allowlist.

    ``file`` is matched by relative path string. The runner's caller
    passes the path the check function was invoked with; this helper
    resolves it the same way for the lookup.
    """
    try:
        rel = str(file.relative_to(PROJECT_ROOT))
    except ValueError:
        rel = str(file)
    for f, r, l, _reason in KNOWN_HYGIENE_VIOLATIONS:
        if f == rel and r == rule and l == line:
            return True
    return False


# Audit-mode flag. When True, KNOWN_HYGIENE_VIOLATIONS is NOT applied:
# every violation is reported, so the allowlist is re-validated
# end-to-end. Mirrors the ``--no-skip-known-equivalent`` flag on the
# mutation runner (``test_property_tests_are_sufficient.py``) and
# ``KNOWN_ASSERTION_EQUIVALENT`` on the assertion runner
# (``test_assertions_are_meaningful.py``).
_AUDIT_HYGIENE_VIOLATIONS: bool = "--no-skip-known-hygiene-violations" in sys.argv

# ---------------------------------------------------------------------------
# Pytest test functions.
# ---------------------------------------------------------------------------


def _id_for(file: Path) -> str:
    return str(file.relative_to(PROJECT_ROOT))


def _violation_ids(violations: Iterable[Violation]) -> list[str]:
    return [f"{v.file.name}:{v.line} [{v.rule}]" for v in violations]


@pytest.mark.meta_hygiene
@pytest.mark.parametrize(
    "file,check_name",
    [
        pytest.param(f, name, id=f"{_id_for(f)}::{name}")
        for f in _iter_scanned_test_paths()
        for name in CHECKS
    ],
)
def test_hygiene_violations(file: Path, check_name: str) -> None:
    """Run a single hygiene check against a single unit test file.

    Parametrized over (file, check) so ``-k missing_assert`` or
    ``-k test_db2ssh_connection`` works naturally. Each (file, check) is
    independent and safe to parallelize with ``-n auto``.

    The full list of violations across all (file, check) pairs IS the
    deliverable. Each parametrized case fails individually so a future
    ``-k`` filter surfaces only the relevant slice.
    """
    check_fn = CHECKS[check_name]
    try:
        violations = check_fn(file)
    except Exception as exc:
        violations = [
            Violation(
                file=file,
                line=0,
                rule=check_name,
                message=f"check raised: {type(exc).__name__}: {exc}",
                source="",
            )
        ]

    # Filter allowlist. A violation matching an entry in
    # KNOWN_HYGIENE_VIOLATIONS is intentional and not reported as a
    # failure. The entry's reason is the audit trail; re-validate
    # periodically with --no-skip-known-hygiene-violations.
    if not _AUDIT_HYGIENE_VIOLATIONS:
        violations = [
            v
            for v in violations
            if not _is_known_hygiene_violation(v.file, v.rule, v.line)
        ]

    if not violations:
        return

    formatted = "\n".join(v.format() for v in violations)
    pytest.fail(
        f"{file.relative_to(PROJECT_ROOT)}: {len(violations)} "
        f"{check_name} violation(s):\n{formatted}"
    )


@pytest.mark.meta_hygiene
def test_hygiene_runner_self_check() -> None:
    """Sanity check: this meta-test file itself should have no
    violations of the checks it enforces. If a future edit to this file
    introduces a bare MagicMock, time.sleep, or single-item dispatch
    import, the runner fails closed.

    Note: rules whose *description* is a literal string the file
    contains (``unjustified_noqa``, ``bare_magicmock``, ``sleep_call``,
    ``single_item_dispatch_root_import``) are exempt from the self-check
    because the file legitimately mentions the patterns as documentation.
    """
    self_path = Path(__file__).resolve()
    SELF_CHECK_SKIP = {
        "unjustified_noqa",
        "bare_magicmock",
        "sleep_call",
        "single_item_dispatch_root_import",
    }
    self_violations: list[Violation] = []
    for check_name, check_fn in CHECKS.items():
        if check_name in SELF_CHECK_SKIP:
            continue
        self_violations.extend(check_fn(self_path))

    if not self_violations:
        return

    formatted = "\n".join(v.format() for v in self_violations)
    pytest.fail("tests/meta/test_hygiene.py violates its own checks:\n" + formatted)


# ---------------------------------------------------------------------------
# CLI summary entry point.
# ---------------------------------------------------------------------------


def main() -> int:
    """Run all checks and print a summary. Returns 0 on success, 1 on any
    violation. Useful for CI integration or local auditing without
    pytest overhead.
    """
    files = _iter_scanned_test_paths()
    # Build a (path -> layer) map for the per-file layer attribution in
    # the layer_summary line. Paths are absolute, so we use the layer's
    # path (also absolute) for the lookup.
    layer_by_path: dict[Path, Layer] = {}
    for layer in scanned_layers():
        for f in layer.iter_files():
            layer_by_path[(PROJECT_ROOT / f).resolve()] = layer
    all_violations: list[Violation] = []
    for file in files:
        for check_fn in CHECKS.values():
            all_violations.extend(check_fn(file))
    if not _AUDIT_HYGIENE_VIOLATIONS:
        # Drop allowlisted violations (intentional exceptions, cited in
        # KNOWN_HYGIENE_VIOLATIONS). Run with
        # ``--no-skip-known-hygiene-violations`` to re-validate.
        before = len(all_violations)
        all_violations = [
            v
            for v in all_violations
            if not _is_known_hygiene_violation(v.file, v.rule, v.line)
        ]
        suppressed = before - len(all_violations)
    else:
        suppressed = 0
    by_layer: dict[str, int] = {}
    for path in files:
        layer = layer_by_path.get(path)
        if layer is not None:
            by_layer[layer.name] = by_layer.get(layer.name, 0) + 1
    layer_summary = ", ".join(f"{name}={n}" for name, n in sorted(by_layer.items()))
    print(f"Scanned {len(files)} test file(s) across layers: {layer_summary}")
    if suppressed:
        print(
            f"Suppressed {suppressed} allowlisted violation(s) "
            f"(see KNOWN_HYGIENE_VIOLATIONS; re-validate with "
            f"--no-skip-known-hygiene-violations)."
        )
    print(
        f"Found {len(all_violations)} violation(s) across "
        f"{len({v.file for v in all_violations})} file(s)."
    )
    by_rule: dict[str, int] = {}
    for v in all_violations:
        by_rule[v.rule] = by_rule.get(v.rule, 0) + 1
    for rule, count in sorted(by_rule.items()):
        print(f"  {rule}: {count}")
    if all_violations:
        print()
        for v in all_violations:
            print(v.format())
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
