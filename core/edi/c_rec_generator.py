"""C-record generator for EDI split sales tax.

This module provides a CRecGenerator class that generates C records
for split prepaid/non-prepaid sales tax using dependency injection.
"""

from dataclasses import dataclass, field
from typing import Protocol, runtime_checkable, Any, TextIO


@runtime_checkable
class QueryRunnerProtocol(Protocol):
    """Protocol for query runner operations.
    
    This protocol allows any query runner implementation to be used,
    enabling easy mocking in tests.
    """
    
    def run_query(self, query: str, params: tuple = None) -> list:
        """Run a SQL query and return results.
        
        Args:
            query: SQL query string
            params: Optional query parameters
            
        Returns:
            List of query results
        """
        ...


@dataclass
class CRecordConfig:
    """Configuration for C-record generation.
    
    Attributes:
        default_uom: Default unit of measure
        default_vendor_oid: Default vendor order ID
        charge_type: Charge type code for C records
    """
    default_uom: str = 'EA'
    default_vendor_oid: str = ''
    charge_type: str = 'TAB'


class CRecGenerator:
    """Generates C records for split prepaid/non-prepaid sales tax.
    
    Uses injectable query runner for database operations,
    enabling testing without actual database connections.
    
    Attributes:
        unappended_records: Whether there are unappended records pending
    """
    
    def __init__(
        self,
        query_runner: QueryRunnerProtocol,
        config: CRecordConfig = None
    ):
        """Initialize with a query runner and optional config.
        
        Args:
            query_runner: Any object implementing QueryRunnerProtocol
            config: Optional configuration for C-record generation
        """
        self._query_runner = query_runner
        self._invoice_number = "0"
        self.unappended_records = False
        self.config = config or CRecordConfig()
    
    def set_invoice_number(self, invoice_number: int) -> None:
        """Set the current invoice number.
        
        This marks that there may be unappended records for this invoice.
        
        Args:
            invoice_number: Invoice number for subsequent operations
        """
        self._invoice_number = invoice_number
        self.unappended_records = True
    
    def fetch_splitted_sales_tax_totals(self, output_file: TextIO) -> None:
        """Fetch and write split sales tax C records.
        
        Queries the database for prepaid and non-prepaid sales tax totals
        for the current invoice and writes C records to the output file.
        
        Args:
            output_file: File handle to write C records to
        """
        qry_ret = self._query_runner.run_query(
            f"""
            SELECT
                sum(CASE odhst.buh6nb WHEN 1 THEN 0 ELSE odhst.bufgpr END),
                sum(CASE odhst.buh6nb WHEN 1 THEN odhst.bufgpr ELSE 0 END)
            FROM
                dacdata.odhst odhst
            WHERE
                odhst.BUHHNB = {self._invoice_number}
            """
        )
        
        qry_ret_non_prepaid, qry_ret_prepaid = qry_ret[0]
        
        if qry_ret_prepaid != 0 and qry_ret_prepaid is not None:
            self._write_line("Prepaid Sales Tax", qry_ret_prepaid, output_file)
        
        if qry_ret_non_prepaid != 0 and qry_ret_non_prepaid is not None:
            self._write_line("Sales Tax", qry_ret_non_prepaid, output_file)
        
        self.unappended_records = False
    
    def _write_line(
        self,
        type_str: str,
        amount: float,
        output_file: TextIO
    ) -> None:
        """Write a C record line to the output file.
        
        Args:
            type_str: Charge type description
            amount: Charge amount
            output_file: File handle to write to
        """
        desc_str = type_str.ljust(25, " ")
        
        if amount < 0:
            amount_builder = amount - (amount * 2)
        else:
            amount_builder = amount
        
        amount_str = str(amount_builder).replace(".", "").rjust(9, "0")
        
        if amount < 0:
            temp_list = list(amount_str)
            temp_list[0] = "-"
            amount_str = "".join(temp_list)
        
        line = f"C{self.config.charge_type}{desc_str}{amount_str}\n"
        output_file.write(line)
    
    def generate_c_record(
        self,
        charge_type: str,
        description: str,
        amount: float
    ) -> str:
        """Generate a single C record string.
        
        Args:
            charge_type: 3-character charge type code
            description: Charge description (will be padded to 25 chars)
            amount: Charge amount
            
        Returns:
            Formatted C record string
        """
        desc_str = description.ljust(25, " ")
        
        if amount < 0:
            amount_builder = amount - (amount * 2)
        else:
            amount_builder = amount
        
        amount_str = str(amount_builder).replace(".", "").rjust(9, "0")
        
        if amount < 0:
            temp_list = list(amount_str)
            temp_list[0] = "-"
            amount_str = "".join(temp_list)
        
        return f"C{charge_type}{desc_str}{amount_str}\n"
    
    def generate_c_records_for_invoice(
        self,
        invoice_data: dict,
        charges: list[dict]
    ) -> list[str]:
        """Generate all C records for an invoice.
        
        Args:
            invoice_data: Invoice header data
            charges: List of charge dictionaries with type, description, amount
            
        Returns:
            List of formatted C record strings
        """
        records = []
        for charge in charges:
            record = self.generate_c_record(
                charge_type=charge.get('type', self.config.charge_type),
                description=charge.get('description', ''),
                amount=charge.get('amount', 0)
            )
            records.append(record)
        return records
