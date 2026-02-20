"""Column Builders for Qt Edit Folders Dialog.

Provides classes and methods to construct the various column layouts for the
Qt edit folders dialog. Each column builder is responsible for creating and
configuring the widgets for a specific section of the dialog.
"""

from typing import Dict, List, Optional, Callable, Any

from PyQt6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QLabel,
    QListWidget,
    QPushButton,
    QGroupBox,
    QFormLayout,
    QCheckBox,
    QLineEdit,
)
from PyQt6.QtCore import Qt


class ColumnBuilders:
    """Builder class for creating dialog columns.

    Handles the construction of all column layouts for the edit folders dialog,
    including the others column, folder column, backend column, and EDI column.
    """

    def __init__(
        self,
        fields: Dict[str, QWidget],
        folder_config: Dict[str, Any],
        alias_provider: Optional[Callable] = None,
        on_copy_config: Optional[Callable] = None,
        on_select_copy_dir: Optional[Callable] = None,
        on_show_path: Optional[Callable] = None,
        on_update_backend_states: Optional[Callable] = None,
    ):
        """Initialize column builders.

        Args:
            fields: Dictionary to store widget references
            folder_config: Current folder configuration
            alias_provider: Callable to get other folder aliases
            on_copy_config: Callback for copy config button
            on_select_copy_dir: Callback for select copy directory button
            on_show_path: Callback for show folder path button
            on_update_backend_states: Callback for backend state updates
        """
        self.fields = fields
        self.folder_config = folder_config
        self.alias_provider = alias_provider
        self.on_copy_config = on_copy_config
        self.on_select_copy_dir = on_select_copy_dir
        self.on_show_path = on_show_path
        self.on_update_backend_states = on_update_backend_states

        # Widget references
        self.others_list = None
        self.copy_config_btn = None
        self.copy_backend_check = None
        self.ftp_backend_check = None
        self.email_backend_check = None
        self.folder_alias_field = None
        self.copy_dest_btn = None
        self.ftp_server_field = None
        self.ftp_port_field = None
        self.ftp_folder_field = None
        self.ftp_username_field = None
        self.ftp_password_field = None
        self.email_recipient_field = None
        self.email_subject_field = None
        self.force_edi_check = None
        self.split_edi_check = None
        self.send_invoices_check = None

    # ------------------------------------------------------------------
    # Column 1 – Others List
    # ------------------------------------------------------------------
    def build_others_column(self) -> QWidget:
        """Build the 'Others' column with folder list and copy config functionality."""
        container = QWidget()
        layout = QVBoxLayout(container)
        layout.setContentsMargins(2, 2, 2, 2)

        layout.addWidget(QLabel("Other Folders:"))

        self.others_list = QListWidget()
        self.others_list.setMaximumWidth(180)
        aliases: List[str] = []
        if self.alias_provider:
            aliases = sorted(self.alias_provider() or [])
        for alias in aliases:
            self.others_list.addItem(alias)
        layout.addWidget(self.others_list)

        self.copy_config_btn = QPushButton("Copy Config")
        if self.on_copy_config:
            self.copy_config_btn.clicked.connect(self.on_copy_config)
        layout.addWidget(self.copy_config_btn)

        return container

    # ------------------------------------------------------------------
    # Column 2 – Folder Settings
    # ------------------------------------------------------------------
    def build_folder_column(self) -> QWidget:
        """Build the 'Folder' column with backend selection and folder alias."""
        container = QWidget()
        layout = QVBoxLayout(container)
        layout.setContentsMargins(2, 2, 2, 2)

        layout.addWidget(QLabel("Backends:"))

        self.copy_backend_check = QCheckBox("Copy Backend")
        if self.on_update_backend_states:
            self.copy_backend_check.toggled.connect(self.on_update_backend_states)
        self.fields["process_backend_copy_check"] = self.copy_backend_check
        layout.addWidget(self.copy_backend_check)

        self.ftp_backend_check = QCheckBox("FTP Backend")
        if self.on_update_backend_states:
            self.ftp_backend_check.toggled.connect(self.on_update_backend_states)
        self.fields["process_backend_ftp_check"] = self.ftp_backend_check
        layout.addWidget(self.ftp_backend_check)

        self.email_backend_check = QCheckBox("Email Backend")
        if self.on_update_backend_states:
            self.email_backend_check.toggled.connect(self.on_update_backend_states)
        self.fields["process_backend_email_check"] = self.email_backend_check
        layout.addWidget(self.email_backend_check)

        if self.folder_config.get("folder_name") != "template":
            alias_group = QGroupBox("Folder Alias")
            alias_layout = QFormLayout(alias_group)
            self.folder_alias_field = QLineEdit()
            self.fields["folder_alias_field"] = self.folder_alias_field
            alias_layout.addRow("Alias:", self.folder_alias_field)

            show_path_btn = QPushButton("Show Folder Path")
            if self.on_show_path:
                show_path_btn.clicked.connect(self.on_show_path)
            alias_layout.addRow(show_path_btn)
            layout.addWidget(alias_group)

        layout.addStretch()
        return container

    # ------------------------------------------------------------------
    # Column 3 – Backend Settings
    # ------------------------------------------------------------------
    def build_backend_column(self) -> QWidget:
        """Build the 'Backend' column with copy, FTP, and email settings."""
        container = QWidget()
        layout = QVBoxLayout(container)
        layout.setContentsMargins(2, 2, 2, 2)

        copy_group = QGroupBox("Copy Backend Settings")
        copy_layout = QVBoxLayout(copy_group)
        self.copy_dest_btn = QPushButton("Select Copy Backend Destination Folder...")
        if self.on_select_copy_dir:
            self.copy_dest_btn.clicked.connect(self.on_select_copy_dir)
        copy_layout.addWidget(self.copy_dest_btn)
        layout.addWidget(copy_group)

        ftp_group = QGroupBox("FTP Backend Settings")
        ftp_layout = QFormLayout(ftp_group)
        self.ftp_server_field = QLineEdit()
        self.fields["ftp_server_field"] = self.ftp_server_field
        ftp_layout.addRow("FTP Server:", self.ftp_server_field)

        self.ftp_port_field = QLineEdit()
        self.fields["ftp_port_field"] = self.ftp_port_field
        ftp_layout.addRow("FTP Port:", self.ftp_port_field)

        self.ftp_folder_field = QLineEdit()
        self.fields["ftp_folder_field"] = self.ftp_folder_field
        ftp_layout.addRow("FTP Folder:", self.ftp_folder_field)

        self.ftp_username_field = QLineEdit()
        self.fields["ftp_username_field"] = self.ftp_username_field
        ftp_layout.addRow("FTP Username:", self.ftp_username_field)

        self.ftp_password_field = QLineEdit()
        self.ftp_password_field.setEchoMode(QLineEdit.EchoMode.Password)
        self.fields["ftp_password_field"] = self.ftp_password_field
        ftp_layout.addRow("FTP Password:", self.ftp_password_field)
        layout.addWidget(ftp_group)

        email_group = QGroupBox("Email Backend Settings")
        email_layout = QFormLayout(email_group)
        self.email_recipient_field = QLineEdit()
        self.fields["email_recepient_field"] = self.email_recipient_field
        email_layout.addRow("Recipient Address:", self.email_recipient_field)

        self.email_subject_field = QLineEdit()
        self.fields["email_sender_subject_field"] = self.email_subject_field
        email_layout.addRow("Email Subject:", self.email_subject_field)
        layout.addWidget(email_group)

        layout.addStretch()
        return container

    # ------------------------------------------------------------------
    # Column 4 – EDI Settings (base column, dynamic sections added separately)
    # ------------------------------------------------------------------
    def build_edi_column(self) -> QWidget:
        """Build the base 'EDI' column with force EDI validation and split EDI options."""
        container = QWidget()
        layout = QVBoxLayout(container)
        layout.setContentsMargins(2, 2, 2, 2)

        self.force_edi_check = QCheckBox("Force EDI Validation")
        self.fields["force_edi_check_var"] = self.force_edi_check
        layout.addWidget(self.force_edi_check)

        split_group = QGroupBox("Split EDI")
        split_layout = QVBoxLayout(split_group)

        self.split_edi_check = QCheckBox("Split EDI")
        self.fields["split_edi"] = self.split_edi_check
        split_layout.addWidget(self.split_edi_check)

        self.send_invoices_check = QCheckBox("Send Invoices")
        self.fields["split_edi_send_invoices"] = self.send_invoices_check
        split_layout.addWidget(self.send_invoices_check)

        return container
