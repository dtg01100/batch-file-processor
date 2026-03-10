"""Qt-based resend configuration dialog.

Replaces the tkinter-based resend_interface.py with a Qt implementation.
"""

from __future__ import annotations

from typing import Any, Dict, Optional

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QCheckBox,
    QDialogButtonBox,
    QFrame,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QSpinBox,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from interface.qt.dialogs.base_dialog import BaseDialog
from interface.qt.theme import Theme

from interface.services.resend_service import ResendService


class ResendDialog(BaseDialog):
    """Dialog for configuring file resend flags.

    Allows users to select which processed files should be marked for resend.
    """

    def __init__(
        self,
        parent: QWidget,
        database_connection: Any,
    ) -> None:
        super().__init__(parent, "Enable Resend")
        self.setWindowModality(Qt.WindowModality.WindowModal)

        self._database_connection = database_connection
        self._service: Optional[ResendService] = None
        self._all_files: List[Dict[str, Any]] = []
        self._filtered_files: List[Dict[str, Any]] = []
        self._selected_files: set = set()
        self._should_show = True  # Flag to control if dialog should be shown

        self._setup_ui()
        self._load_data()

    def _setup_ui(self) -> None:
        """Set up the dialog UI."""
        # Use the main layout from BaseDialog instead of creating a new one
        main_layout = self._main_layout
        main_layout.setContentsMargins(
            Theme.SPACING_MD_INT,
            Theme.SPACING_MD_INT,
            Theme.SPACING_MD_INT,
            Theme.SPACING_MD_INT,
        )
        main_layout.setSpacing(Theme.SPACING_MD_INT)

        # Clear default widgets from BaseDialog
        while main_layout.count() > 0:
            item = main_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        # Set minimum size for comfortable viewing
        self.setMinimumSize(900, 600)

        # Search bar
        search_layout = QHBoxLayout()
        search_label = QLabel("&Search:")
        self._search_input = QLineEdit()
        self._search_input.setPlaceholderText("Filter files by name...")
        self._search_input.textChanged.connect(self._on_search_changed)
        self._search_input.setAccessibleName("Search files")
        self._search_input.setAccessibleDescription("Filter the file list by file name")
        search_layout.addWidget(search_label)
        search_layout.addWidget(self._search_input)
        main_layout.addLayout(search_layout)

        # Table
        self._table = QTableWidget()
        self._table.setColumnCount(5)
        self._table.setHorizontalHeaderLabels([
            "", "Folder", "File Name", "Sent Date", "Resend"
        ])
        self._table.setAlternatingRowColors(True)
        self._table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self._table.setSortingEnabled(True)
        self._table.horizontalHeader().setStretchLastSection(True)
        self._table.setAccessibleName("Files table")
        self._table.setAccessibleDescription("Table of processed files with resend options")
        main_layout.addWidget(self._table)

        # Status bar
        self._status_label = QLabel()
        self._status_label.setAccessibleName("Status information")
        main_layout.addWidget(self._status_label)

        # Bulk action bar (initially hidden)
        self._bulk_action_frame = QFrame()
        self._bulk_action_frame.setFrameStyle(QFrame.Shape.Box)
        self._bulk_action_frame.setVisible(False)
        bulk_layout = QHBoxLayout(self._bulk_action_frame)

        self._bulk_select_all = QPushButton("&Select All")
        self._bulk_select_all.clicked.connect(self._select_all_files)
        bulk_layout.addWidget(self._bulk_select_all)

        self._bulk_clear_selection = QPushButton("&Clear Selection")
        self._bulk_clear_selection.clicked.connect(self._clear_selection)
        bulk_layout.addWidget(self._bulk_clear_selection)

        bulk_layout.addStretch()

        self._bulk_mark_resend = QPushButton("&Mark Selected for Resend")
        self._bulk_mark_resend.clicked.connect(self._mark_selected_for_resend)
        self._bulk_mark_resend.setStyleSheet("QPushButton { background-color: #4CAF50; color: white; }")
        bulk_layout.addWidget(self._bulk_mark_resend)

        self._bulk_clear_resend = QPushButton("&Clear Resend Flags")
        self._bulk_clear_resend.clicked.connect(self._clear_selected_resend_flags)
        bulk_layout.addWidget(self._bulk_clear_resend)

        main_layout.addWidget(self._bulk_action_frame)

        # Close button
        button_box = QDialogButtonBox(QDialogButtonBox.StandardButton.Close)
        button_box.rejected.connect(self.reject)
        close_btn = button_box.button(QDialogButtonBox.StandardButton.Close)
        if close_btn is not None:
            close_btn.setText("&Close")
            close_btn.setAccessibleName("Close resend dialog")
            close_btn.setAccessibleDescription("Close this dialog")
        main_layout.addWidget(button_box)

    def _load_data(self) -> None:
        """Load data from database."""
        try:
            self._service = ResendService(self._database_connection)
            if not self._service.has_processed_files():
                self.show_info("Nothing To Configure", "No processed files found.")
                self._should_show = False
                return
        except Exception as e:
            self.show_error("Database Error", f"Database error: {e}")
            self._should_show = False
            return

        # Load all files
        self._all_files = self._service.get_all_files_for_resend()
        self._filtered_files = self._all_files.copy()
        self._populate_table()
        self._update_status()

    def _populate_table(self) -> None:
        """Populate the table with filtered files."""
        self._table.setRowCount(len(self._filtered_files))

        for row, file_info in enumerate(self._filtered_files):
            # Checkbox column
            checkbox = QCheckBox()
            checkbox.setChecked(file_info["id"] in self._selected_files)
            checkbox.stateChanged.connect(
                lambda state, fid=file_info["id"]: self._on_file_selected(fid, state == 2)
            )
            self._table.setCellWidget(row, 0, checkbox)

            # Folder column
            folder_item = QTableWidgetItem(file_info["folder_alias"])
            folder_item.setFlags(folder_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
            self._table.setItem(row, 1, folder_item)

            # File name column
            file_item = QTableWidgetItem(file_info["file_name"])
            file_item.setFlags(file_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
            self._table.setItem(row, 2, file_item)

            # Sent date column
            from datetime import datetime
            sent_date = datetime.fromisoformat(file_info["sent_date_time"]).strftime("%Y-%m-%d %H:%M")
            date_item = QTableWidgetItem(sent_date)
            date_item.setFlags(date_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
            self._table.setItem(row, 3, date_item)

            # Resend status column
            status = "Yes" if file_info["resend_flag"] else "No"
            status_item = QTableWidgetItem(status)
            status_item.setFlags(status_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
            self._table.setItem(row, 4, status_item)

        self._table.resizeColumnsToContents()
        # Set minimum widths for better readability
        self._table.setColumnWidth(0, 50)  # Checkbox column
        self._table.setColumnWidth(1, 150)  # Folder column
        self._table.setColumnWidth(3, 120)  # Date column
        self._table.setColumnWidth(4, 80)   # Status column
        self._table.horizontalHeader().setStretchLastSection(True)

    def _on_search_changed(self, text: str) -> None:
        """Handle search input changes."""
        if not text:
            self._filtered_files = self._all_files.copy()
        else:
            self._filtered_files = [
                f for f in self._all_files
                if text.lower() in f["file_name"].lower()
            ]
        self._populate_table()
        self._update_status()

    def _on_file_selected(self, file_id: int, selected: bool) -> None:
        """Handle file selection in table."""
        if selected:
            self._selected_files.add(file_id)
        else:
            self._selected_files.discard(file_id)
        self._update_bulk_actions()

    def _update_bulk_actions(self) -> None:
        """Update bulk action bar visibility and state."""
        has_selection = bool(self._selected_files)
        self._bulk_action_frame.setVisible(has_selection)

    def _update_status(self) -> None:
        """Update the status label."""
        total_files = len(self._all_files)
        filtered_files = len(self._filtered_files)
        selected_files = len(self._selected_files)
        resend_count = sum(1 for f in self._all_files if f["resend_flag"])

        if filtered_files < total_files:
            status = f"Showing {filtered_files} of {total_files} files"
        else:
            status = f"{total_files} files total"

        if selected_files > 0:
            status += f" • {selected_files} selected"

        if resend_count > 0:
            status += f" • {resend_count} marked for resend"

        self._status_label.setText(status)

    def _select_all_files(self) -> None:
        """Select all visible files."""
        self._selected_files.update(f["id"] for f in self._filtered_files)
        self._populate_table()
        self._update_bulk_actions()
        self._update_status()

    def _clear_selection(self) -> None:
        """Clear all selections."""
        self._selected_files.clear()
        self._populate_table()
        self._update_bulk_actions()
        self._update_status()

    def _mark_selected_for_resend(self) -> None:
        """Mark selected files for resend."""
        try:
            for file_id in self._selected_files:
                self._service.set_resend_flag(file_id, True)
            # Update local data
            for file_info in self._all_files:
                if file_info["id"] in self._selected_files:
                    file_info["resend_flag"] = True
            self._populate_table()
            self._update_status()
            self.show_info("Success", f"Marked {len(self._selected_files)} files for resend.")
        except Exception as e:
            self.show_error("Database Error", f"Database error: {e}")

    def _clear_selected_resend_flags(self) -> None:
        """Clear resend flags for selected files."""
        try:
            for file_id in self._selected_files:
                self._service.set_resend_flag(file_id, False)
            # Update local data
            for file_info in self._all_files:
                if file_info["id"] in self._selected_files:
                    file_info["resend_flag"] = False
            self._populate_table()
            self._update_status()
            self.show_info("Success", f"Cleared resend flags for {len(self._selected_files)} files.")
        except Exception as e:
            self.show_error("Database Error", f"Database error: {e}")


def show_resend_dialog(parent: QWidget, database_connection: Any) -> None:
    """Show the resend configuration dialog.

    Args:
        parent: Parent widget
        database_connection: Database connection object
    """
    dialog = ResendDialog(parent, database_connection)
    # Only show dialog if data loaded successfully
    if dialog._should_show:
        dialog.exec()
