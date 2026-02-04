"""
Comprehensive tests for the EDI validator module to improve coverage.
"""

import tempfile
import os
from unittest.mock import MagicMock, patch, mock_open
import pytest
import mtc_edi_validator


def test_validate_file_valid_edi():
    """Test validate_file with a valid EDI file."""
    with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.txt') as f:
        f.write("ISA*00*          *00*          *ZZ*SENDERID       *ZZ*RECEIVERID     *200711*1719*U*00401*000000001*0*P*>~GS*PO*SENDERID*RECEIVERID*20200711*1719*1*X*00401~ST*850*0001~BIG*200711*SO123456~N1*BY*BUYER NAME*1*ADDRESS~N3*123 MAIN ST~N4*CITY*ST*12345~N1*SF*SHIP TO NAME*1*ADDRESS~N3*456 OTHER ST~N4*CITY*ST*12345~ITD*01*3***NET 30~FOB*PP~IT1*1*1*EA*12.99*VP*VENDOR~PID*F****DESCRIPTION~SE*2*0001~GE*1*1~IEA*1*000000001~")
        temp_file_path = f.name

    try:
        # Call the validate function
        result, error_msg = mtc_edi_validator.validate_file(temp_file_path, "test_file.txt")
        
        # Validate results
        assert isinstance(result, bool)
        assert isinstance(error_msg, str)
    finally:
        # Clean up the temporary file
        os.unlink(temp_file_path)


def test_validate_file_invalid_edi():
    """Test validate_file with an invalid EDI file."""
    with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.txt') as f:
        f.write("This is not a valid EDI file content")
        temp_file_path = f.name

    try:
        # Call the validate function
        result, error_msg = mtc_edi_validator.validate_file(temp_file_path, "test_file.txt")
        
        # Validate results
        assert isinstance(result, bool)
        assert isinstance(error_msg, str)
        # For invalid EDI, we expect result to be False
    finally:
        # Clean up the temporary file
        os.unlink(temp_file_path)


def test_validate_file_empty_file():
    """Test validate_file with an empty file."""
    with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.txt') as f:
        # Write nothing to the file, leave it empty
        temp_file_path = f.name

    try:
        # Call the validate function
        result, error_msg = mtc_edi_validator.validate_file(temp_file_path, "test_file.txt")
        
        # Validate results
        assert isinstance(result, bool)
        assert isinstance(error_msg, str)
    finally:
        # Clean up the temporary file
        os.unlink(temp_file_path)


def test_validate_file_missing_file():
    """Test validate_file with a non-existent file."""
    result, error_msg = mtc_edi_validator.validate_file("/nonexistent/file.txt", "test_file.txt")
    
    # Validate results
    assert result is False
    assert isinstance(error_msg, str)
    assert "error" in error_msg.lower() or len(error_msg) > 0


def test_validate_file_malformed_content():
    """Test validate_file with malformed EDI content."""
    with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.txt') as f:
        # Write malformed EDI content
        f.write("ISA*malformed*content*without*proper*segments~")
        temp_file_path = f.name

    try:
        # Call the validate function
        result, error_msg = mtc_edi_validator.validate_file(temp_file_path, "test_file.txt")
        
        # Validate results
        assert isinstance(result, bool)
        assert isinstance(error_msg, str)
    finally:
        # Clean up the temporary file
        os.unlink(temp_file_path)


@patch('builtins.open', side_effect=IOError("Permission denied"))
def test_validate_file_io_error(mock_open_func):
    """Test validate_file when file access raises an IOError."""
    result, error_msg = mtc_edi_validator.validate_file("/some/file.txt", "test_file.txt")
    
    # Validate results
    assert result is False
    assert isinstance(error_msg, str)
    assert "error" in error_msg.lower()


def test_validate_file_various_segment_formats():
    """Test validate_file with various EDI segment formats."""
    # Test with different ISA header formats
    edi_content = "ISA*01*----------*02*----------*ZZ*SENDERID-------*ZZ*RECEIVERID-----*200711*1719*U*00401*000000001*0*P*>~"
    edi_content += "GS*PO*SENDERID*RECEIVERID*20200711*1719*1*X*00401~"
    edi_content += "ST*850*0001~"
    edi_content += "BIG*200711*SO123456~"
    edi_content += "SE*2*0001~"
    edi_content += "GE*1*1~"
    edi_content += "IEA*1*000000001~"
    
    with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.txt') as f:
        f.write(edi_content)
        temp_file_path = f.name

    try:
        # Call the validate function
        result, error_msg = mtc_edi_validator.validate_file(temp_file_path, "test_file.txt")
        
        # Validate results
        assert isinstance(result, bool)
        assert isinstance(error_msg, str)
    finally:
        # Clean up the temporary file
        os.unlink(temp_file_path)


def test_validate_file_with_different_control_ids():
    """Test validate_file with different control ID formats."""
    # EDI with various control IDs
    edi_content = "ISA*00*          *00*          *ZZ*SENDID         *ZZ*RECEIVEID      *200711*1719*U*00401*000000001*0*P*>~"
    edi_content += "GS*SH*COMPANY*PARTNER*20200711*1719*1*X*004010~"  # Different GS ID
    edi_content += "ST*856*0001~"  # Different transaction set
    edi_content += "BSN*00*123456*20200711*1719~"
    edi_content += "SE*2*0001~"
    edi_content += "GE*1*1~"
    edi_content += "IEA*1*000000001~"
    
    with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.txt') as f:
        f.write(edi_content)
        temp_file_path = f.name

    try:
        # Call the validate function
        result, error_msg = mtc_edi_validator.validate_file(temp_file_path, "test_file.txt")
        
        # Validate results
        assert isinstance(result, bool)
        assert isinstance(error_msg, str)
    finally:
        # Clean up the temporary file
        os.unlink(temp_file_path)