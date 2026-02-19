"""Qt equivalents of extra widgets from tk_extra_widgets.py.

This file previously contained custom widget implementations that duplicated
functionality provided by Qt's built-in widgets. The custom widgets have been
removed as they were not used in the Qt codebase and their functionality is
already available through standard Qt components:

- RightClickMenu: QLineEdit already provides a standard context menu with
  cut, copy, paste, delete, and select all functionality.

- VerticalScrolledFrame: QScrollArea provides built-in scrollable frame
  functionality.

- ColumnSorterWidget: This custom widget for sorting column entries with
  up/down buttons was not used in the Qt codebase.
"""
