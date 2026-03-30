# PyInstaller hook for scripts package
from PyInstaller.utils.hooks import collect_submodules

hiddenimports = collect_submodules("scripts")
