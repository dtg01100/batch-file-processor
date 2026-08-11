"""Batch File Sender — local webapp.

The webapp-pivot replacement for the Qt desktop UI. It reuses the existing
Qt-free core (``dispatch/``, ``backend/``, ``core/``, ``interface/operations``)
and adds a FastAPI server + browser UI.

Key concepts:

- **base-dir** (``BFS_BASE_DIR``): the root every configured folder's
  relative path resolves against. In Docker this is the mounted volume.
- **data-dir** (``BFS_DATA_DIR``): where ``folders.db`` lives (defaults to
  ``<base-dir>/config``).
- **Import**: upload a legacy desktop ``folders.db``; its absolute folder
  paths are stripped of their roots and stored relative to the base-dir.
"""

__version__ = "0.1.0"
