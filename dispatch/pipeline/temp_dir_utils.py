from __future__ import annotations

from typing import Any


def _extract_pipeline_temp_dirs(folder: dict, context: Any | None) -> list[str] | None:
    if context is not None and hasattr(context, "temp_dirs"):
        temp_dirs = getattr(context, "temp_dirs")
        if isinstance(temp_dirs, list):
            return temp_dirs

    temp_dirs = folder.get("_pipeline_temp_dirs")
    if isinstance(temp_dirs, list):
        return temp_dirs

    return None


def create_pipeline_temp_dir(
    prefix: str, folder: dict, context: Any | None
) -> tuple[str, list[str] | None]:
    """Create a temporary pipeline directory and register it in tracking state."""
    import tempfile

    temp_dir = tempfile.mkdtemp(prefix=f"{prefix}_")
    temp_dirs = _extract_pipeline_temp_dirs(folder, context)
    if temp_dirs is not None:
        temp_dirs.append(temp_dir)
    return temp_dir, temp_dirs


def cleanup_pipeline_temp_dir(temp_dir: str, temp_dirs: list[str] | None) -> None:
    """Remove a temporary pipeline directory and untrack it if necessary."""
    import shutil

    shutil.rmtree(temp_dir, ignore_errors=True)
    if temp_dirs is not None and temp_dir in temp_dirs:
        temp_dirs.remove(temp_dir)
