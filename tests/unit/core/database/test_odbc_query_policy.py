"""Policy tests for read-only AS400 ODBC query usage.

These tests enforce that ODBC query call sites in backend-facing code remain
read-only. Any mutating SQL keyword in a query string literal is a test failure.
"""

from __future__ import annotations

import ast
import re
from pathlib import Path

FORBIDDEN_SQL_KEYWORDS = re.compile(
    r"\b(insert|update|delete|merge|alter|drop|create|truncate)\b",
    re.IGNORECASE,
)
ODBC_QUERY_METHODS = {"run_query", "run_arbitrary_query", "execute"}


def _iter_policy_files(repo_root: Path) -> list[Path]:
    """Return files that may contain AS400 ODBC query call sites."""
    files: set[Path] = set()

    for pattern in (
        "convert_to_*.py",
        "utils.py",
        "core/edi/**/*.py",
        "backend/**/*.py",
    ):
        files.update(repo_root.glob(pattern))

    return sorted(path for path in files if path.is_file())


def _call_name(node: ast.Call) -> str | None:
    """Extract call name from an AST call node."""
    func = node.func
    if isinstance(func, ast.Attribute):
        return func.attr
    if isinstance(func, ast.Name):
        return func.id
    return None


def _first_string_arg(node: ast.Call) -> str | None:
    """Extract first positional string argument when statically available."""
    if not node.args:
        return None

    arg = node.args[0]
    if isinstance(arg, ast.Constant) and isinstance(arg.value, str):
        return arg.value

    if isinstance(arg, ast.JoinedStr):
        parts = [
            value.value
            for value in arg.values
            if isinstance(value, ast.Constant) and isinstance(value.value, str)
        ]
        return "".join(parts) if parts else None

    return None


def test_odbc_query_literals_are_read_only():
    """Fail if backend-facing ODBC query literals contain mutating SQL keywords."""
    repo_root = Path(__file__).resolve().parents[4]
    violations: list[str] = []

    for file_path in _iter_policy_files(repo_root):
        source_text = file_path.read_text(encoding="utf-8")
        tree = ast.parse(source_text, filename=str(file_path))

        for node in ast.walk(tree):
            if not isinstance(node, ast.Call):
                continue

            name = _call_name(node)
            if name not in ODBC_QUERY_METHODS:
                continue

            query_text = _first_string_arg(node)
            if not query_text:
                continue

            if FORBIDDEN_SQL_KEYWORDS.search(query_text):
                rel_path = file_path.relative_to(repo_root)
                violations.append(
                    f"{rel_path}:{node.lineno} -> {query_text.splitlines()[0][:120]}"
                )

    assert not violations, (
        "Mutating SQL keyword detected in backend-facing ODBC query literal(s):\n"
        + "\n".join(f"- {line}" for line in violations)
    )
