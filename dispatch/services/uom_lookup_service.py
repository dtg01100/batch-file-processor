"""UOM (Unit of Measure) lookup service for EDI converters."""
from typing import Any, List, Optional

from core.database import QueryRunner
from core.structured_logging import get_logger

logger = get_logger(__name__)


class UOMLookupService:
    """Service for UOM lookup and resolution from database queries."""

    def __init__(self, query_runner: QueryRunner):
        """Initialize with query runner.

        Args:
            query_runner: Database query runner for executing queries
        """
        self._query_runner = query_runner
        self.uom_lookup_list: List[dict[str, Any]] = []

    def init_uom_lookup(self, invoice_number: str) -> List[dict[str, Any]]:
        """Initialize UOM lookup and fetch UOM data."""
        self.uom_lookup_list = self._query_runner.run_query(
            self._get_uom_query_sql(), (invoice_number,)
        )

        if not self.uom_lookup_list:
            logger.warning("No UOM data found for invoice %s", invoice_number)

        return self.uom_lookup_list

    def get_uom(self, item_number: str, packsize: str) -> str:
        """Get UOM (Unit of Measure) for an item."""
        if not self.uom_lookup_list:
            return "?"

        candidates = self._uom_candidates(item_number)
        selected = self._uom_select(candidates, packsize)

        try:
            uom_code = self._uom_get_key(selected[0], "uom_code", "UOM_CODE")
            return uom_code if uom_code else "?"
        except IndexError:
            return "?"

    def _uom_get_key(self, entry: dict[str, Any], *keys: str) -> Optional[str]:
        for key in keys:
            for k, v in entry.items():
                if k.upper() == key.upper():
                    return v
            for k, v in entry.items():
                if k.lower() == key.lower():
                    return v
        return None

    def _uom_safe_int_eq(self, a: Optional[str], b: str) -> bool:
        try:
            return int(a) == int(b)
        except (ValueError, TypeError):
            return False

    def _uom_candidates(self, item_number: str) -> List[dict[str, Any]]:
        out: List[dict[str, Any]] = []
        for e in self.uom_lookup_list:
            item_no = self._uom_get_key(e, "itemno", "ITEMNO")
            if item_no is None:
                continue
            if self._uom_safe_int_eq(item_no, item_number):
                out.append(e)
        return out

    def _uom_select(
        self, candidates: List[dict[str, Any]], packsize: str
    ) -> List[dict[str, Any]]:
        out: List[dict[str, Any]] = []
        for e in candidates:
            uom_mult = self._uom_get_key(e, "uom_mult", "UOM_MULT")
            if uom_mult is None:
                out.append(e)
                break
            if self._uom_safe_int_eq(uom_mult, packsize):
                out.append(e)
                break
        return out

    def _get_uom_query_sql(self) -> str:
        """Return the SQL query template for UOM lookup."""
        return """
            SELECT DISTINCT bubacd AS itemno,
                           bus3qt AS uom_mult,
                           buhxtx AS uom_code
            FROM dacdata.odhst odhst
            WHERE odhst.buhhnb = ?
        """
