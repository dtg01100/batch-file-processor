"""Qt reimplementation of the resend interface.

Provides a QDialog that shows folders with processed files and allows
toggling the resend flag on individual files via the toolkit-agnostic
:class:`ResendService`.
"""

from __future__ import annotations

import math
import os
from typing import Optional

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont
from PyQt6.QtWidgets import (
    QCheckBox,
    QDialog,
    QFrame,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)

from interface.services.resend_service import ResendService


class ResendDialog(QDialog):
    """Dialog for toggling resend flags on processed files.

    Args:
        parent: Optional parent widget.
        resend_service: The toolkit-agnostic resend business-logic service.
    """

    def __init__(
        self,
        parent: Optional[QWidget],
        resend_service: ResendService,
    ) -> None:
        super().__init__(parent)
        self._service = resend_service
        self._selected_folder_id: Optional[int] = None
        self._folder_buttons: list[QPushButton] = []

        self.setWindowTitle("Enable Resend")
        self.setModal(True)

        self._build_ui()
        self._populate_folders()

    def _build_ui(self) -> None:
        root_layout = QVBoxLayout(self)

        top_bar = QHBoxLayout()
        top_bar.addWidget(QLabel("File Limit:"))
        self._spin_box = QSpinBox()
        self._spin_box.setMinimum(10)
        self._spin_box.setMaximum(5000)
        self._spin_box.setSingleStep(5)
        self._spin_box.setValue(10)
        self._spin_box.setEnabled(False)
        self._spin_box.valueChanged.connect(self._on_limit_changed)
        top_bar.addWidget(self._spin_box)
        root_layout.addLayout(top_bar)

        separator_top = QFrame()
        separator_top.setFrameShape(QFrame.Shape.HLine)
        separator_top.setFrameShadow(QFrame.Shadow.Sunken)
        root_layout.addWidget(separator_top)

        split_layout = QHBoxLayout()

        self._folders_scroll = QScrollArea()
        self._folders_scroll.setWidgetResizable(True)
        self._folders_scroll.setHorizontalScrollBarPolicy(
            Qt.ScrollBarPolicy.ScrollBarAsNeeded
        )
        self._folders_content = QWidget()
        self._folders_layout = QVBoxLayout(self._folders_content)
        self._folders_layout.setContentsMargins(3, 3, 3, 3)
        self._folders_layout.setSpacing(2)
        self._folders_layout.addStretch(1)
        self._folders_scroll.setWidget(self._folders_content)
        split_layout.addWidget(self._folders_scroll)

        self._files_scroll = QScrollArea()
        self._files_scroll.setWidgetResizable(True)
        self._files_scroll.setHorizontalScrollBarPolicy(
            Qt.ScrollBarPolicy.ScrollBarAsNeeded
        )
        self._files_content = QWidget()
        self._files_layout = QVBoxLayout(self._files_content)
        self._files_layout.setContentsMargins(3, 3, 3, 3)
        self._files_layout.setSpacing(2)
        self._select_label = QLabel("Select a Folder.")
        self._files_layout.addWidget(self._select_label)
        self._files_layout.addStretch(1)
        self._files_scroll.setWidget(self._files_content)
        split_layout.addWidget(self._files_scroll)

        root_layout.addLayout(split_layout, stretch=1)

        separator_bottom = QFrame()
        separator_bottom.setFrameShape(QFrame.Shape.HLine)
        separator_bottom.setFrameShadow(QFrame.Shadow.Sunken)
        root_layout.addWidget(separator_bottom)

        close_btn = QPushButton("Close")
        close_btn.clicked.connect(self.close)
        root_layout.addWidget(close_btn, alignment=Qt.AlignmentFlag.AlignCenter)

    def _populate_folders(self) -> None:
        folder_list = self._service.get_folder_list()
        for folder_id, alias in folder_list:
            btn = QPushButton(alias)
            btn.setCheckable(True)
            btn.setAutoExclusive(True)
            btn.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
            btn.clicked.connect(
                lambda _checked, fid=folder_id: self._on_folder_selected(fid)
            )
            self._folder_buttons.append(btn)
            self._folders_layout.insertWidget(
                self._folders_layout.count() - 1, btn
            )

    def _on_folder_selected(self, folder_id: int) -> None:
        self._selected_folder_id = folder_id
        self._spin_box.setEnabled(True)

        file_count = self._service.count_files_for_folder(folder_id)
        rounded_max = self._round_up_to_5(file_count) if file_count > 10 else 10
        self._spin_box.setMaximum(rounded_max)
        if self._spin_box.value() > rounded_max:
            self._spin_box.setValue(rounded_max)

        self._rebuild_file_list()

    def _on_limit_changed(self) -> None:
        if self._selected_folder_id is not None:
            self._rebuild_file_list()

    def _rebuild_file_list(self) -> None:
        while self._files_layout.count():
            item = self._files_layout.takeAt(0)
            widget = item.widget()
            if widget is not None:
                widget.deleteLater()

        if self._selected_folder_id is None:
            self._select_label = QLabel("Select a Folder.")
            self._files_layout.addWidget(self._select_label)
            self._files_layout.addStretch(1)
            return

        file_list = self._service.get_files_for_folder(
            self._selected_folder_id, limit=self._spin_box.value()
        )

        if not file_list:
            self._files_layout.addWidget(QLabel("No files."))
            self._files_layout.addStretch(1)
            return

        file_names = [os.path.basename(f["file_name"]) for f in file_list]
        max_name_length = len(max(file_names, key=len)) if file_names else 0

        mono_font = QFont("monospace")
        mono_font.setStyleHint(QFont.StyleHint.Monospace)

        for file_info in file_list:
            base_name = os.path.basename(file_info["file_name"])
            label_text = base_name.ljust(max_name_length) + " (" + str(file_info["sent_date_time"]) + ")"

            cb = QCheckBox(label_text)
            cb.setFont(mono_font)
            cb.setChecked(bool(file_info["resend_flag"]))
            cb.toggled.connect(
                lambda checked, fid=file_info["id"]: self._service.set_resend_flag(fid, checked)
            )
            self._files_layout.addWidget(cb)

            sep = QFrame()
            sep.setFrameShape(QFrame.Shape.HLine)
            sep.setFrameShadow(QFrame.Shadow.Sunken)
            self._files_layout.addWidget(sep)

        self._files_layout.addStretch(1)

    @staticmethod
    def _round_up_to_5(n: int) -> int:
        return int(math.ceil(n / 5.0)) * 5

    def keyPressEvent(self, event) -> None:  # noqa: N802
        if event.key() == Qt.Key.Key_Escape:
            self.close()
            return
        super().keyPressEvent(event)
