"""Customer lookup service for EDI converters."""
from typing import Any, List

from core.database import QueryRunner
from core.exceptions import CustomerLookupError
from core.structured_logging import get_logger

logger = get_logger(__name__)


class CustomerLookupService:
    """Service for customer header field lookups from AS400 database."""

    def __init__(self, query_runner: QueryRunner, sql_query: str):
        """Initialize with query runner and SQL query template.

        Args:
            query_runner: Database query runner
            sql_query: SQL query template for customer lookup
        """
        self._query_runner = query_runner
        self._sql_query = sql_query
        self._header_dict: dict[str, Any] = {}

    @property
    def header_dict(self) -> dict[str, Any]:
        """Get current customer header fields."""
        return self._header_dict

    def lookup(self, invoice_number: str) -> dict[str, Any]:
        """Look up customer header fields by invoice number.

        Args:
            invoice_number: Invoice number to look up

        Returns:
            Dictionary of customer header fields

        Raises:
            CustomerLookupError: If customer not found
        """
        invoice_param = invoice_number.lstrip("0")

        header_fields = self._query_runner.run_query(self._sql_query, (invoice_param,))

        if len(header_fields) == 0:
            logger.error("Cannot find order %s in AS400 history", invoice_number)
            raise CustomerLookupError(f"Cannot Find Order {invoice_number} In History.")

        self._header_dict = self._build_header_dict(header_fields[0], [])
        return self._header_dict

    def _build_header_dict(
        self, header_fields: dict[str, Any], header_fields_list: List[str]
    ) -> dict[str, Any]:
        """Build customer header dictionary from query results."""
        result = {}
        for key, value in header_fields.items():
            new_key = key.replace(" ", "_")
            result[new_key] = value
        return result