"""Purchase order fetcher with injectable query runner.

This module provides a POFetcher class that retrieves purchase order
data from the database using dependency injection for testability.
"""

from dataclasses import dataclass
from typing import Protocol, runtime_checkable, Optional

from core.database.query_runner import QueryRunner


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
class POData:
    """Purchase order data container.
    
    Attributes:
        po_number: Purchase order number
        vendor_name: Name of the vendor
        order_date: Date of the order
        vendor_oid: Vendor order ID
    """
    po_number: str
    vendor_name: str = ""
    order_date: str = ""
    vendor_oid: str = ""


class POFetcher:
    """Fetches purchase order data from database.
    
    Uses injectable query runner for database operations,
    enabling testing without actual database connections.
    
    Attributes:
        DEFAULT_PO: Default PO number returned when not found
    """
    
    DEFAULT_PO = "no_po_found    "
    
    def __init__(self, query_runner: QueryRunnerProtocol):
        """Initialize with a query runner.
        
        Args:
            query_runner: Any object implementing QueryRunnerProtocol
        """
        self._query_runner = query_runner
    
    def fetch_po_number(self, invoice_number: int) -> str:
        """Fetch PO number for an invoice.
        
        Args:
            invoice_number: Invoice number to look up
            
        Returns:
            PO number string, or default if not found
        """
        qry_ret = self._query_runner.run_query(
            f"""
            SELECT ohhst.bte4cd
            FROM dacdata.ohhst ohhst
            WHERE ohhst.bthhnb = {int(invoice_number)}
            """
        )
        
        if len(qry_ret) == 0:
            return self.DEFAULT_PO
        return str(qry_ret[0][0])
    
    def fetch_po_data(self, invoice_number: int) -> Optional[POData]:
        """Fetch complete PO data for an invoice.
        
        Args:
            invoice_number: Invoice number to look up
            
        Returns:
            POData object if found, None otherwise
        """
        qry_ret = self._query_runner.run_query(
            f"""
            SELECT
                trim(ohhst.bte4cd),
                trim(ohhst.bthinb),
                ohhst.btabnb
            FROM
                dacdata.ohhst ohhst
            WHERE
                ohhst.bthhnb = {int(invoice_number)}
            """
        )
        
        if len(qry_ret) == 0:
            return None
        
        row = qry_ret[0]
        return POData(
            po_number=str(row[0]) if row[0] else "",
            vendor_name=str(row[1]) if row[1] else "",
            vendor_oid=str(row[2]) if row[2] else ""
        )
    
    def fetch_po_lines(self, po_number: str) -> list[dict]:
        """Fetch line items for a purchase order.
        
        Args:
            po_number: Purchase order number
            
        Returns:
            List of dictionaries containing line item data
        """
        qry_ret = self._query_runner.run_query(
            f"""
            SELECT
                odhst.buhlnb,
                odhst.buhcdx,
                odhst.bufgpr,
                odhst.buh6nb
            FROM
                dacdata.odhst odhst
            WHERE
                odhst.bte4cd = '{po_number}'
            """
        )
        
        lines = []
        for row in qry_ret:
            lines.append({
                'line_number': row[0],
                'item_code': row[1],
                'price': row[2],
                'status': row[3]
            })
        
        return lines
