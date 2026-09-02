"""X12 810 (Invoice) outbound converter.

Generates an ASC X12 004010 810 transaction set from the internal
EDI process dict (A/B/C records). The internal parser is unchanged
- this converter is one-way: internal EDI -> X12 810 envelope.

Envelope layout:

    ISA*00*          *00*          *ZZ*<sender>*ZZ*<receiver>*<YYMMDD>*<HHMM>*U*00401*<ctrl>*0*P*:~
    GS*IN*<sender>*<receiver>*<YYMMDD>*<HHMM>*<gs_ctrl>*X*004010~
    ST*810*<st_ctrl>~
    BIG*<YYYYMMDD>*<invoice_number>~
    N1*BT*<bill_to_name>~
    IT1*<seq>*<qty>*UN*<unit_price>*UP*<upc>*VP*<vendor_item>~
    TDS*<total_dollars>~
    CTT*<line_count>~
    SE*<seg_count>*<st_ctrl>~
    GE*1*<gs_ctrl>~
    IEA*1*<isa_ctrl>~

Parameters (parameters_dict):
    x810_sender_id   - 15-char sender ID (required)
    x810_receiver_id - 15-char receiver ID (required)
    x810_bill_to_name - N1*BT entity name (optional, default "")
    x810_isa_control - ISA13, 9 digits (optional, default auto)
    x810_gs_control  - GS06, 1-9 digits (optional, default auto)
    x810_st_control  - ST02, 4-9 digits (optional, default auto)

Element separator: '*'. Sub-element separator: '>'. Segment
terminator: '~'.
"""

CONVERTER_METADATA = {
    "format_name": "x810",
    "display_name": "X12 810 (Invoice)",
    "description": "Emit an ASC X12 004010 810 invoice envelope from internal EDI.",
    "module_name": "dispatch.converters.convert_to_x810",
}


import logging
import time
from datetime import datetime, timezone

from core import utils
from core.structured_logging import get_logger
from dispatch.converters.convert_base import (
    BaseEDIConverter,
    ConversionContext,
    EDIRecord,
    make_edi_convert,
    normalize_parameter,
)

logger = get_logger(__name__)


_ELEMENT = "*"
_SUBELEMENT = ">"
_TERMINATOR = "~"
_BLANK15 = " " * 15


def _pad(value: str, width: int) -> str:
    return (value or "")[:width].ljust(width)


def _to_yymmdd(s: str) -> str:
    if not s or len(s) != 6:
        return datetime.now(tz=timezone.utc).strftime("%y%m%d")
    return s


def _to_yyyymmdd(s: str) -> str:
    if not s or len(s) != 6:
        return datetime.now(tz=timezone.utc).strftime("%Y%m%d")
    try:
        return f"20{s[4:6]}{s[0:2]}{s[2:4]}"
    except (IndexError, ValueError):
        return datetime.now(tz=timezone.utc).strftime("%Y%m%d")


def _format_time() -> str:
    return datetime.now(tz=timezone.utc).strftime("%H%M")


def _gen_control(seed: str, prefix: str, width: int) -> str:
    base = f"{prefix}{int(time.time() * 1000) % (10 ** (width - len(prefix)))}"
    return base[-width:].zfill(width)


class X810Converter(BaseEDIConverter):
    """Converter for X12 004010 810 (Invoice) envelopes."""

    def _initialize_output(self, context: ConversionContext) -> None:
        params = context.parameters_dict
        missing = [
            k
            for k in ("x810_sender_id", "x810_receiver_id")
            if not params.get(k)
        ]
        if missing:
            raise ValueError(
                f"x810 converter missing required parameters: {', '.join(missing)}"
            )

        sender = _pad(params["x810_sender_id"], 15)
        receiver = _pad(params["x810_receiver_id"], 15)
        bill_to = params.get("x810_bill_to_name", "") or ""

        isa_ctrl = params.get("x810_isa_control") or _gen_control(
            sender + receiver, "1", 9
        )
        gs_ctrl = params.get("x810_gs_control") or isa_ctrl[-9:].lstrip("0") or "1"
        st_ctrl = params.get("x810_st_control") or (gs_ctrl or "1").rjust(4, "0")[:9]

        context.user_data["sender"] = sender
        context.user_data["receiver"] = receiver
        context.user_data["bill_to"] = bill_to
        context.user_data["isa_ctrl"] = str(isa_ctrl).zfill(9)[:9]
        context.user_data["gs_ctrl"] = str(gs_ctrl)[:9]
        context.user_data["st_ctrl"] = str(st_ctrl)[:9]
        context.user_data["yymmdd"] = datetime.now(tz=timezone.utc).strftime("%y%m%d")
        context.user_data["hhmm"] = _format_time()
        context.user_data["yyyymmdd"] = datetime.now(tz=timezone.utc).strftime("%Y%m%d")
        context.user_data["line_count"] = 0
        context.user_data["total_cents"] = 0

        context.output_file = open(  # noqa: SIM115 - lifecycle managed by base class
            context.get_output_path(".810"), "w", encoding="utf-8", newline=""
        )

    def process_a_record(self, record: EDIRecord, context: ConversionContext) -> None:
        fields = record.fields
        super().process_a_record(record, context)

        a_date = fields.get("invoice_date", "")
        yyyymmdd = _to_yyyymmdd(a_date)
        context.user_data["yyyymmdd"] = yyyymmdd

        try:
            total_cents = int(fields.get("invoice_total", "0") or "0")
        except (TypeError, ValueError):
            logger.debug(
                "x810: unparseable invoice_total %r, defaulting to 0",
                fields.get("invoice_total"),
            )
            total_cents = 0
        context.user_data["total_cents"] = total_cents

    def process_b_record(self, record: EDIRecord, context: ConversionContext) -> None:
        fields = record.fields

        try:
            unit_cost_cents = int(fields.get("unit_cost", "0") or "0")
            unit_price_dollars = unit_cost_cents / 100.0
        except (TypeError, ValueError):
            unit_price_dollars = 0.0

        try:
            qty_units = int(fields.get("qty_of_units", "0") or "0")
            unit_mult = int(fields.get("unit_multiplier", "1") or "1")
            qty = qty_units * (unit_mult if unit_mult > 0 else 1)
        except (TypeError, ValueError):
            qty = 0

        upc = (fields.get("upc_number") or "").strip()
        if upc and len(upc) < 12:
            upc = upc.zfill(12)
        vendor_item = (fields.get("vendor_item") or "").strip()

        user_data = context.user_data
        user_data["line_count"] += 1
        seq = user_data["line_count"]

        line = _ELEMENT.join(
            [
                "IT1",
                str(seq),
                str(qty),
                "UN",
                f"{unit_price_dollars:.2f}",
                "UP",
                upc,
                "VP",
                vendor_item,
            ]
        )
        user_data.setdefault("it1_lines", []).append(line)

    def process_c_record(self, record: EDIRecord, context: ConversionContext) -> None:
        return

    def _finalize_output(self, context: ConversionContext) -> None:
        user_data = context.user_data
        arec = context.arec_header or {}

        invoice_number = (arec.get("invoice_number") or "").strip()
        total_dollars = user_data["total_cents"] / 100.0
        line_count = user_data["line_count"]

        segments: list[str] = []

        segments.append(
            _ELEMENT.join(
                [
                    "ISA",
                    "00",
                    _BLANK15,
                    "00",
                    _BLANK15,
                    "ZZ",
                    user_data["sender"],
                    "ZZ",
                    user_data["receiver"],
                    user_data["yymmdd"],
                    user_data["hhmm"],
                    "U",
                    "00401",
                    user_data["isa_ctrl"],
                    "0",
                    "P",
                    ":",
                ]
            )
        )

        segments.append(
            _ELEMENT.join(
                [
                    "GS",
                    "IN",
                    user_data["sender"].strip(),
                    user_data["receiver"].strip(),
                    user_data["yymmdd"],
                    user_data["hhmm"],
                    user_data["gs_ctrl"],
                    "X",
                    "004010",
                ]
            )
        )

        segments.append(
            _ELEMENT.join(["ST", "810", user_data["st_ctrl"]])
        )

        segments.append(
            _ELEMENT.join(["BIG", user_data["yyyymmdd"], invoice_number])
        )

        if user_data["bill_to"]:
            segments.append(
                _ELEMENT.join(["N1", "BT", user_data["bill_to"]])
            )

        segments.extend(user_data.get("it1_lines", []))

        segments.append(
            _ELEMENT.join(["TDS", f"{int(total_dollars):010d}"])
        )

        segments.append(
            _ELEMENT.join(["CTT", str(line_count)])
        )

        st_seg_count = sum(
            1
            for s in segments
            if not s.startswith("ISA") and not s.startswith("GS")
            and not s.startswith("GE") and not s.startswith("IEA")
        )
        st_seg_count += 3

        segments.append(
            _ELEMENT.join(["SE", str(st_seg_count), user_data["st_ctrl"]])
        )
        segments.append(
            _ELEMENT.join(["GE", "1", user_data["gs_ctrl"]])
        )
        segments.append(
            _ELEMENT.join(["IEA", "1", user_data["isa_ctrl"]])
        )

        output_file = context.output_file
        assert output_file is not None
        envelope = "\n".join(s + _TERMINATOR for s in segments) + "\n"
        output_file.write(envelope)

        super()._finalize_output(context)

    def _get_return_value(self, context: ConversionContext) -> str:
        return context.get_output_path(".810")


edi_convert = make_edi_convert(X810Converter)
