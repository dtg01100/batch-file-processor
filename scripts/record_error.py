"""Legacy error recording utility.

This module provides a backward-compatible function for recording errors
to both run logs and error logs. New code should use the ErrorHandler class
in dispatch.error_handler instead.
"""

import time
from io import StringIO
from typing import Any


def do(
    run_log: Any,
    errors_log: StringIO,
    error_message: str,
    filename: str,
    error_source: str,
    threaded: bool = False,
) -> tuple[Any, StringIO] | None:
    """Record an error message to both run log and errors log.

    Formats an error message with timestamp, source module, and filename,
    then writes it to both log destinations. In threaded mode, appends to
    lists instead of writing to file handles.

    Args:
        run_log: Run log file handle (with write method) or list for threaded mode.
        errors_log: Error log StringIO or list for threaded mode.
        error_message: The error message to record.
        filename: Name of the file being processed when the error occurred.
        error_source: Name of the module or component where the error originated.
        threaded: If True, use list append mode; if False, use write mode.

    Returns:
        Tuple of (run_log, errors_log) in threaded mode, or None in non-threaded mode.

    """

    # generate log message from input parameters
    message = (
        "At: "
        + str(time.ctime())
        + "\r\n"
        + "From module: "
        + error_source
        + "\r\n"
        + "For object: "
        + filename
        + "\r\n"
        + "Error Message is:"
        + "\r\n"
        + (str(error_message) + "\r\n\r\n")
    )
    # record error to both the run log and the errors log
    if not threaded:
        run_log.write(message.encode())
        errors_log.write(message)
    else:
        run_log.append(message)
        errors_log.append(message)
        return run_log, errors_log
