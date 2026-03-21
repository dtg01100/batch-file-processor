# -*- mode: python ; coding: utf-8 -*-
"""
PyInstaller spec file for Batch File Sender application.
This builds a Windows executable with all dependencies bundled.
"""

from pathlib import Path

from PyInstaller.utils.hooks import collect_data_files, collect_dynamic_libs

project_root = Path(SPECPATH).absolute()
hooks_dir = project_root / "hooks"

pyqt_datas = collect_data_files("PyQt5")
pyqt_binaries = collect_dynamic_libs("PyQt5")

a = Analysis(
    ['main_interface.py'],
    pathex=[str(project_root)],
    binaries=pyqt_binaries,
    datas=pyqt_datas,
    hiddenimports=[
        'PyQt5.sip',
        'PyQt5.QtCore',
        'PyQt5.QtGui',
        'PyQt5.QtWidgets',
        'PyQt5.QtPrintSupport',
        'PyQt5.QtSvg',
        'PyQt5.QtXml',
        'PyQt5.QtNetwork',
        'dispatch.converters.convert_to_csv',
        'dispatch.converters.convert_to_estore_einvoice',
        'dispatch.converters.convert_to_estore_einvoice_generic',
        'dispatch.converters.convert_to_fintech',
        'dispatch.converters.convert_to_jolley_custom',
        'dispatch.converters.convert_to_scannerware',
        'dispatch.converters.convert_to_scansheet_type_a',
        'dispatch.converters.convert_to_simplified_csv',
        'dispatch.converters.convert_to_stewarts_custom',
        'dispatch.converters.convert_to_yellowdog_csv',
        'backend.copy_backend',
        'backend.email_backend',
        'backend.ftp_backend',
        'archive',
        'archive.edi_tweaks',
    ],
    hookspath=[str(hooks_dir)],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=None)

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
    console=True,
    icon=None,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=False,
    name='Batch File Sender',
)
