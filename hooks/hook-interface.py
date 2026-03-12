# PyInstaller hook for interface package
from PyInstaller.utils.hooks import collect_data_files, collect_submodules

hiddenimports = collect_submodules("interface")
datas = collect_data_files("interface")
