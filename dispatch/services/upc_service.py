"""UPC Lookup Service for fetching and caching UPC dictionaries.

This module provides a dedicated service for fetching UPC (Universal Product Code)
dictionaries from the AS400 database. It handles:
- Database connection management
- Query execution and result parsing
- Caching to avoid redundant lookups
- Error handling with configurable strictness modes
"""

from typing import Any

from core.database import QueryRunner
from core.database.query_runner import create_query_runner_from_settings
from core.structured_logging import get_logger
from dispatch.feature_flags import get_strict_testing_mode

logger = get_logger(__name__)


class UPCLookupService:
    """Service for fetching and caching UPC dictionaries.

    This service encapsulates all logic related to UPC dictionary lookups,
    including database queries, result parsing, and error handling.

    Attributes:
        settings: Application settings dictionary
        upc_dict: Cached UPC dictionary
        _last_error: Last error message from lookup attempts

    Example:
        >>> service = UPCLookupService(settings)
        >>> upc_dict = service.get_dictionary()
        >>> if upc_dict:
        ...     print(f"Loaded {len(upc_dict)} UPC entries")

    """

    def __init__(self, settings: dict[str, Any]) -> None:
        """Initialize the UPC lookup service.

        Args:
            settings: Application settings dictionary

        """
        self.settings = settings
        self.upc_dict: dict[int, list[Any]] = {}
        self._last_error: str | None = None

    def get_dictionary(
        self,
        upc_service: Any | None = None,
        strict_db_mode: bool = False,
    ) -> dict[int, list[Any]]:
        """Get or fetch UPC dictionary.

        Attempts to fetch the UPC dictionary using the following strategy:
        1. Return cached dictionary if available
        2. Use injected upc_service if provided
        3. Fallback to direct database query

        Args:
            upc_service: Optional external UPC service to use
            strict_db_mode: If True, raise exceptions on lookup failures

        Returns:
            UPC dictionary (may be empty if initialization fails)

        Raises:
            RuntimeError: If strict_db_mode is True and lookup fails

        """
        logger.debug("Fetching UPC dictionary (cached=%s)", bool(self.upc_dict))
        strict_testing_mode = get_strict_testing_mode()
        self._last_error = None

        # Return cached dictionary if available
        if self.upc_dict:
            return self.upc_dict

        # Try external UPC service if provided
        if upc_service:
            try:
                upc_dict = upc_service.get_dictionary()
                if upc_dict:
                    self.upc_dict = upc_dict
                    logger.debug("UPC dictionary loaded: %d entries", len(upc_dict))
                    return upc_dict
            except Exception as exc:
                if strict_db_mode:
                    raise
                if strict_testing_mode:
                    raise RuntimeError(
                        "Failed to fetch UPC dictionary from upc_service"
                    ) from exc
                logger.exception("Failed to fetch UPC dictionary from upc_service")

        # Fallback to direct database query
        fallback_dict = self._fetch_from_database()
        if fallback_dict:
            self.upc_dict = fallback_dict
            logger.debug(
                "UPC dictionary loaded via fallback query: %d entries",
                len(fallback_dict),
            )
            return fallback_dict

        # UPC dictionary could not be loaded
        if self._last_error:
            logger.warning(
                "UPC dictionary is empty: fallback query failed (%s). "
                "Check AS400 host/user/password and ODBC driver settings.",
                self._last_error,
            )
        else:
            logger.warning(
                "UPC dictionary is empty: no service configured and fallback query "
                "did not return usable rows"
            )

        if strict_db_mode:
            raise RuntimeError(
                "database_lookup_mode is strict but UPC dictionary could not be loaded"
            )
        return {}

    def _fetch_from_database(self) -> dict[int, list[Any]]:
        """Fetch UPC dictionary directly from AS400 database.

        Returns:
            UPC dictionary (may be empty if lookup fails)

        """
        strict_db_mode = self._is_strict_database_lookup()
        strict_testing_mode = get_strict_testing_mode()

        if not self._validate_credentials():
            return {}

        runner = create_query_runner_from_settings(self.settings)

        try:
            return self._execute_query(
                runner,
                strict_db_mode=strict_db_mode,
                strict_testing_mode=strict_testing_mode,
            )
        except Exception as exc:
            self._handle_query_exception(
                exc,
                strict_db_mode=strict_db_mode,
                strict_testing_mode=strict_testing_mode,
            )
            return {}
        finally:
            self._close_runner(runner, strict_testing_mode=strict_testing_mode)

    def _is_strict_database_lookup(self) -> bool:
        """Check if database lookup is in strict mode.

        Returns:
            True if strict mode is enabled

        """
        mode = (
            str(self.settings.get("database_lookup_mode", "optional")).strip().lower()
        )
        return mode in {"strict", "required", "test"}

    def _validate_credentials(self) -> bool:
        """Validate AS400 credentials.

        Returns:
            True if credentials are present, False otherwise

        """
        required_keys = ("as400_username", "as400_password", "as400_address")
        missing_keys = [key for key in required_keys if not self.settings.get(key)]
        if not missing_keys:
            return True

        self._last_error = "missing AS400 settings: " + ", ".join(missing_keys)
        if self._is_strict_database_lookup():
            raise ValueError(
                "database_lookup_mode is strict but AS400 settings are missing: "
                + ", ".join(missing_keys)
            )
        logger.warning(
            "Cannot fetch UPC dictionary: missing AS400 credentials (%s)",
            ", ".join(missing_keys),
        )
        return False

    def _execute_query(
        self,
        runner: QueryRunner,
        *,
        strict_db_mode: bool,
        strict_testing_mode: bool,
    ) -> dict[int, list[Any]]:
        """Execute UPC query and parse results.

        Args:
            runner: Query runner instance
            strict_db_mode: Database strict mode flag
            strict_testing_mode: Testing strict mode flag

        Returns:
            Parsed UPC dictionary

        Raises:
            LookupError: If strict mode and query returns no rows

        """
        rows = runner.run_query("""
            select
                dsanrep.anbacd as anbacd,
                dsanrep.anbbcd as anbbcd,
                strip(dsanrep.anbgcd) as anbgcd,
                strip(dsanrep.anbhcd) as anbhcd,
                strip(dsanrep.anbicd) as anbicd,
                strip(dsanrep.anbjcd) as anbjcd
            from dacdata.dsanrep dsanrep
            """)

        if strict_db_mode and not rows:
            raise LookupError(
                "database_lookup_mode is strict but UPC query returned no rows"
            )

        if not rows:
            self._last_error = "fallback UPC query returned no rows"
            return {}

        upc_dict = self._parse_rows(rows, strict_testing_mode=strict_testing_mode)

        if strict_db_mode and rows and not upc_dict:
            raise LookupError(
                "database_lookup_mode is strict but UPC query returned no parseable rows"
            )

        if not upc_dict:
            self._last_error = (
                "fallback UPC query returned rows, but none were parseable"
            )

        return upc_dict

    def _parse_rows(
        self, rows: list[Any], *, strict_testing_mode: bool
    ) -> dict[int, list[Any]]:
        """Parse query rows into UPC dictionary.

        Supports dictionary rows (case-insensitive column names) and positional
        tuple/list rows where expected columns are in this order:
        anbacd, anbbcd, anbgcd, anbhcd, anbicd, anbjcd.

        Args:
            rows: Query result rows
            strict_testing_mode: Testing strict mode flag

        Returns:
            Parsed UPC dictionary

        Raises:
            RuntimeError: If strict mode and row parsing fails

        """
        upc_dict = {}
        for row in rows:
            try:
                if isinstance(row, dict):
                    normalized_row = {
                        str(key).strip().lower(): value for key, value in row.items()
                    }
                    item_number = int(normalized_row["anbacd"])
                    upc_dict[item_number] = [
                        normalized_row["anbbcd"],
                        normalized_row["anbgcd"],
                        normalized_row["anbhcd"],
                        normalized_row["anbicd"],
                        normalized_row["anbjcd"],
                    ]
                elif isinstance(row, (tuple, list)):
                    item_number = int(row[0])
                    upc_dict[item_number] = [row[1], row[2], row[3], row[4], row[5]]
                else:
                    raise TypeError(f"Unsupported UPC row type: {type(row).__name__}")
            except (TypeError, ValueError, KeyError, IndexError) as exc:
                if strict_testing_mode:
                    raise RuntimeError(
                        f"Malformed UPC row returned from fallback query: {row!r}"
                    ) from exc
                continue
        return upc_dict

    def _close_runner(self, runner: QueryRunner, *, strict_testing_mode: bool) -> None:
        """Close query runner.

        Args:
            runner: Query runner to close
            strict_testing_mode: Testing strict mode flag

        Raises:
            RuntimeError: If strict mode and close fails

        """
        try:
            runner.close()
        except Exception as exc:
            if strict_testing_mode:
                raise RuntimeError("Failed to close UPC query runner") from exc

    def _handle_query_exception(
        self,
        exc: Exception,
        *,
        strict_db_mode: bool,
        strict_testing_mode: bool,
    ) -> None:
        """Handle query execution exceptions.

        Args:
            exc: Exception that occurred
            strict_db_mode: Database strict mode flag
            strict_testing_mode: Testing strict mode flag

        Raises:
            Exception: Re-raised in strict modes

        """
        self._last_error = f"{type(exc).__name__}: {exc}"
        if strict_db_mode:
            raise
        if strict_testing_mode:
            if isinstance(exc, RuntimeError) and "Malformed UPC row" in str(exc):
                raise
            raise RuntimeError(
                "Failed to fetch UPC dictionary via fallback query"
            ) from exc
        logger.exception("Failed to fetch UPC dictionary via fallback query")

    @property
    def last_error(self) -> str | None:
        """Get the last error message from lookup attempts.

        Returns:
            Last error message or None if no errors

        """
        return self._last_error

    def clear_cache(self) -> None:
        """Clear the cached UPC dictionary.

        This forces a fresh lookup on the next get_dictionary() call.

        """
        self.upc_dict = {}
        logger.debug("UPC dictionary cache cleared")
