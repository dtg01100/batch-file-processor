"""Base class architecture for EDI converter plugins.

This module provides a class hierarchy for converting EDI files to various output formats.
The architecture follows the Template Method pattern, where the base class defines the
conversion orchestration and subclasses implement specific record processing logic.

Class Hierarchy:
    BaseConverter (Abstract)
    ├── CSVConverter
    │   ├── DBEnabledConverter
    │   └── [Specific CSV converters: convert_to_csv, convert_to_fintech, etc.]
    └── [Non-CSV converters: convert_to_scannerware, convert_to_scansheet_type_a]

Example Usage:
    # For simple CSV converters:
    class MyConverter(CSVConverter):
        def process_record_a(self, record: dict) -> None:
            self.write_row([record['invoice_number'], record['invoice_date']])
        
        def process_record_b(self, record: dict) -> None:
            self.write_row([record['upc_number'], record['qty_of_units']])
        
        def process_record_c(self, record: dict) -> None:
            pass  # C records not needed
    
    # For DB-enabled converters:
    class MyDBConverter(DBEnabledConverter):
        def initialize_output(self) -> None:
            super().initialize_output()
            self.connect_db()
            # Additional DB setup
        
        def process_record_a(self, record: dict) -> None:
            # Use self.query_object to fetch data
            result = self.query_object.run_arbitrary_query("SELECT ...")
            self.write_row([...])
    
    # Backward-compatible wrapper function:
    def edi_convert(edi_process, output_filename, settings_dict, parameters_dict, upc_lookup):
        converter = MyConverter(edi_process, output_filename, settings_dict, parameters_dict, upc_lookup)
        return converter.convert()
"""

from abc import ABC, abstractmethod
from typing import Any, Optional, TextIO, Union
import csv
import os

import utils
from query_runner import query_runner


class BaseConverter(ABC):
    """Abstract base class for EDI file converters.
    
    This class defines the template method pattern for converting EDI files.
    Subclasses must implement the abstract methods for record processing.
    
    Attributes:
        edi_process: Path to the input EDI file.
        output_filename: Base path for the output file (without extension).
        settings_dict: Dictionary containing application settings.
        parameters_dict: Dictionary containing conversion parameters.
        upc_lookup: Dictionary for UPC code lookups.
        lines: List of lines read from the input file.
        current_a_record: The current A record being processed (header context).
    """

    def __init__(
        self,
        edi_process: str,
        output_filename: str,
        settings_dict: dict,
        parameters_dict: dict,
        upc_lookup: dict,
    ) -> None:
        """Initialize the converter with input parameters.
        
        Args:
            edi_process: Path to the input EDI file.
            output_filename: Base path for the output file (without extension).
            settings_dict: Dictionary containing application settings including
                database credentials, ODBC driver, etc.
            parameters_dict: Dictionary containing conversion-specific parameters
                such as flags for including headers, A records, C records, etc.
            upc_lookup: Dictionary mapping item numbers to UPC information.
        """
        self.edi_process = edi_process
        self.output_filename = output_filename
        self.settings_dict = settings_dict
        self.parameters_dict = parameters_dict
        self.upc_lookup = upc_lookup
        self.lines: list[str] = []
        self.current_a_record: Optional[dict] = None

    @abstractmethod
    def initialize_output(self) -> None:
        """Initialize the output file/resource.
        
        This method is called once before processing begins.
        Subclasses should open files, create database connections,
        write headers, etc.
        
        Example:
            def initialize_output(self) -> None:
                self.output_file = open(self.output_filename + '.csv', 'w')
                self.csv_writer = csv.writer(self.output_file)
                self.csv_writer.writerow(['Header1', 'Header2'])
        """
        pass

    @abstractmethod
    def process_record_a(self, record: dict) -> None:
        """Process an A record (invoice header).
        
        A records contain invoice-level information such as:
        - cust_vendor: Customer/vendor code
        - invoice_number: Invoice identifier
        - invoice_date: Invoice date (MMDDYY format)
        - invoice_total: Total invoice amount (DAC format)
        
        Args:
            record: Dictionary containing parsed A record fields.
        
        Example:
            def process_record_a(self, record: dict) -> None:
                self.current_invoice = record['invoice_number']
                self.write_row([
                    record['invoice_number'],
                    record['invoice_date'],
                    self.convert_to_price(record['invoice_total'])
                ])
        """
        pass

    @abstractmethod
    def process_record_b(self, record: dict) -> None:
        """Process a B record (line item).
        
        B records contain item-level information such as:
        - upc_number: UPC code
        - description: Item description
        - vendor_item: Vendor item number
        - unit_cost: Unit cost (DAC format)
        - combo_code: Combo code
        - unit_multiplier: Units per case
        - qty_of_units: Quantity shipped
        - suggested_retail_price: Suggested retail price
        - price_multi_pack: Price multi-pack
        - parent_item_number: Parent item number (for shippers)
        
        Args:
            record: Dictionary containing parsed B record fields.
        
        Example:
            def process_record_b(self, record: dict) -> None:
                upc = self.process_upc(record['upc_number'])
                qty = self.qty_to_int(record['qty_of_units'])
                cost = self.convert_to_price(record['unit_cost'])
                self.write_row([upc, qty, cost, record['description']])
        """
        pass

    @abstractmethod
    def process_record_c(self, record: dict) -> None:
        """Process a C record (charge/adjustment).
        
        C records contain charge/adjustment information such as:
        - charge_type: Type of charge
        - description: Charge description
        - amount: Charge amount (DAC format)
        
        Args:
            record: Dictionary containing parsed C record fields.
        
        Example:
            def process_record_c(self, record: dict) -> None:
                amount = self.convert_to_price(record['amount'])
                self.write_row([
                    record['charge_type'],
                    record['description'],
                    amount
                ])
        """
        pass

    @abstractmethod
    def finalize_output(self) -> str:
        """Finalize the output and return the output filename.
        
        This method is called once after all records have been processed.
        Subclasses should close files, write footers, commit transactions, etc.
        
        Returns:
            The path to the generated output file.
        
        Example:
            def finalize_output(self) -> str:
                self.output_file.close()
                return self.output_filename + '.csv'
        """
        pass

    def convert(self) -> str:
        """Execute the conversion process.
        
        This is the main orchestration method that:
        1. Reads the input EDI file
        2. Initializes the output
        3. Iterates through all records
        4. Dispatches to appropriate record processors
        5. Finalizes the output
        
        Returns:
            The path to the generated output file.
        
        Raises:
            FileNotFoundError: If the input EDI file does not exist.
            Exception: If any error occurs during processing.
        """
        # Read all lines from input file
        with open(self.edi_process, encoding="utf-8") as work_file:
            self.lines = work_file.readlines()

        # Initialize output
        self.initialize_output()

        # Process each line
        for line in self.lines:
            record = utils.capture_records(line)
            if record is not None:
                record_type = record.get("record_type")
                
                if record_type == "A":
                    self.current_a_record = record
                    self.process_record_a(record)
                elif record_type == "B":
                    self.process_record_b(record)
                elif record_type == "C":
                    self.process_record_c(record)

        # Finalize and return output path
        return self.finalize_output()

    @staticmethod
    def convert_to_price(value: str) -> str:
        """Convert DAC price format to decimal string.
        
        DAC price format stores values as integers with 2 implied decimal places.
        Example: "00012345" -> "123.45", "00000099" -> "0.99"
        
        Args:
            value: Price string in DAC format (6+ characters).
        
        Returns:
            Price as a formatted decimal string.
        
        Example:
            >>> BaseConverter.convert_to_price("00012345")
            '123.45'
            >>> BaseConverter.convert_to_price("00000099")
            '0.99'
        """
        if not value or len(value) < 2:
            return "0.00"
        dollars = value[:-2].lstrip("0")
        if dollars == "":
            dollars = "0"
        cents = value[-2:]
        return f"{dollars}.{cents}"

    @staticmethod
    def qty_to_int(qty: str) -> int:
        """Convert quantity string to integer, handling negative values.
        
        DAC format uses a special negative representation where negative
        values are indicated by specific formatting.
        
        Args:
            qty: Quantity string from EDI record.
        
        Returns:
            Quantity as an integer (negative if indicated).
        
        Example:
            >>> BaseConverter.qty_to_int("0010")
            10
            >>> BaseConverter.qty_to_int("-010")
            -10
        """
        qty = qty.strip()
        if qty.startswith("-"):
            try:
                wrkqty = int(qty[1:])
                return wrkqty - (wrkqty * 2)
            except ValueError:
                return 0
        else:
            try:
                return int(qty)
            except ValueError:
                return 0

    @staticmethod
    def process_upc(upc_string: str, calc_check_digit: bool = True) -> str:
        """Process UPC string, adding check digit or converting UPCE to UPCA.
        
        Handles various UPC formats:
        - 12 digits: Already UPCA, return as-is
        - 11 digits: Add check digit
        - 8 digits: Convert UPCE to UPCA
        - Empty/invalid: Return empty string
        
        Args:
            upc_string: Raw UPC string from EDI record.
            calc_check_digit: Whether to calculate and append check digit
                for 11-digit UPCs. Defaults to True.
        
        Returns:
            Processed 12-digit UPCA string, or empty if invalid.
        
        Example:
            >>> BaseConverter.process_upc("12345678901")  # 11-digit
            '123456789012'  # with check digit
            >>> BaseConverter.process_upc("04182635")  # UPCE
            '041800000265'
        """
        upc_string = upc_string.strip()
        
        # Check if valid numeric
        try:
            _ = int(upc_string)
        except ValueError:
            return ""
        
        if len(upc_string) == 12:
            return upc_string
        elif len(upc_string) == 11 and calc_check_digit:
            return upc_string + str(utils.calc_check_digit(upc_string))
        elif len(upc_string) == 8:
            upca = utils.convert_UPCE_to_UPCA(upc_string)
            return upca if isinstance(upca, str) else ""
        else:
            return ""


class CSVConverter(BaseConverter):
    """Intermediate class for CSV output converters.
    
    This class handles CSV file management including opening, writing,
    and closing CSV files. It uses the excel dialect with CRLF line
    terminators by default.
    
    Attributes:
        csv_file: The csv.writer instance.
        output_file: The file handle for the output file.
        csv_dialect: CSV dialect to use (default: 'excel').
        lineterminator: Line terminator string (default: '\r\n').
        quoting: CSV quoting mode (default: csv.QUOTE_ALL).
    
    Example:
        class MyCSVConverter(CSVConverter):
            def initialize_output(self) -> None:
                super().initialize_output()
                self.write_header(['Column1', 'Column2'])
            
            def process_record_a(self, record: dict) -> None:
                self.write_row([record['invoice_number']])
    """

    def __init__(
        self,
        edi_process: str,
        output_filename: str,
        settings_dict: dict,
        parameters_dict: dict,
        upc_lookup: dict,
    ) -> None:
        """Initialize the CSV converter.
        
        Args:
            edi_process: Path to the input EDI file.
            output_filename: Base path for the output file (without extension).
            settings_dict: Dictionary containing application settings.
            parameters_dict: Dictionary containing conversion parameters.
            upc_lookup: Dictionary for UPC code lookups.
        """
        super().__init__(edi_process, output_filename, settings_dict, parameters_dict, upc_lookup)
        self.csv_file: Any = None
        self.output_file: Optional[TextIO] = None
        self.csv_dialect: str = "excel"
        self.lineterminator: str = "\r\n"
        self.quoting = csv.QUOTE_ALL

    def initialize_output(self) -> None:
        """Initialize the CSV output file.
        
        Opens the output file and creates the csv.writer instance.
        The output filename will have '.csv' appended.
        
        Override this method to customize CSV dialect or write headers.
        Call super().initialize_output() first when overriding.
        """
        output_path = self.output_filename + ".csv"
        self.output_file = open(output_path, "w", newline="", encoding="utf-8")
        self.csv_file = csv.writer(
            self.output_file,
            dialect=self.csv_dialect,
            lineterminator=self.lineterminator,
            quoting=self.quoting,
        )

    def write_header(self, headers: list[str]) -> None:
        """Write a header row to the CSV file.
        
        Args:
            headers: List of column header strings.
        
        Raises:
            RuntimeError: If initialize_output() has not been called.
        """
        if self.csv_file is None:
            raise RuntimeError("CSV file not initialized. Call initialize_output() first.")
        self.csv_file.writerow(headers)

    def write_row(self, row: list[Any]) -> None:
        """Write a data row to the CSV file.
        
        Args:
            row: List of values to write. Values will be converted to strings.
        
        Raises:
            RuntimeError: If initialize_output() has not been called.
        """
        if self.csv_file is None:
            raise RuntimeError("CSV file not initialized. Call initialize_output() first.")
        self.csv_file.writerow(row)

    def finalize_output(self) -> str:
        """Close the CSV output file and return the filename.
        
        Returns:
            The path to the generated CSV file.
        """
        if self.output_file is not None:
            self.output_file.close()
        return self.output_filename + ".csv"


class DBEnabledConverter(CSVConverter):
    """Intermediate class for converters that need database access.
    
    This class extends CSVConverter with database connectivity using
    the query_runner module. It provides lazy database connection
    initialization.
    
    Attributes:
        query_object: The query_runner instance (initialized on first use).
        _db_connected: Flag indicating if database connection is established.
    
    Example:
        class MyDBConverter(DBEnabledConverter):
            def process_record_a(self, record: dict) -> None:
                self.connect_db()
                result = self.query_object.run_arbitrary_query(
                    f"SELECT * FROM orders WHERE invoice = {record['invoice_number']}"
                )
                self.write_row([record['invoice_number'], result[0][0]])
    """

    def __init__(
        self,
        edi_process: str,
        output_filename: str,
        settings_dict: dict,
        parameters_dict: dict,
        upc_lookup: dict,
    ) -> None:
        """Initialize the DB-enabled converter.
        
        Args:
            edi_process: Path to the input EDI file.
            output_filename: Base path for the output file (without extension).
            settings_dict: Dictionary containing application settings including
                as400_username, as400_password, as400_address, odbc_driver.
            parameters_dict: Dictionary containing conversion parameters.
            upc_lookup: Dictionary for UPC code lookups.
        """
        super().__init__(edi_process, output_filename, settings_dict, parameters_dict, upc_lookup)
        self.query_object: Optional[query_runner] = None
        self._db_connected: bool = False

    def connect_db(self) -> None:
        """Establish database connection if not already connected.
        
        This method implements lazy connection initialization. It is safe
        to call multiple times; subsequent calls will be no-ops if already
        connected.
        
        The connection uses credentials from settings_dict:
        - as400_username: Database username
        - as400_password: Database password
        - as400_address: Database host address
        - odbc_driver: ODBC driver string
        
        Raises:
            KeyError: If required database settings are missing.
            Exception: If database connection fails.
        """
        if not self._db_connected:
            self.query_object = query_runner(
                self.settings_dict["as400_username"],
                self.settings_dict["as400_password"],
                self.settings_dict["as400_address"],
                f"{self.settings_dict['odbc_driver']}",
            )
            self._db_connected = True

    def run_query(self, query_string: str) -> list:
        """Execute a database query.
        
        This is a convenience method that ensures the database is connected
        before executing the query.
        
        Args:
            query_string: SQL query to execute.
        
        Returns:
            List of query results (rows).
        
        Raises:
            RuntimeError: If database connection cannot be established.
        """
        self.connect_db()
        if self.query_object is None:
            raise RuntimeError("Failed to initialize database connection")
        return self.query_object.run_arbitrary_query(query_string)


# Backward compatibility wrapper function template
# This can be used in individual converter modules to maintain compatibility
def create_edi_convert_wrapper(converter_class):
    """Create a backward-compatible edi_convert function from a converter class.
    
    Args:
        converter_class: A class inheriting from BaseConverter.
    
    Returns:
        A function with the signature edi_convert(edi_process, output_filename,
        settings_dict, parameters_dict, upc_lookup) that instantiates and runs
        the converter.
    
    Example:
        # In convert_to_csv.py:
        from convert_base import CSVConverter, create_edi_convert_wrapper
        
        class CSVToCSVConverter(CSVConverter):
            def initialize_output(self) -> None:
                super().initialize_output()
                if self.parameters_dict.get('include_headers') != 'False':
                    self.write_header(['UPC', 'Qty', 'Cost'])
            
            def process_record_a(self, record: dict) -> None:
                if self.parameters_dict.get('include_a_records') != 'False':
                    self.write_row([...])
            
            def process_record_b(self, record: dict) -> None:
                self.write_row([...])
            
            def process_record_c(self, record: dict) -> None:
                if self.parameters_dict.get('include_c_records') != 'False':
                    self.write_row([...])
        
        edi_convert = create_edi_convert_wrapper(CSVToCSVConverter)
    """
    def edi_convert(edi_process, output_filename, settings_dict, parameters_dict, upc_lookup):
        converter = converter_class(
            edi_process, output_filename, settings_dict, parameters_dict, upc_lookup
        )
        return converter.convert()
    return edi_convert
