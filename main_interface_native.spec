# -*- mode: python ; coding: utf-8 -*-
"""
PyInstaller spec file for native platform builds (Linux/macOS/Windows).
This spec file builds for the current platform without cross-compilation.

For Windows builds on Linux/macOS, use main_interface_windows.spec instead.
"""

import os
import sys
from PyInstaller.utils.hooks import collect_data_files, collect_dynamic_libs

block_cipher = None

# Collect PyQt6 data files up front so they can be passed to Analysis datas
qt_datas = collect_data_files('PyQt6')

# Hidden imports for dynamically loaded modules
hidden_imports = [
    # Convert backends (dynamically loaded via importlib.import_module('convert_to_' + format_name))
    'convert_to_csv',
    'convert_to_fintech',
    'convert_to_simplified_csv',
    'convert_to_stewarts_custom',
    'convert_to_yellowdog_csv',
    'convert_to_estore_einvoice',
    'convert_to_estore_einvoice_generic',
    'convert_to_scannerware',
    'convert_to_scansheet_type_a',
    'convert_to_jolley_custom',
    
    # Send backends (dynamically loaded)
    'copy_backend',
    'ftp_backend',
    'email_backend',
    
    # Native dependencies requiring hidden imports
    # Note: pyodbc is skipped on Linux builds as it requires system ODBC libraries
    # It will be included in Windows builds via main_interface_windows.spec
    'greenlet',
    'PIL',
    'lxml',
    'lxml.etree',
    'lxml._elementpath',
    
    # Dispatch modules
    'dispatch',
    'dispatch.hash_utils',
    'dispatch.file_utils',
    'dispatch.interfaces',
    'dispatch.edi_validator',
    'dispatch.send_manager',
    'dispatch.error_handler',
    'dispatch.orchestrator',
    'dispatch.log_sender',
    'dispatch.print_service',
    'dispatch.processed_files_tracker',
    
    # Backend modules
    'backend',
    'backend.protocols',
    'backend.file_operations',
    'backend.ftp_client',
    'backend.smtp_client',
    
    # Core modules
    'core.edi',
    'core.edi.edi_parser',
    'core.edi.edi_splitter',
    'core.edi.inv_fetcher',
    'core.edi.po_fetcher',
    'core.edi.c_rec_generator',
    'core.edi.upc_utils',
    
    # Interface modules
    'interface',
    'interface.database',
    'interface.database.database_obj',
    'interface.operations',
    'interface.operations.folder_manager',
    'interface.operations.folder_data_extractor',
    'interface.validation',
    'interface.validation.email_validator',
    'interface.validation.folder_settings_validator',
    'interface.models',
    'interface.models.folder_configuration',
    'interface.services',
    'interface.services.ftp_service',
    'interface.ui',
    'interface.ui.dialogs',
    'interface.ui.dialogs.edit_folders_dialog',
    
    # Other utility modules
    'utils',
    'record_error',
    'doingstuffoverlay',
    'tk_extra_widgets',
    'dialog',
    'create_database',
    'database_import',
    'folders_database_migrator',
    'backup_increment',
    'batch_log_sender',
    'print_run_log',
    'resend_interface',
    'query_runner',
    'mover',
    'clear_old_files',
    'rclick_menu',
    
    # PyQt6 modules (required for GUI functionality)
    'PyQt6',
    'PyQt6.QtCore',
    'PyQt6.QtGui',
    'PyQt6.QtWidgets',
    'PyQt6.QtPrintSupport',
    'PyQt6.QtSvg',
    'PyQt6.QtSvgWidgets',
    'PyQt6.QtXml',
    'PyQt6.QtNetwork',
]

a = Analysis(
    ['main_interface.py'],
    pathex=[],
    binaries=[],
    datas=[
        # Include Qt platform plugins, etc. for PyQt6
        ('interface/qt/**', 'interface/qt'),
        ('hooks/*', 'hooks'),
        
        # Database migrations - include migrations directory and migration files
        ('migrations', 'migrations'),
        # schema.py contains centralized schema definitions needed for migrations
        ('schema.py', '.'),
        # folders_database_migrator.py is the main migration file
        ('folders_database_migrator.py', '.'),
    ] + qt_datas,
    hiddenimports=hidden_imports,
    hookspath=['hooks'],
    hooksconfig={},
    runtime_hooks=[],
    excludes=['pyodbc'],  # Exclude pyodbc on Linux - requires system ODBC libraries
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)
pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='Batch File Sender',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=True,  # Keep console=True to allow --self-test to output to console
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=False,
    upx_exclude=[],
    name='Batch File Sender',
)
