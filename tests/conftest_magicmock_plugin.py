"""Pytest plugin to enforce spec= for MagicMock when mocking database connections.

This plugin catches bare MagicMock() used for mock_db and mock_database_obj,
which should use spec=DatabaseConnectionProtocol to catch method name typos.

Other mocks (mock_service, mock_ui, etc.) are allowed bare since they may
not have formal protocols.

Bypass detection
----------------
The plugin also flags the ``_ = MagicMock()`` workaround used to silence
unused-import linters. Use a module-level ``allow_bare_magicmock = True``
or a per-line ``# allow-bare-magicmock`` trailing comment to opt a file or
line out of the check, respectively.

Callback mocks
--------------
Bare ``MagicMock()`` is acceptable for callbacks (see tests/AGENTS.md). When a
target is itself a callback argument (``on_complete=MagicMock()`` etc.) the
plugin does not flag it; only Assign statements are inspected.
"""

from __future__ import annotations

import ast
import os
from typing import Any

import pytest

DB_MOCK_NAMES = {"mock_db", "mock_database_obj"}
ALLOW_LINE_COMMENT = "# allow-bare-magicmock"
ALLOW_MODULE_FLAG = "allow_bare_magicmock = True"


class MagicMockVisitor(ast.NodeVisitor):
    """Visit AST nodes to find bare MagicMock() used as database mocks."""

    def __init__(self, source_lines: list[str]) -> None:
        self.violations: list[tuple[int, str]] = []
        self._source_lines = source_lines

    def _is_line_allowed(self, lineno: int) -> bool:
        if lineno < 1 or lineno > len(self._source_lines):
            return False
        return ALLOW_LINE_COMMENT in self._source_lines[lineno - 1]

    def visit_Assign(self, node: ast.Assign) -> None:
        """Check if target is a db mock variable without spec=."""
        if self._is_line_allowed(node.lineno):
            return
        if (
            isinstance(node.value, ast.Call)
            and isinstance(node.value.func, ast.Name)
            and node.value.func.id == "MagicMock"
        ):
            has_spec = any(kw.arg == "spec" for kw in node.value.keywords)
            if has_spec:
                return
            target_names = [t.id for t in node.targets if isinstance(t, ast.Name)]
            if not target_names:
                return
            for target_id in target_names:
                if target_id == "_":
                    self.violations.append(
                        (
                            node.lineno,
                            "_ = MagicMock() workaround — delete the line and "
                            "remove the now-unused MagicMock import.",
                        )
                    )
                elif target_id in DB_MOCK_NAMES:
                    self.violations.append(
                        (
                            node.lineno,
                            f"MagicMock() without spec= for '{target_id}'",
                        )
                    )
        self.generic_visit(node)


def _file_has_module_flag(source: str) -> bool:
    return ALLOW_MODULE_FLAG in source


def _check_file_for_bare_magicmock(filepath: str) -> list[tuple[int, str]]:
    """Parse a Python file and return list of (lineno, message) violations."""
    try:
        with open(filepath) as f:
            content = f.read()
    except OSError:
        return []

    if _file_has_module_flag(content):
        return []

    try:
        tree = ast.parse(content, filename=filepath)
    except SyntaxError:
        return []

    visitor = MagicMockVisitor(content.splitlines())
    visitor.visit(tree)
    return visitor.violations


@pytest.fixture(autouse=True)
def _check_bare_magicmock(request: Any) -> None:
    """Check test files for bare MagicMock() used as database mocks."""
    filepath = str(request.fspath)
    if not filepath.endswith(".py") or "tests" not in filepath:
        return

    violations = _check_file_for_bare_magicmock(filepath)

    if violations:
        lines = [f"  Line {lineno}: {msg}" for lineno, msg in violations]
        msg = "\n".join(
            [
                "Bare MagicMock() detected in " f"{os.path.relpath(filepath)}:",
                *lines,
                "",
                "Use MagicMock(spec=...) for typed mocks.",
                "For callbacks, use MagicMock() — pass them as keyword args "
                "(not assignments) so the plugin does not flag them.",
                "Opt-out: trailing '# allow-bare-magicmock' on the line, "
                "or module-level 'allow_bare_magicmock = True'.",
                "See: tests/AGENTS.md - MOCKING CONVENTIONS",
            ]
        )
        pytest.fail(msg)
