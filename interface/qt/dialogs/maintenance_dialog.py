"""Qt reimplementation of the maintenance dialog.

Provides a QDialog wrapper around the toolkit-agnostic
:class:`MaintenanceFunctions` business logic.
"""

from __future__ import annotations

from typing import Any

from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from interface.operations.maintenance_functions import (
    MaintenanceFunctions,
)  # Toolkit-agnostic business logic
from interface.ports import UIServiceProtocol
from interface.qt.dialogs.base_dialog import BaseDialog
from interface.qt.theme import Theme


class MaintenanceDialog(BaseDialog):
    """Advanced maintenance operations dialog.

    Args:
        parent: Optional parent widget.
        maintenance_functions: Pre-configured business-logic object.
        ui_service: UI service for confirmations and file dialogs.

    """

    def __init__(
        self,
        parent: QWidget | None,
        maintenance_functions: Any,
        ui_service: UIServiceProtocol | None = None,
    ) -> None:
        # Backward compatibility: some legacy call sites/tests still pass a
        # database object directly. If so, construct MaintenanceFunctions here.
        if hasattr(maintenance_functions, "set_operation_callbacks"):
            self._mf = maintenance_functions
        else:
            self._mf = MaintenanceFunctions(database_obj=maintenance_functions)
        self._ui = ui_service
        self._buttons: list[QPushButton] = []
        super().__init__(parent, "Maintenance Functions", action_mode="none")

        self.setMinimumSize(600, 400)

        self._mf.set_operation_callbacks(
            self._on_operation_start, self._on_operation_end
        )

    def body(self, parent: QWidget) -> QWidget | None:
        button_layout = QVBoxLayout()
        buttons = [
            ("Move all to active (Skips Settings Validation)", self._set_all_active),
            ("Move all to inactive", self._set_all_inactive),
            ("Clear all resend flags", self._clear_resend_flags),
            ("Clear queued emails", self._clear_queued_emails),
            ("Mark all in active as processed", self._mark_active_as_processed),
            ("Remove all inactive configurations", self._remove_inactive_folders),
            ("Clear sent file records", self._clear_processed_files_log),
            ("Import old configurations...", self._import_old_configurations),
        ]
        for text, slot in buttons:
            btn = QPushButton(text)
            btn.clicked.connect(slot)
            btn.setAccessibleName(text)
            btn.setAccessibleDescription(f"Run maintenance operation: {text}")
            button_layout.addWidget(btn)
            self._buttons.append(btn)

        root_layout = QHBoxLayout()
        root_layout.addLayout(button_layout)

        warning_label = QLabel("WARNING:\nFOR\nADVANCED\nUSERS\nONLY!")
        warning_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        warning_label.setStyleSheet(
            f"color: {Theme.ERROR}; font-weight: bold; font-size: 14pt;"
        )
        root_layout.addWidget(warning_label)

        parent.layout().addLayout(root_layout)

        return None

    def _set_buttons_enabled(self, *, enabled: bool) -> None:
        for btn in self._buttons:
            btn.setEnabled(enabled)

    def _on_operation_start(self) -> None:
        self._set_buttons_enabled(enabled=False)

    def _on_operation_end(self) -> None:
        self._set_buttons_enabled(enabled=True)

    def _set_all_active(self) -> None:
        self._mf.set_all_active()

    def _set_all_inactive(self) -> None:
        self._mf.set_all_inactive()

    def _clear_resend_flags(self) -> None:
        self._mf.clear_resend_flags()

    def _clear_queued_emails(self) -> None:
        self._set_buttons_enabled(enabled=False)
        try:
            self._mf.get_database().emails_table.delete()
        finally:
            self._set_buttons_enabled(enabled=True)

    def _mark_active_as_processed(self) -> None:
        self._mf.mark_active_as_processed()

    def _remove_inactive_folders(self) -> None:
        self._mf.remove_inactive_folders()

    def _clear_processed_files_log(self) -> None:
        self._mf.clear_processed_files_log()

    def _import_old_configurations(self) -> None:
        if self._ui is None:
            return
        path = self._ui.ask_open_filename(title="Select backup file to import")
        if path:
            self._mf.database_import_wrapper(path)

    def keyPressEvent(self, a0) -> None:  # noqa: N802
        event = a0
        if event.key() == Qt.Key.Key_Escape:
            self.reject()
            return
        super().keyPressEvent(event)

    @classmethod
    def open_dialog(
        cls,
        parent: QWidget | None,
        maintenance_functions: MaintenanceFunctions,
        ui_service: UIServiceProtocol | None = None,
    ) -> MaintenanceDialog | None:
        if ui_service and not ui_service.ask_ok_cancel(
            "Maintenance",
            "Maintenance window is for advanced users only, potential for data "
            "loss if incorrectly used. Are you sure you want to continue?",
        ):
            return None
        dialog = cls(parent, maintenance_functions, ui_service)
        dialog.exec()
        return dialog
