# PyInstaller hook for core package
from PyInstaller.utils.hooks import collect_submodules

hiddenimports = collect_submodules("core")
