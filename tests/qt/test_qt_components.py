"""Tests for custom Qt components in Edit Folders Dialog.

Tests cover:
- column_builders.py - Individual column rendering
- dynamic_edi_builder.py - Dynamic EDI field generation
- layout_builder.py - Layout construction
- data_extractor.py - Widget data extraction
- event_handlers.py - Event handler logic
"""

import pytest
from PyQt6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QCheckBox,
    QComboBox,
    QLineEdit,
    QDialog,
)

pytestmark = [pytest.mark.qt, pytest.mark.gui]


@pytest.mark.qt
class TestColumnBuilders:
    """Tests for column builder components."""

    def test_build_others_column(self, qtbot):
        """Test others column builder."""
        from interface.qt.dialogs.edit_folders.column_builders import ColumnBuilders

        parent = QWidget()
        qtbot.addWidget(parent)

        fields = {}
        folder_config = {}

        builders = ColumnBuilders(fields=fields, folder_config=folder_config)

        # Build others column
        column = builders.build_others_column()

        assert column is not None
        assert isinstance(column, QWidget)
        # Should have created others_list in fields
        assert "others_list" in fields

    def test_build_folder_column(self, qtbot):
        """Test folder column builder."""
        from interface.qt.dialogs.edit_folders.column_builders import ColumnBuilders

        parent = QWidget()
        qtbot.addWidget(parent)

        fields = {}
        folder_config = {"folder_name": "test_folder"}

        builders = ColumnBuilders(fields=fields, folder_config=folder_config)

        # Build folder column
        column = builders.build_folder_column()

        assert column is not None
        assert isinstance(column, QWidget)
        # Should have created backend checkboxes in fields
        assert "process_backend_copy_check" in fields
        assert "process_backend_ftp_check" in fields
        assert "process_backend_email_check" in fields

    def test_build_backend_column(self, qtbot):
        """Test backend column builder."""
        from interface.qt.dialogs.edit_folders.column_builders import ColumnBuilders

        parent = QWidget()
        qtbot.addWidget(parent)

        fields = {}
        folder_config = {}

        builders = ColumnBuilders(fields=fields, folder_config=folder_config)

        # Build backend column
        column = builders.build_backend_column()

        assert column is not None
        assert isinstance(column, QWidget)
        # Should have created FTP and email fields
        assert "ftp_server_field" in fields
        assert "email_recipient_field" in fields

    def test_build_edi_column(self, qtbot):
        """Test EDI column builder."""
        from interface.qt.dialogs.edit_folders.column_builders import ColumnBuilders

        parent = QWidget()
        qtbot.addWidget(parent)

        fields = {}
        folder_config = {}

        builders = ColumnBuilders(fields=fields, folder_config=folder_config)

        # Build EDI column
        column = builders.build_edi_column()

        assert column is not None
        assert isinstance(column, QWidget)
        # Should have created EDI option checkboxes
        assert "split_edi" in fields
        assert "force_edi_check_var" in fields


@pytest.mark.qt
class TestDynamicEDIBuilder:
    """Tests for dynamic EDI field builder."""

    def test_build_edi_options_combo(self, qtbot):
        """Test building EDI options combo."""
        from interface.qt.dialogs.edit_folders.dynamic_edi_builder import (
            DynamicEDIBuilder,
        )

        parent = QWidget()
        qtbot.addWidget(parent)

        dynamic_container = QWidget()
        dynamic_layout = QVBoxLayout(dynamic_container)

        fields = {}
        folder_config = {}

        builder = DynamicEDIBuilder(
            fields=fields,
            folder_config=folder_config,
            dynamic_container=dynamic_container,
            dynamic_layout=dynamic_layout,
        )

        # Build EDI options combo
        combo = builder.build_edi_options_combo()

        assert combo is not None
        assert isinstance(combo, QComboBox)
        # Should have Do Nothing, Convert EDI, Tweak EDI options
        assert combo.count() == 3

    def test_edi_option_changed(self, qtbot):
        """Test EDI option change handling."""
        from interface.qt.dialogs.edit_folders.dynamic_edi_builder import (
            DynamicEDIBuilder,
        )

        parent = QWidget()
        qtbot.addWidget(parent)

        dynamic_container = QWidget()
        dynamic_layout = QVBoxLayout(dynamic_container)

        fields = {}
        folder_config = {}

        builder = DynamicEDIBuilder(
            fields=fields,
            folder_config=folder_config,
            dynamic_container=dynamic_container,
            dynamic_layout=dynamic_layout,
        )

        # Build combo and trigger change
        combo = builder.build_edi_options_combo()
        combo.setCurrentText("Convert EDI")

        # Should have created process_edi hidden field
        assert "process_edi" in fields

    def test_convert_format_changed(self, qtbot):
        """Test convert format change handling."""
        from interface.qt.dialogs.edit_folders.dynamic_edi_builder import (
            DynamicEDIBuilder,
        )

        parent = QWidget()
        qtbot.addWidget(parent)

        dynamic_container = QWidget()
        dynamic_layout = QVBoxLayout(dynamic_container)

        fields = {}
        folder_config = {}

        builder = DynamicEDIBuilder(
            fields=fields,
            folder_config=folder_config,
            dynamic_container=dynamic_container,
            dynamic_layout=dynamic_layout,
        )

        # Build EDI options combo first
        builder.edi_options_combo = QComboBox()
        builder.edi_options_combo.addItems(["Do Nothing", "Convert EDI", "Tweak EDI"])
        builder.edi_options_combo.setCurrentText("Convert EDI")

        # Need to also set up the convert sub container
        builder.convert_sub_container = QWidget()
        builder.convert_sub_layout = QVBoxLayout(builder.convert_sub_container)

        # Now handle format change - this bypasses _build_convert_edi_area
        # so convert_formats_var won't be set. But CSV fields will be created.
        builder.handle_convert_format_changed("csv")

        # Should have created CSV-specific fields (upc check is one of them)
        assert "upc_var_check" in fields


@pytest.mark.qt
class TestLayoutBuilder:
    """Tests for layout builder."""

    def test_build_ui(self, qtbot):
        """Test building main dialog layout."""
        from interface.qt.dialogs.edit_folders.layout_builder import UILayoutBuilder

        dialog = QDialog()
        qtbot.addWidget(dialog)

        fields = {}
        folder_config = {"folder_name": "test"}

        builder = UILayoutBuilder(
            dialog=dialog,
            fields=fields,
            folder_config=folder_config,
        )

        # Build layout
        builder.build_ui()

        # Should have created active checkbox
        assert "active_checkbutton" in fields
        assert fields["active_checkbutton"] is not None

    def test_get_column_builders(self, qtbot):
        """Test getting column builders from layout builder."""
        from interface.qt.dialogs.edit_folders.layout_builder import UILayoutBuilder

        dialog = QDialog()
        qtbot.addWidget(dialog)

        fields = {}
        folder_config = {"folder_name": "test"}

        builder = UILayoutBuilder(
            dialog=dialog,
            fields=fields,
            folder_config=folder_config,
        )

        # Build and get column builders
        builder.build_ui()
        column_builders = builder.get_column_builders()

        assert column_builders is not None
        assert hasattr(column_builders, "build_others_column")
        assert hasattr(column_builders, "build_folder_column")


@pytest.mark.qt
class TestDataExtractor:
    """Tests for data extractor."""

    def test_extract_basic_fields(self, qtbot):
        """Test extracting basic field values."""
        from interface.qt.dialogs.edit_folders.data_extractor import (
            QtFolderDataExtractor,
        )

        parent = QWidget()
        qtbot.addWidget(parent)

        # Create test widgets with actual field names expected by extractor
        alias_field = QLineEdit("Test Alias")
        active_checkbox = QCheckBox()
        active_checkbox.setChecked(True)

        fields = {
            "folder_alias_field": alias_field,
            "active_checkbutton": active_checkbox,
        }

        extractor = QtFolderDataExtractor(fields)

        # Extract values
        extracted = extractor.extract_all()

        assert extracted is not None
        assert extracted.alias == "Test Alias"
        assert extracted.folder_is_active is True

    def test_extract_backend_configurations(self, qtbot):
        """Test extracting backend configurations."""
        from interface.qt.dialogs.edit_folders.data_extractor import (
            QtFolderDataExtractor,
        )

        parent = QWidget()
        qtbot.addWidget(parent)

        # Create backend checkboxes
        copy_checkbox = QCheckBox()
        copy_checkbox.setChecked(True)
        ftp_checkbox = QCheckBox()
        ftp_checkbox.setChecked(False)
        email_checkbox = QCheckBox()
        email_checkbox.setChecked(True)

        fields = {
            "process_backend_copy_check": copy_checkbox,
            "process_backend_ftp_check": ftp_checkbox,
            "process_backend_email_check": email_checkbox,
        }

        extractor = QtFolderDataExtractor(fields)
        extracted = extractor.extract_all()

        assert extracted is not None
        assert extracted.process_backend_copy is True
        assert extracted.process_backend_ftp is False
        assert extracted.process_backend_email is True

    def test_extract_edi_options(self, qtbot):
        """Test extracting EDI options."""
        from interface.qt.dialogs.edit_folders.data_extractor import (
            QtFolderDataExtractor,
        )

        parent = QWidget()
        qtbot.addWidget(parent)

        # Create EDI option widgets
        process_edi = QCheckBox()
        process_edi.setChecked(True)
        split_edi = QCheckBox()
        split_edi.setChecked(True)

        fields = {
            "process_edi": process_edi,
            "split_edi": split_edi,
        }

        extractor = QtFolderDataExtractor(fields)
        extracted = extractor.extract_all()

        assert extracted is not None
        assert extracted.process_edi is True
        assert extracted.split_edi is True


@pytest.mark.qt
class TestEventHandlers:
    """Tests for event handlers."""

    def test_update_active_state(self, qtbot):
        """Test handler for active checkbox toggle."""
        from interface.qt.dialogs.edit_folders.event_handlers import EventHandlers

        parent = QWidget()
        qtbot.addWidget(parent)

        # Create required fields
        active_checkbox = QCheckBox("Folder Is Disabled")
        active_checkbox.setChecked(True)

        backend_copy_check = QCheckBox()
        backend_copy_check.setChecked(False)
        backend_ftp_check = QCheckBox()
        backend_ftp_check.setChecked(False)

        fields = {
            "active_checkbutton": active_checkbox,
            "process_backend_copy_check": backend_copy_check,
            "process_backend_ftp_check": backend_ftp_check,
        }

        folder_config = {}

        handlers = EventHandlers(
            dialog=parent,
            folder_config=folder_config,
            fields=fields,
            copy_to_directory="",
            validator=None,
        )

        # Call update_active_state
        handlers.update_active_state()

        # Backend widgets should be enabled when active
        assert backend_copy_check.isEnabled() is True

    def test_update_backend_states(self, qtbot):
        """Test handler for backend checkbox changes."""
        from interface.qt.dialogs.edit_folders.event_handlers import EventHandlers

        parent = QWidget()
        qtbot.addWidget(parent)

        # Create required fields - active AND FTP must be checked for FTP fields to be enabled
        active_checkbox = QCheckBox()
        active_checkbox.setChecked(True)

        copy_checkbox = QCheckBox()
        copy_checkbox.setChecked(True)  # At least one backend must be active

        ftp_checkbox = QCheckBox()
        ftp_checkbox.setChecked(True)  # FTP must be checked for FTP fields

        ftp_server = QLineEdit()
        # Initially enabled

        fields = {
            "active_checkbutton": active_checkbox,
            "process_backend_copy_check": copy_checkbox,
            "process_backend_ftp_check": ftp_checkbox,
            "ftp_server_field": ftp_server,
        }

        folder_config = {}

        handlers = EventHandlers(
            dialog=parent,
            folder_config=folder_config,
            fields=fields,
            copy_to_directory="",
            validator=None,
        )

        # Call update_backend_states
        handlers.update_backend_states()

        # FTP fields should be enabled when active AND FTP backend is checked
        assert ftp_server.isEnabled() is True

    def test_copy_config_from_other(self, qtbot):
        """Test copying config from other folder."""
        from interface.qt.dialogs.edit_folders.event_handlers import EventHandlers

        parent = QWidget()
        qtbot.addWidget(parent)

        # Create required fields
        fields = {}
        folder_config = {}

        handlers = EventHandlers(
            dialog=parent,
            folder_config=folder_config,
            fields=fields,
            copy_to_directory="",
            validator=None,
        )

        # Should have the method
        assert hasattr(handlers, "copy_config_from_other")


@pytest.mark.qt
class TestComponentIntegration:
    """Tests for component integration."""

    def test_builders_with_extractor(self, qtbot):
        """Test using builders and extractor together."""
        from interface.qt.dialogs.edit_folders.column_builders import ColumnBuilders
        from interface.qt.dialogs.edit_folders.data_extractor import (
            QtFolderDataExtractor,
        )

        parent = QWidget()
        qtbot.addWidget(parent)

        # Build widgets using column builders
        fields = {}
        folder_config = {"folder_name": "test"}

        builders = ColumnBuilders(fields=fields, folder_config=folder_config)

        # Build folder column (contains alias field)
        folder_column = builders.build_folder_column()

        # Create alias field manually for this test
        alias_field = QLineEdit("Test Alias")
        fields["folder_alias_field"] = alias_field

        active_checkbox = QCheckBox()
        active_checkbox.setChecked(True)
        fields["active_checkbutton"] = active_checkbox

        # Extract data
        extractor = QtFolderDataExtractor(fields)
        extracted = extractor.extract_all()

        # Verify roundtrip
        assert extracted.alias == "Test Alias"
        assert extracted.folder_is_active is True

    def test_dynamic_fields_with_extraction(self, qtbot):
        """Test dynamic field building and extraction."""
        from interface.qt.dialogs.edit_folders.dynamic_edi_builder import (
            DynamicEDIBuilder,
        )
        from interface.qt.dialogs.edit_folders.data_extractor import (
            QtFolderDataExtractor,
        )

        parent = QWidget()
        qtbot.addWidget(parent)

        dynamic_container = QWidget()
        dynamic_layout = QVBoxLayout(dynamic_container)

        fields = {}
        folder_config = {}

        # Build dynamic fields
        builder = DynamicEDIBuilder(
            fields=fields,
            folder_config=folder_config,
            dynamic_container=dynamic_container,
            dynamic_layout=dynamic_layout,
        )

        # Set up EDI options combo
        builder.edi_options_combo = QComboBox()
        builder.edi_options_combo.addItems(["Do Nothing", "Convert EDI", "Tweak EDI"])
        builder.edi_options_combo.setCurrentText("Convert EDI")

        # Set up convert sub container
        builder.convert_sub_container = QWidget()
        builder.convert_sub_layout = QVBoxLayout(builder.convert_sub_container)

        # Handle format change to CSV
        builder.handle_convert_format_changed("csv")

        # Extract from dynamic fields
        extractor = QtFolderDataExtractor(fields)
        extracted = extractor.extract_all()

        assert extracted is not None


@pytest.mark.qt
class TestComponentErrorHandling:
    """Tests for component error handling."""

    def test_extractor_with_missing_fields(self, qtbot):
        """Test extractor handles missing fields gracefully."""
        from interface.qt.dialogs.edit_folders.data_extractor import (
            QtFolderDataExtractor,
        )

        parent = QWidget()
        qtbot.addWidget(parent)

        # Create incomplete field set
        fields = {
            "folder_alias_field": QLineEdit("Test"),
            # Missing other required fields
        }

        extractor = QtFolderDataExtractor(fields)

        # Should not crash - missing fields return defaults
        extracted = extractor.extract_all()

        assert extracted is not None
        # Missing fields should return defaults
        assert extracted.folder_name == ""

    def test_builder_with_empty_config(self, qtbot):
        """Test builder handles empty configuration."""
        from interface.qt.dialogs.edit_folders.column_builders import ColumnBuilders

        parent = QWidget()
        qtbot.addWidget(parent)

        fields = {}
        folder_config = {}

        builders = ColumnBuilders(fields=fields, folder_config=folder_config)

        # Build with empty config should not crash
        column = builders.build_folder_column()

        assert column is not None
