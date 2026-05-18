"""Pytest plugin to enforce spec= for MagicMock when mocking database connections.

This plugin catches bare MagicMock() used for mock_db and mock_database_obj,
which should use spec=DatabaseConnectionProtocol to catch method name typos.

Other mocks (mock_service, mock_ui, etc.) are allowed bare since they may
not have formal protocols.
"""

from __future__ import annotations

import ast
import os
from typing import Any

import pytest


DB_MOCK_NAMES = {"mock_db", "mock_database_obj"}


class MagicMockVisitor(ast.NodeVisitor):
    """Visit AST nodes to find bare MagicMock() used as database mocks."""

    def __init__(self) -> None:
        self.violations: list[tuple[int, str]] = []

    def visit_Assign(self, node: ast.Assign) -> None:
        """Check if target is a db mock variable without spec=."""
        for target in node.targets:
            if isinstance(target, ast.Name) and target.id in DB_MOCK_NAMES:
                if isinstance(node.value, ast.Call):
                    if isinstance(node.value.func, ast.Name) and node.value.func.id == "MagicMock":
                        has_spec = any(kw.arg == "spec" for kw in node.value.keywords)
                        if not has_spec:
                            self.violations.append(
                                (node.lineno, f"MagicMock() without spec= for '{target.id}'")
                            )
        self.generic_visit(node)


def _check_file_for_bare_magicmock(filepath: str) -> list[tuple[int, str]]:
    """Parse a Python file and return list of (lineno, message) violations."""
    try:
        with open(filepath) as f:
            content = f.read()
    except OSError:
        return []

    try:
        tree = ast.parse(content, filename=filepath)
    except SyntaxError:
        return []

    visitor = MagicMockVisitor()
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
        msg = "\n".join([
            f"Bare MagicMock() used for database mock in {os.path.relpath(filepath)}:",
            *lines,
            "",
            "Use MagicMock(spec=DatabaseConnectionProtocol) for mock_db/mock_database_obj.",
            "See: tests/AGENTS.md - MOCKING CONVENTIONS",
        ])
        pytest.fail(msg)