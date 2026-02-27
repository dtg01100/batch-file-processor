# Hook for PyQt6.QtGui - includes platform plugins needed for GUI
from PyInstaller.utils.hooks import collect_data_files, collect_dynamic_libs

datas = collect_data_files('PyQt6.QtGui')
binaries = collect_dynamic_libs('PyQt6.QtGui')

# Add platform-specific plugins that are required for Qt applications to run
datas += collect_data_files('PyQt6.QtSvg')