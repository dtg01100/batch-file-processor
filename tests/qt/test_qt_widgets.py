"""Tests for Qt widget implementations using pytest-qt with real widgets.

These tests use real Qt widgets in offscreen mode instead of mocks.
Database operations use real DatabaseObj with temporary SQLite databases.
"""

import pytest
from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QPushButton

pytestmark = pytest.mark.qt


@pytest.mark.qt
class TestSearchWidget:
    """Tests for SearchWidget using real Qt widgets."""

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

    def test_same_value_does_not_emit(self, qtbot):
        from interface.qt.widgets.search_widget import SearchWidget

        widget = SearchWidget()
        qtbot.addWidget(widget)
        # setText triggers textChanged, so filter_value is now "same"
        widget.entry.setText("same")
        # Setting the same value again should not emit
        with qtbot.assertNotEmitted(widget.filter_changed):
            widget.entry.setText("same")

    def test_clear_emits_empty_string(self, qtbot):
        from interface.qt.widgets.search_widget import SearchWidget

        widget = SearchWidget()
        qtbot.addWidget(widget)
        widget.entry.setText("test")
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

    def test_set_enabled_true(self, qtbot):
        from interface.qt.widgets.search_widget import SearchWidget

        widget = SearchWidget()
        qtbot.addWidget(widget)
        widget.set_enabled(False)
        widget.set_enabled(True)
        assert widget.entry.isEnabled()

    def test_callback_connected(self, qtbot):
        from interface.qt.widgets.search_widget import SearchWidget

        received = []
        widget = SearchWidget(on_filter_change=lambda t: received.append(t))
        qtbot.addWidget(widget)
        # setText triggers callback via textChanged (after debounce)
        with qtbot.waitSignal(widget.filter_changed, timeout=1000):
            widget.entry.setText("callback test")
        assert received == ["callback test"]

    def test_escape_clears_active_filter(self, qtbot):
        from interface.qt.widgets.search_widget import SearchWidget

        widget = SearchWidget()
        qtbot.addWidget(widget)
        widget.show()
        widget.entry.setText("filter")
        with qtbot.waitSignal(widget.filter_changed, timeout=1000) as blocker:
            widget._escape_shortcut.activated.emit()
        assert blocker.args == [""]
        assert widget.entry.text() == ""

    def test_text_changed_emits_signal(self, qtbot):
        from interface.qt.widgets.search_widget import SearchWidget

        widget = SearchWidget()
        qtbot.addWidget(widget)
        with qtbot.waitSignal(widget.filter_changed, timeout=1000) as blocker:
            widget.entry.setText("type")
        assert blocker.args == ["type"]


@pytest.mark.qt
class TestFolderListWidget:
    """Tests for FolderListWidget using real Qt widgets and real database."""

    def _create_test_folders(self, temp_database):
        """Helper to create test folders in the real database."""
        active_folders = [
            {
                "id": 1,
                "alias": "ActiveFolder1",
                "folder_name": "/path/1",
                "folder_is_active": "True",
            },
            {
                "id": 2,
                "alias": "ActiveFolder2",
                "folder_name": "/path/2",
                "folder_is_active": "True",
            },
        ]
        inactive_folders = [
            {
                "id": 3,
                "alias": "InactiveFolder1",
                "folder_name": "/path/3",
                "folder_is_active": "False",
            },
        ]
        for folder in active_folders + inactive_folders:
            temp_database.folders_table.insert(folder)
        return temp_database

    def test_empty_table(self, qtbot, temp_database):
        from interface.qt.widgets.folder_list_widget import FolderListWidget

        callbacks = {"send": [], "edit": [], "toggle": [], "delete": []}
        widget = FolderListWidget(
            parent=None,
            folders_table=temp_database.folders_table,
            on_send=lambda fid: callbacks["send"].append(fid),
            on_edit=lambda fid: callbacks["edit"].append(fid),
            on_toggle=lambda fid: callbacks["toggle"].append(fid),
            on_delete=lambda fid, name: callbacks["delete"].append((fid, name)),
        )
        qtbot.addWidget(widget)
        # Should render without errors even with empty table

    def test_active_folder_buttons(self, qtbot, temp_database):
        from interface.qt.widgets.folder_list_widget import FolderListWidget

        temp_database.folders_table.insert(
            {
                "id": 1,
                "alias": "FolderA",
                "folder_name": "/path/a",
                "folder_is_active": "True",
            }
        )

        widget = FolderListWidget(
            parent=None,
            folders_table=temp_database.folders_table,
            on_send=lambda fid: None,
            on_edit=lambda fid: None,
            on_toggle=lambda fid: None,
            on_delete=lambda fid, name: None,
        )
        qtbot.addWidget(widget)
        buttons = widget.findChildren(QPushButton)
        button_texts = [b.text() for b in buttons]
        assert "Send" in button_texts
        assert "\u25cf" in button_texts  # ● active toggle button
        assert any("Edit:" in t for t in button_texts)

    def test_inactive_folder_buttons(self, qtbot, temp_database):
        from interface.qt.widgets.folder_list_widget import FolderListWidget

        temp_database.folders_table.insert(
            {
                "id": 2,
                "alias": "FolderB",
                "folder_name": "/path/b",
                "folder_is_active": "False",
            }
        )

        widget = FolderListWidget(
            parent=None,
            folders_table=temp_database.folders_table,
            on_send=lambda fid: None,
            on_edit=lambda fid: None,
            on_toggle=lambda fid: None,
            on_delete=lambda fid, name: None,
        )
        qtbot.addWidget(widget)
        buttons = widget.findChildren(QPushButton)
        button_texts = [b.text() for b in buttons]
        assert "Delete" in button_texts
        assert any("Edit:" in t for t in button_texts)
        assert "<-" not in button_texts
        assert "Send" not in button_texts

    def test_send_callback(self, qtbot, temp_database):
        from interface.qt.widgets.folder_list_widget import FolderListWidget

        received = []
        temp_database.folders_table.insert(
            {
                "id": 7,
                "alias": "Sender",
                "folder_name": "/path/s",
                "folder_is_active": "True",
            }
        )

        widget = FolderListWidget(
            parent=None,
            folders_table=temp_database.folders_table,
            on_send=lambda fid: received.append(fid),
            on_edit=lambda fid: None,
            on_toggle=lambda fid: None,
            on_delete=lambda fid, name: None,
        )
        qtbot.addWidget(widget)
        for btn in widget.findChildren(QPushButton):
            if btn.text() == "Send":
                qtbot.mouseClick(btn, Qt.MouseButton.LeftButton)
                break
        assert received == [7]

    def test_edit_callback(self, qtbot, temp_database):
        from interface.qt.widgets.folder_list_widget import FolderListWidget

        received = []
        temp_database.folders_table.insert(
            {
                "id": 55,
                "alias": "Editable",
                "folder_name": "/path/e",
                "folder_is_active": "True",
            }
        )

        widget = FolderListWidget(
            parent=None,
            folders_table=temp_database.folders_table,
            on_send=lambda fid: None,
            on_edit=lambda fid: received.append(fid),
            on_toggle=lambda fid: None,
            on_delete=lambda fid, name: None,
        )
        qtbot.addWidget(widget)
        for btn in widget.findChildren(QPushButton):
            if "Edit:" in btn.text():
                qtbot.mouseClick(btn, Qt.MouseButton.LeftButton)
                break
        assert received == [55]

    def test_disable_callback(self, qtbot, temp_database):
        from interface.qt.widgets.folder_list_widget import FolderListWidget

        received = []
        temp_database.folders_table.insert(
            {
                "id": 42,
                "alias": "Target",
                "folder_name": "/path/t",
                "folder_is_active": "True",
            }
        )

        widget = FolderListWidget(
            parent=None,
            folders_table=temp_database.folders_table,
            on_send=lambda fid: None,
            on_edit=lambda fid: None,
            on_toggle=lambda fid: received.append(fid),
            on_delete=lambda fid, name: None,
        )
        qtbot.addWidget(widget)
        for btn in widget.findChildren(QPushButton):
            if btn.text() == "\u25cf":  # ● active toggle button
                qtbot.mouseClick(btn, Qt.MouseButton.LeftButton)
                break
        assert received == [42]

    def test_delete_callback(self, qtbot, temp_database):
        from interface.qt.widgets.folder_list_widget import FolderListWidget

        received = []
        temp_database.folders_table.insert(
            {
                "id": 99,
                "alias": "ToDelete",
                "folder_name": "/path/d",
                "folder_is_active": "False",
            }
        )

        widget = FolderListWidget(
            parent=None,
            folders_table=temp_database.folders_table,
            on_send=lambda fid: None,
            on_edit=lambda fid: None,
            on_toggle=lambda fid: None,
            on_delete=lambda fid, name: received.append((fid, name)),
        )
        qtbot.addWidget(widget)
        for btn in widget.findChildren(QPushButton):
            if btn.text() == "Delete":
                qtbot.mouseClick(btn, Qt.MouseButton.LeftButton)
                break
        assert received == [(99, "ToDelete")]

    def test_fuzzy_filter(self, qtbot, temp_database):
        from interface.qt.widgets.folder_list_widget import FolderListWidget

        temp_database.folders_table.insert(
            {"id": 1, "alias": "Alpha", "folder_name": "/a", "folder_is_active": "True"}
        )
        temp_database.folders_table.insert(
            {"id": 2, "alias": "Beta", "folder_name": "/b", "folder_is_active": "True"}
        )

        widget = FolderListWidget(
            parent=None,
            folders_table=temp_database.folders_table,
            on_send=lambda fid: None,
            on_edit=lambda fid: None,
            on_toggle=lambda fid: None,
            on_delete=lambda fid, name: None,
            filter_value="Alp",
        )
        qtbot.addWidget(widget)
        buttons = widget.findChildren(QPushButton)
        visible_edit_texts = [
            b.text()
            for b in buttons
            if "Edit:" in b.text() and not b.parent().isHidden()
        ]
        # Fuzzy filter should show Alpha, hide Beta
        assert any("Alpha" in t for t in visible_edit_texts)
        assert not any("Beta" in t for t in visible_edit_texts)

    def test_total_count_callback(self, qtbot, temp_database):
        from interface.qt.widgets.folder_list_widget import FolderListWidget

        received = []
        temp_database.folders_table.insert(
            {"id": 1, "alias": "A", "folder_name": "/a", "folder_is_active": "True"}
        )
        temp_database.folders_table.insert(
            {"id": 2, "alias": "B", "folder_name": "/b", "folder_is_active": "False"}
        )

        widget = FolderListWidget(
            parent=None,
            folders_table=temp_database.folders_table,
            on_send=lambda fid: None,
            on_edit=lambda fid: None,
            on_toggle=lambda fid: None,
            on_delete=lambda fid, name: None,
            total_count_callback=lambda total, active: received.append((total, active)),
        )
        qtbot.addWidget(widget)
        assert received == [(2, 2)]

    def test_calculate_edit_button_min_width(self, qtbot, temp_database):
        from interface.qt.widgets.folder_list_widget import FolderListWidget

        # Use real database - testing pure logic with real widget
        widget = FolderListWidget(
            parent=None,
            folders_table=temp_database.folders_table,
            on_send=lambda fid: None,
            on_edit=lambda fid: None,
            on_toggle=lambda fid: None,
            on_delete=lambda fid, name: None,
        )
        qtbot.addWidget(widget)

        short_width = widget._calculate_edit_button_min_width([{"alias": "a"}])
        long_width = widget._calculate_edit_button_min_width(
            [{"alias": "very-long-alias"}]
        )
        assert short_width > 0
        assert long_width > short_width
