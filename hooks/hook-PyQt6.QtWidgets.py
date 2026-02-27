# Hook for PyQt6.QtWidgets
from PyInstaller.utils.hooks import collect_data_files, collect_dynamic_libs

datas = collect_data_files('PyQt6.QtWidgets')
binaries = collect_dynamic_libs('PyQt6.QtWidgets')