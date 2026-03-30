# PyInstaller hook for adapters package
from PyInstaller.utils.hooks import collect_submodules

hiddenimports = collect_submodules("adapters")
