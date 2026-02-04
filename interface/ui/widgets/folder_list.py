"""
Folder list widget module for PyQt6 interface.

This module contains the FolderListWidget class which displays
and manages the list of folders with search/filter functionality.
"""

from typing import TYPE_CHECKING, Optional, List, Dict, Callable, Any

from PyQt6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLineEdit,
    QPushButton,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QFrame,
    QMessageBox,
    QInputDialog,
    QFileDialog,
    QSplitter,
    QSizePolicy,
    QListView,
)
from PyQt6.QtCore import pyqtSignal as Signal, Qt, QSize, QAbstractListModel, QModelIndex

from thefuzz import process as fuzzy_process
from operator import itemgetter

if TYPE_CHECKING:
    from interface.database.database_manager import DatabaseManager
    from interface.ui.delegates.folder_card_delegate import FolderCardDelegate

if TYPE_CHECKING:
    from interface.database.database_manager import DatabaseManager


class FolderModel(QAbstractListModel):
    """Model to hold folder data for the list view."""
    
    def __init__(self, folders: List[Dict] = None, parent=None):
        super().__init__(parent)
        self._folders = folders or []
        
    def rowCount(self, parent=QModelIndex()):
        """Return the number of rows."""
        return len(self._folders)
        
    def data(self, index, role=Qt.ItemDataRole.DisplayRole):
        """Return data for the given index and role."""
        if not index.isValid() or index.row() >= len(self._folders):
            return None
            
        folder = self._folders[index.row()]
        
        if role == Qt.ItemDataRole.UserRole:
            return folder
        elif role == Qt.ItemDataRole.DisplayRole:
            return folder.get('alias', 'Unknown')
            
        return None
        
    def setData(self, index, value, role=Qt.ItemDataRole.EditRole):
        """Set data for the given index and role."""
        if not index.isValid() or index.row() >= len(self._folders):
            return False
            
        if role == Qt.ItemDataRole.UserRole:
            self._folders[index.row()] = value
            self.dataChanged.emit(index, index, [role])
            return True
            
        return False
        
    def flags(self, index):
        """Return item flags for the given index."""
        if not index.isValid():
            return Qt.ItemFlag.NoItemFlags
        return Qt.ItemFlag.ItemIsEnabled | Qt.ItemFlag.ItemIsSelectable
        
    def reset_model(self, folders: List[Dict]):
        """Reset the model with new folder data."""
        self.beginResetModel()
        self._folders = folders
        self.endResetModel()


class FolderListWidget(QWidget):
    """Widget for displaying and managing folder list with inactive/active split.

    This widget displays inactive and active folders with:
    - Search/filter field with fuzzy matching
    - Inactive folders list (left side)
    - Active folders list (right side)
    - Buttons for each folder: Edit, Toggle Active, Delete, Send
    - Real-time filtering as user types
    """

    # Signals
    folder_edit_requested = Signal(int)  # folder_id
    folder_toggle_active = Signal(int)  # folder_id
    folder_delete_requested = Signal(int)  # folder_id
    folder_send_requested = Signal(int)  # folder_id

    def __init__(
        self,
        db_manager: "DatabaseManager",
        parent: Optional[QWidget] = None,
        on_edit_folder: Optional[Callable[[int], None]] = None,
        on_toggle_active: Optional[Callable[[int], None]] = None,
        on_delete_folder: Optional[Callable[[int], None]] = None,
        on_send_folder: Optional[Callable[[int], None]] = None,
        filter_query: str = "",
    ):
        """
        Initialize the folder list widget.

        Args:
            db_manager: Database manager instance.
            parent: Parent widget.
            on_edit_folder: Callback when edit button is clicked.
            on_toggle_active: Callback when toggle active button is clicked.
            on_delete_folder: Callback when delete button is clicked.
            on_send_folder: Callback when send button is clicked.
            filter_query: Initial filter query string.
        """
        super().__init__(parent)

        self._db_manager = db_manager
        self._on_edit_folder = on_edit_folder
        self._on_toggle_active = on_toggle_active
        self._on_delete_folder = on_delete_folder
        self._on_send_folder = on_send_folder
        self._filter_query = filter_query

        self._active_folders: List[Dict] = []
        self._inactive_folders: List[Dict] = []

        self._setup_ui()
        self.refresh()

    def _setup_ui(self) -> None:
        """Setup the widget UI."""
        # Main layout
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(5)

        # Search frame
        search_layout = QHBoxLayout()

        filter_label = QLabel("Filter:")
        search_layout.addWidget(filter_label)

        self._filter_field = QLineEdit()
        self._filter_field.setPlaceholderText("Type to filter folders...")
        self._filter_field.setText(self._filter_query)
        self._filter_field.textChanged.connect(self._on_filter_changed)
        search_layout.addWidget(self._filter_field, stretch=1)

        update_filter_btn = QPushButton("Update Filter")
        update_filter_btn.clicked.connect(self.refresh)
        search_layout.addWidget(update_filter_btn)

        layout.addLayout(search_layout)

        # Count label
        self._count_label = QLabel()
        self._count_label.setAlignment(Qt.AlignmentFlag.AlignRight)
        layout.addWidget(self._count_label)

        # Split view for inactive/active (inactive on left, active on right)
        splitter = QSplitter(Qt.Orientation.Horizontal)

        # Inactive folders section
        inactive_frame = QFrame()
        inactive_frame.setFrameStyle(QFrame.Shape.StyledPanel | QFrame.Shadow.Sunken)
        inactive_layout = QVBoxLayout(inactive_frame)
        inactive_layout.setContentsMargins(5, 5, 5, 5)

        inactive_label = QLabel("Inactive Folders")
        inactive_label.setStyleSheet("font-weight: bold;")
        inactive_layout.addWidget(inactive_label)

        self._inactive_list = QListView()
        self._inactive_list.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        # Disable selection to allow button clicks to work properly with delegate
        self._inactive_list.setSelectionMode(QListView.SelectionMode.NoSelection)
        inactive_layout.addWidget(self._inactive_list, stretch=1)

        # Create models for the list views
        self._inactive_model = FolderModel()
        self._active_model = FolderModel()
        
        # Create delegate instance
        from interface.ui.delegates.folder_card_delegate import FolderCardDelegate
        self._delegate = FolderCardDelegate()
        
        # Connect delegate signals to our signals
        self._delegate.edit_clicked.connect(self._on_edit_folder_clicked)
        self._delegate.toggle_active_clicked.connect(self._on_toggle_active_clicked)
        self._delegate.delete_clicked.connect(self._on_delete_folder_clicked)
        self._delegate.send_clicked.connect(self._on_send_folder_clicked)
        
        # Set models and delegates
        self._inactive_list.setModel(self._inactive_model)
        self._inactive_list.setItemDelegate(self._delegate)

        splitter.addWidget(inactive_frame)

        # Active folders section
        active_frame = QFrame()
        active_frame.setFrameStyle(QFrame.Shape.StyledPanel | QFrame.Shadow.Sunken)
        active_layout = QVBoxLayout(active_frame)
        active_layout.setContentsMargins(5, 5, 5, 5)

        active_label = QLabel("Active Folders")
        active_label.setStyleSheet("font-weight: bold;")
        active_layout.addWidget(active_label)

        self._active_list = QListView()
        self._active_list.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        # Disable selection to allow button clicks to work properly with delegate
        self._active_list.setSelectionMode(QListView.SelectionMode.NoSelection)
        active_layout.addWidget(self._active_list, stretch=1)

        # Set model and delegate for active list
        self._active_list.setModel(self._active_model)
        self._active_list.setItemDelegate(self._delegate)

        splitter.addWidget(active_frame)

        layout.addWidget(splitter, stretch=1)

        # Set splitter stretch factors for proportional sizing
        splitter.setStretchFactor(0, 1)
        splitter.setStretchFactor(1, 1)

    def _load_folders(self) -> tuple[List[Dict], List[Dict], List[Dict]]:
        """Load folders from database.

        Returns:
            Tuple of (all_folders, active_folders, inactive_folders).
        """
        if self._db_manager.folders_table is None:
            print(f"[DEBUG] folders_table is None! DB path: {getattr(self._db_manager, '_database_path', 'unknown')}")
            return [], [], []

        all_folders = list(self._db_manager.folders_table.find(order_by="alias"))
        print(f"[DEBUG] Loaded {len(all_folders)} folders from database")
        
        active_folders = []
        inactive_folders = []

        for f in all_folders:
            # Handle cases where folder_is_active might be stored as different types
            is_active_raw = f.get("folder_is_active", "False")

            # Normalize the value to a boolean-like string for comparison
            if is_active_raw is True or str(is_active_raw).lower() in (
                "true",
                "1",
                "yes",
            ):
                active_folders.append(f)
            else:
                inactive_folders.append(f)

        print(f"[DEBUG] Active: {len(active_folders)}, Inactive: {len(inactive_folders)}")
        return all_folders, active_folders, inactive_folders

    def _filter_folders(
        self,
        all_folders: List[Dict],
        active_folders: List[Dict],
        inactive_folders: List[Dict],
        query: str,
    ) -> tuple:
        """Filter folders by search query using fuzzy matching.

        Args:
            all_folders: List of all folder dictionaries.
            active_folders: List of active folder dictionaries.
            inactive_folders: List of inactive folder dictionaries.
            query: Search query string.

        Returns:
            Tuple of (filtered_all, filtered_active, filtered_inactive).
        """
        if not query or query.strip() == "":
            return all_folders, active_folders, inactive_folders

        try:
            # Build list of aliases for fuzzy matching, ensuring aliases exist
            folder_alias_list = []
            for folder in all_folders:
                alias = folder.get("alias")
                if alias and isinstance(alias, str):
                    folder_alias_list.append(alias)

            # If no valid aliases, return all folders
            if not folder_alias_list:
                return all_folders, active_folders, inactive_folders

            # Perform fuzzy matching
            fuzzy_results = list(
                fuzzy_process.extractWithoutOrder(
                    query, folder_alias_list, score_cutoff=80
                )
            )

            # Sort by score (descending)
            fuzzy_results.sort(key=itemgetter(1), reverse=True)

            matching_aliases = [result[0] for result in fuzzy_results]

            def filter_by_alias(folders: List[Dict], aliases: List[str]) -> List[Dict]:
                """Filter folders by alias list."""
                return [f for f in folders if f.get("alias") in aliases]

            filtered_all = filter_by_alias(all_folders, matching_aliases)
            filtered_active = filter_by_alias(active_folders, matching_aliases)
            filtered_inactive = filter_by_alias(inactive_folders, matching_aliases)

            return filtered_all, filtered_active, filtered_inactive
        except Exception as e:
            # If filtering fails, return all folders to prevent crashes
            print(f"Error filtering folders: {str(e)}")
            return all_folders, active_folders, inactive_folders



    def _on_filter_changed(self, query: str) -> None:
        """Handle filter field changes."""
        self._filter_query = query
        self.refresh()

    def _on_edit_folder_clicked(self, folder_id: int) -> None:
        """Handle edit folder button click."""
        callback = self._on_edit_folder
        if callback:
            callback(folder_id)
        self.folder_edit_requested.emit(folder_id)

    def _on_toggle_active_clicked(self, folder_id: int) -> None:
        """Handle toggle active button click."""
        callback = self._on_toggle_active
        if callback:
            callback(folder_id)
        self.folder_toggle_active.emit(folder_id)

    def _on_delete_folder_clicked(self, folder_id: int) -> None:
        """Handle delete folder button click."""
        if self._db_manager.folders_table is None:
            return

        folder = self._db_manager.folders_table.find_one(id=folder_id)
        if folder:
            alias = folder.get("alias", "Unknown")
            reply = QMessageBox.question(
                self,
                "Confirm Delete",
                f"Are you sure you want to remove the folder {alias}?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            )
            if reply == QMessageBox.StandardButton.Yes:
                callback = self._on_delete_folder
                if callback:
                    callback(folder_id)
                self.folder_delete_requested.emit(folder_id)

    def _on_send_folder_clicked(self, folder_id: int) -> None:
        """Handle send folder button click."""
        callback = self._on_send_folder
        if callback:
            callback(folder_id)
        self.folder_send_requested.emit(folder_id)

    def set_filter(self, query: str) -> None:
        """Set the folder filter.

        Args:
            query: The filter query string.
        """
        self._filter_query = query
        self._filter_field.setText(query)
        self.refresh()

    def refresh(self) -> None:
        """Refresh the folder list."""
        print(f"[DEBUG] refresh() called. filter_query='{self._filter_query}'")
        try:
            # Load folders
            all_folders, active_folders, inactive_folders = self._load_folders()
            print(f"[DEBUG] Folders loaded. all={len(all_folders)}, active={len(active_folders)}, inactive={len(inactive_folders)}")

            # Filter folders
            filtered_all, filtered_active, filtered_inactive = self._filter_folders(
                all_folders, active_folders, inactive_folders, self._filter_query
            )
            print(f"[DEBUG] Folders filtered. filtered_active={len(filtered_active)}, filtered_inactive={len(filtered_inactive)}")

            # Update count label
            if len(filtered_all) != len(all_folders):
                self._count_label.setText(
                    f"{len(filtered_all)} of {len(all_folders)} shown"
                )
            else:
                self._count_label.setText(f"{len(all_folders)} folders")

            # Reset models with filtered data
            self._active_model.reset_model(filtered_active)
            self._inactive_model.reset_model(filtered_inactive)
            
            # Clear all button areas since models have been reset
            self._delegate.button_areas.clear()

            # Handle empty states by showing appropriate messages
            if len(filtered_active) == 0:
                # We could potentially add a special empty state item to the model
                pass
            if len(filtered_inactive) == 0:
                # We could potentially add a special empty state item to the model
                pass
                
        except Exception as e:
            # Log the error and handle gracefully
            print(f"Error refreshing folder list: {str(e)}")
            import traceback
            traceback.print_exc()
            # Reset models with empty lists
            self._active_model.reset_model([])
            self._inactive_model.reset_model([])


