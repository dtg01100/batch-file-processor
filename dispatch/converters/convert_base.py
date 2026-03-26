"""BaseEDIConverter - Template Method Pattern for EDI Conversion Backends.

This module provides an abstract base class that implements the Template Method
pattern to eliminate duplication across all 10 EDI convert backends. The common
file processing loop, record type switching, and output file initialization are
implemented in the base class, while specific backends only need to implement
the hook methods for processing A, B, and C records.

Example usage:
    class MyConverter(BaseEDIConverter):
        def _initialize_output(self, context):
            # Initialize CSV writer
            context.output_file = open(context.output_filename + ".csv", "w")
            context.csv_writer = csv.writer(context.output_file)

        def process_a_record(self, record, context):
            # Process header record
            context.arec_header = record

        def process_b_record(self, record, context):
            # Process line item
            context.csv_writer.writerow([...])

        def process_c_record(self, record, context):
            # Process charge record
            context.csv_writer.writerow([...])

        def _finalize_output(self, context):
            context.output_file.close()
"""

import csv
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Dict, Optional, TextIO

import core.utils as utils
from core.database import QueryRunner, create_query_runner
from core.edi.edi_format_parser import EDIFormatParser
from core.utils import safe_int
from interface.plugins.plugin_config import PluginConfigMixin


@dataclass
class EDIRecord:
    """Represents a parsed EDI record.

    Attributes:
        record_type: The type of record ('A', 'B', or 'C')
        raw_line: The original raw line from the EDI file
        fields: Dictionary of parsed field values from the record
    """

    record_type: str
    raw_line: str
    fields: Dict[str, str]


@dataclass
class ConversionContext:
    """Shared state container for EDI conversion process.

    This dataclass holds all the shared state that needs to be passed between
    the various hook methods during conversion. It eliminates the need for
    backends to manage their own state manually.

    Attributes:
        edi_filename: Path to the input EDI file being processed
        output_filename: Base filename for output (without extension)
        settings_dict: Application settings (DB credentials, etc.)
        parameters_dict: Conversion-specific parameters from folder config
        upc_lut: UPC lookup table for item number to UPC mapping

        # Internal state (managed by base class)
        arec_header: Stores the current A record (header) for invoice context
        line_num: Current line number being processed
        records_processed: Count of records successfully processed
        output_file: Output file handle (set by _initialize_output)
        csv_writer: CSV writer instance (commonly used, set by _initialize_output)
        user_data: Dictionary for converters to store custom state
    """

    # Input parameters
    edi_filename: str
    output_filename: str
    settings_dict: Dict[str, Any]
    parameters_dict: Dict[str, Any]
    upc_lut: Dict[int, tuple]

    # Internal state (initialized automatically)
    arec_header: Optional[Dict[str, str]] = field(default=None)
    line_num: int = field(default=0)
    records_processed: int = field(default=0)
    output_file: Optional[TextIO] = field(default=None, repr=False)
    csv_writer: Optional[Any] = field(default=None, repr=False)
    user_data: Dict[str, Any] = field(default_factory=dict)

    def get_output_path(self, extension: str = ".csv") -> str:
        """Get the full output file path with extension."""
        return self.output_filename + extension


class BaseEDIConverter(ABC):
    """Abstract base class for EDI converters using the Template Method pattern.

    This class implements the common EDI file processing algorithm while allowing
    subclasses to customize specific steps through hook methods. This eliminates
    the ~870 lines of duplicated code across the 10 convert backends.

    Template Method Algorithm:
        1. _initialize_output(context) - Set up output file/writer
        2. For each line in EDI file:
           a. Parse line into EDIRecord
           b. Dispatch to process_a_record, process_b_record, or process_c_record
        3. _finalize_output(context) - Clean up and close files

    Subclasses MUST implement:
        - _initialize_output(context): Set up output file/CSV writer
        - process_b_record(record, context): Process line items

    Subclasses MAY override:
        - process_a_record(record, context): Process header records
        - process_c_record(record, context): Process charge/tax records
        - _finalize_output(context): Clean up resources
        - _should_process_record_type(record_type): Filter which records to process

    The subclass can be used in two ways:

    1. Direct instantiation (for testing):
        converter = MyConverter()
        result = converter.edi_convert("input.edi", "output", settings, params, upc_lut)

    2. Module-level wrapper function (for backward compatibility):
        def edi_convert(edi_process, output_filename, settings_dict, parameters_dict, upc_lut):
            converter = MyConverter()
            return converter.edi_convert(edi_process, output_filename, settings_dict,
                                        parameters_dict, upc_lut)
    """

    def edi_convert(
        self,
        edi_process: str,
        output_filename: str,
        settings_dict: Dict[str, Any],
        parameters_dict: Dict[str, Any],
        upc_lut: Dict[int, tuple],
    ) -> str:
        """Main entry point - Template Method defining the conversion algorithm.

        This method defines the skeleton of the EDI conversion algorithm.
        It orchestrates the conversion process by calling hook methods that
        subclasses can override to customize behavior.

        Args:
            edi_process: Path to the input EDI file
            output_filename: Base path for output file (without extension)
            settings_dict: Application settings dictionary
            parameters_dict: Conversion parameters from folder configuration
            upc_lut: UPC lookup table (item_number -> (category, upc_pack, upc_case))

        Returns:
            Path to the generated output file
        """
        # Create conversion context to hold shared state
        context = ConversionContext(
            edi_filename=edi_process,
            output_filename=output_filename,
            settings_dict=settings_dict,
            parameters_dict=parameters_dict,
            upc_lut=upc_lut,
        )

        # Step 1: Initialize output (hook method)
        self._initialize_output(context)

        try:
            # Step 2: Process EDI file line by line
            self._process_edi_file(context)

            # Step 3: Finalize output (hook method)
            self._finalize_output(context)

        except Exception as e:
            # Ensure cleanup on error
            self._cleanup_on_error(context, e)
            raise

        return self._get_return_value(context)

    def _process_edi_file(self, context: ConversionContext) -> None:
        """Process the EDI file line by line.

        This is the core file processing loop that was previously duplicated
        across all 10 convert backends (~40 lines × 10 = 400 lines).

        Args:
            context: The conversion context containing file paths and state
        """
        with open(context.edi_filename, encoding="utf-8") as work_file:
            work_file_lined = [n for n in work_file.readlines()]

            for line_num, line in enumerate(work_file_lined):
                context.line_num = line_num

                # Parse the line into a record dictionary
                input_edi_dict = utils.capture_records(line)

                if input_edi_dict is not None:
                    # Create EDIRecord object
                    record = EDIRecord(
                        record_type=input_edi_dict["record_type"],
                        raw_line=line,
                        fields=input_edi_dict,
                    )

                    # Dispatch to appropriate hook method based on record type
                    self._dispatch_record(record, context)

                    context.records_processed += 1

    def _dispatch_record(self, record: EDIRecord, context: ConversionContext) -> None:
        """Dispatch a record to the appropriate handler based on record type.

        This method implements the record type switching logic that was
        previously duplicated across 9/10 backends (~30 lines × 9 = 270 lines).

        Args:
            record: The EDIRecord to process
            context: The conversion context
        """
        record_type = record.record_type

        # Check if this record type should be processed
        if not self._should_process_record_type(record_type, context):
            return

        # Dispatch to appropriate hook method
        if record_type == "A":
            self.process_a_record(record, context)
        elif record_type == "B":
            self.process_b_record(record, context)
        elif record_type == "C":
            self.process_c_record(record, context)
        else:
            # Unknown record type - can be overridden for custom handling
            self._handle_unknown_record(record, context)

    def _should_process_record_type(
        self, record_type: str, context: ConversionContext
    ) -> bool:
        """Determine if a record type should be processed.

        Subclasses can override this to filter records based on parameters.
        For example, convert_to_csv has flags to include/exclude A and C records.

        Args:
            record_type: The type of record ('A', 'B', or 'C')
            context: The conversion context

        Returns:
            True if the record should be processed, False otherwise
        """
        # Default: process all record types
        return True

    # ========================================================================
    # Abstract Hook Methods - MUST be implemented by subclasses
    # ========================================================================

    @abstractmethod
    def _initialize_output(self, context: ConversionContext) -> None:
        """Initialize output file and writers.

        This method must set up the output file handle and any writers
        (e.g., CSV writer) needed by the converter. The output file handle
        should be stored in context.output_file.

        Args:
            context: The conversion context with output_filename available

        Example:
            context.output_file = open(context.get_output_path(), "w", newline="")
            context.csv_writer = csv.writer(context.output_file, dialect="excel")
        """

    @abstractmethod
    def process_b_record(self, record: EDIRecord, context: ConversionContext) -> None:
        """Process a B record (line item/detail record).

        This is the only REQUIRED hook method since all converters process
        B records (line items). The record contains fields like:
        - upc_number, description, vendor_item, unit_cost
        - qty_of_units, unit_multiplier, suggested_retail_price

        Args:
            record: The EDIRecord containing the B record fields
            context: The conversion context (includes arec_header for invoice info)

        Example:
            csv_file.writerow([
                record.fields['upc_number'],
                record.fields['qty_of_units'],
                ...
            ])
        """

    # ========================================================================
    # Optional Hook Methods - MAY be overridden by subclasses
    # ========================================================================

    def process_a_record(self, record: EDIRecord, context: ConversionContext) -> None:
        """Process an A record (header record).

        Default implementation stores the header in context.arec_header for
        use by B and C record processors. Subclasses can override to add
        custom header processing.

        The record contains fields like:
        - invoice_number, invoice_date, invoice_total, cust_vendor

        Args:
            record: The EDIRecord containing the A record fields
            context: The conversion context

        Example override:
            super().process_a_record(record, context)  # Store header
            context.csv_writer.writerow(["Invoice:", record.fields['invoice_number']])
        """
        context.arec_header = record.fields

    def process_c_record(self, record: EDIRecord, context: ConversionContext) -> None:
        """Process a C record (charge/tax record).

        Default implementation does nothing. Subclasses should override
        to process charge/tax records.

        The record contains fields like:
        - charge_type, description, amount

        Args:
            record: The EDIRecord containing the C record fields
            context: The conversion context
        """

    def _finalize_output(self, context: ConversionContext) -> None:
        """Finalize output and clean up resources.

        Default implementation closes the output file if it was opened.
        Subclasses should override for custom cleanup (e.g., writing footers).

        Args:
            context: The conversion context
        """
        if context.output_file is not None:
            context.output_file.close()
            context.output_file = None

    def _handle_unknown_record(
        self, record: EDIRecord, context: ConversionContext
    ) -> None:
        """Handle unknown record types.

        Default implementation silently ignores unknown records.
        Subclasses can override for custom handling.

        Args:
            record: The unknown EDIRecord
            context: The conversion context
        """

    def _cleanup_on_error(self, context: ConversionContext, error: Exception) -> None:
        """Clean up resources when an error occurs.

        Args:
            context: The conversion context
            error: The exception that was raised
        """
        if context.output_file is not None:
            try:
                context.output_file.close()
            except Exception as e:
                from dispatch.feature_flags import get_strict_testing_mode

                if get_strict_testing_mode():
                    raise RuntimeError(
                        "Failed to close output file during error cleanup"
                    ) from e
            context.output_file = None

    def _get_return_value(self, context: ConversionContext) -> str:
        """Get the return value for edi_convert().

        Default implementation returns the output filename with .csv extension.
        Subclasses can override for different return values.

        Args:
            context: The conversion context

        Returns:
            The path to the generated output file
        """
        return context.get_output_path(".csv")


# =============================================================================
# Utility Functions for Converters
# =============================================================================


def create_csv_writer(
    file_handle: TextIO,
    dialect: str = "excel",
    lineterminator: str = "\r\n",
    quoting: int = csv.QUOTE_ALL,
) -> csv.writer:
    """Create a CSV writer with common settings.

    This utility eliminates the ~20 lines of CSV writer setup duplicated
    across most convert backends.

    Args:
        file_handle: Open file handle for writing
        dialect: CSV dialect to use (default: excel)
        lineterminator: Line terminator string (default: \r\n for Windows compatibility)
        quoting: Quoting mode (default: QUOTE_ALL)

    Returns:
        Configured csv.writer instance
    """
    return csv.writer(
        file_handle, dialect=dialect, lineterminator=lineterminator, quoting=quoting
    )


def normalize_parameter(
    value: Any,
    default: Any = None,
    truthy_values: tuple = ("True", "true", "1", "yes", "on"),
) -> Any:
    """Normalize a parameter value from folder configuration.

    Folder configuration stores parameters as strings. This function
    normalizes common boolean-ish strings to Python booleans.

    Args:
        value: The parameter value (usually a string from config)
        default: Default value if value is None or empty
        truthy_values: Tuple of string values considered True

    Returns:
        Normalized value (bool for truthy/falsy strings, or original value)

    Example:
        >>> normalize_parameter("True", False)
        True
        >>> normalize_parameter("False", True)
        False
        >>> normalize_parameter("DIV001", "DEFAULT")
        'DIV001'
    """
    if value is None or value == "":
        return default
    if isinstance(value, str):
        if value.lower() in ("true", "1", "yes", "on"):
            return True
        if value.lower() in ("false", "0", "no", "off"):
            return False
    return value


class BaseConverter(ABC, PluginConfigMixin):
    """Legacy converter base preserved for older converter plugins."""

    def __init__(
        self,
        edi_process: str,
        output_filename: str,
        settings_dict: dict,
        parameters_dict: dict,
        upc_lookup: dict,
    ) -> None:
        self.edi_process = edi_process
        self.output_filename = output_filename
        self.settings_dict = settings_dict
        self.parameters_dict = parameters_dict
        self.upc_lookup = upc_lookup
        self.lines: list[str] = []
        self.current_a_record: Optional[dict] = None

        format_id = parameters_dict.get("edi_format", "default")
        try:
            self.edi_parser = EDIFormatParser.load_format(format_id)
        except Exception as e:
            from dispatch.feature_flags import get_strict_testing_mode

            if get_strict_testing_mode():
                raise RuntimeError(
                    f"Failed to load EDI format parser for format '{format_id}'"
                ) from e
            self.edi_parser = None

    @abstractmethod
    def initialize_output(self) -> None:
        """Initialize the output resource before record processing."""

    @abstractmethod
    def process_record_a(self, record: dict) -> None:
        """Process an A record."""

    @abstractmethod
    def process_record_b(self, record: dict) -> None:
        """Process a B record."""

    @abstractmethod
    def process_record_c(self, record: dict) -> None:
        """Process a C record."""

    @abstractmethod
    def finalize_output(self) -> str:
        """Finalize output and return the generated filename."""

    def convert(self) -> str:
        """Execute the legacy conversion lifecycle."""
        with open(self.edi_process, encoding="utf-8") as work_file:
            self.lines = work_file.readlines()

        self.initialize_output()

        for line in self.lines:
            try:
                record = utils.capture_records(line, self.edi_parser)
            except Exception as error:
                if "Not An EDI" in str(error):
                    continue
                raise

            if record is None:
                continue

            record_type = record.get("record_type")
            if record_type == "A":
                self.current_a_record = record
                self.process_record_a(record)
            elif record_type == "B":
                self.process_record_b(record)
            elif record_type == "C":
                self.process_record_c(record)

        return self.finalize_output()

    @staticmethod
    def convert_to_price(value: str) -> str:
        if not value or len(value) < 2:
            return "0.00"
        dollars = value[:-2].lstrip("0")
        if dollars == "":
            dollars = "0"
        cents = value[-2:]
        return f"{dollars}.{cents}"

    @staticmethod
    def qty_to_int(qty: str) -> int:
        return safe_int(qty)

    @staticmethod
    def process_upc(upc_string: str, calc_check_digit: bool = True) -> str:
        upc_string = upc_string.strip()
        try:
            int(upc_string)
        except ValueError:
            return ""

        if len(upc_string) == 12:
            return upc_string
        if len(upc_string) == 11 and calc_check_digit:
            return upc_string + str(utils.calc_check_digit(upc_string))
        if len(upc_string) == 8:
            upca = utils.convert_UPCE_to_UPCA(upc_string)
            return upca if isinstance(upca, str) else ""
        return ""


class CSVConverter(BaseConverter):
    """Legacy CSV converter base preserved for older plugins."""

    def __init__(
        self,
        edi_process: str,
        output_filename: str,
        settings_dict: dict,
        parameters_dict: dict,
        upc_lookup: dict,
    ) -> None:
        super().__init__(
            edi_process, output_filename, settings_dict, parameters_dict, upc_lookup
        )
        self.csv_file: Any = None
        self.output_file: Optional[TextIO] = None
        self.csv_dialect: str = "excel"
        self.lineterminator: str = "\r\n"
        self.quoting = csv.QUOTE_ALL

    def initialize_output(self) -> None:
        output_path = self.output_filename + ".csv"
        self.output_file = open(output_path, "w", newline="", encoding="utf-8")
        self.csv_file = csv.writer(
            self.output_file,
            dialect=self.csv_dialect,
            lineterminator=self.lineterminator,
            quoting=self.quoting,
        )

    def write_header(self, headers: list[str]) -> None:
        if self.csv_file is None:
            raise RuntimeError(
                "CSV file not initialized. Call initialize_output() first."
            )
        self.csv_file.writerow(headers)

    def write_row(self, row: list[Any]) -> None:
        if self.csv_file is None:
            raise RuntimeError(
                "CSV file not initialized. Call initialize_output() first."
            )
        self.csv_file.writerow(row)

    def finalize_output(self) -> str:
        if self.output_file is not None:
            self.output_file.close()
        return self.output_filename + ".csv"


class DBEnabledConverter(CSVConverter):
    """Legacy DB-enabled converter base preserved for older plugins."""

    def __init__(
        self,
        edi_process: str,
        output_filename: str,
        settings_dict: dict,
        parameters_dict: dict,
        upc_lookup: dict,
    ) -> None:
        super().__init__(
            edi_process, output_filename, settings_dict, parameters_dict, upc_lookup
        )
        self.query_object: Optional[QueryRunner] = None
        self._db_connected = False

    def connect_db(self) -> None:
        if not self._db_connected:
            self.query_object = create_query_runner(
                username=self.settings_dict["as400_username"],
                password=self.settings_dict["as400_password"],
                dsn=self.settings_dict["as400_address"],
                database="QGPL",
                odbc_driver=f"{self.settings_dict['odbc_driver']}",
            )
            self._db_connected = True

    def run_query(self, query_string: str) -> list:
        self.connect_db()
        if self.query_object is None:
            raise RuntimeError("Failed to initialize database connection")
        return self.query_object.run_query(query_string)


def create_edi_convert_wrapper(converter_class, format_name: str = "edi"):
    """Create the legacy module-level ``edi_convert`` wrapper with logging.

    Args:
        converter_class: The converter class to instantiate
        format_name: Name of the format for logging (e.g., "jolley_custom", "csv")
    """
    import logging
    import os
    import time

    from core.structured_logging import (
        get_logger,
        get_or_create_correlation_id,
        log_file_operation,
        log_with_context,
    )

    def edi_convert(
        edi_process, output_filename, settings_dict, parameters_dict, upc_lookup
    ):
        logger = get_logger(__name__)
        correlation_id = get_or_create_correlation_id()
        start_time = time.perf_counter()

        log_with_context(
            logger,
            logging.INFO,
            f"Starting {format_name} conversion",
            operation="edi_convert",
            context={
                "input_file": os.path.basename(edi_process),
                "output_file": os.path.basename(output_filename),
                "format": format_name,
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
            converter = converter_class(
                edi_process, output_filename, settings_dict, parameters_dict, upc_lookup
            )
            result = converter.edi_convert(
                edi_process, output_filename, settings_dict, parameters_dict, upc_lookup
            )
            duration_ms = time.perf_counter() - start_time

            log_with_context(
                logger,
                logging.INFO,
                f"{format_name} conversion completed",
                operation="edi_convert",
                context={
                    "input_file": os.path.basename(edi_process),
                    "output_file": os.path.basename(result),
                    "format": format_name,
                    "duration_ms": round(duration_ms * 1000, 2),
                },
            )
            log_file_operation(
                logger,
                "write",
                result,
                file_type="csv",
                success=True,
                duration_ms=duration_ms * 1000,
                correlation_id=correlation_id,
            )
            return result
        except Exception as e:
            duration_ms = time.perf_counter() - start_time
            log_with_context(
                logger,
                logging.ERROR,
                f"{format_name} conversion failed: {e}",
                operation="edi_convert",
                context={
                    "input_file": os.path.basename(edi_process),
                    "format": format_name,
                    "duration_ms": round(duration_ms * 1000, 2),
                    "error": str(e),
                },
            )
            raise

    return edi_convert
