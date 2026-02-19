"""Tests for Qt widget implementations using pytest-qt."""
from unittest.mock import MagicMock

import pytest
from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QPushButton


pytestmark = pytest.mark.qt


@pytest.mark.qt
class TestSearchWidget:
    def test_initial_empty_filter(self, qtbot):
        from interface.qt.widgets.search_widget import SearchWidget
        widget = SearchWidget()
        qtbot.addWidget(widget)
        assert widget.value == ""
        assert widget._filter_value == ""

    def test_initial_value_set(self, qtbot):
        from interface.qt.widgets.search_widget import SearchWidget
        widget = SearchWidget(initial_value="test")
        qtbot.addWidget(widget)
        assert widget.entry.text() == "test"

    def test_button_click_emits_signal(self, qtbot):
        from interface.qt.widgets.search_widget import SearchWidget
        widget = SearchWidget()
        qtbot.addWidget(widget)
        widget.entry.setText("hello")
        with qtbot.waitSignal(widget.filter_changed, timeout=1000) as blocker:
            widget.button.click()
        assert blocker.args == ["hello"]

    def test_return_key_emits_signal(self, qtbot):
        from interface.qt.widgets.search_widget import SearchWidget
        widget = SearchWidget()
        qtbot.addWidget(widget)
        widget.entry.setText("world")
        with qtbot.waitSignal(widget.filter_changed, timeout=1000):
            qtbot.keyPress(widget.entry, Qt.Key.Key_Return)

    def test_same_value_does_not_emit(self, qtbot):
        from interface.qt.widgets.search_widget import SearchWidget
        widget = SearchWidget()
        qtbot.addWidget(widget)
        widget.entry.setText("same")
        with qtbot.waitSignal(widget.filter_changed, timeout=1000):
            widget.button.click()
        with qtbot.assertNotEmitted(widget.filter_changed):
            widget.button.click()

    def test_clear_emits_empty_string(self, qtbot):
        from interface.qt.widgets.search_widget import SearchWidget
        widget = SearchWidget()
        qtbot.addWidget(widget)
        widget.entry.setText("test")
        widget.button.click()
        with qtbot.waitSignal(widget.filter_changed, timeout=1000) as blocker:
            widget.clear()
        assert blocker.args == [""]

    def test_set_value_updates_text(self, qtbot):
        from interface.qt.widgets.search_widget import SearchWidget
        widget = SearchWidget()
        qtbot.addWidget(widget)
        widget.set_value("new text")
        assert widget.entry.text() == "new text"

    def test_set_enabled_false(self, qtbot):
        from interface.qt.widgets.search_widget import SearchWidget
        widget = SearchWidget()
        qtbot.addWidget(widget)
        widget.set_enabled(False)
        assert not widget.entry.isEnabled()
        assert not widget.button.isEnabled()

    def test_set_enabled_true(self, qtbot):
        from interface.qt.widgets.search_widget import SearchWidget
        widget = SearchWidget()
        qtbot.addWidget(widget)
        widget.set_enabled(False)
        widget.set_enabled(True)
        assert widget.entry.isEnabled()
        assert widget.button.isEnabled()

    def test_callback_connected(self, qtbot):
        from interface.qt.widgets.search_widget import SearchWidget
        received = []
        widget = SearchWidget(on_filter_change=lambda t: received.append(t))
        qtbot.addWidget(widget)
        widget.entry.setText("callback test")
        widget.button.click()
        assert received == ["callback test"]

    def test_escape_clears_active_filter(self, qtbot):
        from interface.qt.widgets.search_widget import SearchWidget
        widget = SearchWidget()
        qtbot.addWidget(widget)
        widget.show()
        widget.entry.setText("filter")
        widget.button.click()
        with qtbot.waitSignal(widget.filter_changed, timeout=1000) as blocker:
            widget._escape_shortcut.activated.emit()
        assert blocker.args == [""]
        assert widget.entry.text() == ""


@pytest.mark.qt
class TestRightClickMenu:
    
    def test_initialization(self, qtbot):
        from PyQt6.QtWidgets import QLineEdit
        from interface.qt.widgets.extra_widgets import RightClickMenu
        
        line_edit = QLineEdit()
        qtbot.addWidget(line_edit)
        menu = RightClickMenu(line_edit)
        assert menu._parent == line_edit
    
    def test_select_all_shortcut(self, qtbot):
        from PyQt6.QtWidgets import QLineEdit
        from interface.qt.widgets.extra_widgets import RightClickMenu
        
        line_edit = QLineEdit()
        qtbot.addWidget(line_edit)
        line_edit.setText("Test Text")
        menu = RightClickMenu(line_edit)
        
        # Press Ctrl+A
        qtbot.keyClicks(line_edit, "a", Qt.KeyboardModifier.ControlModifier)
        
        assert line_edit.hasSelectedText() is True
        assert line_edit.selectedText() == "Test Text"


@ pytest.mark.qt
class TestVerticalScrolledFrame:
    
    def test_initialization(self, qtbot):
        from interface.qt.widgets.extra_widgets import VerticalScrolledFrame
        frame = VerticalScrolledFrame()
        qtbot.addWidget(frame)
        assert frame.interior is not None
        assert frame.interior_layout is not None
    
    def test_interior_widget(self, qtbot):
        from interface.qt.widgets.extra_widgets import VerticalScrolledFrame
        from PyQt6.QtWidgets import QLabel
        
        frame = VerticalScrolledFrame()
        qtbot.addWidget(frame)
        
        label = QLabel("Test Content")
        frame.interior_layout.addWidget(label)
        
        assert label.parent() == frame.interior
    
    def test_pack_method(self, qtbot):
        from interface.qt.widgets.extra_widgets import VerticalScrolledFrame
        frame = VerticalScrolledFrame()
        qtbot.addWidget(frame)
        
        # Should not raise any errors
        frame.pack(fill=None, expand=False)
        frame.pack(fill="both", expand=True)
        frame.pack()


@ pytest.mark.qt
class TestQtDoingStuffOverlay:
    
    def test_initial_state(self):
        from interface.qt.widgets.doing_stuff_overlay import QtDoingStuffOverlay
        overlay = QtDoingStuffOverlay()
        assert overlay._overlay is None
        assert overlay._message_label is None
        assert overlay._header_label is None
        assert overlay._footer_label is None
    
    def test_make_overlay(self, qtbot):
        from PyQt6.QtWidgets import QWidget
        from interface.qt.widgets.doing_stuff_overlay import QtDoingStuffOverlay
        
        parent = QWidget()
        qtbot.addWidget(parent)
        parent.resize(400, 300)
        parent.show()
        
        overlay = QtDoingStuffOverlay()
        overlay.make_overlay(parent, "Test Message", "Header", "Footer")
        
        assert overlay._overlay is not None
        assert overlay._overlay.isVisible() is True
        assert overlay._message_label is not None
        assert overlay._message_label.text() == "Test Message"
        assert overlay._header_label is not None
        assert overlay._header_label.text() == "Header"
        assert overlay._footer_label is not None
        assert overlay._footer_label.text() == "Footer"
    
    def test_update_overlay(self, qtbot):
        from PyQt6.QtWidgets import QWidget
        from interface.qt.widgets.doing_stuff_overlay import QtDoingStuffOverlay
        
        parent = QWidget()
        qtbot.addWidget(parent)
        parent.resize(400, 300)
        parent.show()
        
        overlay = QtDoingStuffOverlay()
        overlay.make_overlay(parent, "Initial Message", "Initial Header", "Initial Footer")
        
        overlay.update_overlay(parent, "Updated Message", "Updated Header", "Updated Footer")
        
        assert overlay._message_label.text() == "Updated Message"
        assert overlay._header_label.text() == "Updated Header"
        assert overlay._footer_label.text() == "Updated Footer"
    
    def test_destroy_overlay(self, qtbot):
        from PyQt6.QtWidgets import QWidget
        from interface.qt.widgets.doing_stuff_overlay import QtDoingStuffOverlay
        
        parent = QWidget()
        qtbot.addWidget(parent)
        parent.resize(400, 300)
        parent.show()
        
        overlay = QtDoingStuffOverlay()
        overlay.make_overlay(parent, "Test Message", "Header", "Footer")
        overlay.destroy_overlay()
        
        assert overlay._overlay is None
        assert overlay._message_label is None
        assert overlay._header_label is None
        assert overlay._footer_label is None
    
    def test_singleton_functions(self, qtbot):
        from PyQt6.QtWidgets import QWidget
        from interface.qt.widgets.doing_stuff_overlay import make_overlay, update_overlay, destroy_overlay
        
        parent = QWidget()
        qtbot.addWidget(parent)
        parent.resize(400, 300)
        parent.show()
        
        make_overlay(parent, "Singleton Message", "Singleton Header", "Singleton Footer")
        
        # We can't directly access the singleton's attributes, but we can test that it works
        update_overlay(parent, "Updated Singleton", "Updated Header", "Updated Footer")
        
        destroy_overlay()


@ pytest.mark.qt
class TestFolderListWidget:
    def _make_table(self, active=None, inactive=None):
        table = MagicMock()
        active = active or []
        inactive = inactive or []
        all_folders = active + inactive

        def mock_find(**kwargs):
            if kwargs.get("folder_is_active") == "True":
                return iter(active)
            elif kwargs.get("folder_is_active") == "False":
                return iter(inactive)
            elif "order_by" in kwargs:
                return iter(sorted(all_folders, key=lambda x: x.get("alias", "")))
            return iter(all_folders)

        table.find.side_effect = mock_find
        table.count.return_value = len(all_folders)
        return table

    def test_empty_table(self, qtbot):
        from interface.qt.widgets.folder_list_widget import FolderListWidget
        table = self._make_table()
        callbacks = MagicMock(), MagicMock(), MagicMock(), MagicMock()
        widget = FolderListWidget(
            parent=None, folders_table=table,
            on_send=callbacks[0], on_edit=callbacks[1],
            on_disable=callbacks[2], on_delete=callbacks[3],
        )
        qtbot.addWidget(widget)

    def test_active_folder_buttons(self, qtbot):
        from interface.qt.widgets.folder_list_widget import FolderListWidget
        active = [{"id": 1, "alias": "FolderA", "folder_is_active": "True"}]
        table = self._make_table(active=active)
        widget = FolderListWidget(
            parent=None, folders_table=table,
            on_send=MagicMock(), on_edit=MagicMock(),
            on_disable=MagicMock(), on_delete=MagicMock(),
        )
        qtbot.addWidget(widget)
        buttons = widget.findChildren(QPushButton)
        button_texts = [b.text() for b in buttons]
        assert "Send" in button_texts
        assert "<-" in button_texts
        assert any("Edit:" in t for t in button_texts)

    def test_inactive_folder_buttons(self, qtbot):
        from interface.qt.widgets.folder_list_widget import FolderListWidget
        inactive = [{"id": 2, "alias": "FolderB", "folder_is_active": "False"}]
        table = self._make_table(inactive=inactive)
        widget = FolderListWidget(
            parent=None, folders_table=table,
            on_send=MagicMock(), on_edit=MagicMock(),
            on_disable=MagicMock(), on_delete=MagicMock(),
        )
        qtbot.addWidget(widget)
        buttons = widget.findChildren(QPushButton)
        button_texts = [b.text() for b in buttons]
        assert "Delete" in button_texts
        assert any("Edit:" in t for t in button_texts)
        assert "<-" not in button_texts
        assert "Send" not in button_texts

    def test_send_callback(self, qtbot):
        from interface.qt.widgets.folder_list_widget import FolderListWidget
        on_send = MagicMock()
        active = [{"id": 7, "alias": "Sender", "folder_is_active": "True"}]
        table = self._make_table(active=active)
        widget = FolderListWidget(
            parent=None, folders_table=table,
            on_send=on_send, on_edit=MagicMock(),
            on_disable=MagicMock(), on_delete=MagicMock(),
        )
        qtbot.addWidget(widget)
        for btn in widget.findChildren(QPushButton):
            if btn.text() == "Send":
                qtbot.mouseClick(btn, Qt.MouseButton.LeftButton)
                break
        on_send.assert_called_once_with(7)

    def test_edit_callback(self, qtbot):
        from interface.qt.widgets.folder_list_widget import FolderListWidget
        on_edit = MagicMock()
        active = [{"id": 55, "alias": "Editable", "folder_is_active": "True"}]
        table = self._make_table(active=active)
        widget = FolderListWidget(
            parent=None, folders_table=table,
            on_send=MagicMock(), on_edit=on_edit,
            on_disable=MagicMock(), on_delete=MagicMock(),
        )
        qtbot.addWidget(widget)
        for btn in widget.findChildren(QPushButton):
            if "Edit:" in btn.text():
                qtbot.mouseClick(btn, Qt.MouseButton.LeftButton)
                break
        on_edit.assert_called_once_with(55)

    def test_disable_callback(self, qtbot):
        from interface.qt.widgets.folder_list_widget import FolderListWidget
        on_disable = MagicMock()
        active = [{"id": 42, "alias": "Target", "folder_is_active": "True"}]
        table = self._make_table(active=active)
        widget = FolderListWidget(
            parent=None, folders_table=table,
            on_send=MagicMock(), on_edit=MagicMock(),
            on_disable=on_disable, on_delete=MagicMock(),
        )
        qtbot.addWidget(widget)
        for btn in widget.findChildren(QPushButton):
            if btn.text() == "<-":
                qtbot.mouseClick(btn, Qt.MouseButton.LeftButton)
                break
        on_disable.assert_called_once_with(42)

    def test_delete_callback(self, qtbot):
        from interface.qt.widgets.folder_list_widget import FolderListWidget
        on_delete = MagicMock()
        inactive = [{"id": 99, "alias": "ToDelete", "folder_is_active": "False"}]
        table = self._make_table(inactive=inactive)
        widget = FolderListWidget(
            parent=None, folders_table=table,
            on_send=MagicMock(), on_edit=MagicMock(),
            on_disable=MagicMock(), on_delete=on_delete,
        )
        qtbot.addWidget(widget)
        for btn in widget.findChildren(QPushButton):
            if btn.text() == "Delete":
                qtbot.mouseClick(btn, Qt.MouseButton.LeftButton)
                break
        on_delete.assert_called_once_with(99, "ToDelete")

    def test_fuzzy_filter(self, qtbot):
        from unittest.mock import patch
        from interface.qt.widgets.folder_list_widget import FolderListWidget
        active = [
            {"id": 1, "alias": "Alpha", "folder_is_active": "True"},
            {"id": 2, "alias": "Beta", "folder_is_active": "True"},
        ]
        table = self._make_table(active=active)
        with patch("interface.qt.widgets.folder_list_widget.thefuzz.process") as mock_fuzzy:
            mock_fuzzy.extractWithoutOrder.return_value = [("Alpha", 95)]
            widget = FolderListWidget(
                parent=None, folders_table=table,
                on_send=MagicMock(), on_edit=MagicMock(),
                on_disable=MagicMock(), on_delete=MagicMock(),
                filter_value="Alp",
            )
        qtbot.addWidget(widget)
        buttons = widget.findChildren(QPushButton)
        edit_texts = [b.text() for b in buttons if "Edit:" in b.text()]
        assert any("Alpha" in t for t in edit_texts)
        assert not any("Beta" in t for t in edit_texts)

    def test_total_count_callback(self, qtbot):
        from interface.qt.widgets.folder_list_widget import FolderListWidget
        count_cb = MagicMock()
        active = [{"id": 1, "alias": "A", "folder_is_active": "True"}]
        inactive = [{"id": 2, "alias": "B", "folder_is_active": "False"}]
        table = self._make_table(active=active, inactive=inactive)
        widget = FolderListWidget(
            parent=None, folders_table=table,
            on_send=MagicMock(), on_edit=MagicMock(),
            on_disable=MagicMock(), on_delete=MagicMock(),
            total_count_callback=count_cb,
        )
        qtbot.addWidget(widget)
        count_cb.assert_called_once_with(2, 2)

    def test_calculate_max_alias_length(self):
        from interface.qt.widgets.folder_list_widget import FolderListWidget
        assert FolderListWidget._calculate_max_alias_length([]) == 0
        assert FolderListWidget._calculate_max_alias_length([{"alias": "abc"}]) == 3
        assert FolderListWidget._calculate_max_alias_length([{"alias": "a"}, {"alias": "abcde"}]) == 5

    def test_char_width_to_pixels(self):
        from interface.qt.widgets.folder_list_widget import FolderListWidget
        assert FolderListWidget._char_width_to_pixels(10) == 80
        assert FolderListWidget._char_width_to_pixels(10, 10) == 100
