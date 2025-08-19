"""business_logic.errors

Small set of application-specific exceptions and helpers for consistent formatting.

Provides:
- ApplicationError: base class for user-facing errors
- DatabaseError, ValidationError: common specialized errors
- format_exception(exc): concise single-line summary for user display
- detailed_trace(exc): full traceback string for logging
"""
from __future__ import annotations

from typing import Type
import traceback


class ApplicationError(Exception):
    """Base class for application-level errors that may be presented to users."""

    pass


class DatabaseError(ApplicationError):
    """Raised for database related issues."""

    pass


class ValidationError(ApplicationError):
    """Raised when input validation fails."""

    pass


def format_exception(exc: BaseException) -> str:
    """Return a concise single-line string describing an exception.

    Format: "<ExceptionType>: <message>"
    Intended for user-facing short messages (no traceback).
    """
    exc_type: Type[BaseException] = type(exc)
    message = str(exc) or "<no message>"
    return f"{exc_type.__name__}: {message}"


def detailed_trace(exc: BaseException) -> str:
    """Return a detailed traceback string suitable for logging.

    Includes the full formatted traceback produced by traceback.format_exc().
    """
    return "".join(traceback.format_exception(type(exc), exc, exc.__traceback__))