# -*- mode: python ; coding: utf-8 -*-
"""
PyInstaller spec file for Batch File Sender application.
This builds a Windows executable with all dependencies bundled.
"""

import os
import sys
from pathlib import Path

# Project root
project_root = Path(SPECPATH).absolute()

# Add hooks directory
hooks_dir = project_root / "hooks"

# Collect all data files and binaries
added_files = []

# Analysis configuration
a = Analysis(
    ['main_interface.py'],
    pathex=[str(project_root)],
    binaries=[],
    datas=added_files,
    hiddenimports=[
        # PyQt6 modules
        'PyQt6.sip',
        'PyQt6.QtCore',
        'PyQt6.QtGui',
        'PyQt6.QtWidgets',
        'PyQt6.QtPrintSupport',
        'PyQt6.QtSvg',
        'PyQt6.QtXml',
        'PyQt6.QtNetwork',
        # Project packages
        'interface',
        'interface.qt',
        'interface.qt.app',
        'interface.database',
        'interface.database.database_obj',
        'interface.operations',
        'interface.operations.folder_manager',
        'interface.validation',
        'interface.validation.email_validator',
        'interface.models',
        'interface.form',
        'interface.services',
        'interface.plugins',
        'core',
        'core.exceptions',
        'dispatch',
        'dispatch.orchestrator',
        'dispatch.send_manager',
        'dispatch.error_handler',
        'dispatch.log_sender',
        'dispatch.edi_validator',
        'dispatch.compatibility',
        'dispatch.file_utils',
        'dispatch.hash_utils',
        'dispatch.interfaces',
        'dispatch.print_service',
        'dispatch.processed_files_tracker',
        'dispatch.feature_flags',
        'backend',
        'backend.file_operations',
        'backend.ftp_client',
        'backend.smtp_client',
        'backend.protocols',
        # Root-level application modules (dynamically imported, not auto-detected by PyInstaller)
        'utils',
        'schema',
        'create_database',
        'backup_increment',
        'batch_log_sender',
        'print_run_log',
        'folders_database_migrator',
        'mover',
        'convert_base',
        'record_error',
        'clear_old_files',
        'rclick_menu',
        # Interface sub-modules
        'interface.database.sqlite_wrapper',
        'migrations.add_plugin_config_column',
        # Dynamic converters
        'convert_to_csv',
        'convert_to_estore_einvoice',
        'convert_to_estore_einvoice_generic',
        'convert_to_fintech',
        'convert_to_jolley_custom',
        'convert_to_scannerware',
        'convert_to_scansheet_type_a',
        'convert_to_simplified_csv',
        'convert_to_stewarts_custom',
        'convert_to_yellowdog_csv',
        # Dynamic backends
        'copy_backend',
        'email_backend',
        'ftp_backend',
        # Third-party libraries
        'lxml',
        'lxml.etree',
        'lxml._elementpath',
        'PIL',
        'PIL._imaging',
        'PIL._imagingft',
        'PIL._imagingtk',
        'requests',
        'certifi',
        'chardet',
        'charset_normalizer',
        'idna',
        'urllib3',
        'dateutil',
        'dateutil.parser',
        'dateutil.tz',
        'dateutil.zoneinfo',
        'pytz',
        'openpyxl',
        'et_xmlfile',
        'jinja2',
        'markupsafe',
        'premailer',
        'cssselect',
        'cssutils',
        'cachetools',
        'rapidfuzz',
        'thefuzz',
        'thefuzz.fuzz',
        'thefuzz.process',
        'Levenshtein',
        'barcode',
        'barcode.writer',
        'barcode.codex',
        'tendo',
        'tendo.singleton',
        'platformdirs',
        'appdirs',
        'binaryornot',
        'toml',
        'packaging',
        'six',
        'future',
        'pefile',
        'macholib',
        'altgraph',
    ],
    hookspath=[str(hooks_dir)],
    hooksconfig={},
    runtime_hooks=[],
    excludes=['sqlalchemy', 'alembic'],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=None,
    noarchive=False,
)

# Remove duplicate entries
pyz = PYZ(a.pure, a.zipped_data, cipher=None)

# Create the executable
exe = EXE(
    pyz,
    a.scripts,
    [],
    [],
    name='Batch File Sender',
    exclude_binaries=True,
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=True,  # No console window for GUI app
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    # Windows specific options
    icon=None,  # Add icon path here if available
)

# Create the bundled app structure
coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='Batch File Sender',
)
