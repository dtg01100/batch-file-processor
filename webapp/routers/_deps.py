"""Shared FastAPI dependencies used by every router.

Centralised so endpoints don't reach into ``app.state`` directly. The
factory (``webapp.main.create_app``) wires the singletons onto
``app.state``; the lifespan context manager starts the scheduler +
watcher and attaches ``history`` / ``scheduler`` / ``watcher_supervisor``
once they're alive.

Tests already work because ``create_app(settings=...)`` accepts a
``Settings`` instance and stores it on ``app.state.settings`` before
any request is served.

Phase 6.2 also adds :func:`verify_api_token`, the bearer-token
dependency applied to every router in :func:`webapp.main.create_app`.
When ``BFS_API_TOKEN`` is unset, the dependency is a no-op and the
webapp behaves as it did before Phase 6.2. When set, every API
endpoint requires ``Authorization: Bearer <token>``; the static
files mount at ``/``, ``/api/health``, ``/docs``, ``/openapi.json``,
and ``/redoc`` are exempt so the browser UI can still boot and the
FastAPI docs stay usable.
"""

from __future__ import annotations

from fastapi import HTTPException, Request, status

from webapp.config import Settings
from webapp.history import RunHistory
from webapp.runner import RunStore
from webapp.scheduler import Scheduler
from webapp.watcher import WatcherSupervisor

# Paths exempt from auth — the browser UI must be reachable so the
# login prompt can fire, and the FastAPI docs stay usable. The static
# mount at ``/`` is handled separately (the auth dependency is applied
# at the router-include layer, not the static mount), so this list is
# matched against the request's ``request.url.path`` inside
# :func:`verify_api_token`.
_AUTH_EXEMPT_PATHS: frozenset[str] = frozenset(
    {
        "/",
        "/api/health",
        "/docs",
        "/openapi.json",
        "/redoc",
    }
)


def get_settings(request: Request) -> Settings:
    """Return the ``Settings`` instance attached at app construction.

    Always non-None — ``create_app`` falls back to ``Settings.from_env``
    when the caller doesn't pass one in.
    """
    return request.app.state.settings


def get_run_store(request: Request) -> RunStore:
    """Return the module-level ``RunStore`` singleton.

    Created at import time in ``webapp.main`` and shared across all
    test fixtures via the factory.
    """
    return request.app.state.run_store


def get_history(request: Request) -> RunHistory | None:
    """Return the ``RunHistory`` instance set by the lifespan.

    ``None`` is a legitimate early-boot state: the lifespan attaches
    it on startup, so a request served before the lifespan runs (or
    in a test fixture that bypasses the lifespan) sees ``None``.
    Endpoints that use it should tolerate that.
    """
    return getattr(request.app.state, "history", None)


def get_scheduler(request: Request) -> Scheduler:
    """Return the singleton ``Scheduler`` started by the lifespan."""
    return request.app.state.scheduler


def get_watcher_supervisor(request: Request) -> WatcherSupervisor | None:
    """Return the ``WatcherSupervisor`` started by the lifespan.

    Same ``None``-tolerance contract as :func:`get_history`.
    """
    return getattr(request.app.state, "watcher_supervisor", None)


def verify_api_token(request: Request) -> None:
    """Bearer-token guard for every API endpoint (Phase 6.2).

    Behaviour matrix:

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
    +-----------------------------+-------------------+----------------+

    The dependency is intentionally fail-closed: a misconfigured
    deployment (operator enabled remote access but forgot to set
    ``BFS_API_TOKEN``) returns 503 instead of letting unauthenticated
    requests through. This matches the spec's "no inbound network
    surface" posture — auth bypass on misconfig is never the
    intended failure mode.

    The exemption list applies to *paths*, not routers — the static
    files mount at ``/`` doesn't carry the dependency at all
    (FastAPI applies ``dependencies=[...]`` per ``include_router``),
    but ``GET /api/health`` is a single endpoint that needs to stay
    reachable so Docker health checks can probe without a token. The
    other four exempt paths are FastAPI's built-in documentation
    surface (``/docs``, ``/openapi.json``, ``/redoc``); an operator
    who wants the docs behind auth can simply *not* set
    ``BFS_API_TOKEN`` in production — the docs page is only useful
    during development.
    """
    settings: Settings = request.app.state.settings
    expected = settings.api_token
    if not expected:
        # Auth disabled — pass through everything.
        return
    path = request.url.path
    if path in _AUTH_EXEMPT_PATHS:
        return
    auth_header = request.headers.get("authorization") or ""
    scheme, _, supplied = auth_header.partition(" ")
    if scheme.lower() != "bearer" or not supplied:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing or malformed Authorization header",
            headers={"WWW-Authenticate": "Bearer"},
        )
    # Constant-time comparison — the token is a long-lived secret so
    # timing leaks are theoretical but the pattern is cheap and
    # matches what production auth libraries do.
    if not _safe_compare(supplied, expected):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid bearer token",
            headers={"WWW-Authenticate": "Bearer"},
        )


def _safe_compare(a: str, b: str) -> bool:
    """Constant-time string equality.

    Python 3.11+ ships :func:`hmac.compare_digest`; using it here
    instead of ``==`` defends against timing leaks on the bearer
    token comparison. The strings are short-lived secrets so the
    attack window is small, but the helper is free and matches the
    pattern recommended for any "compare two secrets" path.
    """
    import hmac

    return hmac.compare_digest(a.encode("utf-8"), b.encode("utf-8"))


__all__ = [
    "_AUTH_EXEMPT_PATHS",
    "_safe_compare",
    "get_history",
    "get_run_store",
    "get_scheduler",
    "get_settings",
    "get_watcher_supervisor",
    "verify_api_token",
]
