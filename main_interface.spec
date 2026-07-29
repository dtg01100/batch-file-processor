"""
PyInstaller spec file for Batch File Sender application.
This builds a Windows executable with all dependencies bundled.
"""

from pathlib import Path

from PyInstaller.utils.hooks import collect_data_files, collect_dynamic_libs

project_root = Path(SPECPATH).absolute()
hooks_dir = project_root / "hooks"

pyside6_datas = collect_data_files("PySide6")
pyside6_binaries = collect_dynamic_libs("PySide6")

a = Analysis(
    ["main_interface.py"],
    pathex=[str(project_root)],
    binaries=pyside6_binaries,
    datas=pyside6_datas,
    hiddenimports=[
        "PySide6.QtCore",
        "PySide6.QtGui",
        "PySide6.QtWidgets",
        "PySide6.QtPrintSupport",
        "PySide6.QtSvg",
        "PySide6.QtXml",
        "PySide6.QtNetwork",
        "appdirs",
        "lxml",
        "lxml.etree",
        "backend.database.database_obj",
        "backend.ftp_client",
        "backend.smtp_client",
        "backend.copy_backend",
        "backend.email_backend",
        "backend.ftp_backend",
        "backend.http_backend",
        "core.edi.edi_parser",
        "core.edi.edi_splitter",
        "core.edi.inv_fetcher",
        "core.edi.po_fetcher",
        "dispatch",
        "dispatch.orchestrator",
        "dispatch.send_manager",
        "interface.operations.folder_manager",
        "interface.ports",
        "interface.services.reporting_service",
        "interface.qt.app",
        "interface.qt.dialogs.edit_folders_dialog",
        "interface.qt.dialogs.edit_folders.data_extractor",
        "dispatch.converters.convert_to_csv",
        "dispatch.converters.convert_to_estore_einvoice",
        "dispatch.converters.convert_to_estore_einvoice_generic",
        "dispatch.converters.convert_to_fintech",
        "dispatch.converters.convert_to_jolley_custom",
        "dispatch.converters.convert_to_scannerware",
        "dispatch.converters.convert_to_scansheet_type_a",
        "dispatch.converters.convert_to_simplified_csv",
        "dispatch.converters.convert_to_stewarts_custom",
        "dispatch.converters.convert_to_tweaks",
        "dispatch.converters.convert_to_yellowdog_csv",
        "archive",
        "archive.edi_tweaks",
    ],
    hookspath=[str(hooks_dir)],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=None)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    name="Batch File Sender",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=True,
    icon=None,
)
