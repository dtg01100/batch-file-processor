# -*- mode: python ; coding: utf-8 -*-
"""
PyInstaller spec file for Batch File Sender application.
This file configures the build process and includes hidden imports
for dynamically loaded modules.
"""

import os

block_cipher = None

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
    'pyodbc',
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
    'edi_tweaks',
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
    'mtc_edi_validator',
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
    'sip',
]

a = Analysis(
    ['main_interface.py'],
    pathex=[],
    binaries=[],
    datas=[
        # Include Qt platform plugins, etc. for PyQt6
        ('interface/qt/**', 'interface/qt'),
        ('hooks/*', 'hooks'),
    ],
    hiddenimports=hidden_imports,
    hookspath=['hooks'],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

# Add Qt platform plugins and other necessary Qt files after analysis is complete
# This ensures all Qt dependencies are properly bundled
from PyInstaller.utils.hooks import collect_data_files
import PyQt6

# Collect Qt platform plugins automatically
qt_plugins_path = os.path.join(os.path.dirname(PyQt6.__file__), "Qt", "plugins")
if os.path.exists(qt_plugins_path):
    a.datas += [(qt_plugins_path, "PyQt6/Qt/plugins")]

# Collect Qt binary files (DLLs) such as Qt6Core.dll and ICU libraries
qt_bin_path = os.path.join(os.path.dirname(PyQt6.__file__), "Qt", "bin")
if os.path.exists(qt_bin_path):
    a.datas += [(qt_bin_path, "PyQt6/Qt/bin")]

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
