"""Main window construction and UI state helpers for Qt app."""

from __future__ import annotations

from typing import Any

from PyQt6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QSizePolicy,
    QSpacerItem,
    QVBoxLayout,
    QWidget,
)

from interface.qt.theme import Theme


class QtMainWindowController:
    """Builds and refreshes the main window for ``QtBatchFileSenderApp``."""

    def __init__(self, app: Any) -> None:
        self._app = app

    def configure_window(self) -> None:
        self._app._window.adjustSize()
        self._app._window.setMinimumSize(800, 600)

    def build_main_window(self) -> None:
        central = QWidget()
        self._app._window.setCentralWidget(central)

        main_layout = QHBoxLayout(central)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        options_widget = QWidget()
        options_widget.setFixedWidth(260)
        options_widget.setObjectName("sidebar")
        options_layout = QVBoxLayout(options_widget)
        options_layout.setContentsMargins(
            Theme.SPACING_LG_INT,
            Theme.SPACING_XL_INT,
            Theme.SPACING_LG_INT,
            Theme.SPACING_XL_INT,
        )
        options_layout.setSpacing(Theme.SPACING_SM_INT)

        header_label = QLabel("Batch File Sender")
        header_label.setObjectName("sidebar")
        header_label.setStyleSheet(f"""
            font-size: {Theme.FONT_SIZE_XL};
            font-weight: 700;
            color: {Theme.TEXT_ON_SIDEBAR};
            padding-bottom: {Theme.SPACING_LG};
            letter-spacing: 0.5px;
        """)
        options_layout.addWidget(header_label)

        self._add_sidebar_button(
            options_layout, "Add Directory...", self._app._select_folder
        )
        self._add_sidebar_button(
            options_layout, "Batch Add Directories...", self._app._batch_add_folders
        )
        self._add_sidebar_button(
            options_layout, "Set Defaults...", self._app._set_defaults_popup
        )
        self._add_sidebar_button(
            options_layout,
            "Edit Settings...",
            self._app._show_edit_settings_dialog,
        )
        self._add_sidebar_button(
            options_layout,
            "Maintenance...",
            self._app._show_maintenance_dialog_wrapper,
        )

        self._app._processed_files_button = self._add_sidebar_button(
            options_layout,
            "Processed Files Report...",
            self._app._show_processed_files_dialog_wrapper,
        )

        options_layout.addItem(
            QSpacerItem(0, 0, QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Expanding)
        )

        self._app._allow_resend_button = self._add_sidebar_button(
            options_layout,
            "Enable Resend...",
            self._app._show_resend_dialog,
        )

        separator = QFrame()
        separator.setFixedHeight(1)
        separator.setObjectName("sidebar_separator")
        separator.setStyleSheet(f"""
            QFrame#sidebar_separator {{
                background-color: {Theme.SIDEBAR_OUTLINE};
                margin: {Theme.SPACING_MD} 0;
            }}
        """)
        options_layout.addWidget(separator)

        self._app._process_folder_button = QPushButton("Process All Folders")
        self._app._process_folder_button.setProperty("class", "primary")
        self._app._process_folder_button.clicked.connect(
            lambda: self._app._graphical_process_directories(
                self._app._database.folders_table
            )
        )
        options_layout.addWidget(self._app._process_folder_button)

        options_widget.setStyleSheet(f"""
            QWidget#sidebar {{
                background-color: {Theme.SIDEBAR_BACKGROUND};
                border-right: 1px solid {Theme.SIDEBAR_OUTLINE};
            }}
        """)

        main_layout.addWidget(options_widget)

        self._app._right_panel_widget = QWidget()
        self._app._right_panel_widget.setStyleSheet(f"""
            QWidget {{
                background-color: {Theme.BACKGROUND};
            }}
        """)
        right_layout = QVBoxLayout(self._app._right_panel_widget)
        right_layout.setContentsMargins(
            Theme.SPACING_XXL_INT,
            Theme.SPACING_XL_INT,
            Theme.SPACING_XXL_INT,
            Theme.SPACING_XL_INT,
        )
        right_layout.setSpacing(Theme.SPACING_LG_INT)

        self.build_folder_list(right_layout)
        main_layout.addWidget(self._app._right_panel_widget, stretch=1)

    def build_folder_list(self, parent_layout: QVBoxLayout) -> None:
        from interface.qt.widgets.folder_list_widget import FolderListWidget
        from interface.qt.widgets.search_widget import SearchWidget

        self._app._folder_list_widget = FolderListWidget(
            parent=self._app._right_panel_widget,
            folders_table=self._app._database.folders_table,
            on_send=self._app._send_single,
            on_edit=self._app._edit_folder_selector,
            on_toggle=self._app._toggle_folder,
            on_delete=self._app._delete_folder_entry_wrapper,
            filter_value=self._app._folder_filter,
            total_count_callback=None,
        )

        self._app._search_widget = SearchWidget(
            parent=self._app._right_panel_widget,
            initial_value=self._app._folder_filter,
            on_filter_change=self._app._set_folders_filter,
        )

        if self._app._database.folders_table.count() == 0:
            self._app._search_widget.set_enabled(False)

        parent_layout.addWidget(self._app._folder_list_widget, stretch=1)
        parent_layout.addWidget(self._app._search_widget)

    def refresh_users_list(self) -> None:
        if self._app._right_panel_widget is None:
            return

        layout = self._app._right_panel_widget.layout()

        if self._app._folder_list_widget is not None:
            layout.removeWidget(self._app._folder_list_widget)
            self._app._folder_list_widget.setParent(None)
            self._app._folder_list_widget.deleteLater()
            self._app._folder_list_widget = None

        if self._app._search_widget is not None:
            layout.removeWidget(self._app._search_widget)
            self._app._search_widget.setParent(None)
            self._app._search_widget.deleteLater()
            self._app._search_widget = None

        self._app._build_folder_list(layout)
        self._app._set_main_button_states()

    def set_main_button_states(self) -> None:
        if (
            self._app._process_folder_button is None
            or self._app._processed_files_button is None
            or self._app._allow_resend_button is None
        ):
            return

        folder_count = self._app._database.folders_table.count()
        active_count = self._app._database.folders_table.count(folder_is_active=True)
        processed_count = self._app._database.processed_files.count()

        self._app._process_folder_button.setEnabled(active_count > 0)
        has_processed = processed_count > 0
        self._app._processed_files_button.setEnabled(has_processed)
        self._app._allow_resend_button.setEnabled(has_processed)

    def _add_sidebar_button(
        self, parent_layout: QVBoxLayout, text: str, callback: Any
    ) -> QPushButton:
        button = QPushButton(text)
        button.setObjectName("sidebar")
        button.setProperty("class", "sidebar")
        button.clicked.connect(callback)
        parent_layout.addWidget(button)
        return button
