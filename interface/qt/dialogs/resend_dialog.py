"""Qt-based resend configuration dialog.

Replaces the tkinter-based resend_interface.py with a Qt implementation.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QCheckBox,
    QDialog,
    QDialogButtonBox,
    QFrame,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QScrollArea,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)

from interface.qt.dialogs.base_dialog import BaseDialog

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
        self._folder_id: Optional[int] = None
        self._file_checkboxes: Dict[int, QCheckBox] = {}
        self._folder_buttons: Dict[int, QPushButton] = {}

        self._setup_ui()
        self._load_data()

    def _setup_ui(self) -> None:
        """Set up the dialog UI."""
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(10, 10, 10, 10)
        main_layout.setSpacing(10)

        # Set minimum size for comfortable viewing
        self.setMinimumSize(700, 500)

        # Files and folders frame
        files_folders_frame = QFrame()
        files_folders_layout = QHBoxLayout(files_folders_frame)
        files_folders_layout.setContentsMargins(0, 0, 0, 0)

        # Folders frame (left)
        folders_frame = QGroupBox("Folders")
        self._folders_layout = QVBoxLayout(folders_frame)
        self._folders_layout.setSpacing(5)

        # Files frame (right)
        files_frame = QGroupBox("Files")
        files_layout = QVBoxLayout(files_frame)

        # File count control
        file_count_frame = QHBoxLayout()
        file_count_label = QLabel("Show:")
        file_count_frame.addWidget(file_count_label)

        self._file_count_spinbox = QSpinBox()
        self._file_count_spinbox.setMinimum(5)
        self._file_count_spinbox.setMaximum(1000)
        self._file_count_spinbox.setValue(10)
        self._file_count_spinbox.setSingleStep(5)
        self._file_count_spinbox.setEnabled(False)
        self._file_count_spinbox.valueChanged.connect(self._on_file_count_changed)
        file_count_frame.addWidget(self._file_count_spinbox)

        file_count_frame.addStretch()
        files_layout.addLayout(file_count_frame)

        # Scrollable file list
        self._files_scroll = QScrollArea()
        self._files_scroll.setWidgetResizable(True)
        self._files_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self._files_content = QWidget()
        self._files_content_layout = QVBoxLayout(self._files_content)
        self._files_content_layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        self._files_scroll.setWidget(self._files_content)
        files_layout.addWidget(self._files_scroll)

        # Assemble
        files_folders_layout.addWidget(folders_frame, stretch=1)
        files_folders_layout.addWidget(files_frame, stretch=2)
        main_layout.addWidget(files_folders_frame)

        # Close button
        button_box = QDialogButtonBox(QDialogButtonBox.StandardButton.Close)
        button_box.rejected.connect(self.reject)
        main_layout.addWidget(button_box)

    def _load_data(self) -> None:
        """Load data from database."""
        try:
            self._service = ResendService(self._database_connection)
            if not self._service.has_processed_files():
                from PyQt6.QtWidgets import QMessageBox
                QMessageBox.information(self, "Nothing To Configure", "No processed files found.")
                self.reject()
                return
        except Exception as e:
            from PyQt6.QtWidgets import QMessageBox
            QMessageBox.critical(self, "Database Error", f"Database error: {e}")
            self.reject()
            return

        # Load folders
        folders = self._service.get_folders_with_files()
        for folder_info in folders:
            self._add_folder_button(folder_info)

    def _add_folder_button(self, folder_info: Dict[str, Any]) -> None:
        """Add a folder button to the folders list."""
        folder_id = folder_info['id']
        folder_name = folder_info['folder_name']

        button = QPushButton(folder_name)
        button.setCheckable(True)
        button.clicked.connect(lambda checked: self._on_folder_selected(folder_id))
        self._folder_buttons[folder_id] = button
        self._folders_layout.addWidget(button)

    def _on_folder_selected(self, folder_id: int) -> None:
        """Handle folder selection."""
        # Update button states
        for fid, button in self._folder_buttons.items():
            button.setChecked(fid == folder_id)

        self._folder_id = folder_id

        # Load files for this folder
        self._load_files_for_folder(folder_id)

    def _load_files_for_folder(self, folder_id: int) -> None:
        """Load and display files for the selected folder."""
        # Clear existing checkboxes
        for checkbox in self._file_checkboxes.values():
            checkbox.deleteLater()
        self._file_checkboxes.clear()

        # Get file count and update spinbox
        number_of_files = self._service.count_files_for_folder(folder_id)
        self._file_count_spinbox.setEnabled(True)
        self._file_count_spinbox.setMaximum(max(1000, number_of_files))
        if number_of_files > 10:
            self._file_count_spinbox.setValue(((number_of_files + 4) // 5) * 5)
        else:
            self._file_count_spinbox.setValue(10)

        # Load files
        self._populate_file_checkboxes()

    def _populate_file_checkboxes(self) -> None:
        """Populate the file checkboxes."""
        if self._folder_id is None:
            return

        limit = int(self._file_count_spinbox.value())
        files = self._service.get_files_for_folder(self._folder_id, limit=limit)

        # Calculate max filename length for alignment
        if files:
            max_name_length = max(len(f['file_name']) for f in files)
        else:
            max_name_length = 0

        for file_info in files:
            checkbox = QCheckBox(self._files_content)
            checkbox.setText(file_info['file_name'])
            checkbox.setChecked(file_info['resend_flag'])
            checkbox.toggled.connect(
                lambda checked, fid=file_info['id']: self._on_file_toggled(fid, checked)
            )
            self._file_checkboxes[file_info['id']] = checkbox
            self._files_content_layout.addWidget(checkbox)

        self._files_content_layout.addStretch()

    def _on_file_count_changed(self, value: int) -> None:
        """Handle file count spinbox change."""
        if self._folder_id is not None:
            self._populate_file_checkboxes()

    def _on_file_toggled(self, file_id: int, checked: bool) -> None:
        """Handle file checkbox toggle."""
        try:
            self._service.set_resend_flag(file_id, checked)
        except Exception as e:
            from PyQt6.QtWidgets import QMessageBox
            QMessageBox.critical(self, "Database Error", f"Database error: {e}")


def show_resend_dialog(parent: QWidget, database_connection: Any) -> None:
    """Show the resend configuration dialog.

    Args:
        parent: Parent widget
        database_connection: Database connection object
    """
    dialog = ResendDialog(parent, database_connection)
    dialog.exec()
