"""Stub for 1.47 ``record_error.py``.

Captures errors to an in-memory list instead of writing log files. The harness
inspects ``recorded_errors`` for assertions like "no unexpected error was
recorded" (see plan §"Per-row end-to-end test").
"""

from __future__ import annotations

recorded_errors: list[dict] = []


def reset() -> None:
    """Wipe captured errors. Call between tests for isolation."""
    recorded_errors.clear()


def do(
    run_log,
    errors_log,
    error_message,
    filename,
    error_source,
    threaded: bool = False,
) -> tuple[list, list]:
    """Capture the error tuple into ``recorded_errors`` and return unchanged logs."""
    recorded_errors.append(
        {
            "message": str(error_message),
            "filename": str(filename),
            "source": str(error_source),
        }
    )
    return [], []


__all__ = ["do", "recorded_errors", "reset"]
