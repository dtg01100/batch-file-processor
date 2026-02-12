# PyInstaller hook for interface package
from PyInstaller.utils.hooks import collect_submodules, collect_data_files

hiddenimports = collect_submodules("interface")
datas = collect_data_files("interface")
