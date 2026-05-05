"""Semantic validation tests for scansheet_type_a converter.

Unlike other formats that use byte-for-byte comparison, scansheet_type_a
produces Excel files with barcodes that have non-deterministic elements
(timestamps, etc.). These tests validate the semantic content of the output
without requiring exact byte matching.

Tests validate:
- Valid ZIP/Excel structure
- Required worksheets present
- Barcodes present when UPC data exists
"""

import os
import sys
import xml.etree.ElementTree as ET
import zipfile
from pathlib import Path
from typing import Any

import pytest

# Add project root to path for imports
_project_root = Path(__file__).parent.parent.parent.parent
if str(_project_root) not in sys.path:
    sys.path.insert(0, str(_project_root))

# Database credentials from environment
AS400_USERNAME = os.environ.get("AS400_USERNAME", "")
AS400_ADDRESS = os.environ.get("AS400_ADDRESS", "")
AS400_PASSWORD = os.environ.get("AS400_PASSWORD", "")


def run_scansheet_converter(
    input_file: str, output_dir: str, params: dict[str, Any] | None = None
) -> str | None:
    """Run the scansheet_type_a converter.

    Args:
        input_file: Path to input EDI file
        output_dir: Directory for output file
        params: Additional converter parameters

    Returns:
        Path to output file, or None if conversion failed
    """
    from dispatch.converters.convert_to_scansheet_type_a import edi_convert

    if params is None:
        params = {}

    settings_dict: dict[str, Any] = {
        "as400_username": AS400_USERNAME,
        "as400_address": AS400_ADDRESS,
        "as400_password": AS400_PASSWORD,
    }

    # Filter out credentials from params
    filter_params = {k: v for k, v in params.items() if k not in [
        "as400_username", "as400_address", "as400_password"
    ]}

    output_path = os.path.join(output_dir, "output.xlsx")

    try:
        result = edi_convert(
            input_file,
            output_path,
            settings_dict,
            filter_params,
            {},
        )
        return result
    except Exception as e:
        pytest.fail(f"Conversion failed: {e}")


def extract_sheet_data(xlsx_path: str) -> dict[str, Any]:
    """Extract semantic data from an Excel XLSX file.

    Args:
        xlsx_path: Path to the XLSX file

    Returns:
        Dictionary containing extracted data:
        - is_valid_xlsx: Whether file is valid XLSX
        - files: List of files in ZIP
        - has_workbook: Whether workbook.xml exists
        - has_sheet1: Whether sheet1.xml exists
        - has_drawings: Whether drawings are referenced
        - media_count: Number of media/image files
        - cell_count: Number of cells with data
        - upc_values: List of UPC values found in column B
    """
    result: dict[str, Any] = {
        "is_valid_xlsx": False,
        "files": [],
        "has_workbook": False,
        "has_sheet1": False,
        "has_drawings": False,
        "media_count": 0,
        "cell_count": 0,
        "upc_values": [],
        "barcode_images": 0,
    }

    if not os.path.exists(xlsx_path):
        return result

    try:
        with zipfile.ZipFile(xlsx_path, "r") as zf:
            result["files"] = zf.namelist()
            result["is_valid_xlsx"] = True

            # Check for required Excel structure
            result["has_workbook"] = "xl/workbook.xml" in result["files"]
            result["has_sheet1"] = "xl/worksheets/sheet1.xml" in result["files"]

            # Count media files (barcode images)
            result["media_count"] = len([
                f for f in result["files"]
                if f.startswith("xl/media/")
            ])
            result["barcode_images"] = result["media_count"]

            # Check for drawing references
            sheet_rels_path = "xl/worksheets/_rels/sheet1.xml.rels"
            if sheet_rels_path in result["files"]:
                rels_content = zf.read(sheet_rels_path).decode("utf-8")
                if "image" in rels_content.lower():
                    result["has_drawings"] = True

            # Extract cell values from sheet1
            if result["has_sheet1"]:
                sheet_content = zf.read("xl/worksheets/sheet1.xml").decode("utf-8")
                tree = ET.fromstring(sheet_content)

                # Handle both namespaced and non-namespaced XML
                ns = {"ns": "http://schemas.openxmlformats.org/spreadsheetml/2006/main"}

                # Header values to exclude (these are column headers, not data)
                header_values = {"UPC", "Item", "Description", "Pack", "U/M", "Qty", "Price", "Retail"}

                # Count cells with values
                for elem in tree.iter():
                    if elem.tag.endswith("}c") or elem.tag == "c":
                        v_elem = elem.find("ns:v", ns) or elem.find("v")
                        is_elem = elem.find("ns:is", ns) or elem.find("is")
                        if v_elem is not None or is_elem is not None:
                            result["cell_count"] += 1

                    # Extract UPC values from column B (data rows only)
                    if elem.tag.endswith("}row") or elem.tag == "row":
                        row_num = elem.get("r", "0")
                        # Skip header rows (typically rows 1-3)
                        if row_num in ["1", "2", "3"]:
                            continue
                        for cell in elem:
                            if cell.tag.endswith("}c") or cell.tag == "c":
                                cell_ref = cell.get("r", "")
                                # Column B contains UPCs
                                if cell_ref.startswith("B"):
                                    v_elem = cell.find("ns:v", ns) or cell.find("v")
                                    is_elem = cell.find("ns:is/ns:t", ns)
                                    value = None
                                    if is_elem is not None:
                                        value = is_elem.text
                                    elif v_elem is not None and v_elem.text:
                                        value = v_elem.text

                                    # Only count actual UPC values (not header text)
                                    if value and value not in header_values:
                                        # UPC values should be numeric (possibly with leading zeros)
                                        if value.isdigit() and len(value) >= 6:
                                            result["upc_values"].append(value)

    except zipfile.BadZipFile:
        pass
    except Exception:
        pass

    return result


class TestScansheetTypeAStructure:
    """Tests for scansheet_type_a output structure validation."""

    @pytest.fixture
    def sample_edi_file(self, tmp_path: Path) -> str:
        """Create a sample EDI file for testing."""
        edi_content = """AVENDOR   4573208    260427     911.53
B98765432109Test Item One             VI001 0   10     9.99
B12345678901Test Item Two             VI002 0   20    10.99
CTABSales Tax                      000010000"""
        input_file = tmp_path / "test.edi"
        input_file.write_text(edi_content)
        return str(input_file)

    def test_output_is_valid_xlsx(self, sample_edi_file: str, tmp_path: Path) -> None:
        """Test that output is a valid XLSX (ZIP) file."""
        result = run_scansheet_converter(sample_edi_file, str(tmp_path))
        assert result is not None, "Converter returned None"
        assert os.path.exists(result), f"Output file not found: {result}"

        # Verify it's a valid ZIP
        assert zipfile.is_zipfile(result), "Output is not a valid ZIP file"

    def test_xlsx_contains_required_structure(
        self, sample_edi_file: str, tmp_path: Path
    ) -> None:
        """Test that XLSX contains required Excel structure."""
        result = run_scansheet_converter(sample_edi_file, str(tmp_path))
        assert result is not None

        data = extract_sheet_data(result)

        assert data["is_valid_xlsx"], "Output is not a valid XLSX file"
        assert data["has_workbook"], "Missing workbook.xml"
        assert data["has_sheet1"], "Missing sheet1.xml"

        # Check for required Excel files
        required_files = [
            "[Content_Types].xml",
            "_rels/.rels",
            "xl/workbook.xml",
            "xl/worksheets/sheet1.xml",
        ]
        for req_file in required_files:
            assert req_file in data["files"], f"Missing required file: {req_file}"


class TestScansheetTypeABarcodes:
    """Tests for scansheet_type_a barcode validation.

    These tests verify that barcodes are present in the output when
    UPC data exists. The scansheet_type_a format generates barcode
    images for each UPC in column B.
    """

    @pytest.fixture
    def sample_edi_file(self, tmp_path: Path) -> str:
        """Create a sample EDI file with UPCs."""
        edi_content = """AVENDOR   4573208    260427     911.53
B98765432109Test Item One             VI001 0   10     9.99
B12345678901Test Item Two             VI002 0   20    10.99
CTABSales Tax                      000010000"""
        input_file = tmp_path / "test.edi"
        input_file.write_text(edi_content)
        return str(input_file)

    def test_barcodes_present_when_upc_data_exists(
        self, sample_edi_file: str, tmp_path: Path
    ) -> None:
        """Test that barcodes are generated when UPC data is present.

        The scansheet_type_a converter should generate barcode images
        for each item with a UPC in the database. If the database
        returns UPC data, there should be barcode images in the output.
        """
        result = run_scansheet_converter(sample_edi_file, str(tmp_path))
        assert result is not None

        data = extract_sheet_data(result)

        # Extract UPC values from the spreadsheet
        upc_count = len(data["upc_values"])
        barcode_count = data["barcode_images"]

        # If UPC data was found in the spreadsheet, barcodes should exist
        if upc_count > 0:
            assert barcode_count > 0, (
                f"Found {upc_count} UPC values in spreadsheet but "
                f"{barcode_count} barcode images. Barcodes should be generated "
                "for each UPC value."
            )

    def test_barcode_images_are_valid_format(
        self, sample_edi_file: str, tmp_path: Path
    ) -> None:
        """Test that barcode images are in a valid image format."""
        result = run_scansheet_converter(sample_edi_file, str(tmp_path))
        assert result is not None

        with zipfile.ZipFile(result, "r") as zf:
            # Find image files
            image_files = [
                f for f in zf.namelist()
                if f.startswith("xl/media/") and f.endswith((".png", ".gif", ".jpg"))
            ]

            for img_file in image_files:
                img_data = zf.read(img_file)
                # Basic image validation
                assert len(img_data) > 0, f"Image file {img_file} is empty"

                # PNG files start with PNG signature
                if img_file.endswith(".png"):
                    assert img_data[:4] == b"\x89PNG", (
                        f"Image file {img_file} does not have valid PNG signature"
                    )


class TestScansheetTypeAContent:
    """Tests for scansheet_type_a content validation."""

    def test_invoice_number_in_output(
        self, tmp_path: Path
    ) -> None:
        """Test that invoice number from input appears in output."""
        invoice_num = "4573208"
        edi_content = f"""AVENDOR   {invoice_num}    260427     911.53
B98765432109Test Item One             VI001 0   10     9.99
CTABSales Tax                      000010000"""

        input_file = tmp_path / "test.edi"
        input_file.write_text(edi_content)

        result = run_scansheet_converter(str(input_file), str(tmp_path))
        assert result is not None

        with zipfile.ZipFile(result, "r") as zf:
            if "xl/worksheets/sheet1.xml" in zf.namelist():
                sheet_content = zf.read("xl/worksheets/sheet1.xml").decode("utf-8")
                assert invoice_num in sheet_content, (
                    f"Invoice number {invoice_num} not found in output"
                )
