"""Unit tests for convert_to_scannerware.py converter module.

Tests:
- Input validation and edge cases
- Parameter combinations and flag handling
- Data transformation accuracy
- Invoice date offset handling
- Fixed-width TXT output format

Converter: convert_to_scannerware.py (8663 chars)
"""

import os

import pytest

from dispatch.converters import convert_to_scannerware


class TestConvertToScannerwareFixtures:
    """Test fixtures for convert_to_scannerware module."""

    @pytest.fixture
    def sample_header_record(self):
        """Create accurate header record (33 chars)."""
        return "A" + "VENDOR" + "0000000001" + "010125" + "0000010000"

    @pytest.fixture
    def sample_detail_record(self):
        """Create accurate detail record (76 chars)."""
        return (
            "B"
            + "01234567890"
            + "Test Item Description    "
            + "123456"
            + "000100"
            + "01"
            + "000001"
            + "00010"
            + "00199"
            + "001"
            + "000000"
        )

    @pytest.fixture
    def sample_tax_record(self):
        """Create accurate sales tax record (38 chars)."""
        return "C" + "TAB" + "Sales Tax" + " " * 16 + "000010000"

    @pytest.fixture
    def complete_edi_content(
        self, sample_header_record, sample_detail_record, sample_tax_record
    ):
        """Create complete EDI content with header, detail, and tax records."""
        return (
            sample_header_record
            + "\n"
            + sample_detail_record
            + "\n"
            + sample_tax_record
            + "\n"
        )

    @pytest.fixture
    def default_parameters(self):
        """Default parameters dict for convert_to_scannerware."""
        return {
            "a_record_padding": "",
            "append_a_records": "False",
            "a_record_append_text": "",
            "force_txt_file_ext": "False",
            "invoice_date_offset": 0,
        }

    @pytest.fixture
    def default_settings(self):
        """Default settings dict."""
        return {
            "as400_username": "test_user",
            "as400_password": "test_pass",
            "as400_address": "test.address.com",
        }


class TestConvertToScannerwareBasicFunctionality(TestConvertToScannerwareFixtures):
    """Test basic functionality of convert_to_scannerware."""

    def test_module_import(self):
        """Test that convert_to_scannerware module can be imported."""
        from dispatch.converters import convert_to_scannerware

        assert convert_to_scannerware is not None
        assert hasattr(convert_to_scannerware, "edi_convert")

    def test_edi_convert_returns_filename(
        self,
        complete_edi_content,
        default_parameters,
        default_settings,
        tmp_path,
    ):
        """Test that edi_convert returns the expected filename (no .txt by default)."""
        input_file = tmp_path / "input.edi"
        input_file.write_text(complete_edi_content)

        output_file = str(tmp_path / "output")

        result = convert_to_scannerware.edi_convert(
            str(input_file),
            output_file,
            default_settings,
            default_parameters,
            {},
        )

        assert result == output_file

    def test_creates_output_file(
        self,
        complete_edi_content,
        default_parameters,
        default_settings,
        tmp_path,
    ):
        """Test that the output file is actually created."""
        input_file = tmp_path / "input.edi"
        input_file.write_text(complete_edi_content)

        output_file = str(tmp_path / "output")

        result = convert_to_scannerware.edi_convert(
            str(input_file),
            output_file,
            default_settings,
            default_parameters,
            {},
        )

        assert os.path.exists(result)

    def test_force_txt_extension_true(
        self,
        complete_edi_content,
        default_parameters,
        default_settings,
        tmp_path,
    ):
        """Test that force_txt_file_ext=True ensures .txt extension."""
        default_parameters["force_txt_file_ext"] = "True"

        input_file = tmp_path / "input.edi"
        input_file.write_text(complete_edi_content)

        output_file = str(tmp_path / "output")

        result = convert_to_scannerware.edi_convert(
            str(input_file),
            output_file,
            default_settings,
            default_parameters,
            {},
        )

        assert result.endswith(".txt")

    def test_force_txt_extension_false(
        self,
        complete_edi_content,
        default_parameters,
        default_settings,
        tmp_path,
    ):
        """Test that force_txt_file_ext=False uses output filename as-is."""
        default_parameters["force_txt_file_ext"] = "False"

        input_file = tmp_path / "input.edi"
        input_file.write_text(complete_edi_content)

        output_file = str(tmp_path / "output")

        result = convert_to_scannerware.edi_convert(
            str(input_file),
            output_file,
            default_settings,
            default_parameters,
            {},
        )

        assert result == output_file


class TestConvertToScannerwareARecord(TestConvertToScannerwareFixtures):
    """Test A record handling in convert_to_scannerware."""

    def test_a_record_padding(
        self,
        complete_edi_content,
        default_parameters,
        default_settings,
        tmp_path,
    ):
        """Test A record padding functionality."""
        default_parameters["a_record_padding"] = "CUSTOM"

        input_file = tmp_path / "input.edi"
        input_file.write_text(complete_edi_content)

        output_file = str(tmp_path / "output")

        result = convert_to_scannerware.edi_convert(
            str(input_file),
            output_file,
            default_settings,
            default_parameters,
            {},
        )

        with open(result, "rb") as f:
            content = f.read().decode("utf-8")
            assert "CUSTOM" in content

    def test_append_a_records_enabled(
        self,
        complete_edi_content,
        default_parameters,
        default_settings,
        tmp_path,
    ):
        """Test appending custom text to A records when enabled."""
        default_parameters["append_a_records"] = "True"
        default_parameters["a_record_append_text"] = "APPENDED"

        input_file = tmp_path / "input.edi"
        input_file.write_text(complete_edi_content)

        output_file = str(tmp_path / "output")

        result = convert_to_scannerware.edi_convert(
            str(input_file),
            output_file,
            default_settings,
            default_parameters,
            {},
        )

        with open(result, "rb") as f:
            content = f.read().decode("utf-8")
            assert "APPENDED" in content

    def test_append_a_records_disabled(
        self,
        complete_edi_content,
        default_parameters,
        default_settings,
        tmp_path,
    ):
        """Test that append text is not added when append_a_records is False."""
        default_parameters["append_a_records"] = "False"
        default_parameters["a_record_append_text"] = "APPENDED"

        input_file = tmp_path / "input.edi"
        input_file.write_text(complete_edi_content)

        output_file = str(tmp_path / "output")

        result = convert_to_scannerware.edi_convert(
            str(input_file),
            output_file,
            default_settings,
            default_parameters,
            {},
        )

        with open(result, "rb") as f:
            content = f.read().decode("utf-8")
            assert "APPENDED" not in content


class TestConvertToScannerwareDateOffset(TestConvertToScannerwareFixtures):
    """Test invoice date offset handling in convert_to_scannerware."""

    def test_invoice_date_offset_zero(
        self,
        sample_header_record,
        default_parameters,
        default_settings,
        tmp_path,
    ):
        """Test that zero date offset leaves date unchanged."""
        default_parameters["invoice_date_offset"] = 0

        input_file = tmp_path / "input.edi"
        input_file.write_text(sample_header_record + "\n")

        output_file = str(tmp_path / "output")

        result = convert_to_scannerware.edi_convert(
            str(input_file),
            output_file,
            default_settings,
            default_parameters,
            {},
        )

        with open(result, "rb") as f:
            content = f.read().decode("utf-8")
            assert "010125" in content

    def test_invoice_date_offset_positive(
        self,
        sample_header_record,
        default_parameters,
        default_settings,
        tmp_path,
    ):
        """Test that positive date offset shifts date forward."""
        default_parameters["invoice_date_offset"] = 7

        input_file = tmp_path / "input.edi"
        input_file.write_text(sample_header_record + "\n")

        output_file = str(tmp_path / "output")

        result = convert_to_scannerware.edi_convert(
            str(input_file),
            output_file,
            default_settings,
            default_parameters,
            {},
        )

        with open(result, "rb") as f:
            content = f.read().decode("utf-8")
            assert "010125" not in content or "010225" in content

    def test_invoice_date_offset_with_zero_date(
        self,
        default_parameters,
        default_settings,
        tmp_path,
    ):
        """Test that zero invoice date is handled gracefully."""
        header_with_zero_date = "A" + "VENDOR" + "0000000001" + "000000" + "0000010000"
        default_parameters["invoice_date_offset"] = 7

        input_file = tmp_path / "input.edi"
        input_file.write_text(header_with_zero_date + "\n")

        output_file = str(tmp_path / "output")

        result = convert_to_scannerware.edi_convert(
            str(input_file),
            output_file,
            default_settings,
            default_parameters,
            {},
        )

        assert os.path.exists(result)


class TestConvertToScannerwareBRecord(TestConvertToScannerwareFixtures):
    """Test B record (detail) handling in convert_to_scannerware."""

    def test_b_record_output_format(
        self,
        sample_header_record,
        default_parameters,
        default_settings,
        tmp_path,
    ):
        """Test that B records are output in correct fixed-width format."""
        detail = (
            "B"
            + "01234567890"
            + "Test Item Description    "
            + "123456"
            + "000100"
            + "01"
            + "000001"
            + "00010"
            + "00199"
            + "001"
            + "000000"
        )
        edi_content = sample_header_record + "\n" + detail + "\n"

        input_file = tmp_path / "input.edi"
        input_file.write_text(edi_content)

        output_file = str(tmp_path / "output")

        result = convert_to_scannerware.edi_convert(
            str(input_file),
            output_file,
            default_settings,
            default_parameters,
            {},
        )

        with open(result, "rb") as f:
            content = f.read().decode("utf-8")
            assert "B" in content
            assert "01234567890" in content

    def test_multiple_b_records(
        self,
        sample_header_record,
        default_parameters,
        default_settings,
        tmp_path,
    ):
        """Test conversion with multiple B records."""
        detail1 = (
            "B"
            + "01234567890"
            + "Item One Description     "
            + "123456"
            + "000100"
            + "01"
            + "000001"
            + "00010"
            + "00199"
            + "001"
            + "000000"
        )
        detail2 = (
            "B"
            + "01234567891"
            + "Item Two Description     "
            + "234567"
            + "000200"
            + "01"
            + "000002"
            + "00020"
            + "00299"
            + "001"
            + "000000"
        )
        edi_content = sample_header_record + "\n" + detail1 + "\n" + detail2 + "\n"

        input_file = tmp_path / "input.edi"
        input_file.write_text(edi_content)

        output_file = str(tmp_path / "output")

        result = convert_to_scannerware.edi_convert(
            str(input_file),
            output_file,
            default_settings,
            default_parameters,
            {},
        )

        with open(result, "rb") as f:
            content = f.read().decode("utf-8")
            assert content.count("B") >= 2


class TestConvertToScannerwareCRecord(TestConvertToScannerwareFixtures):
    """Test C record (charge) handling in convert_to_scannerware."""

    def test_c_record_output(
        self,
        sample_header_record,
        sample_detail_record,
        default_parameters,
        default_settings,
        tmp_path,
    ):
        """Test that C records are output in correct format."""
        tax = "C" + "TAB" + "Sales Tax" + " " * 16 + "000010000"
        edi_content = (
            sample_header_record + "\n" + sample_detail_record + "\n" + tax + "\n"
        )

        input_file = tmp_path / "input.edi"
        input_file.write_text(edi_content)

        output_file = str(tmp_path / "output")

        result = convert_to_scannerware.edi_convert(
            str(input_file),
            output_file,
            default_settings,
            default_parameters,
            {},
        )

        with open(result, "rb") as f:
            content = f.read().decode("utf-8")
            assert "C" in content
            assert "Sales Tax" in content


class TestConvertToScannerwareEdgeCases(TestConvertToScannerwareFixtures):
    """Test edge cases and error conditions."""

    def test_empty_edi_file(self, default_parameters, default_settings, tmp_path):
        """Test handling of empty EDI file."""
        input_file = tmp_path / "input.edi"
        input_file.write_text("")

        output_file = str(tmp_path / "output")

        result = convert_to_scannerware.edi_convert(
            str(input_file),
            output_file,
            default_settings,
            default_parameters,
            {},
        )

        assert os.path.exists(result)

    def test_whitespace_only_file(self, default_parameters, default_settings, tmp_path):
        """Test handling of whitespace-only file."""
        input_file = tmp_path / "input.edi"
        input_file.write_text("   \n   \n   ")

        output_file = str(tmp_path / "output")

        result = convert_to_scannerware.edi_convert(
            str(input_file),
            output_file,
            default_settings,
            default_parameters,
            {},
        )

        assert os.path.exists(result)

    def test_unknown_record_type(self, default_parameters, default_settings, tmp_path):
        """Test handling of unknown record types."""
        input_file = tmp_path / "input.edi"
        input_file.write_text("Xinvalid_record\n")

        output_file = str(tmp_path / "output")

        result = convert_to_scannerware.edi_convert(
            str(input_file),
            output_file,
            default_settings,
            default_parameters,
            {},
        )

        assert os.path.exists(result)

    def test_missing_input_file(self, default_parameters, default_settings, tmp_path):
        """Test that missing input file raises FileNotFoundError."""
        input_file = tmp_path / "does_not_exist.edi"
        output_file = str(tmp_path / "output")

        with pytest.raises(FileNotFoundError):
            convert_to_scannerware.edi_convert(
                str(input_file),
                output_file,
                default_settings,
                default_parameters,
                {},
            )


class TestConvertToScannerwareIntegration(TestConvertToScannerwareFixtures):
    """Integration tests combining multiple features."""

    def test_full_conversion_with_all_features(
        self,
        complete_edi_content,
        default_parameters,
        default_settings,
        tmp_path,
    ):
        """Test conversion with multiple features enabled."""
        default_parameters["a_record_padding"] = "PAD"
        default_parameters["append_a_records"] = "True"
        default_parameters["a_record_append_text"] = "EXT"
        default_parameters["invoice_date_offset"] = 0

        input_file = tmp_path / "input.edi"
        input_file.write_text(complete_edi_content)

        output_file = str(tmp_path / "output")

        result = convert_to_scannerware.edi_convert(
            str(input_file),
            output_file,
            default_settings,
            default_parameters,
            {},
        )

        assert os.path.exists(result)

        with open(result, "rb") as f:
            content = f.read().decode("utf-8")
            assert "A" in content
            assert "B" in content
            assert "C" in content

    def test_output_has_crlf_line_endings(
        self,
        complete_edi_content,
        default_parameters,
        default_settings,
        tmp_path,
    ):
        """Test that output file uses CRLF line endings."""
        input_file = tmp_path / "input.edi"
        input_file.write_text(complete_edi_content)

        output_file = str(tmp_path / "output")

        result = convert_to_scannerware.edi_convert(
            str(input_file),
            output_file,
            default_settings,
            default_parameters,
            {},
        )

        with open(result, "rb") as f:
            content = f.read()
            assert b"\r\n" in content
