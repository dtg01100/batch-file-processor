"""EDI Tweaker - Modern Class-Based Implementation.

This module provides the EDITweaker class that encapsulates all EDI tweak
functionality, replacing the legacy procedural edi_tweak() function.

The class supports the following transformations:
- A-record padding
- A-record appending (with PO number lookup)
- Invoice date offsetting
- UPC check digit calculation
- UPC-E to UPC-A conversion
- Retail UOM conversion (case to each)
- UPC override from lookup table
- C-record generation for split prepaid sales tax

Example:
    from core.edi.edi_tweaker import EDITweaker

    tweaker = EDITweaker(query_runner)
    result = tweaker.tweak(
        input_path="input.edi",
        output_path="output.edi",
        settings=settings_dict,
        params=params_dict,
        upc_dict=upc_lut,
    )
"""

import os
import time
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from decimal import Decimal
from typing import Any, Dict, Optional, Protocol, TextIO, runtime_checkable

from core.edi.c_rec_generator import CRecGenerator, QueryRunnerProtocol
from core.edi.po_fetcher import POFetcher
from core.structured_logging import (
    StructuredLogger,
    get_logger,
    get_or_create_correlation_id,
)

logger = get_logger(__name__)


@runtime_checkable
class TweakerQueryRunnerProtocol(Protocol):
    """Protocol for query runner operations in the tweaker context."""

    def run_query(self, query: str, params: tuple = None) -> list:
        """Run a SQL query and return results."""
        ...


def _create_query_runner_adapter(settings_dict: dict) -> TweakerQueryRunnerProtocol:
    """Create an adapter that wraps legacy query_runner.

    This function creates a query runner from settings and wraps it
    with an adapter that implements the TweakerQueryRunnerProtocol.

    Args:
        settings_dict: Dictionary containing database connection settings

    Returns:
        Object implementing TweakerQueryRunnerProtocol
    """
    from core.database import query_runner

    legacy_runner = query_runner(
        settings_dict["as400_username"],
        settings_dict["as400_password"],
        settings_dict["as400_address"],
        f"{settings_dict['odbc_driver']}",
    )

    class QueryRunnerAdapter:
        """Adapter wrapping legacy query_runner for protocol compliance."""

        def __init__(self, runner):
            self._runner = runner

        def run_query(self, query: str, params: tuple = None) -> list:
            # Legacy runner returns list of tuples
            return self._runner.run_arbitrary_query(query, params)

    return QueryRunnerAdapter(legacy_runner)


@dataclass
class TweakerConfig:
    """Configuration for the EDI tweaker.

    Attributes:
        pad_arec: Whether to pad A records
        arec_padding: Padding text for A records
        arec_padding_len: Length for A record padding
        append_arec: Whether to append text to A records
        append_arec_text: Text to append to A records
        invoice_date_custom_format: Use custom date format
        invoice_date_custom_format_string: Custom date format string
        force_txt_file_ext: Force .txt extension on output
        calc_upc: Calculate UPC check digit
        invoice_date_offset: Days to offset invoice date
        retail_uom: Convert to retail UOM
        override_upc: Override UPC from lookup table
        override_upc_level: UPC level for override (1=pack, 2=case)
        override_upc_category_filter: Category filter for UPC override
        split_prepaid_sales_tax_crec: Split prepaid sales tax
        upc_target_length: Target UPC length
        upc_padding_pattern: Pattern for UPC padding
    """

    pad_arec: bool = False
    arec_padding: str = ""
    arec_padding_len: int = 0
    append_arec: bool = False
    append_arec_text: str = ""
    invoice_date_custom_format: bool = False
    invoice_date_custom_format_string: str = "%Y-%m-%d"
    force_txt_file_ext: bool = False
    calc_upc: bool = False
    invoice_date_offset: int = 0
    retail_uom: bool = False
    override_upc: bool = False
    override_upc_level: int = 1
    override_upc_category_filter: str = "ALL"
    split_prepaid_sales_tax_crec: bool = False
    upc_target_length: int = 11
    upc_padding_pattern: str = "           "

    @classmethod
    def from_params(cls, params: Dict[str, Any]) -> "TweakerConfig":
        """Create config from parameters dictionary.

        Args:
            params: Dictionary with tweak parameters

        Returns:
            TweakerConfig instance
        """
        from core.utils.bool_utils import normalize_bool

        return cls(
            pad_arec=normalize_bool(params.get("pad_a_records", False)),
            arec_padding=params.get("a_record_padding", ""),
            arec_padding_len=int(params.get("a_record_padding_length", 0) or 0),
            append_arec=normalize_bool(params.get("append_a_records", False)),
            append_arec_text=params.get("a_record_append_text", ""),
            invoice_date_custom_format=normalize_bool(
                params.get("invoice_date_custom_format", False)
            ),
            invoice_date_custom_format_string=params.get(
                "invoice_date_custom_format_string", "%Y-%m-%d"
            ),
            force_txt_file_ext=normalize_bool(params.get("force_txt_file_ext", False)),
            calc_upc=normalize_bool(params.get("calculate_upc_check_digit", False)),
            invoice_date_offset=int(params.get("invoice_date_offset", 0) or 0),
            retail_uom=normalize_bool(params.get("retail_uom", False)),
            override_upc=normalize_bool(params.get("override_upc_bool", False)),
            override_upc_level=int(params.get("override_upc_level", 1) or 1),
            override_upc_category_filter=params.get(
                "override_upc_category_filter", "ALL"
            ),
            split_prepaid_sales_tax_crec=normalize_bool(
                params.get("split_prepaid_sales_tax_crec", False)
            ),
            upc_target_length=int(params.get("upc_target_length", 11) or 11),
            upc_padding_pattern=params.get("upc_padding_pattern", "           "),
        )


class EDITweaker:
    """EDI Tweaker - applies transformations to EDI files.

    This class encapsulates all EDI tweak functionality and uses
    dependency injection for testability.

    Attributes:
        query_runner: Database query runner (injected)
        config: Tweaker configuration
        crec_appender: C-record generator for split tax
        po_fetcher: PO number fetcher
    """

    def __init__(
        self,
        query_runner: TweakerQueryRunnerProtocol,
        config: Optional[TweakerConfig] = None,
    ):
        """Initialize the EDITweaker.

        Args:
            query_runner: Object implementing TweakerQueryRunnerProtocol
            config: Optional configuration (defaults to TweakerConfig())
        """
        self.query_runner = query_runner
        self.config = config or TweakerConfig()
        self.crec_appender = CRecGenerator(query_runner)
        self.po_fetcher = POFetcher(query_runner)

    def tweak(
        self,
        input_path: str,
        output_path: str,
        settings: Dict[str, Any],
        params: Dict[str, Any],
        upc_dict: Dict[int, tuple],
    ) -> str:
        """Apply EDI tweaks to a file.

        Args:
            input_path: Path to input EDI file
            output_path: Path to output file
            settings: Settings dictionary with DB credentials
            params: Parameters dictionary with tweak settings
            upc_dict: UPC lookup dictionary

        Returns:
            Path to the output file (may include .txt extension)
        """
        correlation_id = get_or_create_correlation_id()
        start_time = time.perf_counter()

        # Update config from params
        if params:
            self.config = TweakerConfig.from_params(params)

        StructuredLogger.log_debug(
            logger,
            "tweak",
            __name__,
            f"Starting EDI tweak: {os.path.basename(input_path)}",
            input_file=os.path.basename(input_path),
            output_file=os.path.basename(output_path),
            correlation_id=correlation_id,
        )

        try:
            # Open input file with retry logic
            work_file = self._open_input_with_retry(input_path)

            # Read all lines
            work_file_lined = [n for n in work_file.readlines()]
            work_file.close()

            StructuredLogger.log_debug(
                logger,
                "tweak",
                __name__,
                f"Read {len(work_file_lined)} lines from EDI file",
                line_count=len(work_file_lined),
                correlation_id=correlation_id,
            )

            # Handle force_txt_file_ext
            if self.config.force_txt_file_ext:
                output_path = output_path + ".txt"

            # Open output file with retry logic
            output_file = self._open_output_with_retry(output_path)

            # Process all records
            self._process_records(work_file_lined, output_file, upc_dict)

            output_file.close()

            duration_ms = (time.perf_counter() - start_time) * 1000
            StructuredLogger.log_debug(
                logger,
                "tweak",
                __name__,
                f"EDI tweak completed: {output_path}",
                output_file=os.path.basename(output_path),
                duration_ms=round(duration_ms, 2),
                correlation_id=correlation_id,
            )

            return output_path

        except Exception as e:
            duration_ms = (time.perf_counter() - start_time) * 1000
            StructuredLogger.log_error(
                logger,
                "tweak",
                __name__,
                e,
                {
                    "input_file": input_path,
                    "output_file": output_path,
                },
                duration_ms,
            )
            raise

    def _open_input_with_retry(self, filepath: str) -> TextIO:
        """Open input file with retry logic."""
        read_attempt_counter = 1
        while True:
            try:
                return open(filepath)
            except Exception as error:
                if read_attempt_counter >= 5:
                    time.sleep(read_attempt_counter * read_attempt_counter)
                    read_attempt_counter += 1
                    logger.info("Retrying open %s", filepath)
                else:
                    logger.error(
                        "Error opening file for read %s: %s",
                        filepath,
                        error,
                        exc_info=True,
                    )
                    raise

    def _open_output_with_retry(self, filepath: str) -> TextIO:
        """Open output file with retry logic."""
        write_attempt_counter = 1
        while True:
            try:
                return open(filepath, "w", newline="\r\n")
            except Exception as error:
                if write_attempt_counter >= 5:
                    time.sleep(write_attempt_counter * write_attempt_counter)
                    write_attempt_counter += 1
                    logger.info("Retrying open %s", filepath)
                else:
                    logger.error(
                        "Error opening file for write %s: %s",
                        filepath,
                        error,
                        exc_info=True,
                    )
                    raise

    def _process_records(
        self, lines: list[str], output_file: TextIO, upc_dict: dict
    ) -> None:
        """Process all EDI records.

        Args:
            lines: List of input lines
            output_file: Output file handle
            upc_dict: UPC lookup dictionary
        """
        from core import utils

        a_records = 0
        b_records = 0
        c_records = 0

        for line_num, line in enumerate(lines):
            input_edi_dict = utils.capture_records(line)
            writeable_line = line

            # Log intermediate progress every 100 records
            if line_num > 0 and line_num % 100 == 0:
                StructuredLogger.log_debug(
                    logger,
                    "tweak",
                    __name__,
                    f"Processing: {line_num}/{len(lines)} lines",
                    progress={"current": line_num, "total": len(lines)},
                )

            if writeable_line.startswith("A"):
                a_records += 1
                writeable_line = self._process_a_record(input_edi_dict, output_file)

            if writeable_line.startswith("B"):
                b_records += 1
                writeable_line = self._process_b_record(
                    input_edi_dict, output_file, upc_dict
                )

            if writeable_line.startswith("C"):
                c_records += 1
                writeable_line = self._process_c_record(input_edi_dict, output_file)

            if writeable_line:
                output_file.write(writeable_line)

        StructuredLogger.log_debug(
            logger,
            "tweak",
            __name__,
            "Records processed",
            records={
                "a_records": a_records,
                "b_records": b_records,
                "c_records": c_records,
            },
        )

    def _process_a_record(self, fields: dict, output_file: TextIO) -> str:
        """Process an A record.

        Args:
            fields: Parsed A record fields
            output_file: Output file handle

        Returns:
            Formatted A record line
        """
        invoice_num = fields["invoice_number"]
        self.crec_appender.set_invoice_number(int(invoice_num))

        # Date offset transformation
        if self.config.invoice_date_offset != 0:
            invoice_date_string = fields["invoice_date"]
            if not invoice_date_string == "000000":
                invoice_date = datetime.strptime(invoice_date_string, "%m%d%y")
                offset_invoice_date = invoice_date + timedelta(
                    days=self.config.invoice_date_offset
                )
                fields["invoice_date"] = datetime.strftime(
                    offset_invoice_date, "%m%d%y"
                )

        # Custom date format
        if self.config.invoice_date_custom_format:
            invoice_date_string = fields["invoice_date"]
            try:
                invoice_date = datetime.strptime(invoice_date_string, "%m%d%y")
                fields["invoice_date"] = datetime.strftime(
                    invoice_date, self.config.invoice_date_custom_format_string
                )
            except ValueError:
                fields["invoice_date"] = "ERROR"

        # A record padding
        if self.config.pad_arec:
            padding = self.config.arec_padding
            width = self.config.arec_padding_len
            fields["cust_vendor"] = f"{padding:<{width}}"

        # Build A record line
        line_builder = [
            fields["record_type"],
            fields["cust_vendor"],
            fields["invoice_number"],
            fields["invoice_date"],
            fields["invoice_total"],
        ]

        # Append PO number to A record
        if self.config.append_arec:
            append_text = self.config.append_arec_text
            if "%po_str%" in append_text:
                po_number = self.po_fetcher.fetch_po_number(int(invoice_num))
                append_text = append_text.replace("%po_str%", po_number)
            line_builder.append(append_text)

        line_builder.append("\n")
        return "".join(line_builder)

    def _process_b_record(
        self, fields: dict, output_file: TextIO, upc_dict: dict
    ) -> str:
        """Process a B record.

        Args:
            fields: Parsed B record fields
            output_file: Output file handle
            upc_dict: UPC lookup dictionary

        Returns:
            Formatted B record line
        """
        vendor_item = fields["vendor_item"].strip()

        # UPC override transformation
        if self.config.override_upc:
            fields = self._apply_upc_override(fields, upc_dict)

        # Retail UOM transformation
        if self.config.retail_uom:
            fields = self._apply_retail_uom(fields, upc_dict)

        # UPC check digit calculation
        if self.config.calc_upc:
            fields = self._apply_upc_calc(fields)

        # Determine parent-item handling AFTER UPC and numeric tweaks
        projected_line = "".join(
            (
                fields["record_type"],
                fields["upc_number"],
                fields["description"],
                fields["vendor_item"],
                fields["unit_cost"],
                fields["combo_code"],
                fields["unit_multiplier"],
                fields["qty_of_units"],
                fields["suggested_retail_price"],
                fields["price_multi_pack"],
                fields["parent_item_number"],
            )
        )
        if len(projected_line) < 76:
            fields["parent_item_number"] = ""

        # Handle negative digits
        for field_name in [
            "unit_cost",
            "unit_multiplier",
            "qty_of_units",
            "suggested_retail_price",
        ]:
            tempfield = fields[field_name].replace("-", "")
            if len(tempfield) != len(fields[field_name]):
                fields[field_name] = "-" + tempfield

        # Build B record line
        return "".join(
            (
                fields["record_type"],
                fields["upc_number"],
                fields["description"],
                fields["vendor_item"],
                fields["unit_cost"],
                fields["combo_code"],
                fields["unit_multiplier"],
                fields["qty_of_units"],
                fields["suggested_retail_price"],
                fields["price_multi_pack"],
                fields["parent_item_number"],
                "\n",
            )
        )

    def _process_c_record(self, fields: dict, output_file: TextIO) -> str:
        """Process a C record.

        Args:
            fields: Parsed C record fields
            output_file: Output file handle

        Returns:
            Formatted C record line (may include generated split tax records)
        """
        if (
            self.config.split_prepaid_sales_tax_crec
            and self.crec_appender.unappended_records
        ):
            # Check if this is a "TAB Sales Tax" record
            if fields.get("description", "").startswith("TABSales Tax"):
                self.crec_appender.fetch_splitted_sales_tax_totals(output_file)
                return ""  # Don't write the original C record

        return (
            fields["record_type"]
            + "".join(v for k, v in fields.items() if k != "record_type")
            + "\n"
        )

    def _apply_upc_override(self, fields: dict, upc_dict: dict) -> dict:
        """Apply UPC override from lookup table.

        Args:
            fields: B record fields
            upc_dict: UPC lookup dictionary

        Returns:
            Modified fields dictionary
        """
        try:
            vendor_item = int(fields["vendor_item"].strip())
            category_filter = self.config.override_upc_category_filter.strip()

            if category_filter == "" or category_filter == "ALL":
                fields["upc_number"] = upc_dict[vendor_item][
                    self.config.override_upc_level
                ]
            else:
                if upc_dict[vendor_item][0] in category_filter.split(","):
                    fields["upc_number"] = upc_dict[vendor_item][
                        self.config.override_upc_level
                    ]
        except (KeyError, TypeError):
            fields["upc_number"] = ""

        return fields

    def _apply_retail_uom(self, fields: dict, upc_dict: dict) -> dict:
        """Apply retail UOM transformation.

        Args:
            fields: B record fields
            upc_dict: UPC lookup dictionary

        Returns:
            Modified fields dictionary
        """
        try:
            item_number = int(fields["vendor_item"].strip())
            float(fields["unit_cost"].strip())
            unit_multiplier = int(fields["unit_multiplier"].strip())
            if unit_multiplier == 0:
                raise ValueError
            int(fields["qty_of_units"].strip())
        except Exception:
            return fields

        try:
            # Get UPC for each (retail) from lookup
            each_upc_string = upc_dict[item_number][1][:11].ljust(11)
        except (KeyError, IndexError):
            each_upc_string = self.config.upc_padding_pattern[:11]

        try:
            fields["unit_cost"] = (
                str(
                    Decimal(
                        (Decimal(fields["unit_cost"].strip()) / 100)
                        / Decimal(fields["unit_multiplier"].strip())
                    ).quantize(Decimal(".01"))
                )
                .replace(".", "")[-6:]
                .rjust(6, "0")
            )
            fields["qty_of_units"] = str(
                int(fields["unit_multiplier"].strip())
                * int(fields["qty_of_units"].strip())
            ).rjust(5, "0")
            fields["upc_number"] = each_upc_string
            fields["unit_multiplier"] = "000001"
        except Exception:
            pass

        return fields

    def _apply_upc_calc(self, fields: dict) -> dict:
        """Apply UPC check digit calculation.

        Args:
            fields: B record fields

        Returns:
            Modified fields dictionary
        """
        from core import utils

        try:
            _ = int(fields["upc_number"].rstrip())
            blank_upc = False
        except ValueError:
            blank_upc = True

        if not blank_upc:
            proposed_upc = fields["upc_number"].strip()
            upc_len = len(str(proposed_upc))

            if upc_len == self.config.upc_target_length:
                # Exact match, is valid
                pass
            elif upc_len == 12 and self.config.upc_target_length == 13:
                # Pad a 12-char UPC with check digit to length 13
                fields["upc_number"] = str(proposed_upc).rjust(
                    self.config.upc_target_length,
                    self.config.upc_padding_pattern[0]
                    if self.config.upc_padding_pattern
                    else " ",
                )
            elif upc_len == 11:
                # Add check digit to 11-char base UPC
                check_digit = utils.calc_check_digit(proposed_upc)
                fields["upc_number"] = str(proposed_upc) + str(check_digit)
            elif upc_len == 8:
                # Convert UPC-E to UPC-A
                fields["upc_number"] = str(utils.convert_UPCE_to_UPCA(proposed_upc))
        else:
            fields["upc_number"] = self.config.upc_padding_pattern[
                : self.config.upc_target_length
            ]

        return fields
