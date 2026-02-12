"""Invoice fetcher with injectable query runner.

This module provides the InvFetcher class for fetching invoice-related
data from the database using dependency injection for testability.
"""

from typing import Protocol, runtime_checkable, Optional


@runtime_checkable
class QueryRunnerProtocol(Protocol):
    """Protocol for query runner operations.
    
    This protocol defines the interface required by InvFetcher
    for database operations.
    """
    
    def run_query(self, query: str, params: tuple = None) -> list[dict]:
        """Execute a query and return results.
        
        Args:
            query: SQL query string
            params: Optional query parameters
            
        Returns:
            List of dictionaries representing query results
        """
        ...


class InvFetcher:
    """Fetches invoice-related data from database.
    
    Uses injectable query runner for database operations,
    enabling testing without actual database connections.
    
    Attributes:
        query_runner: The injected query runner for database operations
        settings: Dictionary of settings (for backward compatibility)
        last_invoice_number: Last fetched invoice number (for caching)
        uom_lut: Unit of measure lookup table
        last_invno: Last invoice number for UOM lookup
        po: Cached PO number
        custname: Cached customer name
        custno: Cached customer number
    """
    
    def __init__(self, query_runner: QueryRunnerProtocol, settings: dict = None):
        """Initialize InvFetcher with query runner.
        
        Args:
            query_runner: Query runner implementing QueryRunnerProtocol
            settings: Optional settings dictionary (for backward compatibility)
        """
        self._query_runner = query_runner
        self.settings = settings or {}
        self.last_invoice_number = 0
        self.uom_lut = {0: "N/A"}
        self.last_invno = 0
        self.po = ""
        self.custname = ""
        self.custno = 0
    
    def fetch_po(self, invoice_number: int) -> str:
        """Fetch PO number for invoice.
        
        Uses caching to avoid repeated database queries for the same invoice.
        
        Args:
            invoice_number: Invoice number to look up
            
        Returns:
            PO number string, or empty string if not found
        """
        if invoice_number == self.last_invoice_number:
            return self.po
        
        qry_ret = self._query_runner.run_query(
            f"""
            SELECT
                trim(ohhst.bte4cd),
                trim(ohhst.bthinb),
                ohhst.btabnb
            FROM
                dacdata.ohhst ohhst
            WHERE
                ohhst.BTHHNB = {int(invoice_number)}
            """
        )
        self.last_invoice_number = invoice_number
        try:
            # Results are list of dicts, get first row values
            if qry_ret:
                row = qry_ret[0]
                # Handle both dict and tuple results for flexibility
                if isinstance(row, dict):
                    # Get values by column order
                    values = list(row.values())
                    self.po = values[0] if values else ""
                    self.custname = values[1] if len(values) > 1 else ""
                    self.custno = values[2] if len(values) > 2 else 0
                else:
                    # Tuple result
                    self.po = row[0]
                    self.custname = row[1]
                    self.custno = row[2]
        except (IndexError, KeyError):
            self.po = ""
        return self.po
    
    def fetch_cust_name(self, invoice_number: int) -> str:
        """Fetch customer name for invoice.
        
        Args:
            invoice_number: Invoice number to look up
            
        Returns:
            Customer name string
        """
        self.fetch_po(invoice_number)
        return self.custname
    
    def fetch_cust_no(self, invoice_number: int) -> int:
        """Fetch customer number for invoice.
        
        Args:
            invoice_number: Invoice number to look up
            
        Returns:
            Customer number
        """
        self.fetch_po(invoice_number)
        return self.custno
    
    def fetch_uom_desc(
        self,
        itemno: int,
        uommult: int,
        lineno: int,
        invno: int
    ) -> str:
        """Fetch unit of measure description.
        
        First tries to get UOM from invoice line items, then falls back
        to item master if not found.
        
        Args:
            itemno: Item number
            uommult: Unit of measure multiplier
            lineno: Line number within invoice
            invno: Invoice number
            
        Returns:
            Unit of measure description string
        """
        if invno != self.last_invno:
            self.uom_lut = {0: "N/A"}
            try:
                qry = f"""
                    SELECT
                        BUHUNB,
                        BUHXTX
                    FROM
                        dacdata.odhst odhst
                    WHERE
                        odhst.BUHHNB = {int(invno)}
                """
                qry_ret = self._query_runner.run_query(qry)
                # Convert results to dict lookup
                self.uom_lut = {}
                for row in qry_ret:
                    if isinstance(row, dict):
                        values = list(row.values())
                        self.uom_lut[values[0]] = values[1] if len(values) > 1 else ""
                    else:
                        self.uom_lut[row[0]] = row[1]
            except Exception:
                # On error, keep default uom_lut
                pass
            self.last_invno = invno
        
        try:
            return self.uom_lut[lineno + 1]
        except KeyError:
            return self._fetch_uom_from_item(itemno, uommult)
    
    def _fetch_uom_from_item(self, itemno: int, uommult: int) -> str:
        """Fetch UOM from item master.
        
        Args:
            itemno: Item number
            uommult: Unit of measure multiplier
            
        Returns:
            Unit of measure description string
        """
        try:
            if int(uommult) > 1:
                field = "ANB9TX"
            else:
                field = "ANB8TX"
            qry = f"""
                SELECT dsanrep.{field}
                FROM dacdata.dsanrep dsanrep
                WHERE dsanrep.ANBACD = {int(itemno)}
            """
            qry_ret = self._query_runner.run_query(qry)
            if qry_ret:
                row = qry_ret[0]
                if isinstance(row, dict):
                    return list(row.values())[0]
                return row[0]
            return "HI" if int(uommult) > 1 else "LO"
        except Exception:
            try:
                if int(uommult) > 1:
                    return "HI"
                return "LO"
            except ValueError:
                return "NA"
