import logging
from decimal import Decimal

logger = logging.getLogger(__name__)


def dac_str_int_to_int(dacstr: str) -> int:
    if dacstr.strip() == "":
        return 0
    try:
        if dacstr.startswith("-"):
            return int(dacstr[1:]) - (int(dacstr[1:]) * 2)
        else:
            return int(dacstr)
    except ValueError:
        return 0


def convert_to_price(value):
    return (
        (value[:-2].lstrip("0") if not value[:-2].lstrip("0") == "" else "0")
        + "."
        + value[-2:]
    )


def convert_to_price_decimal(value):
    if len(value) < 2:
        return 0
    retprice = (
        (value[:-2].lstrip("0") if not value[:-2].lstrip("0") == "" else "0")
        + "."
        + value[-2:]
    )
    try:
        return Decimal(retprice)
    except Exception:
        logger.warning(
            "convert_to_price_decimal: could not convert %r to Decimal", value
        )
        return 0


def detect_invoice_is_credit(edi_process):
    from core.edi.edi_parser import capture_records

    try:
        with open(edi_process, encoding="utf-8") as work_file:  # open input file
            fields = capture_records(work_file.readline())
    except (OSError, IOError):
        logger.warning("detect_invoice_is_credit: could not open file %r", edi_process)
        return False

    if fields is None:
        logger.warning(
            "detect_invoice_is_credit: capture_records returned None for %r",
            edi_process,
        )
        return False

    if fields["record_type"] != "A":
        raise ValueError(
            "[Invoice Type Detection]: Somehow ended up in the middle of a file, this should not happen"
        )
    if dac_str_int_to_int(fields["invoice_total"]) >= 0:
        return False
    else:
        return True
