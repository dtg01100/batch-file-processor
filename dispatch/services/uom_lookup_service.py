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

        def get_key(entry: dict, *keys: str) -> Optional[str]:
            """Case-insensitive key lookup."""
            for key in keys:
                for k, v in entry.items():
                    if k.upper() == key.upper():
                        return v
                for k, v in entry.items():
                    if k.lower() == key.lower():
                        return v
            return None

        stage_1_list = []
        stage_2_list = []

        for entry in self.uom_lookup_list:
            item_no = get_key(entry, "itemno", "ITEMNO")
            if item_no is None:
                continue
            try:
                if int(item_no) == int(item_number):
                    stage_1_list.append(entry)
            except (ValueError, TypeError):
                continue

        for entry in stage_1_list:
            uom_mult = get_key(entry, "uom_mult", "UOM_MULT")
            if uom_mult is None:
                stage_2_list.append(entry)
                break
            try:
                if int(uom_mult) == int(packsize):
                    stage_2_list.append(entry)
            except (ValueError, TypeError):
                stage_2_list.append(entry)
                break

        try:
            uom_code = get_key(stage_2_list[0], "uom_code", "UOM_CODE")
            return uom_code if uom_code else "?"
        except IndexError:
            return "?"

    def _get_uom_query_sql(self) -> str:
        """Return the SQL query template for UOM lookup."""
        return """
            SELECT DISTINCT bubacd AS itemno,
                           bus3qt AS uom_mult,
                           buhxtx AS uom_code
            FROM dacdata.odhst odhst
            WHERE odhst.buhhnb = ?
        """
