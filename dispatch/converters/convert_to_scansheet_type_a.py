"""ScanSheet Type A Excel EDI Converter - Refactored with Class-Based Structure.

This module converts EDI files to ScanSheet Type A Excel format with database lookups
and barcode generation. Unlike other converters, this one uses the EDI file only to
extract invoice numbers, then fetches all item data from the database.

The converter features:
- Database queries for invoice item details
- Excel workbook creation with openpyxl
- Automatic barcode generation for each item
- Column width adjustment for readability
- Memory-efficient batch processing with periodic saves

Output Format:
    Excel (.xlsx) file with invoice numbers and item details,
    with barcode images in column A.

Architecture Note:
    This converter extends BaseEDIConverter but overrides edi_convert() because
    it processes data fundamentally differently - instead of processing A/B/C
    records from the EDI file, it extracts invoice numbers from the EDI and
    queries all item data from the database.

Backward Compatibility:
    The module-level edi_convert() function maintains the same signature
    as other converters: edi_convert(edi_process, output_filename, settings_dict,
    parameters_dict, upc_lookup)
"""

import math
import os
import tempfile
from typing import Any

import barcode
import openpyxl
import openpyxl.utils
from barcode.writer import ImageWriter
from openpyxl.drawing.image import Image as OpenPyXlImage
from PIL import Image as pil_Image
from PIL import ImageOps as pil_ImageOps

from core import utils
from core.structured_logging import get_logger
from dispatch.converters.convert_base import BaseEDIConverter, ConversionContext

logger = get_logger(__name__)


class ScanSheetTypeAConverter(BaseEDIConverter):
    """Converter for ScanSheet Type A Excel format with barcodes.

    This converter extends BaseEDIConverter but overrides edi_convert() because
    it uses a fundamentally different algorithm - extracting invoice numbers from
    the EDI and querying the database for item details rather than processing
    A/B/C records individually.
    """

    def __init__(self) -> None:
        """Initialize the converter."""
        super().__init__()
        self.query_object = None
        self.output_spreadsheet = None
        self.output_worksheet = None
        self.output_spreadsheet_name = ""
        self.invoice_rows: list[int] = []
        self.invoice_row_counter = 0

    def _initialize_output(self, context: ConversionContext) -> None:
        """Stub implementation - not used since edi_convert is overridden."""
        pass

    def process_b_record(self, record: Any, context: ConversionContext) -> None:
        """Stub implementation - not used since edi_convert is overridden."""
        pass

    def edi_convert(
        self,
        edi_process: str,
        output_filename: str,
        settings_dict: dict[str, Any],
        parameters_dict: dict[str, Any],
        upc_lut: dict[int, tuple],
    ) -> str:
        """Convert EDI file to ScanSheet Type A Excel format.

        This overrides the BaseEDIConverter template method because ScanSheet
        uses a database-driven algorithm rather than record-by-record processing.

        Args:
            edi_process: Path to the input EDI file
            output_filename: Base path for output file (without extension)
            settings_dict: Application settings dictionary with DB credentials
            parameters_dict: Conversion parameters (not used)
            upc_lookup: UPC lookup table (not used - data comes from DB)

        Returns:
            Path to the generated Excel file

        """
        invoice_list = self._extract_invoices_from_edi(edi_process)
        self._initialize_database(settings_dict)
        self._initialize_workbook(output_filename)
        self._populate_workbook(invoice_list)
        self._process_barcodes()
        self._finalize_output(None)
        return self.output_spreadsheet_name

    def _extract_invoices_from_edi(self, edi_process: str) -> list[str]:
        """Extract invoice numbers from the EDI file.

        Args:
            edi_process: Path to the input EDI file

        Returns:
            List of invoice numbers (last 7 digits)

        """
        invoice_list = []
        with open(edi_process, encoding="utf-8") as work_file:
            work_file_lined = [n for n in work_file.readlines()]
            for line in work_file_lined:
                input_edi_dict = utils.capture_records(line)
                try:
                    if input_edi_dict["record_type"] == "A":
                        invoice_list.append(input_edi_dict["invoice_number"][-7:])
                except TypeError:
                    pass
        logger.debug(
            "Extracted %d invoice numbers from %s",
            len(invoice_list),
            os.path.basename(edi_process),
        )
        return invoice_list

    def _initialize_database(self, settings_dict: dict[str, Any]) -> None:
        """Initialize database connection.

        Args:
            settings_dict: Application settings with DB credentials

        """
        from core.database.query_runner import create_query_runner_from_settings

        self.query_object = create_query_runner_from_settings(settings_dict)

    def _initialize_workbook(self, output_filename: str) -> None:
        """Initialize the Excel workbook.

        Args:
            output_filename: Base path for output file (without extension)

        """
        self.output_spreadsheet = openpyxl.Workbook()
        self.output_worksheet = self.output_spreadsheet.worksheets[0]
        self.output_spreadsheet_name = output_filename + ".xlsx"
        self.invoice_rows = []
        self.invoice_row_counter = 0

    def _populate_workbook(self, invoice_list: list[str]) -> None:
        """Populate the workbook with data from the database.

        Args:
            invoice_list: List of invoice numbers to query

        """
        total_rows = 0
        for idx, invoice in enumerate(invoice_list):
            if idx > 0 and idx % 10 == 0:
                logger.debug("Processing invoices: %d/%d", idx, len(invoice_list))
            result = self.query_object.run_arbitrary_query(
                """SELECT buj4cd AS "UPC",
                    bubacd AS "Item",
                    bufbtx AS "Description",
                    ancctx AS "Pack",
                    buhxtx AS "U/M",
                    bue4qt AS "Qty",
                    bud2pr AS "Price",
                    bueapr AS "Retail"
                    FROM dacdata.odhst odhst
                        INNER JOIN dacdata.dsanrep dsanrep
                            ON odhst.bubacd = dsanrep.anbacd
                    WHERE odhst.buhhnb = ?
                        AND bue4qt <> 0""",
                (invoice,),
            )
            rows_for_export = []
            for row in result:
                trow = [""]
                for entry in row:
                    try:
                        trow.append(entry.strip())
                    except AttributeError:
                        trow.append(entry)
                rows_for_export.append(trow)
            self.output_worksheet.append(["", invoice])
            self.invoice_row_counter += 1
            self.invoice_rows.append(self.invoice_row_counter)
            for items_list_entry in rows_for_export:
                self.output_worksheet.append(items_list_entry)
                self.invoice_row_counter += 1
                total_rows += 1
            self._adjust_column_width(self.output_worksheet)
            self.output_spreadsheet.save(self.output_spreadsheet_name)
        logger.debug("Populated %d invoices, %d rows", len(invoice_list), total_rows)

    def _adjust_column_width(self, adjust_worksheet) -> None:
        """Adjust column widths to fit content.

        Args:
            adjust_worksheet: The worksheet to adjust

        """
        logger.debug("Adjusting column width for %s worksheet", adjust_worksheet.title)
        for col in adjust_worksheet.columns:
            max_length = 0
            column = col[0].column_letter
            for cell in col:
                try:
                    if len(str(cell.value)) > max_length:
                        max_length = len(str(cell.value))
                except Exception as resize_error:
                    logger.warning("Column resize error: %s", resize_error)
            adjusted_width = (max_length + 2) * 1.2
            adjust_worksheet.column_dimensions[column].width = adjusted_width

    def _process_barcodes(self) -> None:
        """Generate and insert barcodes for each item in the workbook."""
        logger.debug("creating temp directory")
        with tempfile.TemporaryDirectory() as tempdir:
            logger.debug("temp directory created as: %s", tempdir)
            save_counter = 0
            barcodes_generated = 0
            barcodes_skipped = 0
            for count, _ in enumerate(self.output_worksheet.iter_rows(), start=1):
                try:
                    if count not in self.invoice_rows:
                        upc_barcode_string = str(
                            self.output_worksheet["B" + str(count)].value
                        )
                        upc_barcode_string = self._interpret_barcode_string(
                            upc_barcode_string
                        )
                        generated_barcode_path, width, height = self._generate_barcode(
                            upc_barcode_string, tempdir
                        )
                        self.output_worksheet.column_dimensions["A"].width = int(
                            math.ceil(float(width) * 0.15)
                        )
                        self.output_worksheet.row_dimensions[count].height = int(
                            math.ceil(float(height) * 0.75)
                        )
                        img = OpenPyXlImage(generated_barcode_path)
                        self.output_worksheet.add_image(img, anchor="A" + str(count))
                        save_counter += 1
                        barcodes_generated += 1
                except ValueError as barcode_error:
                    barcodes_skipped += 1
                    logger.debug("Skipping barcode generation: %s", barcode_error)
                except Exception as barcode_error:
                    barcodes_skipped += 1
                    logger.warning("Barcode error: %s", barcode_error)
                if save_counter >= 100:
                    logger.debug(
                        (
                "saving intermediate workbook to free file handles"
                " (batch of 100)"
            )
                    )
                    self.output_spreadsheet.save(self.output_spreadsheet_name)
                    logger.debug("intermediate save successful")
                    save_counter = 1
            logger.debug("saving workbook to file")
            self.output_spreadsheet.save(self.output_spreadsheet_name)
            logger.debug("workbook saved successfully")
            logger.debug(
                "Barcode generation completed: %d generated, %d skipped",
                barcodes_generated,
                barcodes_skipped,
            )

    def _finalize_output(self, context: ConversionContext | None) -> None:
        """Finalize output by closing database connection.

        Args:
            context: The conversion context (not used in this converter)

        """
        if self.query_object is not None:
            try:
                self.query_object.close()
                logger.debug("Database connection closed")
            except AttributeError:
                pass

    def _generate_barcode(
        self, input_string: str, tempdir: str
    ) -> tuple[str, int, int]:
        """Generate a barcode image for the given UPC string.

        Args:
            input_string: The 12-digit UPC string
            tempdir: Temporary directory for image files

        Returns:
            Tuple of (image_path, width, height)

        """
        ean = barcode.get_barcode_class("UPCA")
        options = {
            "dpi": 130,
            "module_height": 5.0,
            "text_distance": 2,
            "font_size": 6,
            "quiet_zone": 2,
        }
        with tempfile.NamedTemporaryFile(
            dir=tempdir, suffix=".png", delete=False
        ) as initial_temp_file:
            ean(input_string, writer=ImageWriter()).write(
                initial_temp_file, options=options
            )
            filename = initial_temp_file.name
        barcode_image = pil_Image.open(str(filename))
        img_save = pil_ImageOps.expand(barcode_image, border=0, fill="white")
        width, height = img_save.size
        with tempfile.NamedTemporaryFile(
            dir=tempdir, suffix=".png", delete=False
        ) as final_barcode_path:
            img_save.save(final_barcode_path.name)
        return final_barcode_path.name, width, height

    def _interpret_barcode_string(self, upc_barcode_string: str) -> str:
        """Interpret and validate a barcode string.

        Args:
            upc_barcode_string: The input barcode string

        Returns:
            Validated 12-digit UPC string

        Raises:
            ValueError: If the input is empty or invalid

        """
        if upc_barcode_string is None:
            raise ValueError("Input is empty")
        normalized = "".join(
            ch for ch in str(upc_barcode_string).strip() if ch.isdigit()
        )
        if normalized == "":
            raise ValueError("Input contents are not an integer")
        if len(normalized) < 11:
            normalized = normalized.zfill(11)
        elif len(normalized) > 11:
            normalized = normalized[-11:]
        return normalized


# =============================================================================
# Backward Compatibility Wrapper
# =============================================================================

from .convert_base import create_edi_convert_wrapper  # noqa: E402

# Auto-generated wrapper using the standard template
edi_convert = create_edi_convert_wrapper(
    ScanSheetTypeAConverter, format_name="scansheet_type_a"
)
