"""Tests for webapp.config.Settings — Phase 6.1 bind-localhost-by-default."""

from __future__ import annotations

import pytest

from webapp.config import DEFAULT_HOST, DEFAULT_PORT, Settings

pytestmark = [pytest.mark.unit]


def test_settings_default_host_is_localhost() -> None:
    """Phase 6.1: a fresh ``Settings()`` binds ``127.0.0.1``, not
    ``0.0.0.0``. Matches PROJECT_SPEC.md §3.4 ("no inbound network
    surface")."""
    s = Settings(
        base_dir=__import__("pathlib").Path("/tmp/x"),
        data_dir=__import__("pathlib").Path("/tmp/x/c"),
    )
    assert s.host == DEFAULT_HOST == "127.0.0.1"
    assert s.port == DEFAULT_PORT == 8000


def test_settings_default_host_is_module_constant() -> None:
    """The defaults are module-level constants so an operator can
    reference them in docs / tooling without re-typing the literal."""
    assert DEFAULT_HOST == "127.0.0.1"
    assert DEFAULT_PORT == 8000


def test_settings_from_env_no_env_uses_defaults(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """No env vars → defaults. Verified by removing the keys from the
    process environment (in case the test runner was started with
    BFS_HOST/BFS_PORT set)."""
    monkeypatch.delenv("BFS_HOST", raising=False)
    monkeypatch.delenv("BFS_PORT", raising=False)
    s = Settings.from_env()
    assert s.host == "127.0.0.1"
    assert s.port == 8000


def test_settings_from_env_honors_bfs_host(monkeypatch: pytest.MonkeyPatch) -> None:
    """``BFS_HOST`` is honored so an operator can opt in to remote
    access without changing source code."""
    monkeypatch.setenv("BFS_HOST", "0.0.0.0")
    monkeypatch.delenv("BFS_PORT", raising=False)
    s = Settings.from_env()
    assert s.host == "0.0.0.0"
    assert s.port == 8000


def test_settings_from_env_honors_bfs_port(monkeypatch: pytest.MonkeyPatch) -> None:
    """``BFS_PORT`` is honored (parsed as int)."""
    monkeypatch.delenv("BFS_HOST", raising=False)
    monkeypatch.setenv("BFS_PORT", "9001")
    s = Settings.from_env()
    assert s.port == 9001


def test_settings_from_env_honors_both(monkeypatch: pytest.MonkeyPatch) -> None:
    """Both env vars together (the operator's opt-in)."""
    monkeypatch.setenv("BFS_HOST", "0.0.0.0")
    monkeypatch.setenv("BFS_PORT", "9001")
    s = Settings.from_env()
    assert s.host == "0.0.0.0"
    assert s.port == 9001


def test_settings_invalid_port_raises(monkeypatch: pytest.MonkeyPatch) -> None:
    """A non-integer ``BFS_PORT`` raises ``ValueError`` at startup —
    fail loud rather than bind to a wrong port silently."""
    monkeypatch.setenv("BFS_PORT", "not-a-number")
    with pytest.raises(ValueError):
        Settings.from_env()


def test_main_module_uses_settings_host_and_port(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """``webapp.main.main()`` reads the host + port from ``Settings``
    so the env vars actually take effect (this is what
    ``BFS_HOST=0.0.0.0 python -m webapp.main`` relies on).

    We don't actually bind uvicorn (that would require network) — we
    just confirm that ``uvicorn.run`` is called with the right kwargs
    by monkey-patching it.
    """
    monkeypatch.setenv("BFS_HOST", "0.0.0.0")
    monkeypatch.setenv("BFS_PORT", "9001")
    captured: dict = {}

    def _fake_run(*args, **kwargs):
        captured["args"] = args
        captured["kwargs"] = kwargs

    monkeypatch.setattr("uvicorn.run", _fake_run)
    from webapp.main import main as webapp_main

    webapp_main()
    assert captured["kwargs"]["host"] == "0.0.0.0"
    assert captured["kwargs"]["port"] == 9001


def test_settings_kwargs_round_trip() -> None:
    """The dataclass remains a kwargs-friendly round-trip — a test
    fixture that does ``Settings(base_dir=..., data_dir=...)`` (the
    common pattern across the existing webapp test suite) keeps
    working without explicit host/port."""
    from pathlib import Path

    s = Settings(base_dir=Path("/tmp/a"), data_dir=Path("/tmp/a/config"))
    assert s.host == "127.0.0.1"
    assert s.port == 8000
