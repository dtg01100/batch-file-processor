"""Column Builders for Qt Edit Folders Dialog.

Provides classes and methods to construct the various column layouts for the
Qt edit folders dialog. Each column builder is responsible for creating and
configuring the widgets for a specific section of the dialog.
"""

from typing import Any, Callable, Dict, List, Optional

from PyQt6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from interface.qt.theme import Theme
from interface.qt.widgets.search_widget import SearchWidget


class ColumnBuilders:
    """Builder class for creating dialog columns.

    Handles the construction of all column layouts for the edit folders dialog,
    including the others column, folder column, backend column, and EDI column.
    """

    def __init__(
        self,
        fields: Dict[str, Any],
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

    # ------------------------------------------------------------------
    # Column 1 – Others List
    # ------------------------------------------------------------------
    def build_others_column(self) -> QWidget:
        """Build the 'Others' column with folder list and copy config functionality."""
        container = QWidget()
        container.setMinimumWidth(200)
        layout = QVBoxLayout(container)
        layout.setContentsMargins(
            Theme.SPACING_XS_INT,
            Theme.SPACING_XS_INT,
            Theme.SPACING_XS_INT,
            Theme.SPACING_XS_INT,
        )

        layout.addWidget(QLabel("Other Folders:"))

        others_list = QListWidget()
        others_list.setMaximumWidth(180)
        others_list.setAccessibleName("Other folders list")
        others_list.setAccessibleDescription(
            "List of existing folder aliases for copying configuration"
        )
        self.fields["others_list"] = others_list

        aliases: List[str] = []
        if self.alias_provider:
            aliases = sorted(self.alias_provider() or [])
        for alias in aliases:
            others_list.addItem(alias)

        def _filter_others(filter_text: str) -> None:
            text = filter_text.strip().lower()
            for i in range(others_list.count()):
                item = others_list.item(i)
                if item is not None:
                    item.setHidden(bool(text) and text not in item.text().lower())

        others_search = SearchWidget(
            parent=container,
            on_filter_change=_filter_others,
        )
        others_search.setMaximumWidth(180)
        others_search.setAccessibleName("Filter other folders")
        others_search.setAccessibleDescription(
            "Type to filter the folder list by alias"
        )
        self.fields["others_search"] = others_search
        layout.addWidget(others_search)

        layout.addWidget(others_list)

        copy_config_btn = QPushButton("Copy Config")
        copy_config_btn.setAccessibleName("Copy configuration")
        copy_config_btn.setAccessibleDescription(
            "Copy settings from the selected folder in the list"
        )
        if self.on_copy_config:
            copy_config_btn.clicked.connect(self.on_copy_config)
        self.fields["copy_config_btn"] = copy_config_btn
        layout.addWidget(copy_config_btn)

        return container

    # ------------------------------------------------------------------
    # Column 2 – Folder Settings
    # ------------------------------------------------------------------
    def build_folder_column(self) -> QWidget:
        """Build the 'Folder' column with backend selection and folder alias."""
        container = QWidget()
        container.setMinimumWidth(180)
        layout = QVBoxLayout(container)
        layout.setContentsMargins(
            Theme.SPACING_XS_INT,
            Theme.SPACING_XS_INT,
            Theme.SPACING_XS_INT,
            Theme.SPACING_XS_INT,
        )

        layout.addWidget(QLabel("Backends:"))

        copy_backend_check = QCheckBox("Copy Backend")
        copy_backend_check.setAccessibleName("Enable copy backend")
        copy_backend_check.setAccessibleDescription(
            "Enable file copy backend for this folder"
        )
        if self.on_update_backend_states:
            copy_backend_check.toggled.connect(self.on_update_backend_states)
        self.fields["process_backend_copy_check"] = copy_backend_check
        layout.addWidget(copy_backend_check)

        ftp_backend_check = QCheckBox("FTP Backend")
        ftp_backend_check.setAccessibleName("Enable FTP backend")
        ftp_backend_check.setAccessibleDescription("Enable FTP backend for this folder")
        if self.on_update_backend_states:
            ftp_backend_check.toggled.connect(self.on_update_backend_states)
        self.fields["process_backend_ftp_check"] = ftp_backend_check
        layout.addWidget(ftp_backend_check)

        email_backend_check = QCheckBox("Email Backend")
        email_backend_check.setAccessibleName("Enable email backend")
        email_backend_check.setAccessibleDescription(
            "Enable email backend for this folder"
        )
        if self.on_update_backend_states:
            email_backend_check.toggled.connect(self.on_update_backend_states)
        self.fields["process_backend_email_check"] = email_backend_check
        layout.addWidget(email_backend_check)

        if self.folder_config.get("folder_name") != "template":
            alias_group = QGroupBox("Folder Alias")
            alias_layout = QFormLayout(alias_group)
            folder_alias_field = QLineEdit()
            folder_alias_field.setAccessibleName("Folder alias")
            folder_alias_field.setAccessibleDescription(
                "Human-readable folder alias used in UI and reports"
            )
            self.fields["folder_alias_field"] = folder_alias_field
            alias_layout.addRow("Alias:", folder_alias_field)

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
        container.setMinimumWidth(220)
        layout = QVBoxLayout(container)
        layout.setContentsMargins(
            Theme.SPACING_XS_INT,
            Theme.SPACING_XS_INT,
            Theme.SPACING_XS_INT,
            Theme.SPACING_XS_INT,
        )

        copy_group = QGroupBox("Copy Backend Settings")
        copy_layout = QVBoxLayout(copy_group)
        copy_dest_btn = QPushButton("Select Copy Backend Destination Folder...")
        copy_dest_btn.setAccessibleName("Select copy destination")
        copy_dest_btn.setAccessibleDescription(
            "Choose destination directory used by copy backend"
        )
        if self.on_select_copy_dir:
            copy_dest_btn.clicked.connect(self.on_select_copy_dir)
        self.fields["copy_dest_btn"] = copy_dest_btn
        copy_layout.addWidget(copy_dest_btn)
        layout.addWidget(copy_group)

        ftp_group = QGroupBox("FTP Backend Settings")
        ftp_layout = QFormLayout(ftp_group)

        ftp_server_field = QLineEdit()
        ftp_server_field.setAccessibleName("FTP server")
        ftp_server_field.setAccessibleDescription("FTP server hostname or IP address")
        self.fields["ftp_server_field"] = ftp_server_field
        ftp_layout.addRow("FTP Server:", ftp_server_field)

        ftp_port_field = QLineEdit()
        ftp_port_field.setAccessibleName("FTP port")
        ftp_port_field.setAccessibleDescription("FTP server port")
        self.fields["ftp_port_field"] = ftp_port_field
        ftp_layout.addRow("FTP Port:", ftp_port_field)

        ftp_folder_field = QLineEdit()
        ftp_folder_field.setAccessibleName("FTP folder")
        ftp_folder_field.setAccessibleDescription("FTP destination folder path")
        self.fields["ftp_folder_field"] = ftp_folder_field
        ftp_layout.addRow("FTP Folder:", ftp_folder_field)

        ftp_username_field = QLineEdit()
        ftp_username_field.setAccessibleName("FTP username")
        ftp_username_field.setAccessibleDescription("FTP account username")
        self.fields["ftp_username_field"] = ftp_username_field
        ftp_layout.addRow("FTP Username:", ftp_username_field)

        ftp_password_field = QLineEdit()
        ftp_password_field.setEchoMode(QLineEdit.EchoMode.Password)
        ftp_password_field.setAccessibleName("FTP password")
        ftp_password_field.setAccessibleDescription("FTP account password")
        self.fields["ftp_password_field"] = ftp_password_field
        ftp_layout.addRow("FTP Password:", ftp_password_field)
        layout.addWidget(ftp_group)

        email_group = QGroupBox("Email Backend Settings")
        email_layout = QFormLayout(email_group)

        email_recipient_field = QLineEdit()
        email_recipient_field.setAccessibleName("Email recipient")
        email_recipient_field.setAccessibleDescription(
            "Recipient email address or comma separated addresses"
        )
        self.fields["email_recipient_field"] = email_recipient_field
        email_layout.addRow("Recipient Address:", email_recipient_field)

        email_subject_field = QLineEdit()
        email_subject_field.setAccessibleName("Email subject")
        email_subject_field.setAccessibleDescription("Subject line for outgoing emails")
        self.fields["email_sender_subject_field"] = email_subject_field
        email_layout.addRow("Email Subject:", email_subject_field)
        layout.addWidget(email_group)

        layout.addStretch()
        return container

    # ------------------------------------------------------------------
    # Column 4 – EDI Settings (base column, dynamic sections added separately)
    # ------------------------------------------------------------------
    def build_edi_column(self) -> QWidget:
        """Build the base 'EDI' column with force EDI validation and split EDI options."""
        container = QWidget()
        container.setMinimumWidth(260)
        layout = QVBoxLayout(container)
        layout.setContentsMargins(
            Theme.SPACING_XS_INT,
            Theme.SPACING_XS_INT,
            Theme.SPACING_XS_INT,
            Theme.SPACING_XS_INT,
        )

        force_edi_check = QCheckBox("Force EDI Validation")
        force_edi_check.setAccessibleName("Force EDI validation")
        force_edi_check.setAccessibleDescription("Validate EDI input before processing")
        self.fields["force_edi_check_var"] = force_edi_check
        layout.addWidget(force_edi_check)

        split_group = QGroupBox("Split EDI")
        split_layout = QVBoxLayout(split_group)

        split_edi_check = QCheckBox("Split EDI")
        split_edi_check.setAccessibleName("Split EDI")
        split_edi_check.setAccessibleDescription(
            "Enable split EDI output into separate files"
        )
        self.fields["split_edi"] = split_edi_check
        split_layout.addWidget(split_edi_check)

        send_invoices_check = QCheckBox("Send Invoices")
        send_invoices_check.setAccessibleName("Send invoices")
        self.fields["split_edi_send_invoices"] = send_invoices_check
        split_layout.addWidget(send_invoices_check)

        send_credits_check = QCheckBox("Send Credits")
        send_credits_check.setAccessibleName("Send credits")
        self.fields["split_edi_send_credits"] = send_credits_check
        split_layout.addWidget(send_credits_check)

        prepend_dates_check = QCheckBox("Prepend File Dates")
        prepend_dates_check.setAccessibleName("Prepend file dates")
        self.fields["prepend_file_dates"] = prepend_dates_check
        split_layout.addWidget(prepend_dates_check)

        rename_row = QHBoxLayout()
        rename_row.addWidget(QLabel("Rename File:"))
        rename_file_field = QLineEdit()
        rename_file_field.setMaximumWidth(100)
        rename_file_field.setAccessibleName("Rename file")
        rename_file_field.setAccessibleDescription(
            "Optional renamed output filename pattern"
        )
        self.fields["rename_file_field"] = rename_file_field
        rename_row.addWidget(rename_file_field)
        split_layout.addLayout(rename_row)

        cat_row = QHBoxLayout()
        cat_row.addWidget(QLabel("Filter Categories:"))
        filter_categories_field = QLineEdit()
        filter_categories_field.setMaximumWidth(120)
        filter_categories_field.setAccessibleName("Split EDI filter categories")
        filter_categories_field.setAccessibleDescription(
            "ALL or comma separated category numbers"
        )
        filter_categories_field.setToolTip(
            "Enter 'ALL' or a comma separated list of category numbers (e.g., 1,5,12)"
        )
        self.fields["split_edi_filter_categories_entry"] = filter_categories_field
        cat_row.addWidget(filter_categories_field)
        split_layout.addLayout(cat_row)

        mode_row = QHBoxLayout()
        mode_row.addWidget(QLabel("Mode:"))
        filter_mode_combo = QComboBox()
        filter_mode_combo.addItems(["include", "exclude"])
        filter_mode_combo.setAccessibleName("Split EDI filter mode")
        filter_mode_combo.setAccessibleDescription(
            "Choose whether listed categories are included or excluded"
        )
        self.fields["split_edi_filter_mode"] = filter_mode_combo
        mode_row.addWidget(filter_mode_combo)
        split_layout.addLayout(mode_row)

        layout.addWidget(split_group)
        return container
