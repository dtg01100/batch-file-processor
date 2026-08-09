"""Audit Qt code for IntEnum-vs-pure-Enum breakage under PySide6 6.10+.

PySide6 6.10 migrated several ``Qt.*`` enums from int-compatible enums to pure
``enum.Enum`` members. That silently breaks, without any exception:

- ``raw_int == Qt.Enum.Member``  -> always ``False`` (member != int)
- ``int(Qt.Enum.Member)``        -> ``TypeError``
- ``if Qt.Enum.Member:``         -> always ``True`` (pure enums are truthy,
                                     even the 0-value member)

Class-scoped enums (``QDialog.DialogCode``, ``Qt.Key``, ``Qt.FocusPolicy``)
remain int-compatible in 6.10; Flag types (``Qt.ItemFlag``, ``Qt.MouseButton``,
``Qt.AlignmentFlag``) keep bitwise operators. Only *pure* enums are dangerous:
``Qt.CheckState``, ``Qt.CursorShape``, ``Qt.ScrollBarPolicy``,
``Qt.WidgetAttribute``, ``Qt.WindowModality`` (and others added in later
releases — the probe below classifies whatever the installed PySide6 has).

The check has two passes:

1. Static scan (regex + AST) for risky sites: enum-vs-int comparisons,
   ``int()`` coercion, truthiness, bitwise math on a member.
2. Runtime probe: resolves every ``Qt.<NS>.<Member>`` token used by the
   codebase under the *installed* PySide6 and classifies it as pure enum /
   int-enum / flag. A risky site whose token is a pure enum is a failure.

Usage::

    python scripts/qt_enum_audit.py            # audit interface/, core/, tests/, ...
    python scripts/qt_enum_audit.py --jobs 8   # parallelism (probe only)

Exit code is 0 when no breakage is found, 1 otherwise.

Regression history: resend_dialog.py compared ``state == Qt.CheckState.Checked``
(state is a raw int) which became always-False on 6.10 — checkbox selections
stopped registering. Fixed 2026-08-09 by normalizing the enum first
(``Qt.CheckState(state) == Qt.CheckState.Checked``).
"""

from __future__ import annotations

import argparse
import ast
import concurrent.futures
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TARGETS = [
    "interface",
    "core",
    "backend",
    "adapters",
    "dispatch",
    "main_interface.py",
    "main_qt.py",
    "tests",
]

# ---------------------------------------------------------------------------
# Pass 1a: static regex scan
# ---------------------------------------------------------------------------

STATIC_RE = [
    # Coercion / truthiness / bitwise on a Qt.* member literal. Comparison
    # sites are handled in the AST pass where both sides are visible (an
    # enum-to-enum comparison is safe; enum-vs-identifier is not).
    re.compile(r"\bint\(\s*Qt\.[A-Za-z_.]+\.\w+"),
    re.compile(r"\bif\s+Qt\.[A-Za-z_.]+\.\w+\b"),
    re.compile(r"Qt\.[A-Za-z_.]+\.\w+\s*(?:&|\||\^)"),
    re.compile(r"(?:&|\||\^)\s*Qt\.[A-Za-z_.]+\.\w+"),
]

# ---------------------------------------------------------------------------
# Pass 1b: AST scan for int-vs-enum sites
# ---------------------------------------------------------------------------

ENUM_RETURNING_METHODS = {
    "checkState",
    "selectionMode",
    "editTriggers",
    "windowModality",
    "echoMode",
    "orientation",
    "focusPolicy",
    "alignment",
    "dropAction",
    "dragDropMode",
    "textInteractionFlags",
    "contextMenuPolicy",
    "toolButtonStyle",
    "textFormat",
    "caseSensitivity",
    "sortOrder",
    "shape",
    "frameShape",
    "dialogCode",
    "standardButton",
    "state",
    "itemFlags",
    "flags",
    "cursor",
    "scrollBarPolicy",
    "defaultAction",
    "layoutDirection",
}

INT_CONSTS = {0, 1, 2, 3, 4, 8, 16, 32, 64, 128, 256, 512, 16384, 32768, 65536}


def _is_enum_attr(node: ast.AST) -> bool:
    """Attribute chain ending in an all-caps (enum member) segment."""
    return isinstance(node, ast.Attribute) and (
        node.attr.isupper() or (node.attr[:1].isupper() and not node.attr.islower())
    )


def _is_enum_ret_call(node: ast.AST) -> bool:
    return (
        isinstance(node, ast.Call)
        and isinstance(node.func, ast.Attribute)
        and node.func.attr in ENUM_RETURNING_METHODS
    )


def _is_enum_ctor_call(node: ast.AST) -> bool:
    """Qt.<EnumClass>(...) — an enum constructor call (e.g. Qt.CheckState(x))."""
    return (
        isinstance(node, ast.Call)
        and isinstance(node.func, ast.Attribute)
        and isinstance(node.func.value, ast.Name)
        and node.func.value.id == "Qt"
        and node.func.attr[:1].isupper()
    )


def _is_enum_producing(node: ast.AST) -> bool:
    """Expression that yields a Qt enum: literal member, enum-returning
    method call, or Qt.<EnumClass>(...) constructor."""
    return _is_enum_attr(node) or _is_enum_ret_call(node) or _is_enum_ctor_call(node)


def _describe(node: ast.AST) -> str:
    try:
        return ast.unparse(node)[:80]
    except Exception:
        return "<expr>"


def _check_compare(node: ast.Compare, out: list[tuple[int, str]]) -> None:
    """Flag int-vs-enum comparison sites in a Compare node."""
    left = node.left
    for op, comp in zip(node.ops, node.comparators, strict=False):
        if not isinstance(op, (ast.Eq, ast.NotEq)):
            continue
        for side, is_left in ((left, True), (comp, False)):
            other = comp if is_left else left
            # (a) int literal vs enum-ish expression -> risky
            if (
                isinstance(side, ast.Constant)
                and isinstance(side.value, int)
                and side.value in INT_CONSTS
                and (_is_enum_attr(other) or _is_enum_ret_call(other))
            ):
                out.append(
                    (
                        node.lineno,
                        f"{_describe(other)} {type(op).__name__} {side.value}",
                    )
                )
            # (b) Qt.* enum literal vs non-enum expression (bare name or
            #     method call) -> risky; enum-to-enum is safe. Restricted to
            #     Qt.* chains: class-scoped enums (QDialog.DialogCode, ...)
            #     are still int-compatible, and the all-caps heuristic alone
            #     over-matches on plain constants like PAGE_SIZE.
            if (
                _is_enum_attr(side)
                and "Qt." in _describe(side)
                and not _is_enum_producing(other)
            ):
                out.append(
                    (
                        node.lineno,
                        f"{_describe(side)} {type(op).__name__} {_describe(other)}",
                    )
                )


def _check_int_coercion(node: ast.Call, out: list[tuple[int, str]]) -> None:
    """Flag int(<enum-ish>) coercion sites."""
    if not (isinstance(node.func, ast.Name) and node.func.id == "int"):
        return
    arg = node.args[0] if node.args else None
    if arg is not None and (_is_enum_attr(arg) or _is_enum_ret_call(arg)):
        out.append((node.lineno, f"int({_describe(arg)})"))


def _check_truthiness(node: ast.AST, out: list[tuple[int, str]]) -> None:
    """Flag truthiness of an enum expression in if/while tests."""
    test = node.test  # type: ignore[attr-defined]
    if isinstance(test, ast.UnaryOp) and isinstance(test.op, ast.Not):
        test = test.operand
    if _is_enum_attr(test) or _is_enum_ret_call(test):
        out.append((node.lineno, f"if {_describe(test)}:"))


def ast_sites(path: Path) -> list[tuple[int, str]]:
    """Return (lineno, description) for int-vs-enum risky sites."""
    try:
        tree = ast.parse(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, SyntaxError):
        return []
    out: list[tuple[int, str]] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Compare):
            _check_compare(node, out)
        elif isinstance(node, ast.Call):
            _check_int_coercion(node, out)
        elif isinstance(node, (ast.If, ast.While)):
            _check_truthiness(node, out)
    return out


# ---------------------------------------------------------------------------
# Pass 2: runtime classification of every Qt.<NS>.<Member> token in use
# ---------------------------------------------------------------------------

TOKEN_RE = re.compile(r"\bQt\.([A-Z][A-Za-z0-9_]*)\.([A-Za-z0-9_]+)\b")


def classify(probe_code: str) -> str:
    """Return 'int-enum' | 'flag' | 'pure' | 'unresolved' for a Qt.NS.Member.

    Capability-based, so the verdict matches the operation at each site:
      - int-enum: int()/comparison/arithmetic all work (safe everywhere)
      - flag:     bitwise works (~/&/|), int() does not (safe for bitwise
                  pass-through, unsafe for int comparison)
      - pure:     no int ops at all (unsafe except pass-through to Qt APIs)
    """
    script = (
        "import os\n"
        "os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')\n"
        "from PySide6.QtCore import Qt\n"
        "v = " + probe_code + "\n"
        "def _try(fn):\n"
        "    try:\n"
        "        fn(); return True\n"
        "    except Exception:\n"
        "        return False\n"
        "can_int = _try(lambda: int(v))\n"
        "can_invert = _try(lambda: ~v)\n"
        "can_and = _try(lambda: v & v)\n"
        "if can_int: print('int-enum')\n"
        "elif can_invert and can_and: print('flag')\n"
        "elif isinstance(v, __import__('enum').Enum): print('pure')\n"
        "else: print('unresolved')\n"
    )
    try:
        proc = subprocess.run(
            [sys.executable, "-c", script],
            cwd=ROOT,
            capture_output=True,
            text=True,
            timeout=60,
        )
        return proc.stdout.strip() or "unresolved"
    except Exception:
        return "unresolved"


def collect_tokens() -> dict[tuple[str, str], int]:
    tokens: dict[tuple[str, str], int] = {}
    for target in TARGETS:
        p = ROOT / target
        files = [p] if p.is_file() else sorted(p.rglob("*.py"))
        for path in files:
            try:
                text = path.read_text(encoding="utf-8")
            except (OSError, UnicodeDecodeError):
                continue
            for m in TOKEN_RE.finditer(text):
                key = (m.group(1), m.group(2))
                tokens[key] = tokens.get(key, 0) + 1
    return tokens


def _python_files() -> list[Path]:
    files: list[Path] = []
    for target in TARGETS:
        p = ROOT / target
        if p.is_file():
            files.append(p)
        elif p.is_dir():
            files.extend(sorted(p.rglob("*.py")))
    return files


def scan_hits() -> (
    tuple[list[tuple[str, int, str]], list[tuple[Path, list[tuple[int, str]]]]]
):
    """Pass 1: static + AST risky sites across all target files."""
    static_hits: list[tuple[str, int, str]] = []
    ast_hits: list[tuple[Path, list[tuple[int, str]]]] = []
    for path in _python_files():
        try:
            text = path.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError):
            continue
        for lineno, line in enumerate(text.splitlines(), 1):
            if any(rx.search(line) for rx in STATIC_RE):
                static_hits.append((str(path.relative_to(ROOT)), lineno, line.strip()))
        sites = ast_sites(path)
        if sites:
            ast_hits.append((path, sites))
    return static_hits, ast_hits


def probe_kinds(
    tokens: dict[tuple[str, str], int], jobs: int
) -> dict[tuple[str, str], str]:
    """Pass 2: classify every used Qt.* member under the installed PySide6."""
    kinds: dict[tuple[str, str], str] = {}
    with concurrent.futures.ThreadPoolExecutor(max_workers=jobs) as pool:
        futures = {
            pool.submit(classify, f"Qt.{ns}.{member}"): (ns, member)
            for ns, member in tokens
        }
        for fut in concurrent.futures.as_completed(futures):
            ns, member = futures[fut]
            kinds[(ns, member)] = fut.result()
    return kinds


def compute_failures(
    static_hits: list[tuple[str, int, str]],
    ast_hits: list[tuple[Path, list[tuple[int, str]]]],
    kinds: dict[tuple[str, str], str],
) -> list[str]:
    """A site is a failure only when its operation is unsupported by the
    enum's kind there: int ops are bad for pure enums; bitwise math is bad
    for pure but fine for flags; pass-through to Qt APIs is always fine."""
    failures: list[str] = []
    pure_tokens = {k for k, kind in kinds.items() if kind == "pure"}

    for rel, lineno, line in static_hits:
        involved = [k for k in pure_tokens if f"Qt.{k[0]}.{k[1]}" in line]
        is_bitwise = bool(re.search(r"[&|^]", line))
        if involved and not (is_bitwise and all(kinds[k] == "flag" for k in involved)):
            failures.append(f"{rel}:{lineno}: {line}  (pure enum in int op)")

    for path, sites in ast_hits:
        lines = path.read_text(encoding="utf-8").splitlines()
        for lineno, _desc in sites:
            line = lines[lineno - 1] if 0 < lineno <= len(lines) else ""
            if any(f"Qt.{ns}.{m}" in line for ns, m in pure_tokens):
                failures.append(f"{path.relative_to(ROOT)}:{lineno}: {line.strip()}")
    return failures


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--jobs", type=int, default=4, help="parallel probe workers (default: 4)"
    )
    args = parser.parse_args()

    static_hits, ast_hits = scan_hits()
    tokens = collect_tokens()
    kinds = probe_kinds(tokens, args.jobs)

    print("=== Qt enums in use (classified under installed PySide6) ===")
    for (ns, member), kind in sorted(kinds.items()):
        marker = "  <-- PURE" if kind == "pure" else ""
        print(f"  Qt.{ns}.{member:<40} {kind:<10} x{tokens[(ns, member)]}{marker}")

    print("\n=== risky sites (static regex) ===")
    for rel, lineno, line in static_hits:
        print(f"  {rel}:{lineno}: {line}")

    print("\n=== risky sites (AST: int-vs-enum, int(), truthiness) ===")
    for path, sites in ast_hits:
        for lineno, _desc in sites:
            print(f"  {path.relative_to(ROOT)}:{lineno}: {_desc}")

    failures = compute_failures(static_hits, ast_hits, kinds)
    pure_tokens = {k for k, kind in kinds.items() if kind == "pure"}
    print(
        f"\n{len(kinds)} distinct Qt enums classified; "
        f"{len(pure_tokens)} pure (pass-through only is fine); "
        f"{len(static_hits)} static sites; "
        f"{sum(len(s) for _, s in ast_hits)} AST sites"
    )
    if failures:
        print("\nFAILURES:")
        for f in failures:
            print(f"  - {f}")
        return 1
    print("\nNo int-vs-pure-enum breakage found.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
