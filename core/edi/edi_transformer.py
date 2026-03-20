import logging
from decimal import Decimal

from core.structured_logging import get_logger, log_with_context

logger = get_logger(__name__)


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
        log_with_context(
            logger,
            logging.WARNING,
            "Price conversion failed",
            operation="convert_to_price_decimal",
            context={"input_value": value, "parsed_value": retprice},
        )
        return 0


def detect_invoice_is_credit(edi_process):
    from core.edi.edi_parser import capture_records

    try:
        with open(edi_process, encoding="utf-8") as work_file:  # open input file
            fields = capture_records(work_file.readline())
    except (OSError, IOError) as e:
        log_with_context(
            logger,
            logging.WARNING,
            "Credit detection failed - file error",
            operation="detect_invoice_is_credit",
            context={"file_path": edi_process, "error_type": type(e).__name__},
        )
        return False

    if fields is None:
        log_with_context(
            logger,
            logging.WARNING,
            "Credit detection failed - no fields parsed",
            operation="detect_invoice_is_credit",
            context={"file_path": edi_process},
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
