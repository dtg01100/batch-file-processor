"""Stub for 1.47 ``utils.py`` used by the routing-harness tests.

Only the functions exercised by the 1.47 dispatch / converter pipeline are
implemented. Anything not called during the routing path is intentionally
absent; calling it will raise ``AttributeError`` so we notice if the surface
changes.

The 1.47 ``utils.py`` is much larger than this stub. The full file is 313
lines; this shadow is ~80 lines and covers only the surface used by
``dispatch.py`` (see ``dispatch.py:140-520``) and the vendored converters.
"""

from __future__ import annotations

import re
from datetime import datetime, timedelta


def capture_records(line):
    """Capture records out of EDI segment line — minimal stub for split path."""
    return []


def detect_invoice_is_credit(edi_process):
    """Return False (treat as invoice, not credit) for routing tests."""
    return False


def do_split_edi(edi_process, work_directory, parameters_dict):
    """Return a single-element list -> 'do not split'. Matches the no-op branch
    in dispatch.process_files for split_edi=False."""
    return [(edi_process, "", "")]


def convert_to_price(value):
    """Format a numeric value as a price string."""
    if value is None:
        return ""
    return f"{value}"


def calc_check_digit(value):
    return 0


def convert_UPCE_to_UPCA(upce_value):
    return upce_value


def datetime_from_dactime(dac_time):
    return datetime(2000, 1, 1) + timedelta(seconds=int(dac_time or 0))


def dac_str_int_to_int(dacstr):
    return int(dacstr or 0)


def dactime_from_datetime(date_time):
    return ""


def datetime_from_invtime(invtime):
    return datetime(2000, 1, 1)


def dactime_from_invtime(inv_no):
    return ""


def do_clear_old_files(folder_path, maximum_files):
    """No-op error-log rotation stub."""
    return


def is_valid_filename(filename):
    """Pass-through permissive filename check; the harness relies on the same
    regex the vendored dispatch uses at line ~367."""
    return re.match(r"^[A-Za-z0-9. _]+$", filename or "") is not None


class invFetcher:
    """Placeholder for the 1.47 invFetcher; not exercised by routing tests."""

    def __init__(self, *args, **kwargs):
        pass


__all__ = [
    "calc_check_digit",
    "capture_records",
    "convert_UPCE_to_UPCA",
    "convert_to_price",
    "dac_str_int_to_int",
    "dactime_from_datetime",
    "dactime_from_invtime",
    "datetime_from_dactime",
    "datetime_from_invtime",
    "detect_invoice_is_credit",
    "do_clear_old_files",
    "do_split_edi",
    "invFetcher",
    "is_valid_filename",
]
