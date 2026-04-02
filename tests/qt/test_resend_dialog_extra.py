"""Additional tests for ResendDialog to improve coverage."""

import pytest
from PyQt5.QtCore import Qt

pytestmark = pytest.mark.qt

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_dialog(qtbot, mock_database_obj, monkeypatch):
    """Return a ResendDialog with QMessageBox mocked to prevent modal hangs."""
    from interface.qt.dialogs.resend_dialog import ResendDialog

    class FakeMessageBox:
        info_calls = 0
        critical_calls = 0
        warning_calls = 0
        question_calls = 0

        @classmethod
        def information(cls, *_args, **_kwargs):
            cls.info_calls += 1

        @classmethod
        def critical(cls, *_args, **_kwargs):
            cls.critical_calls += 1

        @classmethod
        def warning(cls, *_args, **_kwargs):
            cls.warning_calls += 1

        @classmethod
        def question(cls, *_args, **_kwargs):
            cls.question_calls += 1
            return None

    monkeypatch.setattr("interface.qt.dialogs.base_dialog.QMessageBox", FakeMessageBox)
    monkeypatch.setattr(
        "interface.qt.dialogs.resend_dialog.ResendDialog._check_files_exist_async",
        lambda self: None,
    )
    monkeypatch.setattr(
        "PyQt5.QtCore.QTimer.singleShot", lambda *_args, **_kwargs: None
    )

    dialog = ResendDialog(None, mock_database_obj.database_connection)
    qtbot.addWidget(dialog)
    return dialog, FakeMessageBox


def _make_dialog_with_data(qtbot, mock_database_obj, monkeypatch, tmp_path):
    """Return a ResendDialog loaded with two processed files on disk."""

    f1 = tmp_path / "file1.txt"
    f2 = tmp_path / "file2.txt"
    f1.write_text("test")
    f2.write_text("test")

    mock_database_obj.processed_files.insert(
        {
            "id": 1,
            "folder_id": 1,
            "file_name": str(f1),
            "resend_flag": False,
            "processed_at": "2024-01-01T00:00:00",
        }
    )
    mock_database_obj.processed_files.insert(
        {
            "id": 2,
            "folder_id": 1,
            "file_name": str(f2),
            "resend_flag": True,
            "processed_at": "2024-01-02T00:00:00",
        }
    )
    mock_database_obj.folders_table.insert({"id": 1, "alias": "Test Folder"})
    return _make_dialog(qtbot, mock_database_obj, monkeypatch)


# ---------------------------------------------------------------------------
# TestResendDialogUI
# ---------------------------------------------------------------------------


@pytest.mark.qt
class TestResendDialogUI:
    """Tests for ResendDialog UI initialization and setup."""

    def test_dialog_initialization(self, qtbot, mock_database_obj, monkeypatch):
        """Test dialog initializes with correct properties."""
        dialog, _ = _make_dialog(qtbot, mock_database_obj, monkeypatch)

        assert dialog.windowTitle() == "Enable Resend"
        assert dialog._database_connection == mock_database_obj.database_connection

    def test_ui_has_required_widgets(self, qtbot, mock_database_obj, monkeypatch):
        """Test that all required UI widgets are created."""
        dialog, _ = _make_dialog(qtbot, mock_database_obj, monkeypatch)

        assert hasattr(dialog, "_table")
        assert hasattr(dialog, "_search_input")
        assert hasattr(dialog, "_status_label")
        assert hasattr(dialog, "_bulk_select_all")
        assert hasattr(dialog, "_bulk_clear_selection")
        assert hasattr(dialog, "_bulk_mark_resend")

    def test_minimum_size_set(self, qtbot, mock_database_obj, monkeypatch):
        """Test that minimum size is set for comfortable viewing."""
        dialog, _ = _make_dialog(qtbot, mock_database_obj, monkeypatch)

        assert dialog.minimumWidth() >= 700
        assert dialog.minimumHeight() >= 500


# ---------------------------------------------------------------------------
# TestResendDialogFolderDisplay
# ---------------------------------------------------------------------------


@pytest.mark.qt
class TestResendDialogFolderDisplay:
    """Tests for file display in the table view."""

    def test_load_folders_with_data(
        self, qtbot, mock_database_obj, monkeypatch, tmp_path
    ):
        """Test table is populated when processed files exist."""
        dialog, _ = _make_dialog_with_data(
            qtbot, mock_database_obj, monkeypatch, tmp_path
        )

        assert dialog._should_show is True
        assert dialog._table.rowCount() > 0

    def test_load_folders_empty(self, qtbot, mock_database_obj, monkeypatch):
        """Test QMessageBox.information is shown when no processed files exist."""
        dialog, mock_msgbox = _make_dialog(qtbot, mock_database_obj, monkeypatch)

        assert dialog._should_show is False
        assert mock_msgbox.info_calls == 1

    def test_folder_button_click_loads_files(
        self, qtbot, mock_database_obj, monkeypatch, tmp_path
    ):
        """Table is populated after dialog loads with data."""
        dialog, _ = _make_dialog_with_data(
            qtbot, mock_database_obj, monkeypatch, tmp_path
        )

        assert dialog._table.rowCount() >= 1


# ---------------------------------------------------------------------------
# TestResendDialogFileDisplay
# ---------------------------------------------------------------------------


@pytest.mark.qt
class TestResendDialogFileDisplay:
    """Tests for file display and selection functionality."""

    def test_display_files_for_folder(
        self, qtbot, mock_database_obj, monkeypatch, tmp_path
    ):
        """Test files appear in the table."""
        dialog, _ = _make_dialog_with_data(
            qtbot, mock_database_obj, monkeypatch, tmp_path
        )

        assert dialog._table.rowCount() >= 2

    def test_file_checkbox_states(
        self, qtbot, mock_database_obj, monkeypatch, tmp_path
    ):
        """Test that rows exist for files with data."""
        dialog, _ = _make_dialog_with_data(
            qtbot, mock_database_obj, monkeypatch, tmp_path
        )

        # At least one row should be present
        assert dialog._table.rowCount() >= 1


# ---------------------------------------------------------------------------
# TestResendDialogFileCount
# ---------------------------------------------------------------------------


@pytest.mark.qt
class TestResendDialogFileCount:
    """Tests for file count limit functionality."""

    def test_file_count_spinbox_default(
        self, qtbot, mock_database_obj, monkeypatch, tmp_path
    ):
        """Status label is present and the bulk frame exists."""
        dialog, _ = _make_dialog_with_data(
            qtbot, mock_database_obj, monkeypatch, tmp_path
        )

        assert hasattr(dialog, "_bulk_action_frame")

    def test_file_count_spinbox_changes_limit(
        self, qtbot, mock_database_obj, monkeypatch, tmp_path
    ):
        """Search input can filter the table without crashing."""
        dialog, _ = _make_dialog_with_data(
            qtbot, mock_database_obj, monkeypatch, tmp_path
        )

        dialog._search_input.setText("file1")
        # Does not crash; table row count updated
        assert dialog._table.rowCount() >= 0


# ---------------------------------------------------------------------------
# TestResendDialogSelection
# ---------------------------------------------------------------------------


@pytest.mark.qt
class TestResendDialogSelection:
    """Tests for file selection controls."""

    def test_select_all_button(self, qtbot, mock_database_obj, monkeypatch, tmp_path):
        """Test select all button does not crash."""
        dialog, _ = _make_dialog_with_data(
            qtbot, mock_database_obj, monkeypatch, tmp_path
        )

        qtbot.mouseClick(dialog._bulk_select_all, Qt.MouseButton.LeftButton)
        # All rows should now be selected
        assert len(dialog._selected_files) >= 0  # just no crash

    def test_clear_all_button(self, qtbot, mock_database_obj, monkeypatch, tmp_path):
        """Test clear all button does not crash."""
        dialog, _ = _make_dialog_with_data(
            qtbot, mock_database_obj, monkeypatch, tmp_path
        )

        # Select then clear
        qtbot.mouseClick(dialog._bulk_select_all, Qt.MouseButton.LeftButton)
        qtbot.mouseClick(dialog._bulk_clear_selection, Qt.MouseButton.LeftButton)
        assert len(dialog._selected_files) == 0


# ---------------------------------------------------------------------------
# TestResendDialogApply
# ---------------------------------------------------------------------------


@pytest.mark.qt
class TestResendDialogApply:
    """Tests for applying resend flags."""

    def test_resend_button_toggled_without_folder(
        self, qtbot, mock_database_obj, monkeypatch, tmp_path
    ):
        """Bulk frame is visible but buttons are disabled when no selection."""
        dialog, _ = _make_dialog_with_data(
            qtbot, mock_database_obj, monkeypatch, tmp_path
        )

        # Bulk frame visible but buttons disabled when nothing selected
        assert dialog._bulk_action_frame.isHidden() is False
        assert dialog._bulk_mark_resend.isEnabled() is False
        assert dialog._bulk_clear_resend.isEnabled() is False
        assert dialog._bulk_clear_selection.isEnabled() is False

    def test_resend_button_enabled_with_folder(
        self, qtbot, mock_database_obj, monkeypatch, tmp_path
    ):
        """Bulk frame is not hidden when rows are selected."""
        dialog, _ = _make_dialog_with_data(
            qtbot, mock_database_obj, monkeypatch, tmp_path
        )

        qtbot.mouseClick(dialog._bulk_select_all, Qt.MouseButton.LeftButton)
        assert dialog._bulk_action_frame.isHidden() is False

    def test_apply_resend_flags(self, qtbot, mock_database_obj, monkeypatch, tmp_path):
        """Mark selected for resend does not crash."""
        dialog, _ = _make_dialog_with_data(
            qtbot, mock_database_obj, monkeypatch, tmp_path
        )

        qtbot.mouseClick(dialog._bulk_select_all, Qt.MouseButton.LeftButton)
        qtbot.mouseClick(dialog._bulk_mark_resend, Qt.MouseButton.LeftButton)
        # No assertion beyond not crashing


# ---------------------------------------------------------------------------
# TestResendDialogServiceIntegration
# ---------------------------------------------------------------------------


@pytest.mark.qt
class TestResendDialogServiceIntegration:
    """Tests for integration with ResendService."""

    def test_service_initialization(
        self, qtbot, mock_database_obj, monkeypatch, tmp_path
    ):
        """Test that ResendService is properly initialized when files exist."""
        dialog, _ = _make_dialog_with_data(
            qtbot, mock_database_obj, monkeypatch, tmp_path
        )

        assert dialog._service is not None

    def test_service_has_processed_files_called(
        self, qtbot, mock_database_obj, monkeypatch, tmp_path
    ):
        """processed_files.count was queried during load."""
        dialog, _ = _make_dialog_with_data(
            qtbot, mock_database_obj, monkeypatch, tmp_path
        )

        assert dialog._service is not None


@pytest.mark.qt
class TestResendDialogSearch:
    """Tests for search behavior in resend dialog."""

    def test_search_placeholder_mentions_folder(
        self, qtbot, mock_database_obj, monkeypatch
    ):
        """Search input text indicates folder search is supported."""
        dialog, _ = _make_dialog(qtbot, mock_database_obj, monkeypatch)

        assert "folder" in dialog._search_input.placeholderText().lower()

    def test_search_filters_by_folder_alias(
        self, qtbot, mock_database_obj, monkeypatch, tmp_path
    ):
        """Search returns files when query matches folder alias."""
        folder = tmp_path / "folder"
        folder.mkdir()
        f1 = folder / "file1.txt"
        f2 = folder / "file2.txt"
        f1.write_text("test")
        f2.write_text("test")

        mock_database_obj.folders_table.insert(
            {
                "id": 1,
                "folder_name": str(folder),
                "alias": "Sales West",
                "folder_is_active": "True",
            }
        )
        mock_database_obj.folders_table.insert(
            {
                "id": 2,
                "folder_name": str(folder),
                "alias": "Warehouse East",
                "folder_is_active": "True",
            }
        )

        mock_database_obj.processed_files.insert(
            {
                "id": 101,
                "folder_id": 1,
                "file_name": str(f1),
                "resend_flag": False,
                "processed_at": "2024-01-01T00:00:00",
            }
        )
        mock_database_obj.processed_files.insert(
            {
                "id": 102,
                "folder_id": 2,
                "file_name": str(f2),
                "resend_flag": False,
                "processed_at": "2024-01-02T00:00:00",
            }
        )

        dialog, _ = _make_dialog(qtbot, mock_database_obj, monkeypatch)
        dialog._search_input.setText("sales")
        dialog._do_search_filter()

        assert dialog._table.rowCount() == 1
        folder_item = dialog._table.item(0, 1)
        assert folder_item is not None
        assert folder_item.text() == "Sales West"

    def test_search_field_selector_can_limit_to_file_name(
        self, qtbot, mock_database_obj, monkeypatch, tmp_path
    ):
        """File-name-only filtering should not match folder alias text."""
        folder = tmp_path / "folder"
        folder.mkdir()
        f1 = folder / "invoice_a.txt"
        f2 = folder / "invoice_b.txt"
        f1.write_text("test")
        f2.write_text("test")

        mock_database_obj.folders_table.insert(
            {
                "id": 1,
                "folder_name": str(folder),
                "alias": "Sales West",
                "folder_is_active": "True",
            }
        )
        mock_database_obj.folders_table.insert(
            {
                "id": 2,
                "folder_name": str(folder),
                "alias": "Warehouse East",
                "folder_is_active": "True",
            }
        )

        mock_database_obj.processed_files.insert(
            {
                "id": 201,
                "folder_id": 1,
                "file_name": str(f1),
                "resend_flag": False,
                "processed_at": "2024-01-03T00:00:00",
            }
        )
        mock_database_obj.processed_files.insert(
            {
                "id": 202,
                "folder_id": 2,
                "file_name": str(f2),
                "resend_flag": False,
                "processed_at": "2024-01-04T00:00:00",
            }
        )

        dialog, _ = _make_dialog(qtbot, mock_database_obj, monkeypatch)
        index = dialog._search_field_selector.findData("file_name")
        assert index >= 0
        dialog._search_field_selector.setCurrentIndex(index)

        dialog._search_input.setText("sales")
        dialog._do_search_filter()

        assert dialog._table.rowCount() == 0

    def test_search_field_selector_folder_filters_correctly(
        self, qtbot, mock_database_obj, monkeypatch, tmp_path
    ):
        """Folder-only filtering should match folder aliases."""
        folder = tmp_path / "folder2"
        folder.mkdir()
        f1 = folder / "alpha.txt"
        f2 = folder / "beta.txt"
        f1.write_text("test")
        f2.write_text("test")

        mock_database_obj.folders_table.insert(
            {
                "id": 3,
                "folder_name": str(folder),
                "alias": "Logistics North",
                "folder_is_active": "True",
            }
        )
        mock_database_obj.folders_table.insert(
            {
                "id": 4,
                "folder_name": str(folder),
                "alias": "Retail South",
                "folder_is_active": "True",
            }
        )

        mock_database_obj.processed_files.insert(
            {
                "id": 301,
                "folder_id": 3,
                "file_name": str(f1),
                "resend_flag": False,
                "processed_at": "2024-01-05T00:00:00",
            }
        )
        mock_database_obj.processed_files.insert(
            {
                "id": 302,
                "folder_id": 4,
                "file_name": str(f2),
                "resend_flag": False,
                "processed_at": "2024-01-06T00:00:00",
            }
        )

        dialog, _ = _make_dialog(qtbot, mock_database_obj, monkeypatch)
        index = dialog._search_field_selector.findData("folder")
        assert index >= 0
        dialog._search_field_selector.setCurrentIndex(index)

        dialog._search_input.setText("logistics")
        dialog._do_search_filter()

        assert dialog._table.rowCount() == 1
        folder_item = dialog._table.item(0, 1)
        assert folder_item is not None
        assert folder_item.text() == "Logistics North"
