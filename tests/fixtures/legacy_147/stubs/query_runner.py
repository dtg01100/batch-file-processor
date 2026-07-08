"""Stub for 1.47 ``query_runner.py``.

The 1.47 dispatch instantiates ``query_runner(...)`` from this module and calls
``run_arbitrary_query`` to populate ``upc_dict``. We provide a class that
accepts the same positional args as the real one but never opens a connection
(no pyodbc available in this test environment).
"""

from __future__ import annotations


class query_runner:
    """No-op replacement for the ODBC-backed ``query_runner``.

    ``run_arbitrary_query`` returns an empty iterable. Routing tests do not
    need real UPC data; if a future test needs it, a fixture can replace
    ``sys.modules['query_runner'].query_runner.run_arbitrary_query`` with one
    that yields fixture rows.
    """

    def __init__(
        self,
        as400_username: str = "",  # noqa: ARG002
        as400_password: str = "",  # noqa: ARG002
        as400_address: str = "",  # noqa: ARG002
        odbc_driver: str = "",  # noqa: ARG002
    ) -> None:
        self._runs: list[str] = []

    def run_arbitrary_query(self, _query: str):
        self._runs.append(_query)
        return iter(())

    def run_query(self, _query: str, params=None):  # noqa: ARG002
        return []


__all__ = ["query_runner"]
