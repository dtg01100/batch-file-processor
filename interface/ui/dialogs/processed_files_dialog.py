"""
Processed files dialog module for PyQt6 interface.

This module contains the ProcessedFilesDialog implementation.
A dialog for displaying and exporting the processed files report.
"""

import os
import csv
from typing import TYPE_CHECKING, Dict, Any, Optional, List

from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QWidget,
    QLabel, QPushButton, QListWidget, QListWidgetItem,
    QRadioButton, QGroupBox, QMessageBox, QFileDialog
)
from PyQt6.QtCore import Qt

if TYPE_CHECKING:
    from interface.database.database_manager import DatabaseManager


class ProcessedFilesDialog(QDialog):
    """Dialog for displaying and exporting processed files report."""
    
    def __init__(
        self,
        parent: QWidget = None,
        db_manager: "DatabaseManager" = None
    ):
        """
        Initialize the processed files dialog.
        
        Args:
            parent: Parent window.
            db_manager: Database manager instance.
        """
        super().__init__(parent)
        
        self.db_manager = db_manager
        
        self.setWindowTitle("Processed Files Report")
        self.setModal(True)
        self.resize(500, 400)
        
        self._selected_folder_id: Optional[int] = None
        self._selected_folder_alias: Optional[str] = None
        self._output_folder: str = ""
        
        self._setup_ui()
    
    def _setup_ui(self) -> None:
        """Setup the dialog UI."""
        layout = QHBoxLayout(self)
        
        # Left side - folder selection
        folder_frame = QGroupBox("Select a Folder")
        folder_layout = QVBoxLayout(folder_frame)
        
        self._folder_list = QListWidget()
        self._folder_list.currentRowChanged.connect(self._on_folder_selected)
        folder_layout.addWidget(self._folder_list)
        
        layout.addWidget(folder_frame, stretch=1)
        
        # Right side - actions
        actions_frame = QGroupBox("Actions")
        actions_layout = QVBoxLayout(actions_frame)
        
        self._export_btn = QPushButton("Export Processed Report")
        self._export_btn.setEnabled(False)
        self._export_btn.clicked.connect(self._on_export)
        actions_layout.addWidget(self._export_btn)
        
        # Loading label
        self._loading_label = QLabel("Loading...")
        actions_layout.addWidget(self._loading_label)
        
        layout.addWidget(actions_frame, stretch=1)
        
        # Load folder data
        self._load_folders()
    
    def _load_folders(self) -> None:
        """Load folders with processed files."""
        # Get prior output folder from settings
        oversight = self.db_manager.oversight_and_defaults.find_one(id=1)
        if oversight and oversight.get("export_processed_folder_prior"):
            if os.path.exists(oversight["export_processed_folder_prior"]):
                self._output_folder = oversight["export_processed_folder_prior"]
                self._export_btn.setEnabled(True)
        
        # Get distinct folder IDs
        distinct_folder_ids = []
        for row in self.db_manager.processed_files.distinct("folder_id"):
            distinct_folder_ids.append(row["folder_id"])
        
        # Build folder list
        folder_entry_list = []
        for entry in distinct_folder_ids:
            folder_dict = self.db_manager.folders_table.find_one(id=str(entry))
            if folder_dict:
                folder_entry_list.append([entry, folder_dict.get("alias", "Unknown")])
        
        # Sort by alias
        folder_entry_list.sort(key=lambda x: x[1])
        
        # Populate list
        for folder_id, folder_alias in folder_entry_list:
            item = QListWidgetItem(folder_alias)
            item.setData(Qt.ItemDataRole.UserRole, folder_id)
            self._folder_list.addItem(item)
        
        # Hide loading label
        self._loading_label.hide()
        
        # Check if there are any processed files
        if self.db_manager.processed_files.count() == 0:
            item = QListWidgetItem("No Folders With Processed Files")
            item.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsSelectable & ~Qt.ItemFlag.ItemIsEnabled)
            self._folder_list.addItem(item)
    
    def _on_folder_selected(self, row: int) -> None:
        """Handle folder selection."""
        item = self._folder_list.item(row)
        if item and item.flags() & Qt.ItemFlag.ItemIsSelectable:
            folder_id = item.data(Qt.ItemDataRole.UserRole)
            folder_alias = item.text()
            
            self._selected_folder_id = folder_id
            self._selected_folder_alias = folder_alias
            
            # Ask for output folder if not already selected
            if not self._output_folder:
                self._select_output_folder()
    
    def _select_output_folder(self) -> None:
        """Select the output folder for export."""
        oversight = self.db_manager.oversight_and_defaults.find_one(id=1)
        
        initial_dir = os.path.expanduser("~")
        if oversight and oversight.get("export_processed_folder_prior"):
            if os.path.exists(oversight["export_processed_folder_prior"]):
                initial_dir = oversight["export_processed_folder_prior"]
        
        output_folder = QFileDialog.getExistingDirectory(
            self,
            "Select Output Folder",
            initial_dir,
            QFileDialog.Option.ShowDirsOnly
        )
        
        if output_folder:
            self._output_folder = output_folder
            
            # Update settings
            update_data = {"id": 1, "export_processed_folder_prior": output_folder}
            self.db_manager.oversight_and_defaults.update(update_data, ["id"])
            
            # Enable export button
            self._export_btn.setEnabled(True)
    
    def _on_export(self) -> None:
        """Export processed files report to CSV."""
        if not self._selected_folder_id or not self._output_folder:
            QMessageBox.warning(
                self,
                "Warning",
                "Please select a folder and output folder first."
            )
            return
        
        try:
            # Generate output file path
            folder_alias = self._selected_folder_alias or "Unknown"
            base_path = os.path.join(
                self._output_folder,
                f"{folder_alias} processed report"
            )
            
            output_path = self._avoid_duplicate_export_file(base_path, ".csv")
            
            # Write CSV file
            with open(output_path, "w", newline="", encoding="utf-8") as csvfile:
                writer = csv.writer(csvfile)
                writer.writerow([
                    "File", "Date", "Copy Destination", 
                    "FTP Destination", "Email Destination"
                ])
                
                # Get processed files for selected folder
                processed_files = self.db_manager.processed_files.find(
                    folder_id=str(self._selected_folder_id)
                )
                
                for row in processed_files:
                    sent_date = row.get("sent_date_time", "")
                    if hasattr(sent_date, 'strftime'):
                        sent_date = sent_date.strftime('%Y-%m-%d %H:%M:%S')
                    
                    writer.writerow([
                        row.get("file_name", ""),
                        sent_date,
                        row.get("copy_destination", ""),
                        row.get("ftp_destination", ""),
                        row.get("email_destination", "")
                    ])
            
            count = self.db_manager.processed_files.count(
                folder_id=str(self._selected_folder_id)
            )
            QMessageBox.information(
                self,
                "Success",
                f"Exported {count} records to:\\n{output_path}"
            )
            
        except Exception as e:
            QMessageBox.critical(
                self,
                "Error",
                f"Export failed: {str(e)}"
            )
    
    def _avoid_duplicate_export_file(self, file_name: str, file_extension: str) -> str:
        """Returns a file path that does not already exist.
        
        If the proposed file path exists, appends a number to the file name
        until an available file path is found.
        
        Args:
            file_name: The base file name (without extension).
            file_extension: The file extension (e.g., ".csv").
            
        Returns:
            A unique file path that doesn't exist.
        """
        full_path = file_name + file_extension
        
        if not os.path.exists(full_path):
            return full_path
        
        i = 1
        while True:
            potential_path = f"{file_name} ({i}){file_extension}"
            if not os.path.exists(potential_path):
                return potential_path
            i += 1
