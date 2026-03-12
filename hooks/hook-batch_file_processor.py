# PyInstaller hook for batch_file_processor package
from PyInstaller.utils.hooks import collect_submodules

hiddenimports = collect_submodules("batch_file_processor")
