"""Tests for Qt UI service implementations using pytest-qt."""
import pytest

from PyQt6.QtWidgets import QApplication, QMessageBox, QFileDialog, QWidget

from interface.qt.services.qt_services import QtUIService, QtProgressService

pytestmark = pytest.mark.qt

_StandardButton = QMessageBox.StandardButton


@pytest.mark.qt
class TestQtUIService:

    def test_show_info(self, qtbot, monkeypatch):
        calls = []
        monkeypatch.setattr(
            QMessageBox, "information",
            staticmethod(lambda *args: calls.append(args)),
        )
        service = QtUIService(parent=None)
        service.show_info("Title", "Message")
        assert len(calls) == 1
        assert calls[0] == (None, "Title", "Message")

    def test_show_error(self, qtbot, monkeypatch):
        calls = []
        monkeypatch.setattr(
            QMessageBox, "critical",
            staticmethod(lambda *args: calls.append(args)),
        )
        service = QtUIService(parent=None)
        service.show_error("Error Title", "Error Message")
        assert len(calls) == 1
        assert calls[0] == (None, "Error Title", "Error Message")

    def test_show_warning(self, qtbot, monkeypatch):
        calls = []
        monkeypatch.setattr(
            QMessageBox, "warning",
            staticmethod(lambda *args: calls.append(args)),
        )
        service = QtUIService(parent=None)
        service.show_warning("Warning", "Warning message")
        assert len(calls) == 1
        assert calls[0] == (None, "Warning", "Warning message")

    def test_ask_yes_no_yes(self, qtbot, monkeypatch):
        monkeypatch.setattr(
            QMessageBox, "question",
            staticmethod(lambda *args, **kw: _StandardButton.Yes),
        )
        service = QtUIService(parent=None)
        assert service.ask_yes_no("Q", "Question?") is True

    def test_ask_yes_no_no(self, qtbot, monkeypatch):
        monkeypatch.setattr(
            QMessageBox, "question",
            staticmethod(lambda *args, **kw: _StandardButton.No),
        )
        service = QtUIService(parent=None)
        assert service.ask_yes_no("Q", "Question?") is False

    def test_ask_ok_cancel_ok(self, qtbot, monkeypatch):
        monkeypatch.setattr(
            QMessageBox, "question",
            staticmethod(lambda *args, **kw: _StandardButton.Ok),
        )
        service = QtUIService(parent=None)
        assert service.ask_ok_cancel("Q", "Confirm?") is True

    def test_ask_ok_cancel_cancel(self, qtbot, monkeypatch):
        monkeypatch.setattr(
            QMessageBox, "question",
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
        result = QtUIService._convert_filetypes([
            ("Text Files", "*.txt"),
            ("All Files", "*.*"),
        ])
        assert result == "Text Files (*.txt);;All Files (*.*)"

    def test_ask_directory(self, qtbot, monkeypatch):
        monkeypatch.setattr(
            QFileDialog, "getExistingDirectory",
            staticmethod(lambda *args, **kw: "/some/path"),
        )
        service = QtUIService(parent=None)
        result = service.ask_directory("Select", "/initial")
        assert result == "/some/path"

    def test_ask_directory_cancel(self, qtbot, monkeypatch):
        monkeypatch.setattr(
            QFileDialog, "getExistingDirectory",
            staticmethod(lambda *args, **kw: ""),
        )
        service = QtUIService(parent=None)
        result = service.ask_directory()
        assert result == ""

    def test_ask_open_filename(self, qtbot, monkeypatch):
        monkeypatch.setattr(
            QFileDialog, "getOpenFileName",
            staticmethod(lambda *args, **kw: ("/file.txt", "")),
        )
        service = QtUIService(parent=None)
        result = service.ask_open_filename("Open", filetypes=[("Text", "*.txt")])
        assert result == "/file.txt"

    def test_ask_save_filename_appends_ext(self, qtbot, monkeypatch):
        monkeypatch.setattr(
            QFileDialog, "getSaveFileName",
            staticmethod(lambda *args, **kw: ("/file", "")),
        )
        service = QtUIService(parent=None)
        result = service.ask_save_filename(default_ext=".csv")
        assert result == "/file.csv"

    def test_ask_save_filename_no_double_ext(self, qtbot, monkeypatch):
        monkeypatch.setattr(
            QFileDialog, "getSaveFileName",
            staticmethod(lambda *args, **kw: ("/file.csv", "")),
        )
        service = QtUIService(parent=None)
        result = service.ask_save_filename(default_ext=".csv")
        assert result == "/file.csv"

    def test_pump_events(self, qtbot, monkeypatch):
        calls = []
        monkeypatch.setattr(
            QApplication, "processEvents",
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
        assert service._label.text() == "Loading..."

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
        assert service._label.text() == "Updated"

    def test_update_message_auto_shows(self, qtbot):
        parent = QWidget()
        qtbot.addWidget(parent)
        parent.show()

        service = QtProgressService(parent)
        assert service.is_visible() is False
        service.update_message("Auto-show")
        assert service.is_visible() is True
        assert service._label.text() == "Auto-show"

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
