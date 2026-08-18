"""Shared FastAPI dependencies used by every router.

Centralised so endpoints don't reach into ``app.state`` directly. The
factory (``webapp.main.create_app``) wires the singletons onto
``app.state``; the lifespan context manager starts the scheduler +
watcher and attaches ``history`` / ``scheduler`` / ``watcher_supervisor``
once they're alive.

Tests already work because ``create_app(settings=...)`` accepts a
``Settings`` instance and stores it on ``app.state.settings`` before
any request is served.
"""

from __future__ import annotations

from fastapi import Request

from webapp.config import Settings
from webapp.history import RunHistory
from webapp.runner import RunStore
from webapp.scheduler import Scheduler
from webapp.watcher import WatcherSupervisor


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
