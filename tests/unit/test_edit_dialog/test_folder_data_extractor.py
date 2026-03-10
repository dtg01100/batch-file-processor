"""Folder Data Extractor tests for EditFoldersDialog refactoring."""

import pytest
from unittest.mock import MagicMock
import sys
import os

# Add the project root to the path
sys.path.insert(
    0,
    os.path.dirname(
        os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    ),
)

from interface.operations.folder_data_extractor import (
    FolderDataExtractor,
    ExtractedDialogFields,
)

# =============================================================================
# Widget Factory Helpers - Reduce mock boilerplate
# =============================================================================


def create_mock_widget(value):
    """Create a mock widget with a get() method returning the specified value.

    This helper reduces the mock boilerplate in test fixtures.

    Args:
        value: The value to return from widget.get()

    Returns:
        MagicMock: A mock widget that returns value from get()
    """
    widget = MagicMock()
    widget.get.return_value = value
    return widget


def create_field_dict(**kwargs):
    """Create a dictionary of mock widget fields from keyword arguments.

    This helper creates a dict of mock widgets in one call, reducing boilerplate.

    Args:
        **kwargs: Field names and their values

    Returns:
        dict: Dictionary of mock widgets
    """
    return {key: create_mock_widget(value) for key, value in kwargs.items()}


class TestExtractedDialogFields:
    """Test suite for ExtractedDialogFields dataclass."""

    def test_default_values(self):
        """Test that all fields have correct default values."""
        fields = ExtractedDialogFields()

        # Identity defaults
        assert fields.folder_name == ""
        assert fields.alias == ""
        assert fields.folder_is_active is False

        # Backend toggles defaults
        assert fields.process_backend_copy is False
        assert fields.process_backend_ftp is False
        assert fields.process_backend_email is False

        # FTP defaults
        assert fields.ftp_server == ""
        assert fields.ftp_port == 21
        assert fields.ftp_folder == ""
        assert fields.ftp_username == ""
        assert fields.ftp_password == ""

        # Email defaults
        assert fields.email_to == ""
        assert fields.email_subject_line == ""

        # EDI defaults
        assert fields.process_edi is False
        assert fields.convert_to_format == ""
        assert fields.tweak_edi is False
        assert fields.split_edi is False
        assert fields.split_edi_include_invoices is False
        assert fields.split_edi_include_credits is False
        assert fields.prepend_date_files is False
        assert fields.rename_file == ""
        assert fields.split_edi_filter_categories == "ALL"
        assert fields.split_edi_filter_mode == "include"

        # A-record defaults
        assert fields.pad_a_records is False
        assert fields.a_record_padding == ""
        assert fields.a_record_padding_length == 6
        assert fields.append_a_records is False
        assert fields.a_record_append_text == ""
        assert fields.force_txt_file_ext is False

        # Invoice date defaults
        assert fields.invoice_date_offset == 0
        assert fields.invoice_date_custom_format is False
        assert fields.invoice_date_custom_format_string == ""
        assert fields.retail_uom is False

        # UPC override defaults
        assert fields.override_upc_bool is False
        assert fields.override_upc_level == 1
        assert fields.override_upc_category_filter == ""
        assert fields.upc_target_length == 11
        assert fields.upc_padding_pattern == "           "

        # Copy destination
        assert fields.copy_to_directory == ""

    def test_custom_values(self):
        """Test that custom values are stored correctly."""
        fields = ExtractedDialogFields(
            folder_name="Test Folder",
            alias="test-alias",
            folder_is_active="True",
            ftp_server="ftp.example.com",
            ftp_port=22,
            ftp_username="user",
            ftp_password="pass",
            ftp_folder="/uploads/",
            email_to="test@example.com",
            process_backend_ftp=True,
        )

        assert fields.folder_name == "Test Folder"
        assert fields.alias == "test-alias"
        assert fields.folder_is_active == "True"
        assert fields.ftp_server == "ftp.example.com"
        assert fields.ftp_port == 22
        assert fields.ftp_username == "user"
        assert fields.ftp_password == "pass"
        assert fields.ftp_folder == "/uploads/"
        assert fields.email_to == "test@example.com"
        assert fields.process_backend_ftp is True


class TestFolderDataExtractor:
    """Test suite for FolderDataExtractor."""

    @pytest.fixture
    def mock_fields(self):
        """Create mock dialog fields using factory helpers.

        Uses create_field_dict helper to reduce mock boilerplate.
        """
        return create_field_dict(
            foldersnameinput="/path/to/folder",
            folder_alias_field="alias_field",
            active_checkbutton="True",
            process_backend_copy_check=True,
            process_backend_ftp_check=True,
            process_backend_email_check=False,
            ftp_server_field="ftp.example.com",
            ftp_port_field="21",
            ftp_folder_field="/uploads/",
            ftp_username_field="testuser",
            ftp_password_field="testpass",
            email_recepient_field="test@example.com",
            email_sender_subject_field="Test Subject",
            process_edi="False",
            convert_formats_var="csv",
            tweak_edi=True,
            split_edi=False,
            split_edi_send_invoices=True,
            split_edi_send_credits=True,
            prepend_file_dates=False,
            rename_file_field="",
            split_edi_filter_categories_entry="ALL",
            split_edi_filter_mode="include",
            upc_var_check="True",
            a_rec_var_check="True",
            c_rec_var_check="False",
            headers_check="True",
            ampersand_check="False",
            force_edi_check_var=False,
            pad_arec_check="False",
            a_record_padding_field="",
            a_record_padding_length="6",
            append_arec_check="False",
            a_record_append_field="",
            force_txt_file_ext_check="False",
            invoice_date_offset="0",
            invoice_date_custom_format=False,
            invoice_date_custom_format_field="",
            edi_each_uom_tweak=False,
            override_upc_bool=False,
            override_upc_level="1",
            override_upc_category_filter_entry="",
            upc_target_length_entry="11",
            upc_padding_pattern_entry="           ",
            include_item_numbers=False,
            include_item_description=False,
            simple_csv_column_sorter="",
            split_sales_tax_prepaid_var=False,
            estore_store_number_field="",
            estore_Vendor_OId_field="",
            estore_vendor_namevendoroid_field="",
            fintech_divisionid_field="",
        )

    @pytest.fixture
    def extractor(self, mock_fields):
        """Create extractor with mock fields."""
        return FolderDataExtractor(mock_fields)

    def test_extract_all_returns_extracted_dialog_fields(self, extractor):
        """Test that extract_all returns ExtractedDialogFields instance."""
        result = extractor.extract_all()

        assert isinstance(result, ExtractedDialogFields)

    def test_extract_identity_fields(self, extractor, mock_fields):
        """Test extracting identity fields."""
        result = extractor.extract_all()

        assert result.folder_name == "/path/to/folder"
        assert result.alias == "alias_field"
        assert result.folder_is_active is True

    def test_extract_backend_toggles(self, extractor, mock_fields):
        """Test extracting backend toggle values."""
        result = extractor.extract_all()

        assert result.process_backend_copy is True
        assert result.process_backend_ftp is True
        assert result.process_backend_email is False

    def test_extract_ftp_fields(self, extractor, mock_fields):
        """Test extracting FTP fields."""
        result = extractor.extract_all()

        assert result.ftp_server == "ftp.example.com"
        assert result.ftp_port == 21
        assert result.ftp_folder == "/uploads/"
        assert result.ftp_username == "testuser"
        assert result.ftp_password == "testpass"

    def test_extract_email_fields(self, extractor, mock_fields):
        """Test extracting email fields."""
        result = extractor.extract_all()

        assert result.email_to == "test@example.com"
        assert result.email_subject_line == "Test Subject"

    def test_extract_edi_fields(self, extractor, mock_fields):
        """Test extracting EDI fields."""
        result = extractor.extract_all()

        assert result.process_edi is False
        assert result.convert_to_format == "csv"
        assert result.tweak_edi is True
        assert result.split_edi is False
        assert result.split_edi_include_invoices is True
        assert result.split_edi_include_credits is True
        assert result.prepend_date_files is False

    def test_extract_a_record_fields(self, extractor, mock_fields):
        """Test extracting A-record fields."""
        result = extractor.extract_all()

        assert result.pad_a_records is False
        assert result.a_record_padding == ""
        assert result.a_record_padding_length == 6
        assert result.append_a_records is False
        assert result.a_record_append_text == ""
        assert result.force_txt_file_ext is False

    def test_extract_invoice_date_fields(self, extractor, mock_fields):
        """Test extracting invoice date fields."""
        result = extractor.extract_all()

        assert result.invoice_date_offset == 0
        assert result.invoice_date_custom_format is False
        assert result.invoice_date_custom_format_string == ""
        assert result.retail_uom is False

    def test_extract_upc_override_fields(self, extractor, mock_fields):
        """Test extracting UPC override fields."""
        result = extractor.extract_all()

        assert result.override_upc_bool is False
        assert result.override_upc_level == 1
        assert result.override_upc_category_filter == ""
        assert result.upc_target_length == 11
        assert result.upc_padding_pattern == "           "

    def test_extract_backend_specific_fields(self, extractor, mock_fields):
        """Test extracting backend-specific fields."""
        result = extractor.extract_all()

        assert result.estore_store_number == ""
        assert result.estore_vendor_oid == ""
        assert result.estore_vendor_namevendoroid == ""
        assert result.fintech_division_id == ""

    def test_extract_copy_destination(self, extractor, mock_fields):
        """Test extracting copy destination."""
        result = extractor.extract_all()

        # copy_to_directory is always empty in extract_all
        assert result.copy_to_directory == ""

    def test_get_text_with_missing_field(self, extractor):
        """Test _get_text returns empty string for missing field."""
        result = extractor._get_text("nonexistent_field")

        assert result == ""

    def test_get_text_with_empty_field(self, extractor):
        """Test _get_text returns empty string for empty widget."""
        mock_widget = MagicMock()
        mock_widget.get.return_value = ""

        extractor.fields["test_field"] = mock_widget
        result = extractor._get_text("test_field")

        assert result == ""

    def test_get_int_with_missing_field(self, extractor):
        """Test _get_int returns 0 for missing field."""
        result = extractor._get_int("nonexistent_field")

        assert result == 0

    def test_get_int_with_valid_value(self, extractor):
        """Test _get_int returns correct integer."""
        mock_widget = MagicMock()
        mock_widget.get.return_value = "42"

        extractor.fields["test_field"] = mock_widget
        result = extractor._get_int("test_field")

        assert result == 42

    def test_get_int_with_invalid_value(self, extractor):
        """Test _get_int returns 0 for invalid integer."""
        mock_widget = MagicMock()
        mock_widget.get.side_effect = ValueError("Invalid integer")

        extractor.fields["test_field"] = mock_widget
        result = extractor._get_int("test_field")

        assert result == 0

    def test_get_bool_with_missing_field(self, extractor):
        """Test _get_bool returns False for missing field."""
        result = extractor._get_bool("nonexistent_field")

        assert result is False

    def test_get_bool_with_true_value(self, extractor):
        """Test _get_bool returns True for truthy value."""
        mock_widget = MagicMock()
        mock_widget.get.return_value = True

        extractor.fields["test_field"] = mock_widget
        result = extractor._get_bool("test_field")

        assert result is True

    def test_get_bool_with_false_value(self, extractor):
        """Test _get_bool returns False for falsy value."""
        mock_widget = MagicMock()
        mock_widget.get.return_value = False

        extractor.fields["test_field"] = mock_widget
        result = extractor._get_bool("test_field")

        assert result is False

    def test_get_bool_with_string_false_value(self, extractor):
        """Test _get_bool returns False for string 'False'."""
        mock_widget = MagicMock()
        mock_widget.get.return_value = "False"

        extractor.fields["test_field"] = mock_widget
        result = extractor._get_bool("test_field")

        assert result is False

    def test_get_value_with_missing_field(self, extractor):
        """Test _get_value returns empty string for missing field."""
        result = extractor._get_value("nonexistent_field")

        assert result == ""

    def test_get_value_with_valid_value(self, extractor):
        """Test _get_value returns string of value."""
        mock_widget = MagicMock()
        mock_widget.get.return_value = "test_value"

        extractor.fields["test_field"] = mock_widget
        result = extractor._get_value("test_field")

        assert result == "test_value"


class TestFolderDataExtractorEdgeCases:
    """Test suite for edge cases in FolderDataExtractor."""

    @pytest.fixture
    def empty_extractor(self):
        """Create extractor with empty fields."""
        return FolderDataExtractor({})

    @pytest.fixture
    def extractor_with_none_values(self):
        """Create extractor with None values in fields."""
        fields = {
            "ftp_server_field": None,
            "ftp_port_field": None,
            "ftp_username_field": None,
        }
        return FolderDataExtractor(fields)

    def test_extract_all_with_empty_fields(self, empty_extractor):
        """Test extract_all with no fields defined."""
        result = empty_extractor.extract_all()

        # All should have default values
        assert result.folder_name == ""
        assert result.alias == ""
        assert result.ftp_server == ""
        assert result.ftp_port == 0  # Missing field returns 0 from _get_int
        assert result.process_backend_ftp is False
        assert result.email_to == ""

    def test_extract_all_with_none_values(self, extractor_with_none_values):
        """Test extract_all with None widget values."""
        result = extractor_with_none_values.extract_all()

        # None widgets should not cause errors
        assert result.ftp_server == ""
        assert result.ftp_port == 0  # None returns 0 from _get_int
        assert result.ftp_username == ""

    def test_get_text_with_none_widget(self, empty_extractor):
        """Test _get_text handles None widget gracefully."""
        empty_extractor.fields["test_field"] = None
        result = empty_extractor._get_text("test_field")

        assert result == ""


class TestFolderDataExtractorBackendSpecific:
    """Test suite for backend-specific extraction logic."""

    @pytest.fixture
    def ftp_fields(self):
        """Create FTP-specific mock fields using factory helpers."""
        return create_field_dict(
            process_backend_ftp_check=True,
            ftp_server_field="ftp.test.com",
            ftp_port_field="990",
            ftp_folder_field="/secure/",
            ftp_username_field="admin",
            ftp_password_field="secret",
        )

    @pytest.fixture
    def email_fields(self):
        """Create Email-specific mock fields using factory helpers."""
        return create_field_dict(
            process_backend_email_check=True,
            email_recepient_field="user@example.com, other@example.com",
            email_sender_subject_field="EDIFACT Invoice",
        )

    @pytest.fixture
    def copy_fields(self):
        """Create Copy-specific mock fields using factory helpers."""
        return create_field_dict(
            process_backend_copy_check=True,
            copy_to_directory="/output/dir",
        )

    def test_extract_ftp_backend_enabled(self, ftp_fields):
        """Test extracting FTP backend when enabled."""
        extractor = FolderDataExtractor(ftp_fields)
        result = extractor.extract_all()

        assert result.process_backend_ftp is True
        assert result.ftp_server == "ftp.test.com"
        assert result.ftp_port == 990
        assert result.ftp_folder == "/secure/"
        assert result.ftp_username == "admin"
        assert result.ftp_password == "secret"

    def test_extract_email_backend_enabled(self, email_fields):
        """Test extracting Email backend when enabled."""
        extractor = FolderDataExtractor(email_fields)
        result = extractor.extract_all()

        assert result.process_backend_email is True
        assert result.email_to == "user@example.com, other@example.com"
        assert result.email_subject_line == "EDIFACT Invoice"

    def test_extract_copy_backend_enabled(self, copy_fields):
        """Test extracting Copy backend when enabled."""
        extractor = FolderDataExtractor(copy_fields)
        result = extractor.extract_all()

        # Note: copy_to_directory is not in the default extract_all
        # It's handled separately in the dialog
        assert result.process_backend_copy is True
