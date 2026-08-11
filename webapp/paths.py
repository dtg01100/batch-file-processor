"""Path rebasing between the desktop database and the webapp base-dir.

The desktop app stored **absolute** folder paths (``C:\\Data\\Incoming\\X``,
``/home/user/incoming``). In Docker those paths don't exist, so import
"strips the root": every configured path is converted to a **relative**
path stored in the database (``incoming/x``, forward slashes). At run time
the webapp resolves each relative path against its configured base-dir
(``BFS_BASE_DIR`` — a mounted volume).

Rules:

- ``to_relative`` strips the drive letter (``C:``), the root separator,
  and any UNC prefix, then normalises backslashes to forward slashes.
  Paths that are already relative pass through unchanged. Empty/None
  values pass through unchanged.
- ``resolve`` joins a stored relative path onto ``base_dir``. Values that
  are already absolute (a path someone configured after import) pass
  through unchanged.

Which columns are rebased is defined by the module-level tuples so the
importer, the runner, and the tests share one source of truth.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any

# Folder-row columns that hold filesystem paths.
FOLDER_PATH_FIELDS: tuple[str, ...] = ("folder_name", "copy_to_directory")

# Oversight/defaults columns that hold filesystem paths.
OVERSIGHT_PATH_FIELDS: tuple[str, ...] = ("logs_directory",)

# Settings-table columns that hold filesystem paths.
SETTINGS_PATH_FIELDS: tuple[str, ...] = ("copy_to_directory",)


def to_relative(path: str | None, _source_platform: str = "Windows") -> str | None:
    """Strip the root from an absolute path, returning a relative path.

    Args:
        path: Absolute (or already-relative) filesystem path.
        _source_platform: ``"Windows"`` or ``"Linux"`` — the platform the
            path came from. Informational: both drive-letter (Windows)
            and root-slash (POSIX) forms are stripped uniformly.

    Returns:
        The root-stripped path with forward slashes, or the input
        unchanged when it is empty/None/already relative.

    """
    if not path:
        return path
    normalised = path.replace("\\", "/").strip()
    if not normalised:
        return path

    # Drive letter: C:/x -> x
    if len(normalised) >= 2 and normalised[1] == ":":
        normalised = normalised[2:]

    # Leading slashes (/, //, UNC //server/share): strip them all.
    normalised = normalised.lstrip("/")

    # Collapse duplicate slashes inside the path (C:\a\\b -> a/b).
    while "//" in normalised:
        normalised = normalised.replace("//", "/")

    if not normalised:
        return path
    return normalised


def resolve(base_dir: str | os.PathLike[str], stored: str | None) -> str:
    """Resolve a stored (relative) path against ``base_dir``.

    Absolute stored values (e.g. a folder path typed by hand after import)
    pass through unchanged.

    Args:
        base_dir: The webapp base directory (the Docker volume root).
        stored: The value stored in the database.

    Returns:
        An absolute filesystem path.

    """
    if not stored:
        return ""
    normalised = stored.replace("\\", "/")
    if normalised.startswith("/"):
        return normalised
    # A bare ".hidden" filename is not a relative traversal; joining a
    # relative path onto the base-dir is the only transform needed here.
    return str(Path(base_dir) / normalised)


def rebase_row(row: dict[str, Any], source_platform: str) -> dict[str, Any]:
    """Return a copy of ``row`` with every path field made relative.

    Args:
        row: A folder-row dict (or oversight dict) from the database.
        source_platform: Platform the paths came from ("Windows"/"Linux").

    Returns:
        A new dict with path fields root-stripped. The input is not
        mutated.

    """
    out = dict(row)
    for field in FOLDER_PATH_FIELDS + OVERSIGHT_PATH_FIELDS:
        if field in out:
            out[field] = to_relative(out.get(field), source_platform)
    return out


def resolve_row(
    row: dict[str, Any], base_dir: str | os.PathLike[str]
) -> dict[str, Any]:
    """Return a copy of a folder row with path fields resolved to absolute.

    Used by the runner just before handing a folder to the dispatcher, so
    the dispatch pipeline (which expects absolute paths) is untouched.

    Args:
        row: A folder-row dict from the database (relative paths).
        base_dir: The webapp base directory.

    Returns:
        A new dict with ``folder_name``/``copy_to_directory`` resolved.

    """
    out = dict(row)
    for field in FOLDER_PATH_FIELDS:
        if field in out:
            out[field] = resolve(base_dir, out.get(field))
    return out
