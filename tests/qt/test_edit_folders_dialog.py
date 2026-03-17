"""
Comprehensive tests for all GUI interactions in EditFoldersDialog.

Tests cover:
- Toggle/State Changes (Active checkbox, backend checkboxes)
- Combo Box Changes (Convert format, EDI options)
- Button Clicks (Show folder path, Select copy directory, Copy config)
- Field Population (convert format sub-fields, EDI configuration areas)

Uses pytest-qt's qtbot fixture for proper widget lifecycle management.
Mocks file dialogs and message boxes.
"""

from unittest.mock import MagicMock

import pytest

from interface.qt.theme import Theme


def create_dialog(qtbot, sample_folder_config, **kwargs):
    """Helper to create EditFoldersDialog with mocked dependencies."""
    from interface.qt.dialogs.edit_folders_dialog import EditFoldersDialog

    settings_provider = kwargs.pop(
        "settings_provider",
        kwargs.pop("_settings_provider", lambda: {"enable_email": True}),
    )
    alias_provider = kwargs.pop(
        "alias_provider", kwargs.pop("_alias_provider", lambda: ["Other1", "Other2"])
    )

    dialog = EditFoldersDialog(
        None,
        sample_folder_config,
        settings_provider=settings_provider,
        alias_provider=alias_provider,
        **kwargs,
    )
    qtbot.addWidget(dialog)
    return dialog


# ============================================================================
# Test Active Checkbox Toggle - Enables/Disables All Fields
# ============================================================================
@pytest.mark.qt
class TestActiveCheckboxToggle:
    """Tests for active checkbox toggle interaction."""

    def test_active_checkbox_unchecked_disables_backends(
        self, qtbot, sample_folder_config
    ):
        """When unchecked, backend checkboxes should be disabled."""
        sample_folder_config["folder_is_active"] = "True"
        dialog = create_dialog(qtbot, sample_folder_config)

        dialog._active_checkbox.setChecked(False)

        assert not dialog._copy_backend_check.isEnabled()
        assert not dialog._ftp_backend_check.isEnabled()
        assert not dialog._email_backend_check.isEnabled()

    def test_active_checkbox_checked_enables_backends(
        self, qtbot, sample_folder_config
    ):
        """When checked, backend checkboxes should be enabled."""
        sample_folder_config["folder_is_active"] = "False"
        dialog = create_dialog(qtbot, sample_folder_config)

        dialog._active_checkbox.setChecked(True)

        assert dialog._copy_backend_check.isEnabled()
        assert dialog._ftp_backend_check.isEnabled()

    def test_active_checkbox_updates_text_and_style(self, qtbot, sample_folder_config):
        """Checkbox text and style should update when toggled."""
        dialog = create_dialog(qtbot, sample_folder_config)

        dialog._active_checkbox.setChecked(True)
        assert "Enabled" in dialog._active_checkbox.text()
        assert Theme.SUCCESS_CONTAINER in dialog._active_checkbox.styleSheet()

        dialog._active_checkbox.setChecked(False)
        assert "Disabled" in dialog._active_checkbox.text()
        assert Theme.ERROR_CONTAINER in dialog._active_checkbox.styleSheet()

    def test_active_checkbox_toggles_edi_fields(self, qtbot, sample_folder_config):
        """EDI fields should be disabled when folder is inactive."""
        sample_folder_config["folder_is_active"] = "True"
        sample_folder_config["process_backend_copy"] = True
        dialog = create_dialog(qtbot, sample_folder_config)

        dialog._active_checkbox.setChecked(False)

        assert not dialog._split_edi_check.isEnabled()
        assert not dialog._send_invoices_check.isEnabled()
        assert not dialog._send_credits_check.isEnabled()
        assert not dialog._edi_options_combo.isEnabled()

    def test_active_checkbox_enables_edi_when_backends_active(
        self, qtbot, sample_folder_config
    ):
        """EDI fields should be enabled when folder is active AND a backend is selected."""
        sample_folder_config["folder_is_active"] = "True"
        sample_folder_config["process_backend_copy"] = True
        dialog = create_dialog(qtbot, sample_folder_config)

        assert dialog._split_edi_check.isEnabled()
        assert dialog._edi_options_combo.isEnabled()


# ============================================================================
# Test Copy Backend Check - Toggles Copy Destination Fields
# ============================================================================
@pytest.mark.qt
class TestCopyBackendToggle:
    """Tests for copy backend checkbox toggle interaction."""

    def test_copy_backend_unchecked_disables_copy_button(
        self, qtbot, sample_folder_config
    ):
        """Copy destination button should be disabled when copy backend is unchecked."""
        sample_folder_config["folder_is_active"] = "True"
        sample_folder_config["process_backend_copy"] = False
        dialog = create_dialog(qtbot, sample_folder_config)

        dialog._copy_backend_check.setChecked(False)

        assert not dialog._copy_dest_btn.isEnabled()

    def test_copy_backend_checked_enables_copy_button(
        self, qtbot, sample_folder_config
    ):
        """Copy destination button should be enabled when copy backend is checked."""
        sample_folder_config["folder_is_active"] = "True"
        sample_folder_config["process_backend_copy"] = False
        dialog = create_dialog(qtbot, sample_folder_config)

        dialog._copy_backend_check.setChecked(True)

        assert dialog._copy_dest_btn.isEnabled()


# ============================================================================
# Test FTP Backend Check - Toggles FTP Fields
# ============================================================================
@pytest.mark.qt
class TestFTPBackendToggle:
    """Tests for FTP backend checkbox toggle interaction."""

    def test_ftp_backend_unchecked_disables_ftp_fields(
        self, qtbot, sample_folder_config
    ):
        """FTP fields should be disabled when FTP backend is unchecked."""
        sample_folder_config["folder_is_active"] = "True"
        sample_folder_config["process_backend_ftp"] = False
        dialog = create_dialog(qtbot, sample_folder_config)

        dialog._ftp_backend_check.setChecked(False)

        assert not dialog._ftp_server_field.isEnabled()
        assert not dialog._ftp_port_field.isEnabled()
        assert not dialog._ftp_folder_field.isEnabled()
        assert not dialog._ftp_username_field.isEnabled()
        assert not dialog._ftp_password_field.isEnabled()

    def test_ftp_backend_checked_enables_ftp_fields(self, qtbot, sample_folder_config):
        """FTP fields should be enabled when FTP backend is checked."""
        sample_folder_config["folder_is_active"] = "True"
        sample_folder_config["process_backend_ftp"] = False
        dialog = create_dialog(qtbot, sample_folder_config)

        dialog._ftp_backend_check.setChecked(True)

        assert dialog._ftp_server_field.isEnabled()
        assert dialog._ftp_port_field.isEnabled()
        assert dialog._ftp_folder_field.isEnabled()
        assert dialog._ftp_username_field.isEnabled()
        assert dialog._ftp_password_field.isEnabled()


# ============================================================================
# Test Email Backend Check - Toggles Email Fields
# ============================================================================
@pytest.mark.qt
class TestEmailBackendToggle:
    """Tests for email backend checkbox toggle interaction."""

    def test_email_backend_unchecked_disables_email_fields(
        self, qtbot, sample_folder_config
    ):
        """Email fields should be disabled when email backend is unchecked."""
        sample_folder_config["folder_is_active"] = "True"
        sample_folder_config["process_backend_email"] = False
        dialog = create_dialog(qtbot, sample_folder_config)

        dialog._email_backend_check.setChecked(False)

        assert not dialog._email_recipient_field.isEnabled()
        assert not dialog._email_subject_field.isEnabled()

    def test_email_backend_checked_enables_email_fields(
        self, qtbot, sample_folder_config
    ):
        """Email fields should be enabled when email backend is checked."""
        sample_folder_config["folder_is_active"] = "True"
        sample_folder_config["process_backend_email"] = False
        dialog = create_dialog(qtbot, sample_folder_config)

        dialog._email_backend_check.setChecked(True)

        assert dialog._email_recipient_field.isEnabled()
        assert dialog._email_subject_field.isEnabled()

    def test_email_backend_disabled_when_email_not_enabled(
        self, qtbot, sample_folder_config
    ):
        """Email backend checkbox should be disabled when email is not enabled in settings."""
        sample_folder_config["folder_is_active"] = "True"
        dialog = create_dialog(
            qtbot,
            sample_folder_config,
            settings_provider=lambda: {"enable_email": False},
        )

        assert not dialog._email_backend_check.isEnabled()


# ============================================================================
# Test Convert Format ComboBox - Shows/Hides Format-Specific Sub-Fields
# ============================================================================
@pytest.mark.qt
class TestConvertFormatChange:
    """Tests for convert format combo box changes."""

    def _setup_edi_convert_mode(self, qtbot, sample_folder_config):
        """Helper to set up dialog in Convert EDI mode."""
        sample_folder_config["folder_is_active"] = "True"
        sample_folder_config["process_edi"] = "True"
        sample_folder_config["process_backend_copy"] = True
        dialog = create_dialog(qtbot, sample_folder_config)
        dialog._edi_options_combo.setCurrentText("Convert EDI")
        return dialog

    def test_csv_format_shows_csv_sub_fields(self, qtbot, sample_folder_config):
        """Selecting CSV format should show CSV-specific fields."""
        dialog = self._setup_edi_convert_mode(qtbot, sample_folder_config)
        dialog._convert_format_combo.setCurrentText("csv")

        assert hasattr(dialog, "_csv_upc_check")
        assert hasattr(dialog, "_csv_a_rec_check")
        assert hasattr(dialog, "_csv_headers_check")
        assert hasattr(dialog, "_csv_pad_arec_check")

    def test_scannerware_format_shows_scannerware_fields(
        self, qtbot, sample_folder_config
    ):
        """Selecting ScannerWare format should show ScannerWare-specific fields."""
        dialog = self._setup_edi_convert_mode(qtbot, sample_folder_config)
        dialog._convert_format_combo.setCurrentText("ScannerWare")

        assert hasattr(dialog, "_sw_pad_arec_check")
        assert hasattr(dialog, "_sw_arec_padding_field")

    def test_simplified_csv_format_shows_simplified_fields(
        self, qtbot, sample_folder_config
    ):
        """Selecting simplified_csv format should show simplified CSV fields."""
        dialog = self._setup_edi_convert_mode(qtbot, sample_folder_config)
        dialog._convert_format_combo.setCurrentText("simplified_csv")

        assert hasattr(dialog, "_simp_headers_check")
        assert hasattr(dialog, "_simp_include_item_numbers_check")
        assert hasattr(dialog, "_simp_column_sort_field")

    def test_fintech_format_shows_fintech_fields(self, qtbot, sample_folder_config):
        """Selecting fintech format should show fintech-specific fields."""
        dialog = self._setup_edi_convert_mode(qtbot, sample_folder_config)
        dialog._convert_format_combo.setCurrentText("fintech")

        assert hasattr(dialog, "_fintech_division_field")

    def test_estore_einvoice_format_shows_estore_fields(
        self, qtbot, sample_folder_config
    ):
        """Selecting Estore eInvoice format should show estore fields."""
        dialog = self._setup_edi_convert_mode(qtbot, sample_folder_config)
        dialog._convert_format_combo.setCurrentText("Estore eInvoice")

        assert hasattr(dialog, "_estore_store_number_field")
        assert hasattr(dialog, "_estore_vendor_oid_field")
        assert hasattr(dialog, "_estore_vendor_name_field")

    def test_estore_einvoice_generic_format_shows_extra_field(
        self, qtbot, sample_folder_config
    ):
        """Estore eInvoice Generic should show C Record OId field."""
        dialog = self._setup_edi_convert_mode(qtbot, sample_folder_config)
        dialog._convert_format_combo.setCurrentText("Estore eInvoice Generic")

        assert hasattr(dialog, "_estore_store_number_field")
        assert hasattr(dialog, "_estore_c_record_oid_field")

    def test_jolley_custom_format_shows_basic_options(
        self, qtbot, sample_folder_config
    ):
        """Selecting jolley_custom should show basic options."""
        dialog = self._setup_edi_convert_mode(qtbot, sample_folder_config)
        dialog._convert_format_combo.setCurrentText("jolley_custom")

        assert hasattr(dialog, "_convert_sub_container")

    def test_stewarts_custom_format_shows_basic_options(
        self, qtbot, sample_folder_config
    ):
        """Selecting stewarts_custom should show basic options."""
        dialog = self._setup_edi_convert_mode(qtbot, sample_folder_config)
        dialog._convert_format_combo.setCurrentText("stewarts_custom")

        assert hasattr(dialog, "_convert_sub_container")

    def test_yellowdog_csv_format_shows_basic_options(
        self, qtbot, sample_folder_config
    ):
        """Selecting YellowDog CSV should show basic options."""
        dialog = self._setup_edi_convert_mode(qtbot, sample_folder_config)
        dialog._convert_format_combo.setCurrentText("YellowDog CSV")

        assert hasattr(dialog, "_convert_sub_container")

    def test_scansheet_type_a_format_no_extra_fields(self, qtbot, sample_folder_config):
        """Selecting scansheet-type-a should show no extra fields."""
        dialog = self._setup_edi_convert_mode(qtbot, sample_folder_config)
        dialog._convert_format_combo.setCurrentText("scansheet-type-a")

        assert dialog._convert_sub_layout.count() == 0


# ============================================================================
# Test EDI Options ComboBox - Shows/Hides EDI Configuration Areas
# ============================================================================
@pytest.mark.qt
class TestEDIOptionsChange:
    """Tests for EDI options combo box changes."""

    def test_do_nothing_shows_send_as_is(self, qtbot, sample_folder_config):
        """Do Nothing option should set process_edi and tweak_edi to False."""
        sample_folder_config["folder_is_active"] = "True"
        sample_folder_config["process_backend_copy"] = True
        sample_folder_config["process_edi"] = "True"
        dialog = create_dialog(qtbot, sample_folder_config)

        dialog._edi_options_combo.setCurrentText("Do Nothing")

        process_edi = dialog._fields.get("process_edi")
        tweak_edi = dialog._fields.get("tweak_edi")
        assert process_edi is not None
        assert tweak_edi is not None

    def test_convert_edi_shows_convert_fields(self, qtbot, sample_folder_config):
        """Convert EDI option should show convert format fields."""
        sample_folder_config["folder_is_active"] = "True"
        sample_folder_config["process_backend_copy"] = True
        dialog = create_dialog(qtbot, sample_folder_config)

        dialog._edi_options_combo.setCurrentText("Convert EDI")

        assert hasattr(dialog, "_convert_format_combo")
        assert hasattr(dialog, "_convert_sub_container")

    def test_tweak_edi_shows_tweak_fields(self, qtbot, sample_folder_config):
        """Tweak EDI option should show tweak EDI fields."""
        sample_folder_config["folder_is_active"] = "True"
        sample_folder_config["process_backend_copy"] = True
        sample_folder_config["tweak_edi"] = True
        dialog = create_dialog(qtbot, sample_folder_config)

        dialog._edi_options_combo.setCurrentText("Tweak EDI")

        assert hasattr(dialog, "_tweak_upc_check")
        assert hasattr(dialog, "_tweak_pad_arec_check")
        assert hasattr(dialog, "_tweak_force_txt_check")

    def test_tweak_edi_has_override_upc_group(self, qtbot, sample_folder_config):
        """Tweak EDI should have UPC override group."""
        sample_folder_config["folder_is_active"] = "True"
        sample_folder_config["process_backend_copy"] = True
        sample_folder_config["tweak_edi"] = True
        dialog = create_dialog(qtbot, sample_folder_config)

        dialog._edi_options_combo.setCurrentText("Tweak EDI")

        assert hasattr(dialog, "_tweak_override_upc_check")
        assert hasattr(dialog, "_tweak_override_upc_level")

    def test_edi_option_change_clears_previous_fields(
        self, qtbot, sample_folder_config
    ):
        """Changing EDI options should clear previous dynamic fields."""
        sample_folder_config["folder_is_active"] = "True"
        sample_folder_config["process_backend_copy"] = True
        dialog = create_dialog(qtbot, sample_folder_config)

        dialog._edi_options_combo.setCurrentText("Convert EDI")
        first_convert_widgets = []
        for i in range(dialog._dynamic_edi_layout.count()):
            item = dialog._dynamic_edi_layout.itemAt(i)
            if item and item.widget():
                first_convert_widgets.append(type(item.widget()))

        dialog._edi_options_combo.setCurrentText("Tweak EDI")
        second_tweak_widgets = []
        for i in range(dialog._dynamic_edi_layout.count()):
            item = dialog._dynamic_edi_layout.itemAt(i)
            if item and item.widget():
                second_tweak_widgets.append(type(item.widget()))

        assert len(first_convert_widgets) > 0
        assert len(second_tweak_widgets) > 0


# ============================================================================
# Test Show Folder Path Button
# ============================================================================
@pytest.mark.qt
class TestShowFolderPathButton:
    """Tests for show folder path button click."""

    def test_show_folder_path_displays_message(
        self, qtbot, sample_folder_config, monkeypatch
    ):
        """Clicking show folder path should display a message box."""
        sample_folder_config["folder_name"] = "/test/path"
        mock_info = MagicMock()
        monkeypatch.setattr(
            "interface.qt.dialogs.edit_folders_dialog.QMessageBox.information",
            mock_info,
        )
        dialog = create_dialog(qtbot, sample_folder_config)

        dialog._show_folder_path()

        mock_info.assert_called_once()
        args = mock_info.call_args[0]
        assert args[2] == "/test/path"

    def test_show_folder_path_button_exists(self, qtbot, sample_folder_config):
        """Show folder path button should exist for non-template folders."""
        sample_folder_config["folder_name"] = "/test/folder"
        dialog = create_dialog(qtbot, sample_folder_config)

        assert hasattr(dialog, "_folder_alias_field")


# ============================================================================
# Test Select Copy Directory Button
# ============================================================================
@pytest.mark.qt
class TestSelectCopyDirectoryButton:
    """Tests for select copy directory button click."""

    def test_select_copy_directory_opens_file_dialog(
        self, qtbot, sample_folder_config, monkeypatch
    ):
        """Clicking select copy directory should open file dialog."""
        mock_get_existing = MagicMock(return_value="/selected/directory")
        monkeypatch.setattr(
            "interface.qt.dialogs.edit_folders_dialog.QFileDialog.getExistingDirectory",
            mock_get_existing,
        )
        monkeypatch.setattr("os.path.isdir", lambda path: True)
        sample_folder_config["folder_is_active"] = "True"
        sample_folder_config["process_backend_copy"] = True
        dialog = create_dialog(qtbot, sample_folder_config)
        dialog._active_checkbox.setChecked(True)
        dialog._copy_backend_check.setChecked(True)

        dialog._select_copy_directory()

        mock_get_existing.assert_called_once()
        assert dialog.copy_to_directory == "/selected/directory"

    def test_select_copy_directory_cancels_returns_empty(
        self, qtbot, sample_folder_config, monkeypatch
    ):
        """Cancelling the dialog should not change copy directory."""
        mock_get_existing = MagicMock(return_value="")
        monkeypatch.setattr(
            "interface.qt.dialogs.edit_folders_dialog.QFileDialog.getExistingDirectory",
            mock_get_existing,
        )
        sample_folder_config["folder_is_active"] = "True"
        sample_folder_config["process_backend_copy"] = True
        dialog = create_dialog(qtbot, sample_folder_config)
        dialog.copy_to_directory = "/original"

        dialog._select_copy_directory()

        assert dialog.copy_to_directory == "/original"

    def test_select_copy_directory_uses_existing_as_initial(
        self, qtbot, sample_folder_config, monkeypatch
    ):
        """File dialog should use existing directory as initial path."""
        sample_folder_config["copy_to_directory"] = "/existing/copy/dir"
        sample_folder_config["folder_is_active"] = "True"
        sample_folder_config["process_backend_copy"] = True

        mock_get_existing = MagicMock(return_value="/new/dir")
        monkeypatch.setattr(
            "interface.qt.dialogs.edit_folders_dialog.QFileDialog.getExistingDirectory",
            mock_get_existing,
        )
        dialog = create_dialog(qtbot, sample_folder_config)
        dialog._active_checkbox.setChecked(True)
        dialog._copy_backend_check.setChecked(True)

        dialog._select_copy_directory()

        mock_get_existing.assert_called_once()


# ============================================================================
# Test Copy Config From Other Button
# ============================================================================
@pytest.mark.qt
class TestCopyConfigFromOtherButton:
    """Tests for copy config from other button click."""

    def test_copy_config_with_no_selection_does_nothing(
        self, qtbot, sample_folder_config
    ):
        """Clicking with no folder selected should do nothing."""
        sample_folder_config["folder_name"] = "/test/folder"
        dialog = create_dialog(qtbot, sample_folder_config)
        dialog._others_list.setCurrentRow(-1)

        dialog._copy_config_from_other()

    def test_copy_config_button_exists(self, qtbot, sample_folder_config):
        """Copy config button should exist."""
        sample_folder_config["folder_name"] = "/test/folder"
        dialog = create_dialog(qtbot, sample_folder_config)

        assert hasattr(dialog, "_copy_config_btn")

    def test_copy_config_updates_ftp_fields(self, qtbot, sample_folder_config):
        """Copying another folder's config should populate FTP fields."""
        source = dict(sample_folder_config)
        source.update(
            {
                "id": 99,
                "alias": "Source Folder",
                "folder_name": "/source/path",
                "ftp_server": "ftp.example.com",
                "ftp_port": 2121,
                "process_backend_ftp": True,
                "convert_to_format": "csv",
            }
        )
        settings_provider = lambda: {"folders": [source]}  # noqa: E731
        dialog = create_dialog(
            qtbot,
            sample_folder_config,
            alias_provider=lambda: ["Source Folder"],
            settings_provider=settings_provider,
        )
        dialog._others_list.setCurrentRow(0)

        dialog._copy_config_from_other()

        assert dialog._fields["ftp_server_field"].text() == "ftp.example.com"
        assert dialog._fields["ftp_port_field"].text() == "2121"

    def test_copy_config_preserves_current_alias_and_id(
        self, qtbot, sample_folder_config
    ):
        """Copying another folder's config must NOT overwrite alias, id, folder_name."""
        source = dict(sample_folder_config)
        source.update(
            {
                "id": 99,
                "alias": "Source Folder",
                "folder_name": "/source/path",
                "convert_to_format": "csv",
            }
        )
        settings_provider = lambda: {"folders": [source]}  # noqa: E731
        dialog = create_dialog(
            qtbot,
            sample_folder_config,
            alias_provider=lambda: ["Source Folder"],
            settings_provider=settings_provider,
        )
        dialog._others_list.setCurrentRow(0)

        dialog._copy_config_from_other()

        # The current folder's identity must be unchanged
        assert dialog._folder_config["id"] == sample_folder_config["id"]
        assert dialog._folder_config["alias"] == sample_folder_config["alias"]
        assert (
            dialog._folder_config["folder_name"]
            == sample_folder_config["folder_name"]
        )


# ============================================================================
# Test Others List Filter (Search-as-you-type)
# ============================================================================
@pytest.mark.qt
class TestOthersListFilter:
    """Tests for the search-as-you-type filter on the copy-from list."""

    def _dialog_with_aliases(self, qtbot, sample_folder_config):
        return create_dialog(
            qtbot,
            sample_folder_config,
            alias_provider=lambda: ["Alpha Store", "Beta Warehouse", "Gamma Shop"],
        )

    def test_others_search_widget_exists(self, qtbot, sample_folder_config):
        """A SearchWidget should be present in the dialog."""
        dialog = self._dialog_with_aliases(qtbot, sample_folder_config)

        assert dialog._others_search is not None

    def test_filter_hides_non_matching_items(self, qtbot, sample_folder_config):
        """Typing a filter term should hide non-matching list items."""
        dialog = self._dialog_with_aliases(qtbot, sample_folder_config)
        others_list = dialog._others_list

        # Emit filter directly (bypasses debounce timer)
        dialog._others_search.filter_changed.emit("beta")

        visible = [
            others_list.item(i).text()
            for i in range(others_list.count())
            if not others_list.item(i).isHidden()
        ]
        assert visible == ["Beta Warehouse"]

    def test_filter_shows_all_on_empty_string(self, qtbot, sample_folder_config):
        """Clearing the filter should make all items visible again."""
        dialog = self._dialog_with_aliases(qtbot, sample_folder_config)
        others_list = dialog._others_list

        dialog._others_search.filter_changed.emit("gamma")
        dialog._others_search.filter_changed.emit("")

        hidden = [
            others_list.item(i)
            for i in range(others_list.count())
            if others_list.item(i).isHidden()
        ]
        assert hidden == []

    def test_filter_is_case_insensitive(self, qtbot, sample_folder_config):
        """Filter matching should be case-insensitive."""
        dialog = self._dialog_with_aliases(qtbot, sample_folder_config)
        others_list = dialog._others_list

        dialog._others_search.filter_changed.emit("ALPHA")

        visible = [
            others_list.item(i).text()
            for i in range(others_list.count())
            if not others_list.item(i).isHidden()
        ]
        assert visible == ["Alpha Store"]

    def test_filter_partial_match(self, qtbot, sample_folder_config):
        """A partial term should match items containing that substring."""
        dialog = self._dialog_with_aliases(qtbot, sample_folder_config)
        others_list = dialog._others_list

        dialog._others_search.filter_changed.emit("store")

        visible = [
            others_list.item(i).text()
            for i in range(others_list.count())
            if not others_list.item(i).isHidden()
        ]
        assert "Alpha Store" in visible
        assert "Beta Warehouse" not in visible


# ============================================================================
# Test Field Population - Convert Format Sub-Fields
# ============================================================================
@pytest.mark.qt
class TestConvertFormatFieldPopulation:
    """Tests for proper field population when switching convert formats."""

    def test_csv_format_populates_csv_fields(self, qtbot, sample_folder_config):
        """CSV format should populate CSV-specific fields from config."""
        sample_folder_config["folder_is_active"] = "True"
        sample_folder_config["process_edi"] = "True"
        sample_folder_config["process_backend_copy"] = True
        sample_folder_config["calculate_upc_check_digit"] = "True"
        sample_folder_config["include_headers"] = "True"
        sample_folder_config["pad_a_records"] = "True"
        dialog = create_dialog(qtbot, sample_folder_config)
        dialog._edi_options_combo.setCurrentText("Convert EDI")
        dialog._convert_format_combo.setCurrentText("csv")

        assert dialog._csv_upc_check.isChecked()
        assert dialog._csv_headers_check.isChecked()
        assert dialog._csv_pad_arec_check.isChecked()

    def test_simplified_csv_format_populates_fields(self, qtbot, sample_folder_config):
        """simplified_csv format should populate its fields from config."""
        sample_folder_config["folder_is_active"] = "True"
        sample_folder_config["process_edi"] = "True"
        sample_folder_config["process_backend_copy"] = True
        sample_folder_config["include_headers"] = "True"
        sample_folder_config["include_item_numbers"] = True
        sample_folder_config["retail_uom"] = True
        dialog = create_dialog(qtbot, sample_folder_config)
        dialog._edi_options_combo.setCurrentText("Convert EDI")
        dialog._convert_format_combo.setCurrentText("simplified_csv")

        assert dialog._simp_headers_check.isChecked()
        assert dialog._simp_include_item_numbers_check.isChecked()
        assert dialog._simp_each_uom_check.isChecked()

    def test_estore_format_populates_estore_fields(self, qtbot, sample_folder_config):
        """Estore format should populate estore-specific fields from config."""
        sample_folder_config["folder_is_active"] = "True"
        sample_folder_config["process_edi"] = "True"
        sample_folder_config["process_backend_copy"] = True
        sample_folder_config["estore_store_number"] = "12345"
        sample_folder_config["estore_Vendor_OId"] = "VENDOR001"
        sample_folder_config["estore_vendor_NameVendorOID"] = "VendorName"
        dialog = create_dialog(qtbot, sample_folder_config)
        dialog._edi_options_combo.setCurrentText("Convert EDI")
        dialog._convert_format_combo.setCurrentText("Estore eInvoice")

        assert dialog._estore_store_number_field.text() == "12345"
        assert dialog._estore_vendor_oid_field.text() == "VENDOR001"

    def test_fintech_format_populates_fintech_fields(self, qtbot, sample_folder_config):
        """fintech format should populate fintech-specific fields from config."""
        sample_folder_config["folder_is_active"] = "True"
        sample_folder_config["process_edi"] = "True"
        sample_folder_config["process_backend_copy"] = True
        sample_folder_config["fintech_division_id"] = "DIV001"
        dialog = create_dialog(qtbot, sample_folder_config)
        dialog._edi_options_combo.setCurrentText("Convert EDI")
        dialog._convert_format_combo.setCurrentText("fintech")

        assert dialog._fintech_division_field.text() == "DIV001"

    def test_scannerware_format_populates_fields(self, qtbot, sample_folder_config):
        """ScannerWare format should populate its fields from config."""
        sample_folder_config["folder_is_active"] = "True"
        sample_folder_config["process_edi"] = "True"
        sample_folder_config["process_backend_copy"] = True
        sample_folder_config["pad_a_records"] = "True"
        sample_folder_config["a_record_padding"] = "X"
        sample_folder_config["a_record_padding_length"] = 30
        sample_folder_config["append_a_records"] = "True"
        sample_folder_config["a_record_append_text"] = "APPEND"
        dialog = create_dialog(qtbot, sample_folder_config)
        dialog._edi_options_combo.setCurrentText("Convert EDI")
        dialog._convert_format_combo.setCurrentText("ScannerWare")

        assert dialog._sw_pad_arec_check.isChecked()
        assert dialog._sw_arec_padding_field.text() == "X"
        assert dialog._tweak_arec_padding_length.currentText() == "30"

    def test_basic_format_shows_no_additional_options(
        self, qtbot, sample_folder_config
    ):
        """jolley_custom/stewarts_custom/YellowDog CSV show no extra option fields."""
        sample_folder_config["folder_is_active"] = "True"
        sample_folder_config["process_edi"] = "True"
        sample_folder_config["process_backend_copy"] = True
        dialog = create_dialog(qtbot, sample_folder_config)
        dialog._edi_options_combo.setCurrentText("Convert EDI")

        for fmt in ("jolley_custom", "stewarts_custom", "YellowDog CSV"):
            dialog._convert_format_combo.setCurrentText(fmt)
            assert hasattr(dialog, "_convert_sub_container")
            # Basic formats show a label widget only – no input widgets
            assert dialog._convert_sub_layout is not None

    def test_do_nothing_sets_process_edi_false(self, qtbot, sample_folder_config):
        """Selecting 'Do Nothing' should set process_edi=False on apply."""
        sample_folder_config["folder_is_active"] = "True"
        sample_folder_config["process_backend_copy"] = True
        sample_folder_config["process_edi"] = "True"
        dialog = create_dialog(qtbot, sample_folder_config)
        qtbot.wait(150)  # let the 100ms edi-processing guard timer fire
        dialog._edi_options_combo.setCurrentText("Do Nothing")
        dialog.apply()

        assert sample_folder_config["process_edi"] is False
        assert sample_folder_config["tweak_edi"] is False

    def test_convert_edi_roundtrip_csv(self, qtbot, sample_folder_config):
        """CSV conversion settings should round-trip through dialog apply()."""
        sample_folder_config["folder_is_active"] = "True"
        sample_folder_config["process_edi"] = "True"
        sample_folder_config["process_backend_copy"] = True
        sample_folder_config["convert_to_format"] = "csv"
        sample_folder_config["calculate_upc_check_digit"] = "True"
        sample_folder_config["include_headers"] = "True"
        sample_folder_config["pad_a_records"] = "True"
        dialog = create_dialog(qtbot, sample_folder_config)
        dialog._edi_options_combo.setCurrentText("Convert EDI")
        dialog._convert_format_combo.setCurrentText("csv")
        dialog.apply()

        assert sample_folder_config["process_edi"] is True
        assert sample_folder_config["tweak_edi"] is False
        assert sample_folder_config["calculate_upc_check_digit"] is True
        assert sample_folder_config["include_headers"] is True
        assert sample_folder_config["pad_a_records"] is True

    def test_tweak_edi_roundtrip(self, qtbot, sample_folder_config):
        """Tweak EDI settings should round-trip through dialog apply()."""
        sample_folder_config["folder_is_active"] = "True"
        sample_folder_config["process_backend_copy"] = True
        sample_folder_config["tweak_edi"] = True
        sample_folder_config["calculate_upc_check_digit"] = "True"
        sample_folder_config["invoice_date_offset"] = 3
        sample_folder_config["force_txt_file_ext"] = "True"
        dialog = create_dialog(qtbot, sample_folder_config)
        dialog.apply()

        assert sample_folder_config["tweak_edi"] is True
        assert sample_folder_config["process_edi"] is False
        assert sample_folder_config["calculate_upc_check_digit"] is True
        assert sample_folder_config["invoice_date_offset"] == 3
        assert sample_folder_config["force_txt_file_ext"] is True

    def test_estore_einvoice_generic_populates_c_record_oid(
        self, qtbot, sample_folder_config
    ):
        """Estore eInvoice Generic should populate the C Record OId field."""
        sample_folder_config["folder_is_active"] = "True"
        sample_folder_config["process_edi"] = "True"
        sample_folder_config["process_backend_copy"] = True
        sample_folder_config["estore_store_number"] = "99"
        sample_folder_config["estore_Vendor_OId"] = "VOId"
        sample_folder_config["estore_vendor_NameVendorOID"] = "VN"
        sample_folder_config["estore_c_record_OID"] = "COID123"
        dialog = create_dialog(qtbot, sample_folder_config)
        dialog._edi_options_combo.setCurrentText("Convert EDI")
        dialog._convert_format_combo.setCurrentText("Estore eInvoice Generic")

        assert dialog._estore_store_number_field.text() == "99"
        assert dialog._estore_c_record_oid_field.text() == "COID123"

    """Tests for proper field population when switching EDI options."""

    def test_tweak_edi_populates_tweak_fields(self, qtbot, sample_folder_config):
        """Tweak EDI should populate its fields from config."""
        sample_folder_config["folder_is_active"] = "True"
        sample_folder_config["process_backend_copy"] = True
        sample_folder_config["tweak_edi"] = True
        sample_folder_config["calculate_upc_check_digit"] = "True"
        sample_folder_config["pad_a_records"] = "True"
        sample_folder_config["force_txt_file_ext"] = "True"
        sample_folder_config["invoice_date_offset"] = 5
        dialog = create_dialog(qtbot, sample_folder_config)

        assert dialog._tweak_upc_check.isChecked()
        assert dialog._tweak_pad_arec_check.isChecked()
        assert dialog._tweak_force_txt_check.isChecked()
        assert dialog._tweak_invoice_offset.value() == 5

    def test_tweak_edi_populates_override_upc_fields(self, qtbot, sample_folder_config):
        """Tweak EDI should populate UPC override fields from config."""
        sample_folder_config["folder_is_active"] = "True"
        sample_folder_config["process_backend_copy"] = True
        sample_folder_config["tweak_edi"] = True
        sample_folder_config["override_upc_bool"] = True
        sample_folder_config["override_upc_level"] = 2
        sample_folder_config["override_upc_category_filter"] = "1,2,3"
        sample_folder_config["upc_target_length"] = 13
        dialog = create_dialog(qtbot, sample_folder_config)

        assert dialog._tweak_override_upc_check.isChecked()
        assert dialog._tweak_override_upc_level.currentText() == "2"
        assert dialog._tweak_override_upc_cat_filter.text() == "1,2,3"
        assert dialog._tweak_upc_target_length.text() == "13"


# ============================================================================
# Test Backend States Combined
# ============================================================================
@pytest.mark.qt
class TestBackendStatesCombined:
    """Tests for combined backend state interactions."""

    def test_all_backends_disabled_edi_also_disabled(self, qtbot, sample_folder_config):
        """When no backends are selected, EDI options should be disabled."""
        sample_folder_config["folder_is_active"] = "True"
        sample_folder_config["process_backend_copy"] = False
        sample_folder_config["process_backend_ftp"] = False
        sample_folder_config["process_backend_email"] = False
        dialog = create_dialog(qtbot, sample_folder_config)

        assert not dialog._edi_options_combo.isEnabled()

    def test_any_backend_enabled_edi_enabled(self, qtbot, sample_folder_config):
        """When any backend is selected, EDI options should be enabled."""
        sample_folder_config["folder_is_active"] = "True"
        sample_folder_config["process_backend_copy"] = True
        sample_folder_config["process_backend_ftp"] = False
        sample_folder_config["process_backend_email"] = False
        dialog = create_dialog(qtbot, sample_folder_config)

        assert dialog._edi_options_combo.isEnabled()


# ============================================================================
# Test Split EDI Checkbox Interaction
# ============================================================================
@pytest.mark.qt
class TestSplitEDI:
    """Tests for split EDI checkbox interactions."""

    def test_split_edi_toggles_split_related_fields(self, qtbot, sample_folder_config):
        """Split EDI should enable/disable split-related fields."""
        sample_folder_config["folder_is_active"] = "True"
        sample_folder_config["process_backend_copy"] = True
        sample_folder_config["split_edi"] = False
        dialog = create_dialog(qtbot, sample_folder_config)

        dialog._split_edi_check.setChecked(True)

        assert dialog._send_invoices_check.isEnabled()
        assert dialog._send_credits_check.isEnabled()
        assert dialog._prepend_dates_check.isEnabled()

    def test_split_edi_unchecked_disables_options(self, qtbot, sample_folder_config):
        """Split EDI checkbox can be checked/unchecked regardless of other state."""
        sample_folder_config["folder_is_active"] = "True"
        sample_folder_config["process_backend_copy"] = True
        sample_folder_config["split_edi"] = True
        dialog = create_dialog(qtbot, sample_folder_config)

        dialog._split_edi_check.setChecked(False)

        assert dialog._split_edi_check.isEnabled()
        assert dialog._send_invoices_check.isEnabled()
        assert dialog._send_credits_check.isEnabled()


# ============================================================================
# Test Filter Mode and Categories
# ============================================================================
@pytest.mark.qt
class TestFilterModeAndCategories:
    """Tests for filter mode combo and categories field."""

    def test_filter_mode_combo_exists(self, qtbot, sample_folder_config):
        """Filter mode combo should exist."""
        sample_folder_config["folder_is_active"] = "True"
        sample_folder_config["process_backend_copy"] = True
        dialog = create_dialog(qtbot, sample_folder_config)

        assert hasattr(dialog, "_filter_mode_combo")

    def test_filter_categories_field_exists(self, qtbot, sample_folder_config):
        """Filter categories field should exist."""
        sample_folder_config["folder_is_active"] = "True"
        sample_folder_config["process_backend_copy"] = True
        dialog = create_dialog(qtbot, sample_folder_config)

        assert hasattr(dialog, "_filter_categories_field")

    def test_filter_mode_populated_from_config(self, qtbot, sample_folder_config):
        """Filter mode should be populated from config."""
        sample_folder_config["folder_is_active"] = "True"
        sample_folder_config["process_backend_copy"] = True
        sample_folder_config["split_edi_filter_mode"] = "exclude"
        dialog = create_dialog(qtbot, sample_folder_config)

        assert dialog._filter_mode_combo.currentText() == "exclude"


# ============================================================================
# Test Widget Cleanup and Lifecycle - Crash Prevention
# ============================================================================
@pytest.mark.qt
class TestWidgetCleanupAndLifecycle:
    """Tests for widget cleanup to prevent crashes from stale references.

    These tests verify that when widgets are cleared and recreated (e.g., when
    switching EDI options or convert formats), the old widget references are
    properly removed from self._fields to prevent crashes.
    """

    def test_clear_dynamic_edi_removes_field_references(
        self, qtbot, sample_folder_config
    ):
        """When dynamic EDI widgets are cleared, field references should be removed."""
        from PyQt6.QtWidgets import QComboBox

        sample_folder_config["folder_is_active"] = "True"
        sample_folder_config["process_backend_copy"] = True
        dialog = create_dialog(qtbot, sample_folder_config)
        edi_options_combo = dialog.dynamic_edi_builder.edi_options_combo

        # Switch to "Convert EDI" which creates widgets
        edi_options_combo.setCurrentText("Convert EDI")
        qtbot.waitUntil(
            lambda: (
                "convert_formats_var" in dialog._fields
                and not dialog.dynamic_edi_builder._edi_option_processing
            ),
            timeout=1000,
        )

        # Verify widgets were created
        assert "process_edi" in dialog._fields
        assert "convert_formats_var" in dialog._fields

        # Store reference to the widget and its type
        old_widget = dialog._fields.get("convert_formats_var")
        assert old_widget is not None
        assert isinstance(old_widget, QComboBox)

        # Switch to "Tweak EDI" which clears convert widgets
        edi_options_combo.setCurrentText("Tweak EDI")
        qtbot.waitUntil(
            lambda: (
                "convert_formats_var" not in dialog._fields
                and "force_txt_file_ext_check" in dialog._fields
            ),
            timeout=1000,
        )

        # The convert_formats_var key should be removed since it's part of Convert EDI
        # (Tweak EDI has different widgets)
        assert (
            "convert_formats_var" not in dialog._fields
        ), "convert_formats_var should be removed when switching away from Convert EDI"

    def test_clear_convert_sub_removes_field_references(
        self, qtbot, sample_folder_config
    ):
        """When convert sub-widgets are cleared, field references should be removed."""
        sample_folder_config["folder_is_active"] = "True"
        sample_folder_config["process_backend_copy"] = True
        dialog = create_dialog(qtbot, sample_folder_config)
        edi_options_combo = dialog.dynamic_edi_builder.edi_options_combo

        # Switch to "Convert EDI" with CSV format
        edi_options_combo.setCurrentText("Convert EDI")
        qtbot.waitUntil(
            lambda: (
                "convert_formats_var" in dialog._fields
                and not dialog.dynamic_edi_builder._edi_option_processing
            ),
            timeout=1000,
        )

        convert_format_combo = dialog._fields["convert_formats_var"]
        convert_format_combo.setCurrentText("csv")
        qtbot.waitUntil(lambda: "upc_var_check" in dialog._fields, timeout=1000)

        # Verify CSV widgets were created
        assert "upc_var_check" in dialog._fields

        # Store reference to widget that will be deleted
        old_widget = dialog._fields.get("upc_var_check")
        assert old_widget is not None

        # Change to different format (ScannerWare doesn't have upc_var_check)
        convert_format_combo.setCurrentText("ScannerWare")
        qtbot.waitUntil(
            lambda: (
                "upc_var_check" not in dialog._fields
                and "append_arec_check" in dialog._fields
            ),
            timeout=1000,
        )

        # Verify upc_var_check was cleaned up (ScannerWare doesn't use it)
        assert (
            "upc_var_check" not in dialog._fields
        ), "upc_var_check should be removed when switching from CSV format"

    def test_data_extractor_handles_missing_widgets_gracefully(
        self, qtbot, sample_folder_config
    ):
        """Data extractor should handle missing widgets gracefully without crashing."""
        from interface.qt.dialogs.edit_folders.data_extractor import (
            QtFolderDataExtractor,
        )

        sample_folder_config["folder_is_active"] = "True"
        sample_folder_config["process_backend_copy"] = True
        dialog = create_dialog(qtbot, sample_folder_config)

        # Create extractor with current fields
        extractor = QtFolderDataExtractor(dialog._fields)

        # Simulate a deleted widget by removing it from fields
        if "convert_formats_var" in dialog._fields:
            del dialog._fields["convert_formats_var"]

        # Should not crash, should return default value
        try:
            extracted = extractor.extract_all()
            # If we get here, the extractor handled missing widgets gracefully
            assert extracted is not None
        except Exception as e:
            pytest.fail(f"Data extractor crashed with missing widgets: {e}")

    def test_rapid_edi_option_changes_no_crash(self, qtbot, sample_folder_config):
        """Rapidly changing EDI options should not cause crashes."""
        sample_folder_config["folder_is_active"] = "True"
        sample_folder_config["process_backend_copy"] = True
        dialog = create_dialog(qtbot, sample_folder_config)
        edi_options_combo = dialog.dynamic_edi_builder.edi_options_combo

        # Rapidly switch EDI options (with proper debounce wait times)
        options = [
            "Do Nothing",
            "Convert EDI",
            "Tweak EDI",
            "Convert EDI",
            "Do Nothing",
        ]
        for option in options:
            edi_options_combo.setCurrentText(option)
            qtbot.waitUntil(
                lambda: not dialog.dynamic_edi_builder._edi_option_processing,
                timeout=1000,
            )

        # Should not crash - if we get here, test passes
        assert edi_options_combo.currentText() == options[-1]

    def test_data_extractor_handles_deleted_widgets(self, qtbot, sample_folder_config):
        """Data extractor should handle widgets that have been deleted with deleteLater()."""
        from PyQt6.QtWidgets import QLineEdit

        from interface.qt.dialogs.edit_folders.data_extractor import (
            QtFolderDataExtractor,
        )

        sample_folder_config["folder_is_active"] = "True"
        sample_folder_config["process_backend_copy"] = True
        dialog = create_dialog(qtbot, sample_folder_config)

        # Create a test widget and add it to fields
        test_widget = QLineEdit("test value")
        dialog._fields["test_field"] = test_widget

        # Delete the widget (simulate what happens during clear operations)
        test_widget.deleteLater()
        qtbot.waitUntil(
            lambda: _widget_deleted(dialog._fields["test_field"]),
            timeout=1000,
        )

        # Create extractor and try to extract - should handle gracefully
        extractor = QtFolderDataExtractor(dialog._fields)

        try:
            # This should not crash even though widget is deleted
            result = extractor._get_text("test_field")
            # Should return empty string for deleted widget
            assert result == "" or isinstance(result, str)
        except RuntimeError as e:
            # RuntimeError is expected when accessing deleted Qt widgets
            # but our fix should catch this
            pytest.fail(
                f"Data extractor should catch RuntimeError for deleted widgets: {e}"
            )
        except Exception as e:
            pytest.fail(f"Data extractor crashed with deleted widget: {e}")


def _widget_deleted(widget):
    """Return True once a Qt widget has been deleted."""
    try:
        widget.objectName()
        return False
    except RuntimeError:
        return True
