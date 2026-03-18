"""Tests for Qt UI service implementations using pytest-qt."""

import pytest
from PyQt6.QtCore import QEvent
from PyQt6.QtWidgets import QApplication, QFileDialog, QMessageBox, QWidget

from interface.qt.theme import Theme
from interface.qt.services.qt_services import QtProgressService, QtUIService

pytestmark = pytest.mark.qt

_StandardButton = QMessageBox.StandardButton


@pytest.mark.qt
class TestQtUIService:

    def test_show_info(self, qtbot, monkeypatch):
        calls = []
        monkeypatch.setattr(
            QMessageBox,
            "information",
            staticmethod(lambda *args: calls.append(args)),
        )
        service = QtUIService(parent=None)
        service.show_info("Title", "Message")
        assert len(calls) == 1
        assert calls[0] == (None, "Title", "Message")

    def test_show_error(self, qtbot, monkeypatch):
        calls = []
        monkeypatch.setattr(
            QMessageBox,
            "critical",
            staticmethod(lambda *args: calls.append(args)),
        )
        service = QtUIService(parent=None)
        service.show_error("Error Title", "Error Message")
        assert len(calls) == 1
        assert calls[0] == (None, "Error Title", "Error Message")

    def test_show_warning(self, qtbot, monkeypatch):
        calls = []
        monkeypatch.setattr(
            QMessageBox,
            "warning",
            staticmethod(lambda *args: calls.append(args)),
        )
        service = QtUIService(parent=None)
        service.show_warning("Warning", "Warning message")
        assert len(calls) == 1
        assert calls[0] == (None, "Warning", "Warning message")

    def test_ask_yes_no_yes(self, qtbot, monkeypatch):
        monkeypatch.setattr(
            QMessageBox,
            "question",
            staticmethod(lambda *args, **kw: _StandardButton.Yes),
        )
        service = QtUIService(parent=None)
        assert service.ask_yes_no("Q", "Question?") is True

    def test_ask_yes_no_no(self, qtbot, monkeypatch):
        monkeypatch.setattr(
            QMessageBox,
            "question",
            staticmethod(lambda *args, **kw: _StandardButton.No),
        )
        service = QtUIService(parent=None)
        assert service.ask_yes_no("Q", "Question?") is False

    def test_ask_ok_cancel_ok(self, qtbot, monkeypatch):
        monkeypatch.setattr(
            QMessageBox,
            "question",
            staticmethod(lambda *args, **kw: _StandardButton.Ok),
        )
        service = QtUIService(parent=None)
        assert service.ask_ok_cancel("Q", "Confirm?") is True

    def test_ask_ok_cancel_cancel(self, qtbot, monkeypatch):
        monkeypatch.setattr(
            QMessageBox,
            "question",
            staticmethod(lambda *args, **kw: _StandardButton.Cancel),
        )
        service = QtUIService(parent=None)
        assert service.ask_ok_cancel("Q", "Confirm?") is False

    def test_convert_filetypes_none(self):
        assert QtUIService._convert_filetypes(None) == ""

    def test_convert_filetypes_single(self):
        result = QtUIService._convert_filetypes([("Text Files", "*.txt")])
        assert result == "Text Files (*.txt)"

    def test_convert_filetypes_multiple(self):
        result = QtUIService._convert_filetypes(
            [
                ("Text Files", "*.txt"),
                ("All Files", "*.*"),
            ]
        )
        assert result == "Text Files (*.txt);;All Files (*.*)"

    def test_ask_directory(self, qtbot, monkeypatch):
        monkeypatch.setattr(
            QFileDialog,
            "getExistingDirectory",
            staticmethod(lambda *args, **kw: "/some/path"),
        )
        service = QtUIService(parent=None)
        result = service.ask_directory("Select", "/initial")
        assert result == "/some/path"

    def test_ask_directory_cancel(self, qtbot, monkeypatch):
        monkeypatch.setattr(
            QFileDialog,
            "getExistingDirectory",
            staticmethod(lambda *args, **kw: ""),
        )
        service = QtUIService(parent=None)
        result = service.ask_directory()
        assert result == ""

    def test_ask_open_filename(self, qtbot, monkeypatch):
        monkeypatch.setattr(
            QFileDialog,
            "getOpenFileName",
            staticmethod(lambda *args, **kw: ("/file.txt", "")),
        )
        service = QtUIService(parent=None)
        result = service.ask_open_filename("Open", filetypes=[("Text", "*.txt")])
        assert result == "/file.txt"

    def test_ask_save_filename_appends_ext(self, qtbot, monkeypatch):
        monkeypatch.setattr(
            QFileDialog,
            "getSaveFileName",
            staticmethod(lambda *args, **kw: ("/file", "")),
        )
        service = QtUIService(parent=None)
        result = service.ask_save_filename(default_ext=".csv")
        assert result == "/file.csv"

    def test_ask_save_filename_no_double_ext(self, qtbot, monkeypatch):
        monkeypatch.setattr(
            QFileDialog,
            "getSaveFileName",
            staticmethod(lambda *args, **kw: ("/file.csv", "")),
        )
        service = QtUIService(parent=None)
        result = service.ask_save_filename(default_ext=".csv")
        assert result == "/file.csv"

    def test_pump_events(self, qtbot, monkeypatch):
        calls = []
        monkeypatch.setattr(
            QApplication,
            "processEvents",
            staticmethod(lambda *args: calls.append(True)),
        )
        service = QtUIService(parent=None)
        service.pump_events()
        assert len(calls) == 1


@pytest.mark.qt
class TestQtProgressService:

    def test_initially_hidden(self, qtbot):
        parent = QWidget()
        qtbot.addWidget(parent)
        parent.show()

        service = QtProgressService(parent)
        assert service.is_visible() is False

    def test_show_makes_visible(self, qtbot):
        parent = QWidget()
        qtbot.addWidget(parent)
        parent.resize(400, 300)
        parent.show()

        service = QtProgressService(parent)
        service.show("Loading...")
        assert service.is_visible() is True

    def test_show_sets_text(self, qtbot):
        parent = QWidget()
        qtbot.addWidget(parent)
        parent.show()

        service = QtProgressService(parent)
        service.show("Loading...")
        assert service._title_label.text() == "Loading..."

    def test_hide_makes_invisible(self, qtbot):
        parent = QWidget()
        qtbot.addWidget(parent)
        parent.show()

        service = QtProgressService(parent)
        service.show("Visible")
        assert service.is_visible() is True
        service.hide()
        assert service.is_visible() is False

    def test_update_message_changes_text(self, qtbot):
        parent = QWidget()
        qtbot.addWidget(parent)
        parent.show()

        service = QtProgressService(parent)
        service.show("Initial")
        service.update_message("Updated")
        assert service._title_label.text() == "Updated"

    def test_update_message_auto_shows(self, qtbot):
        parent = QWidget()
        qtbot.addWidget(parent)
        parent.show()

        service = QtProgressService(parent)
        assert service.is_visible() is False
        service.update_message("Auto-show")
        assert service.is_visible() is True
        assert service._title_label.text() == "Auto-show"

    def test_is_visible_reflects_state(self, qtbot):
        parent = QWidget()
        qtbot.addWidget(parent)
        parent.show()

        service = QtProgressService(parent)
        assert service.is_visible() is False
        service.show("msg")
        assert service.is_visible() is True
        service.hide()
        assert service.is_visible() is False

    def test_resize_syncs_geometry(self, qtbot):
        parent = QWidget()
        qtbot.addWidget(parent)
        parent.resize(400, 300)
        parent.show()

        service = QtProgressService(parent)
        service.show("msg")

        parent.resize(800, 600)
        QApplication.processEvents()

        assert service._overlay.geometry() == parent.rect()

    def test_progress_dialog_property_exposes_overlay(self, qtbot):
        parent = QWidget()
        qtbot.addWidget(parent)
        parent.show()

        service = QtProgressService(parent)
        assert service.progress_dialog is service._overlay

    def test_update_detailed_progress_updates_labels_and_footer(self, qtbot):
        parent = QWidget()
        qtbot.addWidget(parent)
        parent.show()

        service = QtProgressService(parent)
        service.update_detailed_progress(2, 5, 7, 9, "Finalizing...")

        assert service._folder_label.text() == "Folder 2 of 5"
        assert service._file_label.text() == "File 7 of 9"
        assert service._footer_label.text() == "Finalizing..."
        assert service._folder_label.isHidden() is False
        assert service._file_label.isHidden() is False
        assert service._footer_label.isHidden() is False

    def test_update_detailed_progress_hides_labels_when_totals_zero(self, qtbot):
        parent = QWidget()
        qtbot.addWidget(parent)
        parent.show()

        service = QtProgressService(parent)
        service.update_detailed_progress(0, 0, 0, 0, "")

        assert service._folder_label.isHidden() is True
        assert service._file_label.isHidden() is True
        assert service._footer_label.isHidden() is True

    def test_update_progress_switches_from_throbber_to_progressbar(self, qtbot):
        parent = QWidget()
        qtbot.addWidget(parent)
        parent.show()

        service = QtProgressService(parent)
        service.set_indeterminate()
        assert service._throbber.isHidden() is False
        assert service._progress_bar.isHidden() is True

        service.update_progress(42)

        assert service._progress_bar.value() == 42
        assert service._throbber.isHidden() is True
        assert service._progress_bar.isHidden() is False

    def test_set_current_uses_total_to_compute_percentage(self, qtbot):
        parent = QWidget()
        qtbot.addWidget(parent)
        parent.show()

        service = QtProgressService(parent)
        service.set_total(8)
        service.set_current(2)

        assert service._progress_bar.value() == 25

    def test_start_folder_initializes_dispatch_progress_state(self, qtbot):
        parent = QWidget()
        qtbot.addWidget(parent)
        parent.show()

        service = QtProgressService(parent)
        service.start_folder("test_edi", 43)

        assert service._title_label.text() == "Processing folder: test_edi"
        assert service._file_label.text() == "File 0 of 43"

    def test_update_file_updates_percentage_and_file_label(self, qtbot):
        parent = QWidget()
        qtbot.addWidget(parent)
        parent.show()

        service = QtProgressService(parent)
        service.start_folder("test_edi", 10)
        service.update_file(3, 10)

        assert service._progress_bar.value() == 30
        assert service._file_label.text() == "File 3 of 10"

    def test_complete_folder_sets_done_message_and_100_percent(self, qtbot):
        parent = QWidget()
        qtbot.addWidget(parent)
        parent.show()

        service = QtProgressService(parent)
        service.start_folder("test_edi", 5)
        service.complete_folder(success=False)

        assert service._title_label.text() == "Completed with errors: test_edi"
        assert service._progress_bar.value() == 100

    def test_overlay_has_explicit_background_style(self, qtbot):
        parent = QWidget()
        qtbot.addWidget(parent)
        parent.show()

        service = QtProgressService(parent)

        assert service._overlay.objectName() == "qt_progress_overlay"
        assert Theme.OVERLAY_BACKGROUND in service._overlay.styleSheet()

    def test_discovery_and_sending_use_distinct_progress_bars(self, qtbot):
        parent = QWidget()
        qtbot.addWidget(parent)
        parent.show()

        service = QtProgressService(parent)

        service.start_discovery(folder_total=2)
        service.update_discovery_progress(
            folder_num=1,
            folder_total=2,
            folder_name="Folder A",
            pending_for_folder=3,
            pending_total=3,
        )
        service.finish_discovery(total_pending=5)

        assert service._discovery_progress_bar.value() == 100

        service.start_sending(total_files=5, total_folders=2)
        service.start_folder("Folder A", total_files=3, folder_num=1, folder_total=2)
        service.update_file(2, 3)

        assert service._progress_bar.value() == 40
        assert service._send_progress_label.text() == "Sending files (2/5)"
        assert service._folder_label.text() == "Folder 1 of 2"
        assert service._file_label.text() == "File 2 of 3"

    def test_event_filter_handles_missing_parent_attribute(self, qtbot):
        parent = QWidget()
        qtbot.addWidget(parent)
        parent.show()

        service = QtProgressService(parent)
        delattr(service, "_parent")

        event = QEvent(QEvent.Type.Resize)
        # Should not raise even when _parent is missing.
        handled = service.eventFilter(parent, event)
        assert isinstance(handled, bool)
