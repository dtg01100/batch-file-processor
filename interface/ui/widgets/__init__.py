"""UI widgets for the Batch File Sender application.

This package contains reusable UI widget components extracted from the main
application for better maintainability and testability.

Widgets:
    FolderListWidget: Displays active and inactive folder lists with actions
    SearchWidget: Search/filter field for folder list filtering
"""

from interface.ui.widgets.folder_list_widget import FolderListWidget
from interface.ui.widgets.search_widget import SearchWidget

__all__ = [
    "FolderListWidget",
    "SearchWidget",
]
