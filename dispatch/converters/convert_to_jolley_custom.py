"""Jolley Custom CSV EDI Converter - Refactored to use Template Method Pattern.

This module converts EDI files to Jolley Custom CSV format with database lookups
for customer information. It has been refactored to use the BaseEDIConverter
base class, eliminating ~60 lines of duplicated code while maintaining the
exact same behavior and output format.

The converter features:
- Database lookups via QueryRunner for customer information
- Corporate customer fallback logic for ship-to addresses
- UPC code generation with check digit calculation
- UOM (Unit of Measure) lookup from database
- Item total calculations with proper decimal handling
- Date prettification for display

Output Format:
    Multi-section CSV with invoice details, bill/ship addresses,
    and line items with descriptions, UPC, quantities, UOM, prices, and totals.

Differences from Stewarts Custom:
    - No Customer_Store_Number in database query
    - Corporate customer fields fallback to customer fields if None
    - Bill To / Ship To layout swapped
    - Different column layout for line items

Backward Compatibility:
    The module-level edi_convert() function maintains the same signature
    as before: edi_convert(edi_process, output_filename, settings_dict,
    parameters_dict, upc_dict)
"""

import csv
import decimal
from typing import Any, Dict, List, Tuple

import core.utils
from core.structured_logging import (
    get_logger,
    log_file_operation,
    log_with_context,
)
from dispatch.converters.convert_base import (
    BaseEDIConverter,
    ConversionContext,
    EDIRecord,
)
from core.database import LegacyQueryRunnerAdapter, create_query_runner
from core.exceptions import CustomerLookupError
from core.utils import prettify_dates

logger = get_logger(__name__)


class JolleyCustomConverter(BaseEDIConverter):
    """Converter for Jolley Custom CSV format with database lookups.

    This class implements the hook methods required by BaseEDIConverter
    to produce Jolley-compatible CSV output. It features:
    - Database lookups for customer and invoice information
    - Corporate customer fallback for ship-to addresses
    - UOM (Unit of Measure) lookup and caching
    - UPC code generation with check digit calculation
    - Proper decimal arithmetic for item totals
    """

    def _initialize_output(self, context: ConversionContext) -> None:
        """Initialize CSV output file, writer, and database connection.

        Args:
            context: The conversion context
        """
        # Initialize database connection using new QueryRunner with legacy adapter
        settings_dict = context.settings_dict
        runner = create_query_runner(
            username=settings_dict["as400_username"],
            password=settings_dict["as400_password"],
            dsn=settings_dict["as400_address"],
            database="QGPL",
            odbc_driver=settings_dict.get(
                "odbc_driver", "IBM i Access ODBC Driver 64-bit"
            ),
        )
        self.query_object = LegacyQueryRunnerAdapter(runner)

        # Initialize state
        self.header_fields_dict: Dict[str, Any] = {}
        self.uom_lookup_list: List[Tuple] = []
        self.header_a_record: Dict[str, str] = {}

        # Open output file and create CSV writer
        context.output_file = open(
            context.get_output_path(".csv"), "w", newline="\n", encoding="utf-8"
        )
        context.csv_writer = csv.writer(context.output_file, dialect="unix")

    def _get_customer_header_fields(self, invoice_number: str) -> Dict[str, Any]:
        """Fetch customer header fields from database.

        Args:
            invoice_number: The invoice number to look up

        Returns:
            Dictionary of customer header fields

        Raises:
            CustomerLookupError: If the order is not found in history
        """
        header_fields = self.query_object.run_arbitrary_query(
            """
    SELECT TRIM(dsadrep.adbbtx) AS "Salesperson Name",
        ohhst.btcfdt AS "Invoice Date",
        TRIM(ohhst.btfdtx) AS "Terms Code",
        dsagrep.agrrnb AS "Terms Duration",
        dsabrep.abbvst AS "Customer Status",
        dsabrep.ababnb AS "Customer Number",
        TRIM(dsabrep.abaatx) AS "Customer Name",
        TRIM(dsabrep.ababtx) AS "Customer Address",
        TRIM(dsabrep.abaetx) AS "Customer Town",
        TRIM(dsabrep.abaftx) AS "Customer State",
        TRIM(dsabrep.abagtx) AS "Customer Zip",
        CONCAT(dsabrep.abadnb, dsabrep.abaenb) AS "Customer Phone",
        TRIM(cvgrrep.grm9xt) AS "Customer Email",
        TRIM(cvgrrep.grnaxt) AS "Customer Email 2",
        dsabrep_corp.abbvst AS "Corporate Customer Status",
        dsabrep_corp.ababnb AS "Corporate Customer Number",
        TRIM(dsabrep_corp.abaatx) AS "Corporate Customer Name",
        TRIM(dsabrep_corp.ababtx) AS "Corporate Customer Address",
        TRIM(dsabrep_corp.abaetx) AS "Corporate Customer Town",
        TRIM(dsabrep_corp.abaftx) AS "Corporate Customer State",
        TRIM(dsabrep_corp.abagtx) AS "Corporate Customer Zip",
        CONCAT(dsabrep_corp.abadnb, dsabrep.abaenb) AS "Corporate Customer Phone",
        TRIM(cvgrrep_corp.grm9xt) AS "Corporate Customer Email",
        TRIM(cvgrrep_corp.grnaxt) AS "Corporate Customer Email 2"
        FROM dacdata.ohhst ohhst
            INNER JOIN dacdata.dsabrep dsabrep
                ON ohhst.btabnb = dsabrep.ababnb
            left outer JOIN dacdata.cvgrrep cvgrrep
                ON dsabrep.ababnb = cvgrrep.grabnb
            INNER JOIN dacdata.dsadrep dsadrep
                ON dsabrep.abajcd = dsadrep.adaecd
                inner join dacdata.dsagrep dsagrep
                on ohhst.bta0cd = dsagrep.aga0cd
            LEFT outer JOIN dacdata.dsabrep dsabrep_corp
                ON dsabrep.abalnb = dsabrep_corp.ababnb
            LEFT outer JOIN dacdata.cvgrrep cvgrrep_corp
                ON dsabrep_corp.ababnb = cvgrrep_corp.grabnb
            LEFT outer JOIN dacdata.dsadrep dsadrep_corp
                ON dsabrep_corp.abajcd = dsadrep_corp.adaecd
        WHERE ohhst.bthhnb = ?
            """,
            (invoice_number.lstrip("0"),),
        )

        if len(header_fields) == 0:
            logger.error(
                "Jolley custom converter: Cannot find order %s in AS400 history",
                invoice_number,
            )
            raise CustomerLookupError(f"Cannot Find Order {invoice_number} In History.")

        header_fields_list = [
            "Salesperson_Name",
            "Invoice_Date",
            "Terms_Code",
            "Terms_Duration",
            "Customer_Status",
            "Customer_Number",
            "Customer_Name",
            "Customer_Address",
            "Customer_Town",
            "Customer_State",
            "Customer_Zip",
            "Customer_Phone",
            "Customer_Email",
            "Customer_Email_2",
            "Corporate_Customer_Status",
            "Corporate_Customer_Number",
            "Corporate_Customer_Name",
            "Corporate_Customer_Address",
            "Corporate_Customer_Town",
            "Corporate_Customer_State",
            "Corporate_Customer_Zip",
            "Corporate_Customer_Phone",
            "Corporate_Customer_Email",
            "Corporate_Customer_Email_2",
        ]

        header_fields_dict = dict(zip(header_fields_list, header_fields[0]))

        # Jolley-specific: fallback corporate fields to customer fields if None
        if header_fields_dict["Corporate_Customer_Number"] is None:
            header_fields_dict["Corporate_Customer_Number"] = header_fields_dict[
                "Customer_Number"
            ]
            header_fields_dict["Corporate_Customer_Name"] = header_fields_dict[
                "Customer_Name"
            ]
            header_fields_dict["Corporate_Customer_Address"] = header_fields_dict[
                "Customer_Address"
            ]
            header_fields_dict["Corporate_Customer_Town"] = header_fields_dict[
                "Customer_Town"
            ]
            header_fields_dict["Corporate_Customer_State"] = header_fields_dict[
                "Customer_State"
            ]
            header_fields_dict["Corporate_Customer_Zip"] = header_fields_dict[
                "Customer_Zip"
            ]

        return header_fields_dict

    def _get_uom_lookup(self, invoice_number: str) -> List[Tuple]:
        """Fetch UOM lookup list from database.

        Args:
            invoice_number: The invoice number to look up

        Returns:
            List of tuples containing (itemno, uom_mult, uom_code)
        """
        uom_list = self.query_object.run_arbitrary_query(
            """
            select distinct bubacd as itemno, bus3qt as uom_mult, buhxtx as uom_code from dacdata.odhst odhst
            where odhst.buhhnb = ?
            """,
            (invoice_number,),
        )
        if not uom_list:
            logger.warning(
                "Jolley custom converter: No UOM data found for invoice %s",
                invoice_number,
            )
        return uom_list

    def _get_uom(self, item_number: str, packsize: str) -> str:
        """Get UOM (Unit of Measure) for an item.

        Args:
            item_number: The vendor item number
            packsize: The unit multiplier/pack size

        Returns:
            UOM code string (e.g., 'EA', 'CS') or '?' if not found
        """
        stage_1_list = []
        stage_2_list = []
        for entry in self.uom_lookup_list:
            if int(entry[0]) == int(item_number):
                stage_1_list.append(entry)
        for entry in stage_1_list:
            try:
                if int(entry[1]) == int(packsize):
                    stage_2_list.append(entry)
            except Exception:
                stage_2_list.append(entry)
                break
        try:
            return stage_2_list[0][2]
        except IndexError:
            return "?"

    def _convert_to_item_total(
        self, unit_cost: str, qty: str
    ) -> Tuple[decimal.Decimal, int]:
        """Calculate item total from unit cost and quantity.

        Args:
            unit_cost: The unit cost string
            qty: The quantity string (may be negative)

        Returns:
            Tuple of (item_total, qty_as_int)
        """
        if qty.startswith("-"):
            wrkqty = int(qty[1:])
            wrkqtyint = wrkqty - (wrkqty * 2)
        else:
            try:
                wrkqtyint = int(qty)
            except ValueError:
                wrkqtyint = 0
        try:
            item_total = decimal.Decimal(utils.convert_to_price(unit_cost)) * wrkqtyint
        except ValueError:
            item_total = decimal.Decimal()
        except decimal.InvalidOperation:
            item_total = decimal.Decimal()
        return item_total, wrkqtyint

    def _generate_full_upc(self, input_upc: str) -> str:
        """Generate a full 12-digit UPC from input.

        Args:
            input_upc: The input UPC string (may be 8 or 11 digits)

        Returns:
            Full 12-digit UPC string or empty string if invalid
        """
        input_upc = input_upc.strip()
        upc_string = ""
        blank_upc = False
        try:
            _ = int(input_upc)
        except ValueError:
            blank_upc = True

        if blank_upc is False:
            proposed_upc = input_upc
            if len(str(proposed_upc)) == 11:
                upc_string = str(proposed_upc) + str(
                    utils.calc_check_digit(proposed_upc)
                )
            else:
                if len(str(proposed_upc)) == 8:
                    upc_string = str(utils.convert_UPCE_to_UPCA(proposed_upc))
        return upc_string

    def process_a_record(self, record: EDIRecord, context: ConversionContext) -> None:
        """Process an A record (header), writing invoice header to CSV.

        Args:
            record: The A record
            context: The conversion context
        """
        super().process_a_record(record, context)
        self.header_a_record = record.fields

        # Fetch customer data from database
        self.header_fields_dict = self._get_customer_header_fields(
            record.fields["invoice_number"]
        )

        # Fetch UOM lookup data
        self.uom_lookup_list = self._get_uom_lookup(record.fields["invoice_number"])

        csv_writer = context.csv_writer

        # Write invoice header section
        csv_writer.writerow(["Invoice Details"])
        csv_writer.writerow([""])
        csv_writer.writerow(
            ["Delivery Date", "Terms", "Invoice Number", "Due Date", "PO Number"]
        )
        csv_writer.writerow(
            [
                prettify_dates(self.header_fields_dict["Invoice_Date"]),
                self.header_fields_dict["Terms_Code"],
                record.fields["invoice_number"],
                prettify_dates(
                    self.header_fields_dict["Invoice_Date"],
                    self.header_fields_dict["Terms_Duration"],
                    -1,
                ),
            ]
        )

        # Build ship-to segment (uses corporate customer if available)
        ship_to_segment = [
            str(self.header_fields_dict["Corporate_Customer_Number"])
            + "\n"
            + self.header_fields_dict["Corporate_Customer_Name"]
            + "\n"
            + self.header_fields_dict["Corporate_Customer_Address"]
            + "\n"
            + self.header_fields_dict["Corporate_Customer_Town"]
            + ", "
            + self.header_fields_dict["Corporate_Customer_State"]
            + ", "
            + self.header_fields_dict["Corporate_Customer_Zip"]
            + ", "
            + "\n"
            + "US",
        ]

        # Write bill-to/ship-to section (Jolley layout: Bill To on left, Ship To on right)
        csv_writer.writerow(
            [
                "Bill To:",
                str(self.header_fields_dict["Customer_Number"])
                + "\n"
                + self.header_fields_dict["Customer_Name"]
                + "\n"
                + self.header_fields_dict["Customer_Address"]
                + "\n"
                + self.header_fields_dict["Customer_Town"]
                + ", "
                + self.header_fields_dict["Customer_State"]
                + ", "
                + self.header_fields_dict["Customer_Zip"]
                + ", "
                + "\n"
                + "US",
                "Ship To:",
            ]
            + ship_to_segment
        )
        csv_writer.writerow([""])
        csv_writer.writerow(
            ["Description", "UPC #", "Quantity", "UOM", "Price", "Amount"]
        )

    def process_b_record(self, record: EDIRecord, context: ConversionContext) -> None:
        """Process a B record (line item), writing to CSV.

        Args:
            record: The B record
            context: The conversion context
        """
        total_price, qtyint = self._convert_to_item_total(
            record.fields["unit_cost"], record.fields["qty_of_units"]
        )
        context.csv_writer.writerow(
            [
                record.fields["description"],
                self._generate_full_upc(record.fields["upc_number"]),
                qtyint,
                self._get_uom(
                    record.fields["vendor_item"], record.fields["unit_multiplier"]
                ),
                "$" + str(utils.convert_to_price(record.fields["unit_cost"])),
                "$" + str(total_price),
            ]
        )

    def process_c_record(self, record: EDIRecord, context: ConversionContext) -> None:
        """Process a C record (charge/tax), writing to CSV.

        Args:
            record: The C record
            context: The conversion context
        """
        context.csv_writer.writerow(
            [
                record.fields["description"],
                "000000000000",
                1,
                "EA",
                "$" + str(utils.convert_to_price(record.fields["amount"])),
                "$" + str(utils.convert_to_price(record.fields["amount"])),
            ]
        )

    def _finalize_output(self, context: ConversionContext) -> None:
        """Finalize output by writing total row and closing file.

        Args:
            context: The conversion context
        """
        # Write total row
        if self.header_a_record:
            context.csv_writer.writerow(
                [
                    "",
                    "",
                    "",
                    "",
                    "Total:",
                    "$"
                    + str(
                        utils.convert_to_price(
                            self.header_a_record["invoice_total"]
                        ).lstrip("0")
                    ),
                ]
            )

        # Close the output file
        if context.output_file is not None:
            context.output_file.close()
            context.output_file = None

        # Close database connection if it exists
        if hasattr(self, "query_object") and self.query_object is not None:
            try:
                self.query_object.close()
            except AttributeError:
                # query_object might not have a close method in some implementations
                pass


# =============================================================================
# Backward Compatibility Wrapper
# =============================================================================


def edi_convert(
    edi_process: str,
    output_filename: str,
    settings_dict: dict,
    parameters_dict: dict,
    upc_dict: dict,
) -> str:
    """Convert EDI file to Jolley Custom CSV format with database lookups.

    This is the original function signature maintained for backward compatibility.
    It simply creates a JolleyCustomConverter instance and delegates to it.

    Args:
        edi_process: Path to the input EDI file
        output_filename: Base path for output file (without extension)
        settings_dict: Application settings dictionary with DB credentials
        parameters_dict: Conversion parameters (Jolley has no specific params)
        upc_dict: UPC lookup table (not used in this converter)

    Returns:
        Path to the generated CSV file

    Example:
        >>> result = edi_convert(
        ...     "input.edi",
        ...     "output",
        ...     {'as400_username': 'user', 'as400_password': 'pass', ...},
        ...     {},
        ...     {}
        ... )
        >>> print(result)
        'output.csv'
    """
    import logging
    import os
    import time

    from core.structured_logging import get_or_create_correlation_id

    correlation_id = get_or_create_correlation_id()
    start_time = time.perf_counter()

    log_with_context(
        logger,
        logging.INFO,
        "Starting Jolley Custom conversion",
        operation="edi_convert",
        context={
            "input_file": os.path.basename(edi_process),
            "output_file": os.path.basename(output_filename) + ".csv",
            "format": "jolley_custom",
        },
    )
    log_file_operation(
        logger,
        "read",
        edi_process,
        file_type="edi",
        correlation_id=correlation_id,
    )

    try:
        converter = JolleyCustomConverter()
        result = converter.edi_convert(
            edi_process, output_filename, settings_dict, parameters_dict, upc_dict
        )
        duration_ms = (time.perf_counter() - start_time) * 1000

        log_with_context(
            logger,
            logging.INFO,
            "Jolley Custom conversion completed",
            operation="edi_convert",
            context={
                "input_file": os.path.basename(edi_process),
                "output_file": os.path.basename(result),
                "format": "jolley_custom",
                "duration_ms": round(duration_ms, 2),
            },
        )
        log_file_operation(
            logger,
            "write",
            result,
            file_type="csv",
            success=True,
            duration_ms=duration_ms,
            correlation_id=correlation_id,
        )
        return result
    except Exception as e:
        duration_ms = (time.perf_counter() - start_time) * 1000
        log_with_context(
            logger,
            logging.ERROR,
            f"Jolley Custom conversion failed: {e}",
            operation="edi_convert",
            context={
                "input_file": os.path.basename(edi_process),
                "format": "jolley_custom",
                "duration_ms": round(duration_ms, 2),
                "error": str(e),
            },
        )
        raise
