"""Pytest fixtures for EditFoldersDialog testing.

This module provides shared fixtures for testing the EditFoldersDialog
and related components (validator, extractor, FTP service).
"""

import sys
from pathlib import Path
from typing import Dict, Any, Optional, List, Callable
from dataclasses import dataclass, field
from unittest.mock import MagicMock

import pytest

# Ensure project root is in path
project_root = Path(__file__).parent.parent.parent.parent.resolve()
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from interface.models.folder_configuration import (
    FolderConfiguration,
    FTPConfiguration,
    EmailConfiguration,
    CopyConfiguration,
    EDIConfiguration,
    UPCOverrideConfiguration,
    ARecordPaddingConfiguration,
    InvoiceDateConfiguration,
    BackendSpecificConfiguration,
    CSVConfiguration,
)
from interface.operations.folder_data_extractor import (
    FolderDataExtractor,
    ExtractedDialogFields,
)
from interface.validation.folder_settings_validator import (
    FolderSettingsValidator,
    ValidationResult,
    ValidationError,
)
from interface.services.ftp_service import (
    FTPServiceProtocol,
    FTPConnectionResult,
    MockFTPService,
)


# =============================================================================
# FTP Service Fixtures
# =============================================================================


@pytest.fixture
def mock_ftp_service() -> MagicMock:
    """Create a mock FTP service with configurable behavior.

    The mock implements FTPServiceProtocol and can be configured to:
    - Succeed or fail connections
    - Track connection attempts
    - Return specific error types

    Returns:
        MagicMock: A mock implementing FTPServiceProtocol

    Example:
        >>> mock_ftp_service.test_connection.return_value = FTPConnectionResult(success=True)
    """
    mock = MagicMock(spec=FTPServiceProtocol)

    # Default to successful connection
    mock.test_connection = MagicMock(
        return_value=FTPConnectionResult(success=True)
    )

    # Track connection attempts for verification
    mock.connection_attempts = []

    def track_connection(server, port, username, password, folder):
        mock.connection_attempts.append({
            'server': server,
            'port': port,
            'username': username,
            'folder': folder
        })
        return FTPConnectionResult(success=True)

    mock.test_connection.side_effect = track_connection

    return mock


@pytest.fixture
def failing_ftp_service() -> MagicMock:
    """Create a mock FTP service that always fails connections.

    Returns:
        MagicMock: A mock FTP service configured to fail
    """
    mock = MagicMock(spec=FTPServiceProtocol)
    mock.test_connection = MagicMock(
        return_value=FTPConnectionResult(
            success=False,
            error_message="Connection failed",
            error_type="server"
        )
    )
    return mock


# =============================================================================
# Validator Fixtures
# =============================================================================


@pytest.fixture
def mock_validator() -> MagicMock:
    """Create a mock FolderSettingsValidator with configurable validation.

    The mock can be configured to:
    - Return success or specific validation errors
    - Track validation calls and arguments
    - Support FTP connection testing via mock FTP service

    Returns:
        MagicMock: A mock validator with validation control

    Example:
        >>> validator = mock_validator()
        >>> validator.validate_extracted_fields.return_value = ValidationResult(is_valid=False)
    """
    mock = MagicMock(spec=FolderSettingsValidator)

    # Default successful validation
    mock.validate_extracted_fields = MagicMock(
        return_value=ValidationResult(is_valid=True)
    )

    # Track calls for verification
    mock.validate_call_args = None
    mock.validate_called = False

    def track_validation(extracted, current_alias=""):
        mock.validate_called = True
        mock.validate_call_args = (extracted, current_alias)
        return ValidationResult(is_valid=True)

    mock.validate_extracted_fields.side_effect = track_validation

    # Mock other validator methods
    mock.validate_ftp_settings = MagicMock(return_value=[])
    mock.validate_email_settings = MagicMock(return_value=[])
    mock.validate_copy_settings = MagicMock(return_value=[])
    mock.validate_edi_settings = MagicMock(return_value=[])

    return mock


@pytest.fixture
def failing_mock_validator() -> MagicMock:
    """Create a mock validator that returns validation failures.

    Returns:
        MagicMock: A validator configured to fail with errors
    """
    mock = MagicMock(spec=FolderSettingsValidator)

    # Return failed validation with sample errors
    def return_errors(extracted, current_alias=""):
        result = ValidationResult(is_valid=False)
        result.add_error("folder_name", "Folder name is required")
        result.add_error("alias", "Alias must be unique")
        return result

    mock.validate_extracted_fields.side_effect = return_errors

    return mock


@pytest.fixture
def validating_mock_validator(mock_ftp_service) -> FolderSettingsValidator:
    """Create a real FolderSettingsValidator with mock FTP service.

    Args:
        mock_ftp_service: Mock FTP service fixture

    Returns:
        FolderSettingsValidator: Validator configured with mock dependencies
    """
    return FolderSettingsValidator(
        ftp_service=mock_ftp_service,
        existing_aliases=[]
    )


# =============================================================================
# Extractor Fixtures
# =============================================================================


@pytest.fixture
def mock_extractor() -> MagicMock:
    """Create a mock FolderDataExtractor with configurable extraction.

    The mock can be configured to:
    - Return specific extracted field values
    - Track extraction calls
    - Support all dialog field extraction

    Returns:
        MagicMock: A mock extractor with extraction control

    Example:
        >>> extractor = mock_extractor()
        >>> extractor.extract_all.return_value = ExtractedDialogFields(folder_name="/test")
    """
    mock = MagicMock(spec=FolderDataExtractor)

    # Default extracted fields
    default_fields = ExtractedDialogFields(
        folder_name="/test/folder",
        alias="Test Folder",
        folder_is_active="True",
        process_backend_copy=False,
        process_backend_ftp=True,
        process_backend_email=False,
        ftp_server="ftp.example.com",
        ftp_port=21,
        ftp_folder="/uploads/",
        ftp_username="testuser",
        ftp_password="testpass",
        email_to="",
        email_subject_line="",
        process_edi="False",
        convert_to_format=""
    )

    mock.extract_all = MagicMock(return_value=default_fields)
    mock.extract_called = False

    def track_extraction():
        mock.extract_called = True
        return default_fields

    mock.extract_all.side_effect = track_extraction

    return mock


@pytest.fixture
def sample_extracted_fields() -> ExtractedDialogFields:
    """Create sample extracted dialog fields for testing.

    Returns:
        ExtractedDialogFields: A complete set of extracted field values
    """
    return ExtractedDialogFields(
        folder_name="/test/folder",
        alias="Test Folder",
        folder_is_active="True",
        process_backend_copy=True,
        process_backend_ftp=True,
        process_backend_email=True,
        ftp_server="ftp.example.com",
        ftp_port=21,
        ftp_folder="/uploads/",
        ftp_username="testuser",
        ftp_password="testpass",
        email_to="recipient@example.com",
        email_subject_line="Test Subject",
        process_edi="True",
        convert_to_format="CSV",
        tweak_edi=True,
        split_edi=False,
        prepend_date_files=False,
        rename_file="",
        split_edi_filter_categories="ALL",
        split_edi_filter_mode="include"
    )


# =============================================================================
# Folder Configuration Fixtures
# =============================================================================


@pytest.fixture
def sample_folder_config() -> FolderConfiguration:
    """Create a sample FolderConfiguration with typical values.

    Returns:
        FolderConfiguration: Complete folder config with FTP, Email, Copy, and EDI settings
    """
    return FolderConfiguration(
        folder_name="/test/folder",
        folder_is_active="True",
        alias="test-folder",
        is_template=False,
        process_backend_copy=True,
        process_backend_ftp=True,
        process_backend_email=False,
        ftp=FTPConfiguration(
            server="ftp.example.com",
            port=21,
            username="testuser",
            password="testpass",
            folder="/uploads/"
        ),
        email=EmailConfiguration(
            recipients="recipient@example.com",
            subject_line="Test Subject"
        ),
        copy=CopyConfiguration(
            destination_directory="/copy/destination"
        ),
        edi=EDIConfiguration(
            process_edi="True",
            tweak_edi=True,
            split_edi=False,
            split_edi_include_invoices=True,
            split_edi_include_credits=False,
            prepend_date_files=False,
            convert_to_format="CSV",
            force_edi_validation=False,
            rename_file="",
            split_edi_filter_categories="ALL",
            split_edi_filter_mode="include"
        ),
        upc_override=UPCOverrideConfiguration(
            enabled=False,
            level=1,
            category_filter="",
            target_length=11,
            padding_pattern="           "
        ),
        a_record_padding=ARecordPaddingConfiguration(
            enabled=False,
            padding_text="",
            padding_length=6,
            append_text="",
            append_enabled=False,
            force_txt_extension=False
        ),
        invoice_date=InvoiceDateConfiguration(
            offset=0,
            custom_format_enabled=False,
            custom_format_string="",
            retail_uom=False
        ),
        backend_specific=BackendSpecificConfiguration(
            estore_store_number="",
            estore_vendor_oid="",
            estore_vendor_namevendoroid="",
            fintech_division_id=""
        ),
        csv=CSVConfiguration(
            include_headers=True,
            filter_ampersand=False,
            include_item_numbers=False,
            include_item_description=False,
            simple_csv_sort_order="",
            split_prepaid_sales_tax_crec=False
        )
    )


@pytest.fixture
def sample_ftp_folder_config() -> FolderConfiguration:
    """Create a sample FolderConfiguration with FTP-only settings.

    Returns:
        FolderConfiguration: Config with FTP backend enabled
    """
    return FolderConfiguration(
        folder_name="/ftp/folder",
        folder_is_active="True",
        alias="ftp-folder",
        process_backend_ftp=True,
        process_backend_copy=False,
        process_backend_email=False,
        ftp=FTPConfiguration(
            server="ftp.example.com",
            port=21,
            username="ftpuser",
            password="ftppass",
            folder="/incoming/"
        ),
        email=None,
        copy=None,
        edi=EDIConfiguration(process_edi="False")
    )


@pytest.fixture
def sample_email_folder_config() -> FolderConfiguration:
    """Create a sample FolderConfiguration with Email-only settings.

    Returns:
        FolderConfiguration: Config with Email backend enabled
    """
    return FolderConfiguration(
        folder_name="/email/folder",
        folder_is_active="True",
        alias="email-folder",
        process_backend_email=True,
        process_backend_ftp=False,
        process_backend_copy=False,
        email=EmailConfiguration(
            recipients="test@example.com, other@example.com",
            subject_line="Daily Report"
        ),
        ftp=None,
        copy=None,
        edi=EDIConfiguration(process_edi="False")
    )


@pytest.fixture
def sample_edi_folder_config() -> FolderConfiguration:
    """Create a sample FolderConfiguration with EDI settings.

    Returns:
        FolderConfiguration: Config with EDI processing enabled
    """
    return FolderConfiguration(
        folder_name="/edi/folder",
        folder_is_active="True",
        alias="edi-folder",
        process_backend_copy=True,
        copy=CopyConfiguration(destination_directory="/output"),
        edi=EDIConfiguration(
            process_edi="True",
            tweak_edi=True,
            split_edi=True,
            split_edi_include_invoices=True,
            split_edi_include_credits=True,
            convert_to_format="CSV",
            prepend_date_files=True,
            rename_file="processed_{filename}"
        )
    )


# =============================================================================
# Folder Dictionary Fixtures
# =============================================================================


@pytest.fixture
def sample_folder_dict() -> Dict[str, Any]:
    """Create a sample folder configuration dictionary.

    This represents the dictionary format as would come from the database.

    Returns:
        Dict[str, Any]: Folder configuration as dictionary
    """
    return {
        'folder_name': '/test/folder',
        'folder_is_active': 'True',
        'alias': 'test-folder',
        'is_template': False,
        # Backend toggles
        'process_backend_copy': True,
        'process_backend_ftp': True,
        'process_backend_email': False,
        # FTP fields
        'ftp_server': 'ftp.example.com',
        'ftp_port': 21,
        'ftp_folder': '/uploads/',
        'ftp_username': 'testuser',
        'ftp_password': 'testpass',
        # Email fields
        'email_to': 'recipient@example.com',
        'email_subject_line': 'Test Subject',
        # Copy fields
        'copy_to_directory': '/copy/destination',
        # EDI fields
        'process_edi': 'True',
        'convert_to_format': 'CSV',
        'tweak_edi': True,
        'split_edi': False,
        'split_edi_include_invoices': True,
        'split_edi_include_credits': False,
        'prepend_date_files': False,
        'rename_file': '',
        'split_edi_filter_categories': 'ALL',
        'split_edi_filter_mode': 'include',
        'force_edi_validation': False,
        # EDI options
        'calculate_upc_check_digit': 'True',
        'include_a_records': 'True',
        'include_c_records': 'False',
        'include_headers': 'True',
        'filter_ampersand': 'False',
        # A-record
        'pad_a_records': 'False',
        'a_record_padding': '',
        'a_record_padding_length': 6,
        'append_a_records': 'False',
        'a_record_append_text': '',
        'force_txt_file_ext': 'False',
        # Invoice date
        'invoice_date_offset': 0,
        'invoice_date_custom_format': False,
        'invoice_date_custom_format_string': '',
        'retail_uom': False,
        # UPC override
        'override_upc_bool': False,
        'override_upc_level': 1,
        'override_upc_category_filter': '',
        'upc_target_length': 11,
        'upc_padding_pattern': '           ',
        # Backend-specific
        'estore_store_number': '',
        'estore_vendor_oid': '',
        'estore_vendor_namevendoroid': '',
        'fintech_division_id': '',
        # CSV
        'include_item_numbers': False,
        'include_item_description': False,
        'simple_csv_sort_order': '',
        'split_prepaid_sales_tax_crec': False
    }


@pytest.fixture
def minimal_folder_dict() -> Dict[str, Any]:
    """Create a minimal folder configuration dictionary.

    Returns:
        Dict[str, Any]: Minimal folder config with required fields only
    """
    return {
        'folder_name': '/minimal/folder',
        'folder_is_active': 'False',
        'alias': 'minimal-folder',
        'process_backend_copy': False,
        'process_backend_ftp': False,
        'process_backend_email': False,
        'process_edi': 'False'
    }


# =============================================================================
# Combined Dependencies Fixtures
# =============================================================================


@pytest.fixture
def dialog_dependencies(
    mock_ftp_service: MagicMock,
    mock_validator: MagicMock,
    mock_extractor: MagicMock
) -> Dict[str, Any]:
    """Provide all three dependencies for EditFoldersDialog testing.

    This fixture combines the three main dependencies (ftp_service,
    validator, extractor) into a single dictionary for convenient use.

    Args:
        mock_ftp_service: Mock FTP service fixture
        mock_validator: Mock validator fixture
        mock_extractor: Mock extractor fixture

    Returns:
        Dict containing 'ftp_service', 'validator', and 'extractor'

    Example:
        >>> deps = dialog_dependencies()
        >>> dialog = EditFoldersDialog(
        ...     parent=None,
        ...     foldersnameinput={},
        ...     ftp_service=deps['ftp_service'],
        ...     validator=deps['validator'],
        ...     extractor=deps['extractor']
        ... )
    """
    return {
        'ftp_service': mock_ftp_service,
        'validator': mock_validator,
        'extractor': mock_extractor
    }


@pytest.fixture
def dialog_dependencies_with_real_validator(
    mock_ftp_service: MagicMock,
    sample_folder_dict: Dict[str, Any]
) -> Dict[str, Any]:
    """Provide dependencies with a real FolderSettingsValidator.

    Args:
        mock_ftp_service: Mock FTP service fixture
        sample_folder_dict: Sample folder dictionary for alias extraction

    Returns:
        Dict containing dependencies with real validator
    """
    # Extract existing aliases from sample data
    existing_aliases = [sample_folder_dict.get('alias', '')]

    return {
        'ftp_service': mock_ftp_service,
        'validator': FolderSettingsValidator(
            ftp_service=mock_ftp_service,
            existing_aliases=existing_aliases
        ),
        'extractor': MagicMock(spec=FolderDataExtractor)
    }


# =============================================================================
# Settings and Alias Provider Fixtures
# =============================================================================


@pytest.fixture
def mock_settings_provider() -> Callable:
    """Create a mock settings provider function.

    Returns:
        Callable: Function that returns mock settings dict
    """
    def provider():
        return {
            'company_name': 'Test Company',
            'email_sender': 'noreply@test.com',
            'default_ftp_port': 21
        }
    return provider


@pytest.fixture
def mock_alias_provider() -> Callable:
    """Create a mock alias provider function.

    Returns:
        Callable: Function that returns list of existing aliases
    """
    def provider():
        return [
            'existing-folder-1',
            'existing-folder-2',
            'test-folder'
        ]
    return provider


# =============================================================================
# Validation Result Fixtures
# =============================================================================


@pytest.fixture
def valid_validation_result() -> ValidationResult:
    """Create a validation result indicating success.

    Returns:
        ValidationResult: Valid result with no errors
    """
    return ValidationResult(is_valid=True)


@pytest.fixture
def invalid_validation_result() -> ValidationResult:
    """Create a validation result with errors.

    Returns:
        ValidationResult: Invalid result with sample errors
    """
    result = ValidationResult(is_valid=False)
    result.add_error("folder_name", "Folder name is required")
    result.add_error("alias", "Alias must be unique")
    return result


@pytest.fixture
def validation_result_with_warnings() -> ValidationResult:
    """Create a validation result with warnings.

    Returns:
        ValidationResult: Valid result with warnings
    """
    result = ValidationResult(is_valid=True)
    result.add_warning("ftp_password", "Password is empty, FTP may fail")
    result.add_warning("email_to", "No recipients specified")
    return result
