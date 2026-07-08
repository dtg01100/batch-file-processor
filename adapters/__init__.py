"""Adapters package.

Concrete implementations of the ports declared in :mod:`core.ports`.
Subpackages:

- :mod:`adapters.sqlite` — Production SQLite-backed implementations.
- :mod:`adapters.inmemory` — Pure-Python implementations for tests and
  fast in-process use. Useful when the consumer needs the contract but
  doesn't need (or want) a real database.
"""
