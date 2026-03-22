# PyInstaller hook for archive package
from PyInstaller.utils.hooks import collect_data_files, collect_submodules

hiddenimports = collect_submodules("archive")
datas = collect_data_files("archive")
