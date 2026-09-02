"""Typed EDI records (Phase 11.1).

The legacy ``capture_records`` returns ``dict[str, str]`` because
the parser uses string-key dispatch internally. Phase 11.1 wraps
that dict in a typed dataclass (``ARecord`` / ``BRecord`` /
``CRecord``) and exposes both attribute access
(``record.invoice_number``) and dict-style access
(``record["invoice_number"]``) so converters can migrate one at a
time.

The dict-style access uses ``__getitem__`` on the dataclass
itself, so legacy code that does ``record.fields["x"]`` keeps
working — but `record.fields` is now the typed dataclass, not a
plain dict. Code that does ``record.fields["x"] = "y"`` would
fail (frozen dataclass); the migration to attribute access
catches that at the test boundary.

The dataclasses are imported from ``core.edi.edi_parser`` where
they already exist.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Union

from core.edi.edi_parser import ARecord, BRecord, CRecord


@dataclass
class TypedRecordProxy:
    """Wraps a typed EDI record dataclass with dict-style access.

    ``record.invoice_number`` works (attribute access on the
    underlying dataclass). ``record["invoice_number"]`` also works
    (this proxy's ``__getitem__`` forwards to
    ``getattr(self._record, key)``).

    The proxy itself doesn't carry field types — those live on the
    wrapped dataclass. The proxy is a thin facade for the
    migration window where some converters still use
    ``record.fields["key"]`` and others use
    ``record.fields.key``.
    """

    record: Union[ARecord, BRecord, CRecord]

    def __getitem__(self, key: str) -> Any:
        return getattr(self.record, key)

    def __getattr__(self, name: str) -> Any:
        # Forward attribute access to the wrapped record. Only called
        # when the attribute isn't found on the proxy itself (Python's
        # attribute lookup falls back to __getattr__).
        return getattr(self.record, name)

    def __contains__(self, key: str) -> bool:
        return hasattr(self.record, key)

    def get(self, key: str, default: Any = None) -> Any:
        return getattr(self.record, key, default)

    def keys(self):
        return self.record.__dataclass_fields__.keys()

    def values(self):
        return (getattr(self.record, k) for k in self.record.__dataclass_fields__)

    def items(self):
        return (
            (k, getattr(self.record, k)) for k in self.record.__dataclass_fields__
        )


def parse_typed_record(record_dict: dict) -> TypedRecordProxy:
    """Convert a legacy ``capture_records`` dict into a typed proxy.

    Args:
        record_dict: The dict returned by ``core.edi.edi_parser.capture_records``.

    Returns:
        A ``TypedRecordProxy`` wrapping the appropriate dataclass.

    Raises:
        ValueError: If ``record_dict`` is missing ``record_type`` or
            the type is unknown.

    """
    record_type = record_dict.get("record_type")
    if record_type == "A":
        typed = ARecord(
            record_type="A",
            cust_vendor=record_dict.get("cust_vendor", ""),
            invoice_number=record_dict.get("invoice_number", ""),
            invoice_date=record_dict.get("invoice_date", ""),
            invoice_total=record_dict.get("invoice_total", ""),
        )
    elif record_type == "B":
        typed = BRecord(
            record_type="B",
            upc_number=record_dict.get("upc_number", ""),
            description=record_dict.get("description", ""),
            vendor_item=record_dict.get("vendor_item", ""),
            unit_cost=record_dict.get("unit_cost", ""),
            combo_code=record_dict.get("combo_code", ""),
            unit_multiplier=record_dict.get("unit_multiplier", ""),
            qty_of_units=record_dict.get("qty_of_units", ""),
            suggested_retail_price=record_dict.get(
                "suggested_retail_price", ""
            ),
            price_multi_pack=record_dict.get("price_multi_pack", ""),
            parent_item_number=record_dict.get("parent_item_number", ""),
        )
    elif record_type == "C":
        typed = CRecord(
            record_type="C",
            charge_type=record_dict.get("charge_type", ""),
            description=record_dict.get("description", ""),
            amount=record_dict.get("amount", ""),
        )
    else:
        raise ValueError(f"Unknown record_type: {record_type!r}")
    return TypedRecordProxy(record=typed)
