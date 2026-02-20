"""Layout Builder for Qt Edit Folders Dialog.

Constructs the complete UI layout for the Qt edit folders dialog,
managing widget container creation, spacing, and scroll area setup.
"""

from typing import Dict, Any, Optional, Callable

from PyQt6.QtWidgets import (
    QDialog,
    QVBoxLayout,
    QHBoxLayout,
    QWidget,
    QScrollArea,
    QDialogButtonBox,
    QCheckBox,
    QLabel,
)
from PyQt6.QtCore import Qt

from interface.qt.dialogs.edit_folders.column_builders import ColumnBuilders
from interface.qt.dialogs.edit_folders.dynamic_edi_builder import DynamicEDIBuilder


class UILayoutBuilder:
    """Builder class for constructing the complete dialog UI layout.

    Handles widget container management, scroll area setup, and overall
    dialog layout construction.
    """

    def __init__(
        self,
        dialog: QDialog,
        fields: Dict[str, QWidget],
        folder_config: Dict[str, Any],
        alias_provider: Optional[Callable] = None,
        on_copy_config: Optional[Callable] = None,
        on_select_copy_dir: Optional[Callable] = None,
        on_show_path: Optional[Callable] = None,
        on_update_backend_states: Optional[Callable] = None,
        on_convert_format_changed: Optional[Callable] = None,
        on_ok: Optional[Callable] = None,
        on_cancel: Optional[Callable] = None,
    ):
        """Initialize the UI layout builder.

        Args:
            dialog: Reference to the dialog widget
            fields: Dictionary to store widget references
            folder_config: Current folder configuration
            alias_provider: Callable to get other folder aliases
            on_copy_config: Callback for copy config button
            on_select_copy_dir: Callback for select copy directory button
            on_show_path: Callback for show folder path button
            on_update_backend_states: Callback for backend state updates
            on_convert_format_changed: Callback for convert format changes
            on_ok: Callback for OK button
            on_cancel: Callback for Cancel button
        """
        self.dialog = dialog
        self.fields = fields
        self.folder_config = folder_config
        self.alias_provider = alias_provider
        self.on_copy_config = on_copy_config
        self.on_select_copy_dir = on_select_copy_dir
        self.on_show_path = on_show_path
        self.on_update_backend_states = on_update_backend_states
        self.on_convert_format_changed = on_convert_format_changed
        self.on_ok = on_ok
        self.on_cancel = on_cancel

        # Component instances
        self.column_builders = None
        self.dynamic_edi_builder = None

        # Widget references
        self.active_checkbox = None
        self.dynamic_edi_container = None
        self.dynamic_edi_layout = None

    def build_ui(self):
        """Build the complete dialog UI layout."""
        # Create outer layout with scroll area
        outer_layout = QVBoxLayout(self.dialog)

        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)

        scroll_content = QWidget()
        main_layout = QVBoxLayout(scroll_content)

        # Active state checkbox
        self.active_checkbox = QCheckBox("Folder Is Disabled")
        self.active_checkbox.setStyleSheet(
            "QCheckBox { background-color: red; padding: 4px; }"
        )
        if self.on_update_backend_states:
            self.active_checkbox.toggled.connect(self.on_update_backend_states)
        self.fields["active_checkbutton"] = self.active_checkbox
        main_layout.addWidget(self.active_checkbox)

        # Create column builders
        self.column_builders = ColumnBuilders(
            fields=self.fields,
            folder_config=self.folder_config,
            alias_provider=self.alias_provider,
            on_copy_config=self.on_copy_config,
            on_select_copy_dir=self.on_select_copy_dir,
            on_show_path=self.on_show_path,
            on_update_backend_states=self.on_update_backend_states,
        )

        # Build columns
        columns_layout = QHBoxLayout()

        columns_layout.addWidget(self.column_builders.build_others_column())
        columns_layout.addSpacing(10)
        columns_layout.addWidget(self.column_builders.build_folder_column())
        columns_layout.addSpacing(10)
        columns_layout.addWidget(self.column_builders.build_backend_column())
        columns_layout.addSpacing(10)

        # Build EDI column with dynamic content container
        edi_column = self.column_builders.build_edi_column()
        self._add_dynamic_edi_container(edi_column)
        columns_layout.addWidget(edi_column)

        main_layout.addLayout(columns_layout)

        scroll_area.setWidget(scroll_content)
        outer_layout.addWidget(scroll_area)

        # Add button box
        button_box = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        if self.on_ok:
            button_box.accepted.connect(self.on_ok)
        if self.on_cancel:
            button_box.rejected.connect(self.on_cancel)
        outer_layout.addWidget(button_box)

        # Initialize dynamic EDI builder
        self.dynamic_edi_builder = DynamicEDIBuilder(
            fields=self.fields,
            folder_config=self.folder_config,
            dynamic_container=self.dynamic_edi_container,
            dynamic_layout=self.dynamic_edi_layout,
            on_convert_format_changed=self.on_convert_format_changed,
        )

        # Add EDI options combo to EDI column
        self._add_edi_options_combo(edi_column)

        return self

    def _add_dynamic_edi_container(self, container: QWidget):
        """Add dynamic EDI container to the specified widget."""
        # Find the layout of the container widget
        container_layout = container.layout()
        if not container_layout:
            container_layout = QVBoxLayout(container)

        # Create dynamic EDI container
        self.dynamic_edi_container = QWidget()
        self.dynamic_edi_layout = QVBoxLayout(self.dynamic_edi_container)
        self.dynamic_edi_layout.setContentsMargins(0, 0, 0, 0)

        container_layout.addWidget(self.dynamic_edi_container)
        container_layout.addStretch()

    def _add_edi_options_combo(self, container: QWidget):
        """Add EDI options combo to the EDI column."""
        container_layout = container.layout()
        if not container_layout:
            container_layout = QVBoxLayout(container)

        edi_opt_row = QHBoxLayout()
        edi_opt_row.addWidget(QLabel("EDI Options:"))
        edi_combo = self.dynamic_edi_builder.build_edi_options_combo()
        edi_opt_row.addWidget(edi_combo)
        container_layout.addLayout(edi_opt_row)

    def get_column_builders(self) -> ColumnBuilders:
        """Get the column builders instance."""
        return self.column_builders

    def get_dynamic_edi_builder(self) -> DynamicEDIBuilder:
        """Get the dynamic EDI builder instance."""
        return self.dynamic_edi_builder

    def get_active_checkbox(self) -> QCheckBox:
        """Get the active state checkbox widget."""
        return self.active_checkbox

    def get_dynamic_edi_container(self) -> QWidget:
        """Get the dynamic EDI container widget."""
        return self.dynamic_edi_container

    def get_dynamic_edi_layout(self) -> QVBoxLayout:
        """Get the dynamic EDI layout."""
        return self.dynamic_edi_layout
