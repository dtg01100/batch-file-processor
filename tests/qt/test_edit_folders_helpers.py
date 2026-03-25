"""Focused tests for edit_folders helper modules.

These tests target low-coverage helper modules used by the Qt EditFolders dialog.
"""

from unittest.mock import MagicMock

import pytest
from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import QCheckBox, QDialog, QPushButton, QVBoxLayout, QWidget

from interface.qt.dialogs.edit_folders.column_builders import ColumnBuilders
from interface.qt.dialogs.edit_folders.dynamic_edi_builder import DynamicEDIBuilder
from interface.qt.dialogs.edit_folders.event_handlers import EventHandlers
from interface.qt.dialogs.edit_folders.layout_builder import UILayoutBuilder


@pytest.mark.qt
class TestColumnBuilders:
    def test_build_others_column_populates_sorted_aliases_and_copy_callback(
        self, qtbot
    ):
        fields = {}
        copy_cb = MagicMock()

        builder = ColumnBuilders(
            fields=fields,
            folder_config={},
            alias_provider=lambda: ["Zulu", "Alpha"],
            on_copy_config=copy_cb,
        )

        col = builder.build_others_column()
        qtbot.addWidget(col)

        others_list = fields["others_list"]
        assert others_list.count() == 2
        assert others_list.item(0).text() == "Alpha"
        assert others_list.item(1).text() == "Zulu"

        # Locate copy button by text to avoid relying on private attributes
        copy_button = None
        for btn in col.findChildren(QPushButton):
            if btn.text() == "Copy Config":
                copy_button = btn
                break

        assert copy_button is not None
        qtbot.mouseClick(copy_button, Qt.MouseButton.LeftButton)
        copy_cb.assert_called_once()

    def test_build_folder_column_creates_alias_field_for_non_template(self, qtbot):
        fields = {}
        show_path_cb = MagicMock()

        builder = ColumnBuilders(
            fields=fields,
            folder_config={"folder_name": "/tmp/folder"},
            on_show_path=show_path_cb,
        )

        col = builder.build_folder_column()
        qtbot.addWidget(col)

        assert "folder_alias_field" in fields
        assert fields["folder_alias_field"] is not None

    def test_build_backend_column_wires_select_copy_callback(self, qtbot):
        fields = {}
        select_copy_cb = MagicMock()

        builder = ColumnBuilders(
            fields=fields,
            folder_config={},
            on_select_copy_dir=select_copy_cb,
        )

        col = builder.build_backend_column()
        qtbot.addWidget(col)

        qtbot.mouseClick(fields["copy_dest_btn"], Qt.MouseButton.LeftButton)
        select_copy_cb.assert_called_once()
        assert "ftp_password_field" in fields


@pytest.mark.qt
class TestUILayoutBuilder:
    def test_build_ui_creates_dynamic_edi_components(self, qtbot):
        dialog = QDialog()
        qtbot.addWidget(dialog)
        fields = {}

        builder = UILayoutBuilder(
            dialog=dialog,
            fields=fields,
            folder_config={"folder_name": "template"},
            alias_provider=lambda: [],
            on_update_backend_states=MagicMock(),
            on_convert_format_changed=MagicMock(),
            on_ok=MagicMock(),
            on_cancel=MagicMock(),
        ).build_ui()

        assert builder.get_column_builders() is not None
        assert builder.get_dynamic_edi_builder() is not None
        assert builder.get_active_checkbox() is not None
        assert builder.get_dynamic_edi_layout() is not None


@pytest.mark.qt
class TestDynamicEDIBuilder:
    def test_edi_option_do_nothing_sets_hidden_flags(self, qtbot):
        container = QWidget()
        qtbot.addWidget(container)
        layout = QVBoxLayout(container)

        fields = {}
        builder = DynamicEDIBuilder(
            fields=fields,
            folder_config={},
            dynamic_container=container,
            dynamic_layout=layout,
        )

        builder._on_edi_check_toggled(False)

        assert "process_edi" in fields
        assert fields["process_edi"] is False

    def test_edi_option_convert_supports_tweaks_target(self, qtbot):
        container = QWidget()
        qtbot.addWidget(container)
        layout = QVBoxLayout(container)

        fields = {}
        builder = DynamicEDIBuilder(
            fields=fields,
            folder_config={
                "process_edi": True,
                "convert_to_format": "Tweaks",
            },
            dynamic_container=container,
            dynamic_layout=layout,
        )

        builder._on_edi_check_toggled(True)

        assert "convert_formats_var" in fields
        assert builder.convert_format_combo is not None
        assert builder.convert_format_combo.count() > 0

    def test_handle_convert_format_changed_dispatches_fallback_builders(self, qtbot):
        container = QWidget()
        qtbot.addWidget(container)
        layout = QVBoxLayout(container)

        fields = {}
        builder = DynamicEDIBuilder(
            fields=fields,
            folder_config={},
            dynamic_container=container,
            dynamic_layout=layout,
        )

        builder.convert_sub_container = container
        builder.convert_sub_layout = layout
        builder.plugin_manager.get_configuration_plugin_by_format_name = MagicMock(
            return_value=None
        )
        isolated_pm = MagicMock()
        isolated_pm.get_configuration_plugins.return_value = []
        isolated_pm.get_configuration_plugin_by_format_name = MagicMock(
            return_value=None
        )
        builder = DynamicEDIBuilder(
            fields=fields,
            folder_config={},
            dynamic_container=container,
            dynamic_layout=layout,
            plugin_manager=isolated_pm,
        )

        builder.convert_sub_container = container
        builder.convert_sub_layout = layout

        csv_cb = MagicMock()
        fintech_cb = MagicMock()
        basic_cb = MagicMock()

        builder._build_csv_sub = csv_cb
        builder._build_fintech_sub = fintech_cb
        builder._build_basic_options_sub = basic_cb

        builder.handle_convert_format_changed("csv")
        csv_cb.assert_called_once()

        builder.handle_convert_format_changed("fintech")
        fintech_cb.assert_called_once()

        builder.handle_convert_format_changed("jolley_custom")
        basic_cb.assert_called_once()

    def test_handle_convert_format_changed_uses_plugin_builder(self, qtbot):
        container = QWidget()
        qtbot.addWidget(container)
        layout = QVBoxLayout(container)

        fields = {}
        mock_plugin_manager = MagicMock()
        mock_plugin_manager.get_configuration_plugins.return_value = []
        builder = DynamicEDIBuilder(
            fields=fields,
            folder_config={},
            dynamic_container=container,
            dynamic_layout=layout,
            plugin_manager=mock_plugin_manager,
        )

        builder.convert_sub_container = container
        builder.convert_sub_layout = layout

        plugin = MagicMock()
        mock_plugin_manager.get_configuration_plugin_by_format_name = MagicMock(
            return_value=plugin
        )
        plugin_builder = MagicMock()
        builder._build_plugin_config_sub = plugin_builder

        builder.handle_convert_format_changed("custom_plugin_format")

        plugin_builder.assert_called_once_with(plugin)

    def test_build_edi_options_check_wires_signal(self, qtbot):
        container = QWidget()
        qtbot.addWidget(container)
        layout = QVBoxLayout(container)

        builder = DynamicEDIBuilder(
            fields={},
            folder_config={},
            dynamic_container=container,
            dynamic_layout=layout,
        )

        check = builder.build_edi_options_check()
        qtbot.addWidget(check)
        check.setChecked(True)

        assert isinstance(check, QCheckBox)
        assert builder.convert_format_combo is not None

    def test_clear_convert_sub_removes_nested_widgets(self, qtbot):
        container = QWidget()
        qtbot.addWidget(container)
        layout = QVBoxLayout(container)

        builder = DynamicEDIBuilder(
            fields={},
            folder_config={},
            dynamic_container=container,
            dynamic_layout=layout,
        )
        builder.convert_sub_container = container
        builder.convert_sub_layout = layout

        child = QWidget()
        layout.addWidget(child)
        assert layout.count() == 1

        builder._clear_convert_sub()

        assert layout.count() == 0

    def test_get_convert_formats_returns_plugin_formats(self, qtbot):
        container = QWidget()
        qtbot.addWidget(container)
        layout = QVBoxLayout(container)

        plugin1 = MagicMock()
        plugin1.get_format_name.return_value = "csv"
        plugin2 = MagicMock()
        plugin2.get_format_name.return_value = "fintech"

        builder = DynamicEDIBuilder(
            fields={},
            folder_config={},
            dynamic_container=container,
            dynamic_layout=layout,
        )
        builder.configuration_plugins = [plugin1, plugin2]

        formats = builder._get_convert_formats()

        assert "csv" in formats
        assert "fintech" in formats
        # Only the injected plugins are reflected; no hardcoded extras
        assert len(formats) == 2

    def test_build_convert_edi_area_sets_format_and_callback(self, qtbot):
        container = QWidget()
        qtbot.addWidget(container)
        layout = QVBoxLayout(container)

        on_change = MagicMock()
        builder = DynamicEDIBuilder(
            fields={},
            folder_config={"convert_to_format": "Fintech"},
            dynamic_container=container,
            dynamic_layout=layout,
            on_convert_format_changed=on_change,
        )

        builder._build_convert_edi_area()

        assert builder.convert_format_combo is not None
        assert builder.convert_format_combo.currentText() == "Fintech"
        on_change.assert_called()

    def test_convert_sub_builders_create_expected_fields(self, qtbot):
        container = QWidget()
        qtbot.addWidget(container)
        layout = QVBoxLayout(container)

        fields = {}
        builder = DynamicEDIBuilder(
            fields=fields,
            folder_config={},
            dynamic_container=container,
            dynamic_layout=layout,
        )
        builder.convert_sub_container = container
        builder.convert_sub_layout = layout

        builder._build_csv_sub()
        builder._build_simplified_csv_sub()
        builder._build_estore_sub("Estore eInvoice")
        builder._build_fintech_sub()
        builder._build_basic_options_sub()
        builder._build_scannerware_sub()

        assert "include_item_numbers" in fields
        assert "include_item_description" in fields
        assert "simple_csv_column_sorter" in fields
        assert "estore_store_number_field" in fields
        assert "estore_Vendor_OId_field" in fields
        assert "estore_vendor_namevendoroid_field" in fields
        assert "fintech_divisionid_field" in fields


@pytest.mark.qt
class TestEventHandlers:
    def test_select_copy_directory_updates_path(self, qtbot, monkeypatch):
        dialog = QDialog()
        qtbot.addWidget(dialog)
        handlers = EventHandlers(
            dialog=dialog,
            folder_config={},
            fields={},
            copy_to_directory="/old",
            validator=None,
        )

        monkeypatch.setattr(
            "interface.qt.dialogs.edit_folders.event_handlers.QFileDialog.getExistingDirectory",
            lambda *args, **kwargs: "/new/path",
        )

        handlers.select_copy_directory()

        assert handlers.copy_to_directory == "/new/path"

    def test_on_ok_calls_dialog_private_handler_when_present(self, qtbot):
        dialog = QDialog()
        qtbot.addWidget(dialog)
        dialog._on_ok = MagicMock()

        handlers = EventHandlers(
            dialog=dialog,
            folder_config={},
            fields={},
            copy_to_directory="",
            validator=None,
        )

        handlers.on_ok()

        dialog._on_ok.assert_called_once()

    def test_on_ok_success_calls_callback_and_accept(self, qtbot):
        dialog = QDialog()
        qtbot.addWidget(dialog)
        dialog_accept = MagicMock()
        dialog.accept = dialog_accept

        handlers = EventHandlers(
            dialog=dialog,
            folder_config={},
            fields={},
            copy_to_directory="",
            validator=None,
        )

        handlers.on_ok()

        dialog_accept.assert_called_once()

    def test_on_ok_propagates_private_handler_exception(self, qtbot):
        dialog = QDialog()
        qtbot.addWidget(dialog)
        dialog._on_ok = MagicMock(side_effect=RuntimeError("boom"))

        handlers = EventHandlers(
            dialog=dialog,
            folder_config={},
            fields={},
            copy_to_directory="",
            validator=None,
        )

        with pytest.raises(RuntimeError, match="boom"):
            handlers.on_ok()

    def test_select_copy_directory_cancel_keeps_path(self, qtbot, monkeypatch):
        dialog = QDialog()
        qtbot.addWidget(dialog)
        handlers = EventHandlers(
            dialog=dialog,
            folder_config={},
            fields={},
            copy_to_directory="/original",
            validator=None,
        )

        monkeypatch.setattr(
            "interface.qt.dialogs.edit_folders.event_handlers.QFileDialog.getExistingDirectory",
            lambda *args, **kwargs: "",
        )

        handlers.select_copy_directory()

        assert handlers.copy_to_directory == "/original"

    def test_noop_event_handler_methods_are_callable(self, qtbot, monkeypatch):
        dialog = QDialog()
        qtbot.addWidget(dialog)
        dialog.accept = MagicMock()
        dialog.reject = MagicMock()

        handlers = EventHandlers(
            dialog=dialog,
            folder_config={},
            fields={},
            copy_to_directory="",
            validator=None,
        )

        info_mock = MagicMock()
        monkeypatch.setattr(
            "interface.qt.dialogs.edit_folders.event_handlers.QMessageBox.information",
            info_mock,
        )

        handlers.update_active_state()
        handlers.update_backend_states()
        handlers.copy_config_from_other()
        handlers.show_folder_path()
        handlers.on_ok()
        handlers.on_cancel()

        info_mock.assert_called_once()
        dialog.accept.assert_called_once()
        dialog.reject.assert_called_once()
