"""Deprecated demo shim — right-click menu demo was Tk-based and has been replaced by the Qt implementation.

This module now re-exports the Qt `RightClickMenu` where possible to preserve import compatibility
for any remaining legacy code. Importing this module in a non-GUI/test environment is a no-op.
"""

try:
    # Prefer Qt implementation (keeps API surface for tests that import this demo)
    from interface.qt.widgets.extra_widgets import RightClickMenu  # type: ignore
except Exception:  # pragma: no cover - best-effort compatibility shim
    # Fallback minimal shim matching the callable API used in legacy demos/tests
    class RightClickMenu(object):
        def __init__(self, widget=None):
            self._widget = widget
        def __call__(self, event=None):
            return None

if __name__ == '__main__':
    print("rclick_menu demo removed — use the Qt demo in interface/qt/widgets instead.")