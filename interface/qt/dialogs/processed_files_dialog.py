"""Qt reimplementation of the processed files dialog.

Allows the user to select a folder that has processed files, choose an output
directory, and export a CSV report via the shared
:func:`~interface.ui.dialogs.processed_files_dialog.export_processed_report`
helper.
"""

from __future__ import annotations

import os
from operator import itemgetter
from typing import Any, List, Optional, Tuple

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QButtonGroup,
    QDialog,
    QFileDialog,
    QFrame,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

from interface.ports import UIServiceProtocol
from interface.ui.dialogs.processed_files_dialog import export_processed_report


class ProcessedFilesDialog(QDialog):
    """Modal dialog for exporting processed-file reports per folder."""

    def __init__(
        self,
        parent: Optional[QWidget],
        database_obj: Any,
        ui_service: Optional[UIServiceProtocol] = None,
    ) -> None:
        super().__init__(parent)
        self._database_obj = database_obj
        self._ui_service = ui_service

        self._selected_folder_id: Optional[int] = None
        self._output_folder: str = ""
        self._output_folder_confirmed: bool = False

        prior = database_obj.oversight_and_defaults.find_one(id=1)
        if prior:
            self._output_folder = prior.get("export_processed_folder_prior", "")

        self.setWindowTitle("Processed Files Report")
        self.setModal(True)

        self._button_group = QButtonGroup(self)
        self._button_group.setExclusive(True)

        self.setMinimumSize(600, 450)
        self._build_ui()

    def _build_ui(self) -> None:
        root_layout = QVBoxLayout(self)

        body_layout = QHBoxLayout()
        root_layout.addLayout(body_layout, stretch=1)

        body_layout.addWidget(self._build_folder_list(), stretch=1)

        self._actions_container = QWidget()
        self._actions_layout = QVBoxLayout(self._actions_container)
        self._actions_layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        self._actions_layout.addWidget(QLabel("Select a Folder."))
        body_layout.addWidget(self._actions_container)

        separator = QFrame()
        separator.setFrameShape(QFrame.Shape.HLine)
        separator.setFrameShadow(QFrame.Shadow.Sunken)
        root_layout.addWidget(separator)

        close_btn = QPushButton("Close")
        close_btn.clicked.connect(self.close)
        root_layout.addWidget(close_btn)

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
        layout.setContentsMargins(3, 3, 3, 3)
        layout.setSpacing(2)

        folder_tuples = self._get_folder_tuples()

        if not folder_tuples:
            label = QLabel("No Folders With Processed Files")
            label.setContentsMargins(10, 0, 10, 0)
            layout.addWidget(label)
        else:
            for folder_id, alias in folder_tuples:
                btn = QPushButton(alias)
                btn.setCheckable(True)
                btn.setFlat(True)
                btn.setSizePolicy(
                    QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed,
                )
                self._button_group.addButton(btn, folder_id)
                btn.clicked.connect(
                    lambda _checked, fid=folder_id: self._on_folder_selected(fid),
                )
                layout.addWidget(btn)

        layout.addStretch(1)
        scroll_area.setWidget(content)
        return scroll_area

    def _get_folder_tuples(self) -> List[Tuple[int, str]]:
        distinct_ids: List[int] = [
            row["folder_id"]
            for row in self._database_obj.processed_files.distinct("folder_id")
        ]

        tuples: List[Tuple[int, str]] = []
        for fid in distinct_ids:
            folder = self._database_obj.folders_table.find_one(id=str(fid))
            if folder is None:
                continue
            tuples.append((fid, folder["alias"]))

        tuples.sort(key=itemgetter(1))
        return tuples

    def _on_folder_selected(self, folder_id: int) -> None:
        self._selected_folder_id = folder_id
        self._rebuild_actions()

    def _rebuild_actions(self) -> None:
        while self._actions_layout.count():
            item = self._actions_layout.takeAt(0)
            widget = item.widget()
            if widget is not None:
                widget.deleteLater()

        choose_btn = QPushButton("Choose Output Folder")
        choose_btn.clicked.connect(self._choose_output_folder)
        self._actions_layout.addWidget(choose_btn)

        self._export_btn = QPushButton("Export Processed Report")
        self._export_btn.setEnabled(self._output_folder_confirmed)
        self._export_btn.clicked.connect(self._do_export)
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
                self, "Select Output Folder", initial_dir,
            )

        if not chosen:
            return

        self._output_folder = chosen
        self._output_folder_confirmed = True

        self._database_obj.oversight_and_defaults.update(
            dict(id=1, export_processed_folder_prior=chosen), ["id"],
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

    def keyPressEvent(self, event) -> None:  # noqa: N802
        if event.key() == Qt.Key.Key_Escape:
            self.close()
        else:
            super().keyPressEvent(event)
