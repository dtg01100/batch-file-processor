from PyInstaller.utils.hooks import collect_data_files, collect_dynamic_libs, collect_system_data_files, copy_metadata
import os
import sys
import PyQt6

# Collect all necessary PyQt6 data files
datas = collect_data_files('PyQt6')

# Collect all necessary PyQt6 binaries
binaries = collect_dynamic_libs('PyQt6')

# Include platform-specific Qt plugins
datas += collect_data_files('PyQt6.QtSvg')
datas += collect_data_files('PyQt6.QtPrintSupport')

# Include additional Qt platform files
datas += collect_data_files('PyQt6.QtQml')

# Collect Qt platform plugins (needed for GUI to work)
hiddenimports = [
    'PyQt6.sip',
    'PyQt6.QtCore',
    'PyQt6.QtGui',
    'PyQt6.QtWidgets',
    'PyQt6.QtPrintSupport',
    'PyQt6.QtSvg',
    'PyQt6.QtXml',
    'PyQt6.QtNetwork',
]

# Collect Qt bin DLLs (e.g., Qt6Core.dll, icu*.dll) to ensure they are bundled on Windows.
# This is critical for PyQt6 to work - ICU libraries are required by Qt6Core.dll
qt_bin_path = os.path.join(os.path.dirname(PyQt6.__file__), "Qt6", "bin")
if os.path.exists(qt_bin_path):
    # Explicitly collect all DLLs from Qt6/bin directory
    for filename in os.listdir(qt_bin_path):
        if filename.endswith('.dll'):
            datas.append((os.path.join(qt_bin_path, filename), 'PyQt6/Qt6/bin'))
