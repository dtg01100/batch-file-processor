# -*- mode: python ; coding: utf-8 -*-
"""
PyInstaller spec file for Batch File Sender application.
This builds a Windows executable with all dependencies bundled.
"""

from pathlib import Path

from PyInstaller.utils.hooks import collect_data_files, collect_dynamic_libs

# Project root
project_root = Path(SPECPATH).absolute()

# Add hooks directory
hooks_dir = project_root / "hooks"

# Collect the PyQt6 runtime with upstream PyInstaller helpers so Windows
# bundles include the full Qt runtime tree and dependent DLLs automatically.
pyqt_runtime_datas = collect_data_files("PyQt6", subdir="Qt6")
pyqt_runtime_binaries = collect_dynamic_libs("PyQt6")

# Collect all data files and binaries
added_files = pyqt_runtime_datas

# Analysis configuration
a = Analysis(
    ['main_interface.py'],
    pathex=[str(project_root)],
    binaries=pyqt_runtime_binaries,
    datas=added_files,
    hiddenimports=[
        # PyQt6 entry points
        'PyQt6.sip',
        'PyQt6.QtCore',
        'PyQt6.QtGui',
        'PyQt6.QtWidgets',
        'PyQt6.QtDBus',
        'PyQt6.QtPrintSupport',
        'PyQt6.QtSvg',
        'PyQt6.QtXml',
        'PyQt6.QtNetwork',
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
    ],
    hookspath=[str(hooks_dir)],
    hooksconfig={},
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
    upx=False,
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
    upx=False,
    upx_exclude=[],
    name='Batch File Sender',
)
