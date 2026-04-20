"""Item processing service for EDI converters."""
import decimal
from typing import Tuple

from core.utils import calc_check_digit, convert_to_price, convert_UPCE_to_UPCA, safe_int


class ItemProcessor:
    """Service for item total calculation and UPC generation."""

    def convert_to_item_total(self, unit_cost: str, qty: str) -> Tuple[decimal.Decimal, int]:
        """Calculate item total from unit cost and quantity."""
        wrkqtyint = safe_int(qty)
        try:
            item_total = decimal.Decimal(convert_to_price(unit_cost)) * wrkqtyint
        except ValueError:
            item_total = decimal.Decimal()
        except decimal.InvalidOperation:
            item_total = decimal.Decimal()
        return item_total, wrkqtyint

    def generate_full_upc(self, input_upc: str) -> str:
        """Generate a full 12-digit UPC from input."""
        input_upc = input_upc.strip()
        if not input_upc:
            return ""
        try:
            int(input_upc)
        except ValueError:
            return ""
        proposed_upc = input_upc
        upc_len = len(str(proposed_upc))
        if upc_len == 11:
            upc_string = str(proposed_upc) + str(self._calc_check_digit(proposed_upc))
        elif upc_len == 8:
            converted = convert_UPCE_to_UPCA(proposed_upc)
            upc_string = converted if isinstance(converted, str) else ""
        elif upc_len == 12:
            upc_string = str(proposed_upc)
        else:
            upc_string = ""
        return upc_string

    def _calc_check_digit(self, upc: str) -> int:
        """Calculate UPC check digit."""
        return calc_check_digit(upc)
