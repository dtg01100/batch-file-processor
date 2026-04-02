"""Qt-based resend configuration dialog.

Replaces the tkinter-based resend_interface.py with a Qt implementation.
"""

from __future__ import annotations

import os
from datetime import datetime
from typing import Any

from PyQt5.QtCore import QDate, QItemSelectionModel, Qt, QThread, QTimer, pyqtSignal
from PyQt5.QtGui import QColor
from PyQt5.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDateEdit,
    QDialogButtonBox,
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QToolButton,
    QWidget,
)

from core.constants import MAX_DATE, MIN_DATE
from interface.qt.dialogs.base_dialog import BaseDialog
from interface.qt.theme import Theme
from interface.services.resend_service import ResendService


class FileExistenceWorker(QThread):
    """Background worker for checking file existence on disk."""

    file_checked = pyqtSignal(dict)
    finished = pyqtSignal(int, int)

    def __init__(self, files: list[dict[str, Any]], parent: QWidget = None) -> None:
        super().__init__(parent)
        self._files = files
        self._is_cancelled = False

    def run(self) -> None:
        """Check file existence in background thread."""
        missing_count = 0
        total = len(self._files)
        for file_info in self._files:
            if self._is_cancelled:
                break
            file_info["file_exists"] = os.path.exists(file_info["file_name"])
            if not file_info["file_exists"]:
                missing_count += 1
            self.file_checked.emit(file_info)
        self.finished.emit(missing_count, total)

    def cancel(self) -> None:
        """Cancel the worker."""
        self._is_cancelled = True


class ResendDialog(BaseDialog):
    """Dialog for configuring file resend flags.

    Allows users to select which processed files should be marked for resend.
    """

    PAGE_SIZE = 500

    def __init__(
        self,
        parent: QWidget,
        database_connection: Any,
    ) -> None:
        super().__init__(parent, "Enable Resend", action_mode="none")
        self.setWindowModality(Qt.WindowModality.WindowModal)

        self._database_connection = database_connection
        self._service: ResendService | None = None
        self._all_files: list[dict[str, Any]] = []
        self._filtered_files: list[dict[str, Any]] = []
        self._selected_files: set = set()
        self._is_updating_selection = False
        self._ignore_table_selection_changes = False
        self._should_show = True
        self._search_timer = QTimer()
        self._search_timer.setSingleShot(True)
        self._search_timer.timeout.connect(self._do_search_filter)

        self._current_offset = 0
        self._total_files = 0
        self._file_check_worker: FileExistenceWorker | None = None
        self._is_loading = False
        self._has_more_data = True
        self._search_text = ""
        self._search_offset = 0

        self._setup_ui()
        self._load_data()

    def _create_date_edit_with_today_button(self) -> QDateEdit:
        """Create a date edit with a 'Today' button in the calendar popup."""
        date_edit = QDateEdit()
        date_edit.setCalendarPopup(True)

        date_edit.setStyleSheet("""
            QDateEdit {
                background-color: white;
                color: black;
            }
        """)

        calendar = date_edit.calendarWidget()
        if calendar is not None:
            calendar.setNavigationBarVisible(True)

            calendar.setStyleSheet("""
                QCalendarWidget {
                    background-color: white;
                    color: black;
                }
                QCalendarWidget QAbstractItemView {
                    background-color: white;
                    color: black;
                    selection-background-color: #4CAF50;
                    selection-color: white;
                }
                QCalendarWidget QToolButton {
                    background-color: #f0f0f0;
                    color: black;
                }
                QCalendarWidget QMenu {
                    background-color: white;
                    color: black;
                }
            """)

            nav_bar = calendar.findChild(QToolButton, "qt_calendar_navigation_bar")
            if nav_bar is not None:
                today_button = QToolButton()
                today_button.setText("Today")
                today_button.setToolTip("Jump to today")
                today_button.clicked.connect(
                    lambda: calendar.setSelectedDate(QDate.currentDate())
                )
                today_button.setStyleSheet(
                    "background-color: #4CAF50; color: white; padding: 4px;"
                )
                nav_bar.insertWidget(
                    nav_bar.children()[0] if nav_bar.children() else None, today_button
                )

        date_edit.setAccessibleName("Date selector")
        date_edit.setAccessibleDescription("Select a date")

        return date_edit

    def _setup_ui(self) -> None:
        """Set up the dialog UI."""
        main_layout = self._main_layout
        main_layout.setContentsMargins(
            Theme.SPACING_MD_INT,
            Theme.SPACING_MD_INT,
            Theme.SPACING_MD_INT,
            Theme.SPACING_MD_INT,
        )
        main_layout.setSpacing(Theme.SPACING_MD_INT)

        self.setMinimumSize(900, 600)

        search_layout = QHBoxLayout()
        search_label = QLabel("&Search:")
        self._search_input = QLineEdit()
        self._search_input.setPlaceholderText(
            "Filter by folder, file name, or invoice number..."
        )
        self._search_input.textChanged.connect(self._on_search_changed)
        self._search_input.setAccessibleName("Search files")
        self._search_input.setAccessibleDescription(
            "Filter the file list by folder, file name, or invoice number"
        )

        self._search_field_selector = QComboBox()
        self._search_field_selector.addItem("All fields", "all")
        self._search_field_selector.addItem("Folder", "folder")
        self._search_field_selector.addItem("File name", "file_name")
        self._search_field_selector.addItem("Invoice number", "invoice_numbers")
        self._search_field_selector.setAccessibleName("Search field selector")
        self._search_field_selector.setAccessibleDescription(
            "Choose which field to search: all fields, folder, file name, or invoice number"
        )
        self._search_field_selector.currentIndexChanged.connect(
            self._on_search_field_changed
        )

        self._date_filter_checkbox = QCheckBox("Filter by date")
        self._date_filter_checkbox.setChecked(False)
        self._date_filter_checkbox.toggled.connect(self._on_date_filter_toggled)
        self._date_filter_checkbox.setAccessibleName("Enable date range filter")

        self._date_from_input = self._create_date_edit_with_today_button()
        self._date_from_input.setDisplayFormat("yyyy-MM-dd")
        today = QDate.currentDate()
        week_ago = today.addDays(-7)
        self._date_from_input.setDate(week_ago)
        self._date_from_input.setMinimumDate(
            QDate(MIN_DATE.year, MIN_DATE.month, MIN_DATE.day)
        )
        self._date_from_input.setMaximumDate(
            QDate(MAX_DATE.year, MAX_DATE.month, MAX_DATE.day)
        )
        self._date_from_input.dateChanged.connect(self._on_date_range_changed)
        self._date_from_input.setAccessibleName("Start date")

        self._date_to_input = self._create_date_edit_with_today_button()
        self._date_to_input.setDisplayFormat("yyyy-MM-dd")
        self._date_to_input.setDate(today)
        self._date_to_input.setMinimumDate(
            QDate(MIN_DATE.year, MIN_DATE.month, MIN_DATE.day)
        )
        self._date_to_input.setMaximumDate(
            QDate(MAX_DATE.year, MAX_DATE.month, MAX_DATE.day)
        )
        self._date_to_input.dateChanged.connect(self._on_date_range_changed)
        self._date_to_input.setAccessibleName("End date")

        self._clear_date_range_button = QPushButton("Clear &Date Range")
        self._clear_date_range_button.clicked.connect(self._clear_date_range)
        self._clear_date_range_button.setAccessibleName("Clear date range filter")
        self._date_from_input.setEnabled(False)
        self._date_to_input.setEnabled(False)
        self._clear_date_range_button.setEnabled(False)

        search_layout.addWidget(search_label)
        search_layout.addWidget(self._search_field_selector)
        search_layout.addWidget(self._search_input)
        search_layout.addWidget(self._date_filter_checkbox)
        search_layout.addWidget(QLabel("From:"))
        search_layout.addWidget(self._date_from_input)
        search_layout.addWidget(QLabel("To:"))
        search_layout.addWidget(self._date_to_input)
        search_layout.addWidget(self._clear_date_range_button)
        main_layout.addLayout(search_layout)

        self._table = QTableWidget()
        self._table.setColumnCount(5)
        self._table.setHorizontalHeaderLabels(
            ["", "Folder", "File Name", "Sent Date", "Resend"]
        )
        self._table.setAlternatingRowColors(True)
        self._table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self._table.setSelectionMode(QTableWidget.SelectionMode.ExtendedSelection)
        self._table.itemSelectionChanged.connect(self._on_table_selection_changed)
        self._table.setSortingEnabled(True)
        self._table.horizontalHeader().setStretchLastSection(True)
        self._table.setAccessibleName("Files table")
        self._table.setAccessibleDescription(
            "Table of processed files with resend options"
        )
        main_layout.addWidget(self._table)

        pagination_layout = QHBoxLayout()

        self._page_label = QLabel("Showing 0 files")
        self._page_label.setAccessibleName("Page information")
        pagination_layout.addWidget(self._page_label)

        pagination_layout.addStretch()

        self._load_more_button = QPushButton("Load More")
        self._load_more_button.clicked.connect(self._load_more)
        pagination_layout.addWidget(self._load_more_button)

        self._loading_label = QLabel("")
        self._loading_label.setAccessibleName("Loading status")
        pagination_layout.addWidget(self._loading_label)

        main_layout.addLayout(pagination_layout)

        self._status_label = QLabel()
        self._status_label.setAccessibleName("Status information")
        main_layout.addWidget(self._status_label)

        self._bulk_action_frame = QFrame()
        self._bulk_action_frame.setFrameStyle(QFrame.Shape.Box)
        self._bulk_action_frame.setVisible(True)
        bulk_layout = QHBoxLayout(self._bulk_action_frame)

        self._bulk_select_all = QPushButton("&Select All")
        self._bulk_select_all.clicked.connect(self._select_all_files)
        bulk_layout.addWidget(self._bulk_select_all)

        self._bulk_clear_selection = QPushButton("&Clear Selection")
        self._bulk_clear_selection.clicked.connect(self._clear_selection)
        self._bulk_clear_selection.setEnabled(False)
        bulk_layout.addWidget(self._bulk_clear_selection)

        bulk_layout.addStretch()

        self._bulk_mark_resend = QPushButton("&Mark Selected for Resend")
        self._bulk_mark_resend.clicked.connect(self._mark_selected_for_resend)
        self._bulk_mark_resend.setEnabled(False)
        self._bulk_mark_resend.setStyleSheet(
            "QPushButton { background-color: #4CAF50; color: white; }"
        )
        bulk_layout.addWidget(self._bulk_mark_resend)

        self._bulk_clear_resend = QPushButton("&Clear Resend Flags")
        self._bulk_clear_resend.clicked.connect(self._clear_selected_resend_flags)
        self._bulk_clear_resend.setEnabled(False)
        bulk_layout.addWidget(self._bulk_clear_resend)

        main_layout.addWidget(self._bulk_action_frame)

        button_box = QDialogButtonBox(QDialogButtonBox.StandardButton.Close)
        button_box.rejected.connect(self.reject)
        close_btn = button_box.button(QDialogButtonBox.StandardButton.Close)
        if close_btn is not None:
            close_btn.setText("&Close")
            close_btn.setAccessibleName("Close resend dialog")
            close_btn.setAccessibleDescription("Close this dialog")
        main_layout.addWidget(button_box)

    def _load_data(self) -> None:
        """Load data from database with pagination."""
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

        try:
            self._total_files = self._service.get_total_file_count()
        except (TypeError, AttributeError):
            self._total_files = len(self._all_files) if self._all_files else 0
        self._current_offset = 0

        date_from, date_to = self._get_date_filters()
        try:
            self._all_files = self._service.get_all_files_for_resend(
                check_file_exists=False,
                limit=self.PAGE_SIZE,
                offset=0,
                date_from=date_from,
                date_to=date_to,
            )
        except (TypeError, AttributeError):
            self._all_files = []
        self._filtered_files = self._all_files.copy()
        self._has_more_data = len(self._all_files) == self.PAGE_SIZE
        self._populate_table()
        self._update_pagination()
        self._update_status()

        QTimer.singleShot(100, self._check_files_exist_async)

    def _populate_table(self) -> None:
        """Populate the table with filtered files."""
        self._table.setRowCount(len(self._filtered_files))

        self._is_updating_selection = True
        self._table.clearSelection()

        for row, file_info in enumerate(self._filtered_files):
            checkbox = QCheckBox()
            checkbox.setChecked(file_info["id"] in self._selected_files)
            checkbox.pressed.connect(self._on_checkbox_pressed)
            checkbox.released.connect(self._on_checkbox_released)
            checkbox.stateChanged.connect(
                lambda state, fid=file_info["id"]: self._on_file_selected(
                    fid, selected=state == Qt.CheckState.Checked
                )
            )
            self._table.setCellWidget(row, 0, checkbox)

            if file_info["id"] in self._selected_files:
                self._table.selectRow(row)

            folder_item = QTableWidgetItem(file_info["folder_alias"])
            folder_item.setFlags(folder_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
            self._table.setItem(row, 1, folder_item)

            file_item = QTableWidgetItem(file_info["file_name"])
            file_item.setFlags(file_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
            self._table.setItem(row, 2, file_item)

            sent_date_str = file_info.get("sent_date_time") or ""
            try:
                if sent_date_str:
                    sent_date = datetime.fromisoformat(sent_date_str).strftime(
                        "%Y-%m-%d %H:%M"
                    )
                else:
                    sent_date = ""
            except (ValueError, TypeError):
                sent_date = str(sent_date_str) if sent_date_str else ""
            date_item = QTableWidgetItem(sent_date)
            date_item.setFlags(date_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
            self._table.setItem(row, 3, date_item)

            status = "Yes" if file_info["resend_flag"] else "No"
            status_item = QTableWidgetItem(status)
            status_item.setFlags(status_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
            self._table.setItem(row, 4, status_item)

        self._table.setColumnWidth(0, 50)
        self._table.setColumnWidth(1, 150)
        self._table.setColumnWidth(3, 120)
        self._table.setColumnWidth(4, 80)
        self._table.horizontalHeader().setStretchLastSection(True)
        self._is_updating_selection = False

    def _check_files_exist_async(self) -> None:
        """Check which files exist on disk in background thread."""
        if not self._all_files:
            return

        self._loading_label.setText("Checking file existence...")

        self._file_check_worker = FileExistenceWorker(self._all_files)
        self._file_check_worker.file_checked.connect(self._on_file_checked)
        self._file_check_worker.finished.connect(self._on_file_check_finished)
        self._file_check_worker.start()

    def _on_file_checked(self, file_info: dict[str, Any]) -> None:
        """Handle individual file check result."""
        for f in self._filtered_files:
            if f["id"] == file_info["id"]:
                f["file_exists"] = file_info["file_exists"]
                break

    def _on_file_check_finished(self, missing_count: int, total_count: int) -> None:
        """Handle file existence check completion."""
        self._loading_label.setText("")
        if missing_count > 0:
            self._highlight_missing_files()
            self._update_status()

    def _highlight_missing_files(self) -> None:
        """Highlight rows for files that no longer exist on disk."""
        missing_color = QColor("#FFCCCC")
        warning_icon = "⚠"

        for row in range(self._table.rowCount()):
            file_info = self._filtered_files[row]
            if not file_info.get("file_exists", True):
                for col in range(self._table.columnCount()):
                    item = self._table.item(row, col)
                    if item is not None:
                        item.setBackground(missing_color)
                file_item = self._table.item(row, 2)
                if file_item is not None:
                    file_item.setText(f"{warning_icon} {file_item.text()}")

    def _on_search_changed(self, text: str) -> None:
        """Handle search input changes with debouncing."""
        self._search_timer.stop()
        self._search_timer.start(150)

    def _on_search_field_changed(self, index: int) -> None:
        """Re-apply search when the selected search field changes."""
        self._search_timer.stop()
        self._do_search_filter()

    def _on_date_filter_toggled(self, checked: bool) -> None:  # noqa: FBT001
        """Handle date filter checkbox toggle."""
        self._date_from_input.setEnabled(checked)
        self._date_to_input.setEnabled(checked)
        self._clear_date_range_button.setEnabled(checked)
        if not checked:
            self._do_search_filter()

    def _on_date_range_changed(self) -> None:
        """Re-run query when the date range inputs change."""
        if self._date_filter_checkbox.isChecked():
            self._search_timer.stop()
            self._search_timer.start(150)

    def _clear_date_range(self) -> None:
        """Clear date filters and reload data."""
        self._date_filter_checkbox.setChecked(False)

    def _get_date_filters(self) -> tuple[str | None, str | None]:
        """Return date_from/date_to values for queries, or None if not set."""
        if not self._date_filter_checkbox.isChecked():
            return None, None

        date_from = self._date_from_input.date()
        date_to = self._date_to_input.date()
        date_from_str = date_from.toString("yyyy-MM-dd")
        date_to_str = date_to.toString("yyyy-MM-dd")

        return date_from_str, date_to_str

    def _get_selected_search_field(self) -> str:
        """Return the selected search field key."""
        selected_field = self._search_field_selector.currentData()
        return selected_field if isinstance(selected_field, str) else "all"

    @staticmethod
    def _matches_search_field(
        file_info: dict[str, Any], lower_text: str, field: str
    ) -> bool:
        """Check if a row matches text based on selected search field."""
        if field == "file_name":
            return lower_text in (file_info.get("file_name") or "").lower()
        if field == "invoice_numbers":
            return lower_text in (file_info.get("invoice_numbers") or "").lower()
        if field == "folder":
            return lower_text in (file_info.get("folder_alias") or "").lower()

        return (
            lower_text in (file_info.get("file_name") or "").lower()
            or lower_text in (file_info.get("invoice_numbers") or "").lower()
            or lower_text in (file_info.get("folder_alias") or "").lower()
        )

    def _do_search_filter(self) -> None:
        """Perform the actual search filtering after debounce."""
        text = self._search_input.text()
        search_field = self._get_selected_search_field()
        self._search_text = text
        self._search_offset = 0

        date_from, date_to = self._get_date_filters()

        if not text:
            self._current_offset = 0
            try:
                self._all_files = self._service.get_all_files_for_resend(
                    check_file_exists=False,
                    limit=self.PAGE_SIZE,
                    offset=0,
                    date_from=date_from,
                    date_to=date_to,
                )
            except (TypeError, AttributeError):
                self._all_files = []
            self._filtered_files = self._all_files.copy()
            self._has_more_data = len(self._all_files) == self.PAGE_SIZE
        else:
            self._current_offset = 0
            try:
                self._filtered_files = self._service.search_files_for_resend(
                    text,
                    limit=self.PAGE_SIZE,
                    offset=0,
                    search_field=search_field,
                    date_from=date_from,
                    date_to=date_to,
                )
            except (TypeError, AttributeError):
                lower_text = text.lower()
                self._filtered_files = [
                    f
                    for f in self._all_files
                    if self._matches_search_field(f, lower_text, search_field)
                ]
            self._all_files = self._filtered_files.copy()
            self._has_more_data = len(self._filtered_files) == self.PAGE_SIZE

        self._selected_files.clear()
        self._populate_table()
        self._update_pagination()
        self._update_status()

    def _on_file_selected(self, file_id: int, *, selected: bool) -> None:
        """Handle file selection in table."""
        self._ignore_table_selection_changes = False
        if selected:
            self._selected_files.add(file_id)
        else:
            self._selected_files.discard(file_id)

        if not self._is_updating_selection:
            self._is_updating_selection = True
            # Synchronize row selection with checkbox selection.
            for row, file_info in enumerate(self._filtered_files):
                if file_info["id"] == file_id:
                    if selected:
                        self._table.selectRow(row)
                    else:
                        self._table.selectionModel().select(
                            self._table.model().index(row, 0),
                            QItemSelectionModel.Deselect | QItemSelectionModel.Rows,
                        )
                    break
            self._is_updating_selection = False

        self._update_bulk_actions()
        self._update_status()

    def _on_checkbox_pressed(self) -> None:
        """Handle checkbox press to suppress selection syncing temporarily."""
        # When user presses checkbox inside the table, we temporarily suppress
        # _on_table_selection_changed so row selection updates don't conflict
        # with the checkbox-state event stream. This prevents a rapid select+clear
        # flip-flop when both checkbox stateChanged and table selection change
        # events fire.
        self._ignore_table_selection_changes = True

    def _on_checkbox_released(self) -> None:
        """Handle checkbox release and clear selection suppression."""
        # Allow table selection changes again after checkbox action completes.
        self._ignore_table_selection_changes = False

    def _on_table_selection_changed(self) -> None:
        """Sync checkbox state when user selects rows."""
        if self._is_updating_selection or self._ignore_table_selection_changes:
            return

        self._is_updating_selection = True
        selected_rows = {item.row() for item in self._table.selectedItems()}
        self._selected_files = {
            self._filtered_files[row]["id"]
            for row in selected_rows
            if row < len(self._filtered_files)
        }

        for row in range(self._table.rowCount()):
            checkbox = self._table.cellWidget(row, 0)
            if checkbox is None:
                continue
            should_check = self._filtered_files[row]["id"] in self._selected_files
            if checkbox.isChecked() != should_check:
                checkbox.blockSignals(True)  # noqa: FBT003
                checkbox.setChecked(should_check)
                checkbox.blockSignals(False)  # noqa: FBT003

        self._is_updating_selection = False

        self._update_bulk_actions()
        self._update_status()

    def _update_bulk_actions(self) -> None:
        """Update bulk action bar buttons state."""
        has_selection = bool(self._selected_files)

        # Always show bulk actions so "Select All" is available on first view.
        self._bulk_action_frame.setVisible(True)

        self._bulk_mark_resend.setEnabled(has_selection)
        self._bulk_clear_resend.setEnabled(has_selection)
        self._bulk_clear_selection.setEnabled(has_selection)

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

    def _update_pagination(self) -> None:
        """Update pagination controls."""
        self._page_label.setText(f"Showing {len(self._filtered_files)} files")

        self._load_more_button.setEnabled(self._has_more_data and not self._is_loading)

    def _cancel_file_check_worker(self) -> None:
        """Cancel existing file check worker safely."""
        if self._file_check_worker and self._file_check_worker.isRunning():
            self._file_check_worker.cancel()
            self._file_check_worker.deleteLater()
            QTimer.singleShot(500, self._file_check_worker.deleteLater)
            self._file_check_worker = None

    def _load_more(self) -> None:
        """Load more results (append to existing list)."""
        if self._is_loading:
            return
        if not self._has_more_data:
            return

        self._is_loading = True
        self._load_more_button.setEnabled(False)
        self._loading_label.setText("Loading...")

        self._cancel_file_check_worker()

        date_from, date_to = self._get_date_filters()

        if self._search_text:
            # Load more search results
            self._search_offset += self.PAGE_SIZE
            search_field = self._get_selected_search_field()
            try:
                new_files = self._service.search_files_for_resend(
                    self._search_text,
                    limit=self.PAGE_SIZE,
                    offset=self._search_offset,
                    search_field=search_field,
                    date_from=date_from,
                    date_to=date_to,
                )
            except (TypeError, AttributeError):
                new_files = []
        else:
            # Load more regular results
            self._current_offset += self.PAGE_SIZE
            try:
                new_files = self._service.get_all_files_for_resend(
                    check_file_exists=False,
                    limit=self.PAGE_SIZE,
                    offset=self._current_offset,
                    date_from=date_from,
                    date_to=date_to,
                )
            except (TypeError, AttributeError):
                new_files = []

        if len(new_files) < self.PAGE_SIZE:
            self._has_more_data = False

        existing_ids = {f["id"] for f in self._all_files}
        for new_file in new_files:
            if new_file["id"] not in existing_ids:
                self._all_files.append(new_file)

        self._filtered_files = self._all_files.copy()
        self._populate_table()
        self._update_status()

        self._is_loading = False
        self._loading_label.setText("")
        self._update_pagination()

        QTimer.singleShot(100, self._check_files_exist_async)

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
            self._service.set_resend_flags_batch(file_ids, resend_flag=True)
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
            self._service.set_resend_flags_batch(file_ids, resend_flag=False)
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
    if dialog._should_show:
        dialog.exec()
