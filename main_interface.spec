# -*- mode: python ; coding: utf-8 -*-
"""
PyInstaller spec file for Batch File Sender application.
This file configures the build process and includes hidden imports
for dynamically loaded modules.

Note: This spec file includes logic to download Windows PyQt6 ICU DLLs
when building on Linux for Windows targets.
"""

import os
import sys
import tempfile
import zipfile
import subprocess
import shutil

block_cipher = None


def get_windows_pyqt6_icu_dlls():
    """
    Download and extract Windows PyQt6 wheel to get ICU DLLs.
    Returns a list of tuples (source_path, dest_dir) for the ICU DLLs.
    """
    icu_dlls = []
    icu_dll_names = ['icuuc.dll', 'icuin.dll', 'icudt.dll']
    
    # Check if we're on Windows with PyQt6 installed
    if sys.platform == 'win32':
        try:
            import PyQt6
            qt_bin_path = os.path.join(os.path.dirname(PyQt6.__file__), "Qt6", "bin")
            if os.path.exists(qt_bin_path):
                for dll in icu_dll_names:
                    dll_path = os.path.join(qt_bin_path, dll)
                    if os.path.exists(dll_path):
                        icu_dlls.append((dll_path, 'PyQt6/Qt6/bin'))
                return icu_dlls
        except ImportError:
            pass
    
    # On Linux/macOS or if Windows PyQt6 not found, download Windows wheel
    temp_dir = tempfile.mkdtemp(prefix='pyqt6_windows_wheel_')
    
    try:
        # Download the Windows PyQt6 wheel
        print("Downloading Windows PyQt6 wheel to extract ICU DLLs...")
        subprocess.run([
            sys.executable, '-m', 'pip', 'download',
            '--only-binary', ':all:',
            '--platform', 'win_amd64',
            '--python-version', '311',
            '--no-deps',
            '-d', temp_dir,
            'PyQt6'
        ], check=True, capture_output=True)
        
        # Find the downloaded wheel
        wheel_files = [f for f in os.listdir(temp_dir) if f.endswith('.whl')]
        if not wheel_files:
            print("Warning: Could not download Windows PyQt6 wheel")
            return []
        
        wheel_path = os.path.join(temp_dir, wheel_files[0])
        print(f"Extracting ICU DLLs from {wheel_files[0]}...")
        
        # Extract the wheel
        extract_dir = os.path.join(temp_dir, 'extracted')
        with zipfile.ZipFile(wheel_path, 'r') as zip_ref:
            zip_ref.extractall(extract_dir)
        
        # Look for ICU DLLs in the extracted wheel
        # They are typically in PyQt6/Qt6/bin/
        possible_paths = [
            os.path.join(extract_dir, 'PyQt6', 'Qt6', 'bin'),
            os.path.join(extract_dir, 'PyQt6', 'Qt', 'bin'),
        ]
        
        for qt_bin_path in possible_paths:
            if os.path.exists(qt_bin_path):
                for dll in icu_dll_names:
                    dll_path = os.path.join(qt_bin_path, dll)
                    if os.path.exists(dll_path):
                        print(f"Found ICU DLL: {dll}")
                        icu_dlls.append((dll_path, 'PyQt6/Qt6/bin'))
                break
        
        if not icu_dlls:
            print("Warning: Could not find ICU DLLs in Windows PyQt6 wheel")
            # List what we found for debugging
            for root, dirs, files in os.walk(extract_dir):
                for f in files:
                    if f.endswith('.dll'):
                        print(f"  Found DLL: {os.path.join(root, f)}")
        
    except subprocess.CalledProcessError as e:
        print(f"Warning: Failed to download Windows PyQt6 wheel: {e}")
    except Exception as e:
        print(f"Warning: Error extracting ICU DLLs: {e}")
    finally:
        # Clean up temp directory but keep the DLLs (they're copied)
        shutil.rmtree(temp_dir, ignore_errors=True)
    
    return icu_dlls


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

# Get ICU DLLs from Windows PyQt6 wheel
icu_binaries = get_windows_pyqt6_icu_dlls()
if icu_binaries:
    print(f"Including {len(icu_binaries)} ICU DLLs from Windows PyQt6")

a = Analysis(
    ['main_interface.py'],
    pathex=[],
    binaries=icu_binaries,
    datas=[
        # Include Qt platform plugins, etc. for PyQt6
        ('interface/qt/**', 'interface/qt'),
        ('hooks/*', 'hooks'),
        
        # Database migrations - include migrations directory and migration files
        # The migrations directory for future use (even if empty)
        ('migrations', 'migrations'),
        # schema.py contains centralized schema definitions needed for migrations
        ('schema.py', '.'),
        # folders_database_migrator.py is the main migration file
        ('folders_database_migrator.py', '.'),
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
