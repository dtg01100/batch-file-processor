"""Nuitka build configuration for Batch File Sender.

Phase 5 of plans/QT6_AND_MODERN_PYTHON_MIGRATION_PLAN.md.
Companion to main_interface.spec (the PyInstaller spec). The
build script (build_linux.py, build_windows.py) reads this
module and constructs the python -m nuitka invocation from
these lists.

The lists are the single source of truth for what needs to be
bundled with the application. Tests in
tests/unit/test_nuitka_config.py assert that the converters,
data dirs, and PySide6 plugin are all covered.
"""

from __future__ import annotations

# All `dispatch.converters.convert_to_*` modules are loaded by
# name string at runtime via `importlib.import_module`. PyInstaller
# hookspath figured this out automatically; Nuitka needs the
# whole package listed explicitly so all converters are bundled.
INCLUDED_PACKAGES: tuple[str, ...] = (
    "dispatch",
    "dispatch.converters",
    "dispatch.pipeline",
    "interface",
    "interface.qt",
    "interface.qt.dialogs",
    "interface.qt.dialogs.edit_folders",
    "interface.qt.services",
    "interface.qt.widgets",
    "interface.form",
    "interface.operations",
    "interface.plugins",
    "interface.services",
    "core",
    "core.edi",
    "backend",
    "adapters",
    "adapters.sqlite",
    "adapters.sqlite.repositories",
    "adapters.inmemory",
    "adapters.inmemory.repositories",
    "adapters.db2ssh",
    "migrations",
)

# Modules that are imported via `importlib.import_module` with a
# string name (e.g. plugin auto-discovery via pkgutil) and would
# otherwise be missed by Nuitka's static analysis. Add each such
# module here.
INCLUDED_MODULES: tuple[str, ...] = (
    "appdirs",
    "lxml._elementpath",
    "thefuzz.process",
    "rapidfuzz.process",
)

# Data directories that need to ship next to the binary. Same
# paths the PyInstaller spec collects via `collect_data_files`.
INCLUDED_DATA_DIRS: tuple[tuple[str, str], ...] = (
    ("edi_formats", "edi_formats"),
    # docs/ is large and primarily for development; ship only the
    # user-facing subset if any. Leaving commented until we audit.
    # ("docs", "docs"),
)

# Files that need to ship individually (one-to-one path mapping).
INCLUDED_DATA_FILES: tuple[str, ...] = (
    # Add per-file entries here as needed.
)

# Nuitka plugins to enable. PySide6 is the critical one — it
# handles Qt's dynamic imports, shiboken binding init, and Qt
# platform plugin discovery. Without it, the binary won't start.
ENABLED_PLUGINS: tuple[str, ...] = ("pyside6",)

# Application metadata used for the Windows PE header.
COMPANY_NAME = "Capital Candy"
PRODUCT_NAME = "Batch File Sender"
FILE_VERSION = "1.0.0"
PRODUCT_VERSION = "1.0.0"

# Entry point: the script Nuitka compiles.
ENTRY_POINT = "main_interface.py"

# Output filename for onefile builds. Has no effect on standalone
# (folder) builds.
OUTPUT_FILENAME_WINDOWS = "Batch File Sender.exe"

# Build flavor. Plan decision N1: onefile. Decision N3: standalone
# (folder) for Linux dev smoke tests, onefile for shipping Windows.
# We support both via the build_linux.py / build_windows.py
# scripts; this constant is the default.
DEFAULT_FLAVOR_WINDOWS = "onefile"
DEFAULT_FLAVOR_LINUX = "standalone"
