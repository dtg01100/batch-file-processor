"""
Comprehensive unit tests for the dispatch EDI processor module.

These tests cover the EDISplitter, EDIConverter, EDITweaker, EDIProcessor,
and FileNamer classes with extensive mocking of external dependencies.
"""

import os
import tempfile
from io import StringIO
from unittest.mock import MagicMock, Mock, patch, mock_open

import pytest

# Import the module under test
from dispatch.edi_processor import (
    EDISplitter,
    EDIConverter,
    EDITweaker,
    EDIProcessor,
    FileNamer,
)


# =============================================================================
# Fixtures
# =============================================================================


@pytest.fixture
def sample_parameters_dict():
    """Provide sample parameters dictionary for testing."""
    return {
        "convert_to_format": "CSV",
        "process_edi": "True",
        "tweak_edi": True,
        "split_edi": True,
        "rename_file": "output_%datetime%",
        "prepend_date_files": False,
    }


@pytest.fixture
def sample_parameters_dict_no_processing():
    """Provide sample parameters dictionary with no processing enabled."""
    return {
        "convert_to_format": "CSV",
        "process_edi": "False",
        "tweak_edi": False,
        "split_edi": False,
        "rename_file": "",
        "prepend_date_files": False,
    }


@pytest.fixture
def sample_settings():
    """Provide sample settings dictionary for testing."""
    return {
        "as400_username": "test_user",
        "as400_password": "test_pass",
        "as400_address": "test_host",
        "odbc_driver": "test_driver",
    }


@pytest.fixture
def sample_upc_dict():
    """Provide sample UPC dictionary for testing."""
    return {
        12345: ["CAT1", "UPC1", "UPC2", "UPC3", "UPC4"],
        67890: ["CAT2", "UPC5", "UPC6", "UPC7", "UPC8"],
    }


@pytest.fixture
def sample_edi_content():
    """Provide sample EDI file content."""
    return """A000001INV00001011221251000012345
B012345678901Product Description 1234561234567890100001000100050000
C00100000123
A000002INV00002011221251000054321
B098765432109Another Product 7890123456789010200002000200100000
C00200000543
"""


@pytest.fixture
def sample_single_edi_content():
    """Provide sample single-invoice EDI file content."""
    return """A000001INV00001011221251000012345
B012345678901Product Description 1234561234567890100001000100050000
C00100000123
"""


# =============================================================================
# EDISplitter Tests
# =============================================================================


class TestEDISplitter:
    """Tests for the EDISplitter class."""

    def test_split_edi_success(self, sample_parameters_dict, sample_edi_content):
        """Test successful EDI file splitting."""
        with tempfile.TemporaryDirectory() as scratch_folder:
            # Create test EDI file
            input_file = os.path.join(scratch_folder, "test.edi")
            with open(input_file, "w") as f:
                f.write(sample_edi_content)

            with patch("dispatch.edi_processor.utils.do_split_edi") as mock_split:
                mock_split.return_value = [
                    (os.path.join(scratch_folder, "split_1.edi"), "", ".inv"),
                    (os.path.join(scratch_folder, "split_2.edi"), "", ".inv"),
                ]

                result = EDISplitter.split_edi(
                    input_file, scratch_folder, sample_parameters_dict
                )

                assert len(result) == 2
                assert result[0][0].endswith("split_1.edi")
                assert result[1][0].endswith("split_2.edi")
                mock_split.assert_called_once_with(
                    input_file, scratch_folder, sample_parameters_dict
                )

    def test_split_edi_single_file(
        self, sample_parameters_dict, sample_single_edi_content
    ):
        """Test EDI splitting with single file result."""
        with tempfile.TemporaryDirectory() as scratch_folder:
            input_file = os.path.join(scratch_folder, "test.edi")
            with open(input_file, "w") as f:
                f.write(sample_single_edi_content)

            with patch("dispatch.edi_processor.utils.do_split_edi") as mock_split:
                mock_split.return_value = [
                    (os.path.join(scratch_folder, "split_1.edi"), "", ".inv"),
                ]

                result = EDISplitter.split_edi(
                    input_file, scratch_folder, sample_parameters_dict
                )

                assert len(result) == 1
                mock_split.assert_called_once()

    def test_split_edi_empty_result(self, sample_parameters_dict):
        """Test EDI splitting with empty result."""
        with tempfile.TemporaryDirectory() as scratch_folder:
            input_file = os.path.join(scratch_folder, "test.edi")
            with open(input_file, "w") as f:
                f.write("")

            with patch("dispatch.edi_processor.utils.do_split_edi") as mock_split:
                mock_split.return_value = []

                result = EDISplitter.split_edi(
                    input_file, scratch_folder, sample_parameters_dict
                )

                assert result == []

    def test_split_edi_exception_handling(self, sample_parameters_dict):
        """Test EDI splitting exception handling."""
        with tempfile.TemporaryDirectory() as scratch_folder:
            input_file = os.path.join(scratch_folder, "test.edi")
            with open(input_file, "w") as f:
                f.write("content")

            with patch("dispatch.edi_processor.utils.do_split_edi") as mock_split:
                mock_split.side_effect = Exception("Split error")

                result = EDISplitter.split_edi(
                    input_file, scratch_folder, sample_parameters_dict
                )

                # Should return original file on error
                assert len(result) == 1
                assert result[0][0] == input_file
                assert result[0][1] == ""
                assert result[0][2] == ""

    def test_split_edi_multiple_files_output(self, sample_parameters_dict):
        """Test EDI splitting with multiple output files."""
        with tempfile.TemporaryDirectory() as scratch_folder:
            input_file = os.path.join(scratch_folder, "test.edi")
            with open(input_file, "w") as f:
                f.write("EDI content")

            with (
                patch("dispatch.edi_processor.utils.do_split_edi") as mock_split,
                patch("builtins.print") as mock_print,
            ):
                mock_split.return_value = [
                    (os.path.join(scratch_folder, "split_1.edi"), "A_", ".inv"),
                    (os.path.join(scratch_folder, "split_2.edi"), "B_", ".inv"),
                    (os.path.join(scratch_folder, "split_3.edi"), "C_", ".cr"),
                ]

                result = EDISplitter.split_edi(
                    input_file, scratch_folder, sample_parameters_dict
                )

                assert len(result) == 3
                mock_print.assert_called_once()
                assert "split into 3 files" in mock_print.call_args[0][0]


# =============================================================================
# EDIConverter Tests
# =============================================================================


class TestEDIConverter:
    """Tests for the EDIConverter class."""

    def test_convert_edi_success(self, sample_parameters_dict, sample_settings):
        """Test successful EDI conversion."""
        with tempfile.TemporaryDirectory() as temp_dir:
            input_file = os.path.join(temp_dir, "input.edi")
            output_file = os.path.join(temp_dir, "output.csv")
            upc_dict = {}

            with open(input_file, "w") as f:
                f.write("EDI content")

            with patch("dispatch.edi_processor.importlib.import_module") as mock_import:
                mock_module = MagicMock()
                mock_module.edi_convert.return_value = output_file
                mock_import.return_value = mock_module

                result = EDIConverter.convert_edi(
                    input_file,
                    output_file,
                    sample_settings,
                    sample_parameters_dict,
                    upc_dict,
                )

                assert result == output_file
                mock_import.assert_any_call("convert_to_csv")
                mock_module.edi_convert.assert_called_once_with(
                    input_file,
                    output_file,
                    sample_settings,
                    sample_parameters_dict,
                    upc_dict,
                )

    def test_convert_edi_different_format(self, sample_settings):
        """Test EDI conversion with different format."""
        parameters_dict = {
            "convert_to_format": "Fintech",
        }

        with patch("dispatch.edi_processor.importlib.import_module") as mock_import:
            mock_module = MagicMock()
            mock_module.edi_convert.return_value = "/output/file.txt"
            mock_import.return_value = mock_module

            result = EDIConverter.convert_edi(
                "/input/file.edi",
                "/output/file.txt",
                sample_settings,
                parameters_dict,
                {},
            )

            mock_import.assert_called_once_with("convert_to_fintech")

    def test_convert_edi_format_normalization(self, sample_settings):
        """Test EDI conversion format name normalization."""
        parameters_dict = {
            "convert_to_format": "E-Store Invoice",
        }

        with patch("dispatch.edi_processor.importlib.import_module") as mock_import:
            mock_module = MagicMock()
            mock_module.edi_convert.return_value = "/output/file.txt"
            mock_import.return_value = mock_module

            EDIConverter.convert_edi(
                "/input/file.edi",
                "/output/file.txt",
                sample_settings,
                parameters_dict,
                {},
            )

            # Should convert "E-Store Invoice" to "convert_to_e_store_invoice"
            mock_import.assert_called_once_with("convert_to_e_store_invoice")

    def test_convert_edi_import_error(self, sample_parameters_dict, sample_settings):
        """Test EDI conversion handles import error."""
        with patch("dispatch.edi_processor.importlib.import_module") as mock_import:
            mock_import.side_effect = ImportError("Module not found")

            with pytest.raises(ImportError):
                EDIConverter.convert_edi(
                    "/input/file.edi",
                    "/output/file.csv",
                    sample_settings,
                    sample_parameters_dict,
                    {},
                )


# =============================================================================
# EDITweaker Tests
# =============================================================================


class TestEDITweaker:
    """Tests for the EDITweaker class."""

    def test_tweak_edi_success(
        self, sample_parameters_dict, sample_settings, sample_upc_dict
    ):
        """Test successful EDI tweaking."""
        with tempfile.TemporaryDirectory() as temp_dir:
            input_file = os.path.join(temp_dir, "input.edi")
            output_file = os.path.join(temp_dir, "output.edi")

            with open(input_file, "w") as f:
                f.write("EDI content")

            with (
                patch(
                    "dispatch.edi_processor.convert_to_edi_tweaks.edi_tweak"
                ) as mock_tweak,
                patch("builtins.print") as mock_print,
            ):
                mock_tweak.return_value = output_file

                result = EDITweaker.tweak_edi(
                    input_file,
                    output_file,
                    sample_settings,
                    sample_parameters_dict,
                    sample_upc_dict,
                )

                assert result == output_file
                mock_tweak.assert_called_once_with(
                    input_file,
                    output_file,
                    sample_settings,
                    sample_parameters_dict,
                    sample_upc_dict,
                )
                mock_print.assert_called_once()

    def test_tweak_edi_exception(
        self, sample_parameters_dict, sample_settings, sample_upc_dict
    ):
        """Test EDI tweaking exception handling."""
        with patch(
            "dispatch.edi_processor.convert_to_edi_tweaks.edi_tweak"
        ) as mock_tweak:
            mock_tweak.side_effect = Exception("Tweak error")

            with pytest.raises(Exception) as exc_info:
                EDITweaker.tweak_edi(
                    "/input/file.edi",
                    "/output/file.edi",
                    sample_settings,
                    sample_parameters_dict,
                    sample_upc_dict,
                )

            assert "Tweak error" in str(exc_info.value)


# =============================================================================
# EDIProcessor Tests
# =============================================================================


class TestEDIProcessor:
    """Tests for the EDIProcessor class."""

    def test_process_edi_no_split(
        self, sample_parameters_dict_no_processing, sample_settings, sample_upc_dict
    ):
        """Test EDI processing without splitting."""
        with tempfile.TemporaryDirectory() as scratch_folder:
            input_file = os.path.join(scratch_folder, "test.edi")
            with open(input_file, "w") as f:
                f.write("EDI content")

            parameters = sample_parameters_dict_no_processing.copy()
            parameters["split_edi"] = False
            parameters["process_edi"] = "False"

            result = EDIProcessor.process_edi(
                input_file, parameters, sample_settings, sample_upc_dict, scratch_folder
            )

            assert len(result) == 1
            assert result[0][0] == input_file
            assert result[0][1] == ""
            assert result[0][2] == ""

    def test_process_edi_with_split(
        self, sample_parameters_dict_no_processing, sample_settings, sample_upc_dict
    ):
        """Test EDI processing with splitting."""
        with tempfile.TemporaryDirectory() as scratch_folder:
            input_file = os.path.join(scratch_folder, "test.edi")
            with open(input_file, "w") as f:
                f.write("EDI content")

            # Create split files that the mock will return
            split1 = os.path.join(scratch_folder, "split1.edi")
            split2 = os.path.join(scratch_folder, "split2.edi")
            with open(split1, "w") as f:
                f.write("Split 1 content")
            with open(split2, "w") as f:
                f.write("Split 2 content")

            parameters = sample_parameters_dict_no_processing.copy()
            parameters["split_edi"] = True

            with patch("dispatch.edi_processor.EDISplitter.split_edi") as mock_split:
                mock_split.return_value = [
                    (split1, "A_", ".inv"),
                    (split2, "B_", ".inv"),
                ]

                result = EDIProcessor.process_edi(
                    input_file,
                    parameters,
                    sample_settings,
                    sample_upc_dict,
                    scratch_folder,
                )

                assert len(result) == 2
                mock_split.assert_called_once()

    def test_process_edi_with_conversion(
        self, sample_parameters_dict, sample_settings, sample_upc_dict
    ):
        """Test EDI processing with conversion."""
        with tempfile.TemporaryDirectory() as scratch_folder:
            input_file = os.path.join(scratch_folder, "test.edi")
            with open(input_file, "w") as f:
                f.write("EDI content")

            parameters = sample_parameters_dict.copy()
            parameters["split_edi"] = False
            parameters["process_edi"] = "True"
            parameters["tweak_edi"] = False

            with patch(
                "dispatch.edi_processor.EDIConverter.convert_edi"
            ) as mock_convert:
                mock_convert.return_value = os.path.join(
                    scratch_folder, "converted_test.edi"
                )

                result = EDIProcessor.process_edi(
                    input_file,
                    parameters,
                    sample_settings,
                    sample_upc_dict,
                    scratch_folder,
                )

                assert len(result) == 1
                mock_convert.assert_called_once()

    def test_process_edi_with_tweaking(
        self, sample_parameters_dict, sample_settings, sample_upc_dict
    ):
        """Test EDI processing with tweaking."""
        with tempfile.TemporaryDirectory() as scratch_folder:
            input_file = os.path.join(scratch_folder, "test.edi")
            with open(input_file, "w") as f:
                f.write("EDI content")

            parameters = sample_parameters_dict.copy()
            parameters["split_edi"] = False
            parameters["process_edi"] = "False"
            parameters["tweak_edi"] = True

            with patch("dispatch.edi_processor.EDITweaker.tweak_edi") as mock_tweak:
                mock_tweak.return_value = os.path.join(
                    scratch_folder, "tweaked_test.edi"
                )

                result = EDIProcessor.process_edi(
                    input_file,
                    parameters,
                    sample_settings,
                    sample_upc_dict,
                    scratch_folder,
                )

                assert len(result) == 1
                mock_tweak.assert_called_once()

    def test_process_edi_full_pipeline(
        self, sample_parameters_dict, sample_settings, sample_upc_dict
    ):
        """Test EDI processing with full pipeline (split + convert + tweak)."""
        with tempfile.TemporaryDirectory() as scratch_folder:
            input_file = os.path.join(scratch_folder, "test.edi")
            with open(input_file, "w") as f:
                f.write("EDI content")

            split1 = os.path.join(scratch_folder, "split1.edi")
            with open(split1, "w") as f:
                f.write("Split 1 content")

            parameters = sample_parameters_dict.copy()
            parameters["split_edi"] = True
            parameters["process_edi"] = "True"
            parameters["tweak_edi"] = True

            with (
                patch("dispatch.edi_processor.EDISplitter.split_edi") as mock_split,
                patch(
                    "dispatch.edi_processor.EDIConverter.convert_edi"
                ) as mock_convert,
                patch("dispatch.edi_processor.EDITweaker.tweak_edi") as mock_tweak,
            ):
                mock_split.return_value = [
                    (split1, "A_", ".inv"),
                ]
                mock_convert.return_value = os.path.join(
                    scratch_folder, "converted_split1.edi"
                )
                mock_tweak.return_value = os.path.join(
                    scratch_folder, "tweaked_converted_split1.edi"
                )

                result = EDIProcessor.process_edi(
                    input_file,
                    parameters,
                    sample_settings,
                    sample_upc_dict,
                    scratch_folder,
                )

                assert len(result) == 1
                mock_split.assert_called_once()
                mock_convert.assert_called_once()
                mock_tweak.assert_called_once()

    def test_process_single_file_copy(
        self, sample_parameters_dict_no_processing, sample_settings, sample_upc_dict
    ):
        """Test _process_single_file copies file to scratch folder."""
        with tempfile.TemporaryDirectory() as scratch_folder:
            input_file = os.path.join(scratch_folder, "input.edi")
            with open(input_file, "w") as f:
                f.write("EDI content")

            parameters = sample_parameters_dict_no_processing.copy()

            result = EDIProcessor._process_single_file(
                input_file, parameters, sample_settings, sample_upc_dict, scratch_folder
            )

            # Should return path to copied file in scratch folder
            assert os.path.basename(result) == "input.edi"
            assert scratch_folder in result
            assert os.path.exists(result)

    def test_process_single_file_with_processing(
        self, sample_parameters_dict, sample_settings, sample_upc_dict
    ):
        """Test _process_single_file with EDI processing enabled."""
        with tempfile.TemporaryDirectory() as scratch_folder:
            input_file = os.path.join(scratch_folder, "input.edi")
            with open(input_file, "w") as f:
                f.write("EDI content")

            parameters = sample_parameters_dict.copy()
            parameters["process_edi"] = "True"
            parameters["tweak_edi"] = False
            parameters["split_edi"] = False

            with patch(
                "dispatch.edi_processor.EDIConverter.convert_edi"
            ) as mock_convert:
                mock_convert.return_value = os.path.join(
                    scratch_folder, "converted_input.edi"
                )

                result = EDIProcessor._process_single_file(
                    input_file,
                    parameters,
                    sample_settings,
                    sample_upc_dict,
                    scratch_folder,
                )

                mock_convert.assert_called_once()
                assert "converted_" in result


# =============================================================================
# FileNamer Tests
# =============================================================================


class TestFileNamer:
    """Tests for the FileNamer class."""

    def test_generate_output_filename_no_rename(
        self, sample_parameters_dict_no_processing
    ):
        """Test filename generation with no rename pattern."""
        parameters = sample_parameters_dict_no_processing.copy()
        parameters["rename_file"] = ""

        result = FileNamer.generate_output_filename("/path/to/test.edi", parameters)

        assert result == "test.edi"

    def test_generate_output_filename_with_rename(self, sample_parameters_dict):
        """Test filename generation with rename pattern."""
        parameters = sample_parameters_dict.copy()

        with patch("dispatch.edi_processor.datetime.datetime") as mock_datetime:
            mock_now = MagicMock()
            mock_datetime.now.return_value = mock_now
            mock_datetime.strftime.return_value = "20240115"

            result = FileNamer.generate_output_filename(
                "/path/to/test.edi", parameters, "prefix_", "_suffix"
            )

            assert "output_20240115" in result
            assert result.endswith(".edi_suffix")
            assert result.startswith("prefix_output")

    def test_generate_output_filename_datetime_replacement(self):
        """Test datetime placeholder replacement in filename."""
        parameters = {"rename_file": "invoice_%datetime%_export"}

        with patch("dispatch.edi_processor.datetime.datetime") as mock_datetime:
            mock_now = MagicMock()
            mock_datetime.now.return_value = mock_now
            mock_datetime.strftime.return_value = "20240115"

            result = FileNamer.generate_output_filename("input.edi", parameters)

            assert "invoice_20240115_export" in result

    def test_generate_output_filename_strips_invalid_chars(self):
        """Test that invalid characters are stripped from filename."""
        parameters = {"rename_file": "file<name>:with|invalid*chars?"}

        result = FileNamer.generate_output_filename("test.edi", parameters)

        # Invalid characters should be stripped
        assert "<" not in result
        assert ">" not in result
        assert ":" not in result
        assert "|" not in result
        assert "*" not in result
        assert "?" not in result

    def test_generate_output_filename_preserves_valid_chars(self):
        """Test that valid characters are preserved in filename."""
        parameters = {"rename_file": "Valid_File-Name v2.1"}

        result = FileNamer.generate_output_filename("test.edi", parameters)

        assert "Valid_File-Name v2.1" in result
        assert ".edi" in result

    def test_generate_output_filename_with_prefix_suffix(self):
        """Test filename generation with prefix and suffix."""
        parameters = {"rename_file": "output"}

        result = FileNamer.generate_output_filename(
            "input.edi", parameters, filename_prefix="PRE_", filename_suffix="_SUF"
        )

        assert result.startswith("PRE_output")
        assert result.endswith(".edi_SUF")

    def test_generate_output_filename_different_extensions(self):
        """Test filename generation preserves different extensions."""
        parameters = {"rename_file": "export"}

        result_txt = FileNamer.generate_output_filename("input.txt", parameters)
        result_csv = FileNamer.generate_output_filename("input.csv", parameters)
        result_xml = FileNamer.generate_output_filename("input.xml", parameters)

        assert result_txt.endswith(".txt")
        assert result_csv.endswith(".csv")
        assert result_xml.endswith(".xml")


# =============================================================================
# Integration Tests
# =============================================================================


class TestEDIProcessorIntegration:
    """Integration tests for EDI processing workflows."""

    def test_full_edi_processing_workflow(self, sample_settings, sample_upc_dict):
        """Test complete EDI processing workflow."""
        with tempfile.TemporaryDirectory() as scratch_folder:
            input_file = os.path.join(scratch_folder, "test.edi")
            with open(input_file, "w") as f:
                f.write("A000001INV00001011221251000012345\n")
                f.write(
                    "B012345678901Product Description 1234561234567890100001000100050000\n"
                )
                f.write("C00100000123\n")

            parameters = {
                "convert_to_format": "CSV",
                "process_edi": "True",
                "tweak_edi": True,
                "split_edi": False,
                "rename_file": "",
            }

            with (
                patch(
                    "dispatch.edi_processor.EDIConverter.convert_edi"
                ) as mock_convert,
                patch("dispatch.edi_processor.EDITweaker.tweak_edi") as mock_tweak,
            ):
                converted_file = os.path.join(scratch_folder, "converted_test.edi")
                tweaked_file = os.path.join(
                    scratch_folder, "tweaked_converted_test.edi"
                )
                mock_convert.return_value = converted_file
                mock_tweak.return_value = tweaked_file

                result = EDIProcessor.process_edi(
                    input_file,
                    parameters,
                    sample_settings,
                    sample_upc_dict,
                    scratch_folder,
                )

                assert len(result) == 1

    def test_split_and_process_multiple_files(self, sample_settings, sample_upc_dict):
        """Test splitting and processing multiple files."""
        with tempfile.TemporaryDirectory() as scratch_folder:
            input_file = os.path.join(scratch_folder, "test.edi")
            with open(input_file, "w") as f:
                f.write("EDI content")

            split1 = os.path.join(scratch_folder, "split1.edi")
            split2 = os.path.join(scratch_folder, "split2.edi")
            split3 = os.path.join(scratch_folder, "split3.edi")
            for sf in [split1, split2, split3]:
                with open(sf, "w") as f:
                    f.write("Split content")

            parameters = {
                "convert_to_format": "CSV",
                "process_edi": "True",
                "tweak_edi": True,
                "split_edi": True,
                "rename_file": "",
            }

            with (
                patch("dispatch.edi_processor.EDISplitter.split_edi") as mock_split,
                patch(
                    "dispatch.edi_processor.EDIConverter.convert_edi"
                ) as mock_convert,
                patch("dispatch.edi_processor.EDITweaker.tweak_edi") as mock_tweak,
            ):
                mock_split.return_value = [
                    (split1, "A_", ".inv"),
                    (split2, "B_", ".inv"),
                    (split3, "C_", ".cr"),
                ]
                mock_convert.side_effect = [
                    os.path.join(scratch_folder, "converted_split1.edi"),
                    os.path.join(scratch_folder, "converted_split2.edi"),
                    os.path.join(scratch_folder, "converted_split3.edi"),
                ]
                mock_tweak.side_effect = [
                    os.path.join(scratch_folder, "tweaked_split1.edi"),
                    os.path.join(scratch_folder, "tweaked_split2.edi"),
                    os.path.join(scratch_folder, "tweaked_split3.edi"),
                ]

                result = EDIProcessor.process_edi(
                    input_file,
                    parameters,
                    sample_settings,
                    sample_upc_dict,
                    scratch_folder,
                )

                assert len(result) == 3
                assert result[0][1] == "A_"
                assert result[0][2] == ".inv"
                assert result[2][1] == "C_"
                assert result[2][2] == ".cr"


# =============================================================================
# Edge Case Tests
# =============================================================================


class TestEdgeCases:
    """Tests for edge cases and boundary conditions."""

    def test_empty_file_processing(
        self, sample_parameters_dict_no_processing, sample_settings
    ):
        """Test processing of empty EDI file."""
        with tempfile.TemporaryDirectory() as scratch_folder:
            input_file = os.path.join(scratch_folder, "empty.edi")
            with open(input_file, "w") as f:
                f.write("")

            parameters = sample_parameters_dict_no_processing.copy()
            parameters["split_edi"] = False

            result = EDIProcessor.process_edi(
                input_file, parameters, sample_settings, {}, scratch_folder
            )

            assert len(result) == 1

    def test_very_long_filename(self, sample_parameters_dict_no_processing):
        """Test handling of very long filenames."""
        parameters = sample_parameters_dict_no_processing.copy()
        parameters["rename_file"] = "a" * 200

        result = FileNamer.generate_output_filename("test.edi", parameters)

        # Should handle long filenames without error
        assert result is not None
        assert ".edi" in result

    def test_filename_with_special_chars(self, sample_parameters_dict_no_processing):
        """Test handling of filenames with special characters."""
        parameters = sample_parameters_dict_no_processing.copy()
        parameters["rename_file"] = "file with spaces and-underscores"

        result = FileNamer.generate_output_filename("test.edi", parameters)

        assert "file with spaces" in result
        assert "underscores" in result

    def test_unicode_in_filename(self, sample_parameters_dict_no_processing):
        """Test handling of unicode characters in filename."""
        parameters = sample_parameters_dict_no_processing.copy()
        parameters["rename_file"] = "fichier_avec_accents_éèà"

        result = FileNamer.generate_output_filename("test.edi", parameters)

        assert result is not None

    def test_multiple_extensions(self, sample_parameters_dict_no_processing):
        """Test handling of files with multiple extensions."""
        parameters = sample_parameters_dict_no_processing.copy()
        parameters["rename_file"] = "output"

        result = FileNamer.generate_output_filename("archive.tar.gz", parameters)

        # Should preserve the last extension
        assert result.endswith(".gz")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
