"""Qt-based resend configuration dialog.

Replaces the tkinter-based resend_interface.py with a Qt implementation.
"""

from __future__ import annotations

import os
from datetime import datetime
from typing import Any, Dict, List, Optional

from PyQt5.QtCore import Qt, QTimer
from PyQt5.QtGui import QColor
from PyQt5.QtWidgets import (
    QCheckBox,
    QDialogButtonBox,
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
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
        super().__init__(parent, "Enable Resend", action_mode="none")
        self.setWindowModality(Qt.WindowModality.WindowModal)

        self._database_connection = database_connection
        self._service: Optional[ResendService] = None
        self._all_files: List[Dict[str, Any]] = []
        self._filtered_files: List[Dict[str, Any]] = []
        self._selected_files: set = set()
        self._should_show = True  # Flag to control if dialog should be shown
        self._search_timer = QTimer()
        self._search_timer.setSingleShot(True)
        self._search_timer.timeout.connect(self._do_search_filter)

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
        self._table.setHorizontalHeaderLabels(
            ["", "Folder", "File Name", "Sent Date", "Resend"]
        )
        self._table.setAlternatingRowColors(True)
        self._table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self._table.setSortingEnabled(True)
        self._table.horizontalHeader().setStretchLastSection(True)
        self._table.setAccessibleName("Files table")
        self._table.setAccessibleDescription(
            "Table of processed files with resend options"
        )
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
        self._bulk_mark_resend.setStyleSheet(
            "QPushButton { background-color: #4CAF50; color: white; }"
        )
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

        # Load all files without file existence check for faster initial load
        self._all_files = self._service.get_all_files_for_resend(
            check_file_exists=False
        )
        self._filtered_files = self._all_files.copy()
        self._populate_table()
        self._update_status()

        # Schedule async file existence check after UI is loaded
        QTimer.singleShot(100, self._check_files_exist_async)

    def _populate_table(self) -> None:
        """Populate the table with filtered files."""
        self._table.setRowCount(len(self._filtered_files))

        for row, file_info in enumerate(self._filtered_files):
            # Checkbox column
            checkbox = QCheckBox()
            checkbox.setChecked(file_info["id"] in self._selected_files)
            checkbox.stateChanged.connect(
                lambda state, fid=file_info["id"]: self._on_file_selected(
                    fid, state == Qt.CheckState.Checked
                )
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
            sent_date = datetime.fromisoformat(file_info["sent_date_time"]).strftime(
                "%Y-%m-%d %H:%M"
            )
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
        self._table.setColumnWidth(4, 80)  # Status column
        self._table.horizontalHeader().setStretchLastSection(True)

    def _check_files_exist_async(self) -> None:
        """Check which files exist on disk and update UI with warnings."""
        missing_count = 0
        for file_info in self._all_files:
            file_info["file_exists"] = os.path.exists(file_info["file_name"])
            if not file_info["file_exists"]:
                missing_count += 1

        # Update filtered files and refresh table highlighting
        for file_info in self._filtered_files:
            if file_info["id"] in {
                f["id"] for f in self._all_files if not f["file_exists"]
            }:
                file_info["file_exists"] = False

        if missing_count > 0:
            self._highlight_missing_files()
            self._update_status()

    def _highlight_missing_files(self) -> None:
        """Highlight rows for files that no longer exist on disk."""
        missing_color = QColor("#FFCCCC")  # Light red background
        warning_icon = "⚠"

        for row in range(self._table.rowCount()):
            file_info = self._filtered_files[row]
            if not file_info.get("file_exists", True):
                # Highlight the entire row
                for col in range(self._table.columnCount()):
                    item = self._table.item(row, col)
                    if item is not None:
                        item.setBackground(missing_color)
                # Add warning to file name
                file_item = self._table.item(row, 2)
                if file_item is not None:
                    file_item.setText(f"{warning_icon} {file_item.text()}")

    def _on_search_changed(self, text: str) -> None:
        """Handle search input changes with debouncing."""
        self._search_timer.stop()
        self._search_timer.start(150)  # 150ms debounce

    def _do_search_filter(self) -> None:
        """Perform the actual search filtering after debounce."""
        text = self._search_input.text()
        if not text:
            self._filtered_files = self._all_files.copy()
        else:
            lower_text = text.lower()
            self._filtered_files = [
                f for f in self._all_files if lower_text in f["file_name"].lower()
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
            file_ids = list(self._selected_files)
            self._service.set_resend_flags_batch(file_ids, True)
            # Update local data
            selected_set = set(file_ids)
            for file_info in self._all_files:
                if file_info["id"] in selected_set:
                    file_info["resend_flag"] = True
            count = len(file_ids)
            self._selected_files.clear()
            self._populate_table()
            self._update_bulk_actions()
            self._update_status()
            self.show_info("Success", f"Marked {count} files for resend.")
        except Exception as e:
            self.show_error("Database Error", f"Database error: {e}")

    def _clear_selected_resend_flags(self) -> None:
        """Clear resend flags for selected files."""
        try:
            file_ids = list(self._selected_files)
            self._service.set_resend_flags_batch(file_ids, False)
            # Update local data
            selected_set = set(file_ids)
            for file_info in self._all_files:
                if file_info["id"] in selected_set:
                    file_info["resend_flag"] = False
            count = len(file_ids)
            self._selected_files.clear()
            self._populate_table()
            self._update_bulk_actions()
            self._update_status()
            self.show_info("Success", f"Cleared resend flags for {count} files.")
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
