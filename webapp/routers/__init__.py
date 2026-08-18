"""FastAPI routers for the Batch File Sender webapp.

Each module owns one domain (folders, runs, errors, ...) and exposes a
``router`` (an ``fastapi.APIRouter``). ``webapp.main.create_app`` calls
``app.include_router(router)`` for each one.

Why split? ``webapp/main.py`` grew to 1,350 lines / 52 endpoints with a
flat ``create_app()`` registry. That file now only owns:

  * the FastAPI app factory (``create_app(settings: Settings | None)``)
  * the lifespan context manager (start/stop the scheduler + watcher)
  * the static-files mount for the browser UI
  * the ``app = create_app()`` module instance for ``uvicorn webapp.main:app``

Everything that *does* something lives in a router below.

Conventions for new endpoints in this package:

  * Use ``Depends(get_settings)`` (from ``_deps``) instead of reading
    ``app.state.settings`` directly. Keeps tests honest and avoids the
    hidden dependency on the factory wiring.
  * Use ``Depends(get_run_store)`` / ``get_history`` /
    ``get_watcher_supervisor`` for the singletons ``create_app`` wires
    onto ``app.state``.
  * Use the response builders in ``_helpers`` (``folder_summary``,
    ``config_payload``, ``run_summary``, ``dataclass_to_dict``) so two
    endpoints that build the same payload don't drift apart.
"""
