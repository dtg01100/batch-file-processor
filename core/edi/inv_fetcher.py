"""Invoice fetcher with injectable query runner.

This module provides the InvFetcher class for fetching invoice-related
data from the database using dependency injection for testability.
"""

import logging
from typing import Protocol, runtime_checkable

from batch_file_processor.structured_logging import get_logger, log_with_context

logger = get_logger(__name__)


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
        self._database_lookup_mode = (
            str(self.settings.get("database_lookup_mode", "optional")).strip().lower()
        )
        self._strict_database_lookup = self._database_lookup_mode in {
            "strict",
            "required",
            "test",
        }
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

        # Handle case where no query_runner is provided (for testing)
        if self._query_runner is None:
            msg = "InvFetcher.fetch_po() called with no query_runner"
            if self._strict_database_lookup:
                raise RuntimeError(msg)
            logger.warning("%s - returning empty PO", msg)
            return ""

        try:
            qry_ret = self._query_runner.run_query(
                """
                SELECT
                    trim(ohhst.bte4cd),
                    trim(ohhst.bthinb),
                    ohhst.btabnb
                FROM
                    dacdata.ohhst ohhst
                WHERE
                    ohhst.BTHHNB = ?
                """,
                (int(invoice_number),),
            )
            log_with_context(
                logger,
                logging.DEBUG,
                "PO fetch query executed",
                operation="fetch_po",
                context={
                    "invoice_number": invoice_number,
                    "query_type": "SELECT",
                    "table": "dacdata.ohhst",
                    "params": (int(invoice_number),),
                    "result_count": len(qry_ret),
                },
            )
        except Exception:
            if self._strict_database_lookup:
                raise
            log_with_context(
                logger,
                logging.ERROR,
                "PO fetch query failed",
                operation="fetch_po",
                context={
                    "invoice_number": invoice_number,
                    "query_type": "SELECT",
                    "table": "dacdata.ohhst",
                },
                exc_info=True,
            )
            return ""
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
            elif self._strict_database_lookup:
                raise LookupError(
                    f"No invoice header found in AS400 for invoice {invoice_number}"
                )
        except (IndexError, KeyError):
            if self._strict_database_lookup:
                raise
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

    def fetch_uom_desc(self, itemno: int, uommult: int, lineno: int, invno: int) -> str:
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

            # Handle case where no query_runner is provided (for testing)
            if self._query_runner is None:
                msg = "InvFetcher.fetch_uom_desc() called with no query_runner"
                if self._strict_database_lookup:
                    raise RuntimeError(msg)
                logger.warning("%s - returning empty UOM", msg)
                return ""

            try:
                qry = """
                    SELECT
                        BUHUNB,
                        BUHXTX
                    FROM
                        dacdata.odhst odhst
                    WHERE
                        odhst.BUHHNB = ?
                """
                qry_ret = self._query_runner.run_query(qry, (int(invno),))
                # Convert results to dict lookup
                self.uom_lut = {}
                for row in qry_ret:
                    if isinstance(row, dict):
                        values = list(row.values())
                        self.uom_lut[values[0]] = values[1] if len(values) > 1 else ""
                    else:
                        self.uom_lut[row[0]] = row[1]
                log_with_context(
                    logger,
                    logging.DEBUG,
                    "UOM lookup query executed",
                    operation="fetch_uom_desc",
                    context={
                        "invoice_number": invno,
                        "query_type": "SELECT",
                        "table": "dacdata.odhst",
                        "params": (int(invno),),
                        "uom_count": len(self.uom_lut),
                    },
                )
            except Exception:
                if self._strict_database_lookup:
                    raise
                log_with_context(
                    logger,
                    logging.ERROR,
                    "UOM lookup query failed",
                    operation="fetch_uom_desc",
                    context={
                        "invoice_number": invno,
                        "query_type": "SELECT",
                        "table": "dacdata.odhst",
                    },
                    exc_info=True,
                )
            self.last_invno = invno

        try:
            return self.uom_lut[lineno + 1]
        except KeyError:
            uom_result = self._fetch_uom_from_item(itemno, uommult)
            if not uom_result:
                log_with_context(
                    logger,
                    logging.DEBUG,
                    "UOM lookup failed",
                    operation="fetch_uom_desc",
                    context={
                        "item_number": itemno,
                        "uom_multiplier": uommult,
                        "line_number": lineno,
                        "invoice_number": invno,
                    },
                )
                if self._strict_database_lookup:
                    raise LookupError(
                        f"No UOM found for item {itemno} multiplier {uommult}"
                    )
            return uom_result

    def _fetch_uom_from_item(self, itemno: int, uommult: int) -> str:
        """Fetch UOM from item master.

        Args:
            itemno: Item number
            uommult: Unit of measure multiplier

        Returns:
            Unit of measure description string
        """
        # Handle case where no query_runner is provided (for testing)
        if self._query_runner is None:
            if self._strict_database_lookup:
                raise RuntimeError(
                    "InvFetcher._fetch_uom_from_item() called with no query_runner"
                )
            return "HI" if int(uommult) > 1 else "LO"

        try:
            _ALLOWED_UOM_FIELDS = {"ANB9TX", "ANB8TX"}
            if int(uommult) > 1:
                field = "ANB9TX"
            else:
                field = "ANB8TX"
            assert field in _ALLOWED_UOM_FIELDS, f"Unexpected UOM field: {field}"
            qry = f"""
                SELECT dsanrep.{field}
                FROM dacdata.dsanrep dsanrep
                WHERE dsanrep.ANBACD = ?
            """
            qry_ret = self._query_runner.run_query(qry, (int(itemno),))
            if qry_ret:
                row = qry_ret[0]
                if isinstance(row, dict):
                    return list(row.values())[0]
                return row[0]
            if self._strict_database_lookup:
                raise LookupError(
                    f"No item-master UOM found in AS400 for item {itemno}"
                )
            return "HI" if int(uommult) > 1 else "LO"
        except Exception:
            if self._strict_database_lookup:
                raise
            try:
                if int(uommult) > 1:
                    return "HI"
                return "LO"
            except ValueError:
                return "NA"
