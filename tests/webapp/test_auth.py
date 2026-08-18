"""Phase 6.2 — bearer-token auth tests.

The dependency is :func:`webapp.routers._deps.verify_api_token`;
it's applied to every router include in
:func:`webapp.main.create_app`. Tests cover the documented behaviour
matrix:

+-----------------------------+-------------------+----------------+
| ``BFS_API_TOKEN``           | Header            | Result         |
+=============================+===================+================+
| empty (auth disabled)       | any / none        | pass-through   |
+-----------------------------+-------------------+----------------+
| set, matches header         | ``Bearer <tok>``  | pass-through   |
+-----------------------------+-------------------+----------------+
| set, header missing/wrong   | n/a               | 401            |
+-----------------------------+-------------------+----------------+
| set, exempt path (``/``,    | n/a               | pass-through   |
| ``/api/health``, ``/docs``, |                   |                |
| ``/openapi.json``,          |                   |                |
| ``/redoc``)                 |                   |                |

The exemption list applies at the path level inside the dependency,
so every endpoint test (folder CRUD, diagnostics, settings, etc.) is
implicitly covered by the "token set, no header → 401" / "token set,
right header → 200" cases below. The static mount at ``/`` doesn't
carry the dependency at all (it's added per-router, not per-mount),
so ``GET /`` is always 200.
"""

from __future__ import annotations

import os
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from webapp.config import Settings
from webapp.database import open_database
from webapp.main import create_app

pytestmark = [pytest.mark.integration]


@pytest.fixture
def base_settings(tmp_path: Path) -> Settings:
    """A base ``Settings`` instance with the env vars cleared.

    Each test monkey-patches ``BFS_API_TOKEN`` (or doesn't) before
    building the client, so the fixture itself doesn't set the
    token — it just clears any inherited value so a CI runner that
    happens to have ``BFS_API_TOKEN`` set doesn't accidentally
    affect the auth-disabled tests.
    """
    os.environ.pop("BFS_API_TOKEN", None)
    return Settings(
        base_dir=tmp_path / "data", data_dir=tmp_path / "data" / "config"
    )


@pytest.fixture
def client(base_settings: Settings, monkeypatch: pytest.MonkeyPatch):
    """A ``TestClient`` against a freshly created app.

    Returns the client and the settings so individual tests can
    monkey-patch ``BFS_API_TOKEN`` before re-creating the app if
    they need to flip the auth state mid-test.

    The fixture uses ``monkeypatch`` (autouse-style cleanup at test
    teardown) so ``BFS_API_TOKEN`` is restored to "unset" after each
    test — without this, the token tests would leak the env var into
    every other test in the suite, breaking the auth-disabled
    baseline that the rest of the test suite relies on.
    """
    settings = base_settings
    # Belt-and-braces: the fixture already pops the env var in
    # ``base_settings``, but ``monkeypatch.setenv`` on a separate test
    # would survive into the next test if the runner doesn't isolate
    # env state. The explicit ``delenv(raising=False)`` here is the
    # canonical "auth disabled" precondition for every test that
    # uses this fixture.
    monkeypatch.delenv("BFS_API_TOKEN", raising=False)
    settings.ensure_dirs()
    # Seed a single folder so non-exempt endpoints have something to
    # read; the auth tests don't care about row contents, only the
    # status code, but having a row keeps the path the same as the
    # real dashboard load.
    db = open_database(settings)
    try:
        db.folders_table.insert(
            {
                "folder_name": "inbox/auth-test",
                "folder_is_active": True,
                "alias": "AUTH",
                "process_backend_copy": False,
                "process_backend_ftp": False,
                "process_backend_email": False,
                "process_backend_http": False,
                "created_at": "2026-08-18T12:00:00",
            }
        )
    finally:
        db.close()
    app = create_app(settings=settings)
    return TestClient(app), settings


def _build_client_with_token(
    settings: Settings, token: str | None, monkeypatch: pytest.MonkeyPatch
) -> TestClient:
    """Build a TestClient after monkey-patching ``BFS_API_TOKEN``.

    ``Settings.api_token`` reads from the environment on every
    access, so swapping the env var in place is enough to flip the
    auth state for the freshly built app. ``monkeypatch`` is the
    cleanup mechanism — the env var is restored to its pre-test
    state at test teardown, so token-leaking across tests is
    impossible.
    """
    if token is None:
        monkeypatch.delenv("BFS_API_TOKEN", raising=False)
    else:
        monkeypatch.setenv("BFS_API_TOKEN", token)
    app = create_app(settings=settings)
    return TestClient(app)


def test_health_exempt_from_auth(client, monkeypatch: pytest.MonkeyPatch) -> None:
    """``/api/health`` is reachable without a token even when auth is
    enabled — Docker health checks need to probe without one."""
    test_client, settings = client
    authed_client = _build_client_with_token(settings, "s3cret-token", monkeypatch)
    # Without any header: 200 (exempt).
    r = authed_client.get("/api/health")
    assert r.status_code == 200
    # With a wrong header: still 200 (exempt).
    r = authed_client.get(
        "/api/health", headers={"Authorization": "Bearer wrong"}
    )
    assert r.status_code == 200


def test_docs_exempt_from_auth(client, monkeypatch: pytest.MonkeyPatch) -> None:
    """FastAPI's ``/docs``, ``/openapi.json``, ``/redoc`` are exempt
    so the operator can inspect the API surface during development."""
    test_client, settings = client
    authed_client = _build_client_with_token(settings, "s3cret-token", monkeypatch)
    for path in ("/docs", "/openapi.json", "/redoc"):
        r = authed_client.get(path)
        assert r.status_code == 200, f"{path} should be exempt"


def test_index_exempt_from_auth(client, monkeypatch: pytest.MonkeyPatch) -> None:
    """The static mount at ``/`` doesn't carry the auth dependency;
    the browser UI must be reachable so the login prompt can fire."""
    test_client, settings = client
    authed_client = _build_client_with_token(settings, "s3cret-token", monkeypatch)
    r = authed_client.get("/")
    assert r.status_code == 200


def test_endpoint_requires_token_when_configured(client, monkeypatch: pytest.MonkeyPatch) -> None:
    """When ``BFS_API_TOKEN`` is set, an endpoint without a header
    returns 401."""
    test_client, settings = client
    authed_client = _build_client_with_token(settings, "s3cret-token", monkeypatch)
    r = authed_client.get("/api/folders")
    assert r.status_code == 401
    # The WWW-Authenticate header advertises the bearer scheme so
    # curl / httpie know what to retry with.
    assert r.headers.get("www-authenticate", "").lower().startswith("bearer")


def test_endpoint_accepts_matching_bearer(client, monkeypatch: pytest.MonkeyPatch) -> None:
    """The right token → 200."""
    test_client, settings = client
    authed_client = _build_client_with_token(settings, "s3cret-token", monkeypatch)
    r = authed_client.get(
        "/api/folders",
        headers={"Authorization": "Bearer s3cret-token"},
    )
    assert r.status_code == 200


def test_endpoint_rejects_wrong_bearer(client, monkeypatch: pytest.MonkeyPatch) -> None:
    """A wrong token → 401."""
    test_client, settings = client
    authed_client = _build_client_with_token(settings, "s3cret-token", monkeypatch)
    r = authed_client.get(
        "/api/folders",
        headers={"Authorization": "Bearer wrong-token"},
    )
    assert r.status_code == 401


def test_endpoint_rejects_non_bearer_scheme(client, monkeypatch: pytest.MonkeyPatch) -> None:
    """A non-``Bearer`` scheme (e.g. ``Basic``) → 401."""
    test_client, settings = client
    authed_client = _build_client_with_token(settings, "s3cret-token", monkeypatch)
    r = authed_client.get(
        "/api/folders",
        headers={"Authorization": "Basic dXNlcjpwYXNz"},
    )
    assert r.status_code == 401


def test_endpoint_rejects_malformed_header(client, monkeypatch: pytest.MonkeyPatch) -> None:
    """A header that's neither a bearer scheme nor a recognised
    alternative (e.g. ``Token abc``) → 401."""
    test_client, settings = client
    authed_client = _build_client_with_token(settings, "s3cret-token", monkeypatch)
    r = authed_client.get(
        "/api/folders",
        headers={"Authorization": "Token s3cret-token"},
    )
    assert r.status_code == 401


def test_endpoint_passes_through_when_token_empty(client, monkeypatch: pytest.MonkeyPatch) -> None:
    """The default ``BFS_API_TOKEN`` is empty — every endpoint
    behaves as in 6.1."""
    test_client, _ = client
    # Make sure the env var is empty (the fixture clears it, but a
    # future test might have leaked it).
    os.environ.pop("BFS_API_TOKEN", None)
    r = test_client.get("/api/folders")
    assert r.status_code == 200


def test_endpoint_passes_through_after_token_cleared(client, monkeypatch: pytest.MonkeyPatch) -> None:
    """Re-clearing the token restores pass-through — operators can
    disable auth by unsetting the env var and restarting."""
    test_client, settings = client
    # First turn auth on, verify the 401.
    authed_client = _build_client_with_token(settings, "s3cret-token", monkeypatch)
    assert authed_client.get("/api/folders").status_code == 401
    # Now turn it off; a fresh app should pass through.
    auth_off_client = _build_client_with_token(settings, None, monkeypatch)
    assert auth_off_client.get("/api/folders").status_code == 200


def test_auth_applies_to_writes(client, monkeypatch: pytest.MonkeyPatch) -> None:
    """Mutating endpoints are also behind the guard — the auth layer
    covers PUT/POST/DELETE the same way as GET."""
    test_client, settings = client
    authed_client = _build_client_with_token(settings, "s3cret-token", monkeypatch)
    # POST without token: 401.
    r = authed_client.post(
        "/api/folders",
        json={"folder_name": "inbox/x", "alias": "X"},
    )
    assert r.status_code == 401
    # PUT without token: 401.
    r = authed_client.put(
        "/api/folders/1",
        json={"id": 1, "folder_name": "inbox/auth-test", "alias": "AUTH"},
    )
    assert r.status_code == 401
    # DELETE without token: 401.
    r = authed_client.delete("/api/folders/1")
    assert r.status_code == 401


def test_auth_applies_to_diagnostics(client, monkeypatch: pytest.MonkeyPatch) -> None:
    """``/api/diagnostics`` is a non-exempt endpoint — it surfaces
    the dispatch pipeline's health and shouldn't be world-readable
    on a remote deployment."""
    test_client, settings = client
    authed_client = _build_client_with_token(settings, "s3cret-token", monkeypatch)
    r = authed_client.get("/api/diagnostics")
    assert r.status_code == 401
    r = authed_client.get(
        "/api/diagnostics",
        headers={"Authorization": "Bearer s3cret-token"},
    )
    assert r.status_code == 200


def test_constant_time_compare_works() -> None:
    """The ``_safe_compare`` helper uses ``hmac.compare_digest`` so
    timing leaks are bounded. Sanity-check it returns the obvious
    boolean values for both equal and unequal inputs."""
    from webapp.routers._deps import _safe_compare

    assert _safe_compare("abc", "abc") is True
    assert _safe_compare("abc", "abd") is False
    assert _safe_compare("", "") is True
    assert _safe_compare("", "x") is False


def test_settings_api_token_reads_from_env(monkeypatch) -> None:
    """``Settings.api_token`` reads ``BFS_API_TOKEN`` from the
    process environment — the dataclass stays at the 6.1 shape and
    tests don't have to rebuild the instance to flip the value."""
    monkeypatch.delenv("BFS_API_TOKEN", raising=False)
    s = Settings(
        base_dir=Path("/tmp/x"), data_dir=Path("/tmp/x/c")
    )
    assert s.api_token == ""
    monkeypatch.setenv("BFS_API_TOKEN", "round-trip")
    assert s.api_token == "round-trip"
    monkeypatch.delenv("BFS_API_TOKEN", raising=False)
    assert s.api_token == ""
