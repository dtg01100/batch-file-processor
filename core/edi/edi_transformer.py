import logging
from decimal import Decimal, InvalidOperation

from core.structured_logging import get_logger, log_with_context
from core.utils.safe_parse import safe_int

logger = get_logger(__name__)


def dac_str_int_to_int(dacstr: str) -> int:
    return safe_int(dacstr)


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
    except (InvalidOperation, ValueError) as e:
        log_with_context(
            logger,
            logging.WARNING,
            "Price conversion failed",
            operation="convert_to_price_decimal",
            context={"input_value": value, "parsed_value": retprice, "error": str(e)},
        )
        return 0


def detect_invoice_is_credit(edi_process) -> bool:
    from core.edi.edi_parser import capture_records

    first_line = None
    try:
        with open(edi_process, encoding="utf-8") as work_file:  # open input file
            first_line = work_file.readline()
            fields = capture_records(first_line)
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
        if first_line and first_line[0] not in ("A", " "):
            raise ValueError(
                "EDI file does not start with A record at beginning of file"
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
