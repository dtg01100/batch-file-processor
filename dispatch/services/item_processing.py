"""Item processing service for EDI converters."""

import decimal

from core.constants import UPC_A_LENGTH, UPC_A_NO_CHECK_LENGTH, UPCE_LENGTH
from core.utils import (
    calc_check_digit,
    convert_to_price,
    convert_upce_to_upca,
    safe_int,
)


class ItemProcessor:
    """Service for item total calculation and UPC generation."""

    def convert_to_item_total(
        self, unit_cost: str, qty: str
    ) -> tuple[decimal.Decimal, int]:
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
        if upc_len == UPC_A_NO_CHECK_LENGTH:
            upc_string = str(proposed_upc) + str(self._calc_check_digit(proposed_upc))
        elif upc_len == UPCE_LENGTH:
            converted = convert_upce_to_upca(proposed_upc)
            upc_string = converted if isinstance(converted, str) else ""
        elif upc_len == UPC_A_LENGTH:
            upc_string = str(proposed_upc)
        else:
            upc_string = ""
        return upc_string

    def _calc_check_digit(self, upc: str) -> int:
        """Calculate UPC check digit."""
        return calc_check_digit(upc)
