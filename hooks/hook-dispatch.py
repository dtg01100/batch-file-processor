# PyInstaller hook for dispatch package
from PyInstaller.utils.hooks import collect_submodules

hiddenimports = collect_submodules("dispatch")
