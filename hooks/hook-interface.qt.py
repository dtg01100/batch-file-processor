# Hook for the interface.qt package
from PyInstaller.utils.hooks import collect_data_files, collect_submodules

# Collect all submodules of interface.qt
hiddenimports = collect_submodules('interface.qt')

# Collect all data files for the Qt interface
datas = collect_data_files('interface.qt')