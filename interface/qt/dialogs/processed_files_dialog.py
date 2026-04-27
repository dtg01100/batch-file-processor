"""Qt reimplementation of the processed files dialog.

Allows the user to select a folder that has processed files, choose an output
directory, and export a CSV report via the shared
:func:`~interface.ui.dialogs.processed_files_dialog.export_processed_report`
helper.
"""

from __future__ import annotations

import os
from typing import Any

from PyQt5.QtCore import Qt
from PyQt5.QtGui import QKeyEvent
from PyQt5.QtWidgets import (
    QButtonGroup,
    QDialogButtonBox,
    QFileDialog,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

from interface.operations.processed_files import export_processed_report
from interface.ports import UIServiceProtocol
from interface.qt.dialogs.base_dialog import BaseDialog
from interface.qt.theme import Theme


class ProcessedFilesDialog(BaseDialog):
    """Modal dialog for exporting processed-file reports per folder."""

    def __init__(
        self,
        parent: QWidget | None,
        database_obj: Any,
        ui_service: UIServiceProtocol | None = None,
    ) -> None:
        self._database_obj = database_obj
        self._ui_service = ui_service

        self._selected_folder_id: int | None = None
        self._output_folder: str = ""
        self._output_folder_confirmed: bool = False
        self._button_group = QButtonGroup()
        self._button_group.setExclusive(True)

        super().__init__(parent, "Processed Files Report", action_mode="close_only")

        self._button_group.setParent(self)

        prior = database_obj.get_oversight_or_default()
        self._output_folder = prior.get("export_processed_folder_prior", "")

        self.setWindowTitle("Processed Files Report")

        self.setMinimumSize(600, 450)
        self._build_ui()
        if self._button_box is not None:
            close_btn = self._button_box.button(QDialogButtonBox.StandardButton.Close)
            if close_btn is not None:
                close_btn.setText("&Close")
                close_btn.setAccessibleName("Close processed files report")
                close_btn.setAccessibleDescription("Close this dialog")

    def _build_ui(self) -> None:
        root_layout = self._body_layout

        body_layout = QHBoxLayout()
        root_layout.addLayout(body_layout, stretch=1)

        body_layout.addWidget(self._build_folder_list(), stretch=1)

        self._actions_container = QWidget()
        self._actions_container.setMinimumWidth(160)
        self._actions_layout = QVBoxLayout(self._actions_container)
        self._actions_layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        self._actions_layout.addWidget(QLabel("Select a Folder."))
        body_layout.addWidget(self._actions_container)

    def _build_folder_list(self) -> QScrollArea:
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setHorizontalScrollBarPolicy(
            Qt.ScrollBarPolicy.ScrollBarAsNeeded,
        )
        scroll_area.setVerticalScrollBarPolicy(
            Qt.ScrollBarPolicy.ScrollBarAsNeeded,
        )

        content = QWidget()
        layout = QVBoxLayout(content)
        layout.setContentsMargins(
            Theme.SPACING_XS_INT,
            Theme.SPACING_XS_INT,
            Theme.SPACING_XS_INT,
            Theme.SPACING_XS_INT,
        )
        layout.setSpacing(Theme.SPACING_XS_INT)

        folder_tuples = self._get_folder_tuples()

        if not folder_tuples:
            label = QLabel("No Folders With Processed Files")
            label.setContentsMargins(Theme.SPACING_MD_INT, 0, Theme.SPACING_MD_INT, 0)
            label.setAccessibleName("No folders with processed files")
            label.setAccessibleDescription(
                "No processed files are available for export"
            )
            layout.addWidget(label)
        else:
            for folder_id, alias in folder_tuples:
                btn = QPushButton(alias)
                btn.setCheckable(True)
                btn.setFlat(True)
                btn.setSizePolicy(
                    QSizePolicy.Policy.Expanding,
                    QSizePolicy.Policy.Fixed,
                )
                self._button_group.addButton(btn, folder_id)
                btn.setAccessibleName(f"Folder {alias}")
                btn.setAccessibleDescription(
                    f"Select folder '{alias}' for report export"
                )
                btn.clicked.connect(
                    lambda _checked, fid=folder_id: self._on_folder_selected(fid),
                )
                layout.addWidget(btn)

        layout.addStretch(1)
        scroll_area.setWidget(content)
        return scroll_area

    def _get_folder_tuples(self) -> list[tuple[int, str]]:
        # Use a single JOIN query to get distinct folder_id -> alias mapping
        # instead of N individual queries
        sql = """
            SELECT DISTINCT pf.folder_id, f.alias
            FROM processed_files pf
            JOIN folders f ON pf.folder_id = f.id
            ORDER BY f.alias
        """
        results = self._database_obj.query(sql)
        return [(row["folder_id"], row["alias"]) for row in results]

    def _on_folder_selected(self, folder_id: int) -> None:
        self._selected_folder_id = folder_id
        self._rebuild_actions()

    def _rebuild_actions(self) -> None:
        def _clear_layout(layout) -> None:
            while layout.count():
                item = layout.takeAt(0)
                if item is None:
                    continue
                widget = item.widget()
                if widget:
                    widget.setParent(None)
                    widget.deleteLater()
                elif item.layout():
                    _clear_layout(item.layout())

        _clear_layout(self._actions_layout)

        choose_btn = QPushButton("&Choose Output Folder")
        choose_btn.clicked.connect(self._choose_output_folder)
        choose_btn.setAccessibleName("Choose output folder")
        choose_btn.setAccessibleDescription(
            "Choose a destination folder for the processed files report"
        )
        self._actions_layout.addWidget(choose_btn)

        self._export_btn = QPushButton("E&xport Processed Report")
        self._export_btn.setEnabled(self._output_folder_confirmed)
        self._export_btn.clicked.connect(self._do_export)
        self._export_btn.setAccessibleName("Export processed files report")
        self._export_btn.setAccessibleDescription(
            "Export a CSV report for the selected folder"
        )
        self._actions_layout.addWidget(self._export_btn)

    def _choose_output_folder(self) -> None:
        initial_dir = self._output_folder
        if not initial_dir or not os.path.exists(initial_dir):
            initial_dir = os.path.expanduser("~")

        if self._ui_service is not None:
            chosen = self._ui_service.ask_directory(
                title="Select Output Folder",
                initial_dir=initial_dir,
            )
        else:
            chosen = QFileDialog.getExistingDirectory(
                self,
                "Select Output Folder",
                initial_dir,
            )

        if not chosen:
            return

        self._output_folder = chosen
        self._output_folder_confirmed = True

        self._database_obj.oversight_and_defaults.upsert(
            dict(id=1, export_processed_folder_prior=chosen),
            ["id"],
        )

        if hasattr(self, "_export_btn"):
            self._export_btn.setEnabled(True)

    def _do_export(self) -> None:
        if self._selected_folder_id is None or not self._output_folder:
            return
        export_processed_report(
            self._selected_folder_id,
            self._output_folder,
            self._database_obj,
        )

    def keyPressEvent(self, event: QKeyEvent) -> None:
        if event.key() == Qt.Key.Key_Escape:
            self.reject()
        else:
            super().keyPressEvent(event)
