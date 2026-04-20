"""Database connector service for EDI converters."""
from typing import Any

from core.database import QueryRunner
from core.structured_logging import get_logger

logger = get_logger(__name__)


class DatabaseConnector:
    """Service for managing database connections for converters."""

    def __init__(self):
        """Initialize the database connector."""
        self._query_runner: QueryRunner | None = None
        self._db_initialized: bool = False

    @property
    def query_runner(self) -> QueryRunner | None:
        """Get the query runner."""
        return self._query_runner

    @property
    def is_initialized(self) -> bool:
        """Check if database connection is initialized."""
        return self._db_initialized

    def init_connection(
        self,
        settings_dict: dict[str, Any],
        database: str = "QGPL",
        required_keys: tuple[str, ...] = (
            "as400_username",
            "as400_address",
        ),
    ) -> None:
        """Initialize the database connection.

        Args:
            settings_dict: Dictionary containing database connection settings
            database: Database name (default: QGPL)
            required_keys: Tuple of required settings keys

        """
        if self._db_initialized:
            return

        missing_keys = [
            key
            for key in required_keys
            if key not in settings_dict or not settings_dict[key]
        ]
        if missing_keys:
            raise ValueError(
                f"Missing required database settings: {', '.join(missing_keys)}"
            )

        ssh_key_filename = settings_dict.get("ssh_key_filename", "").strip() or None
        as400_password = settings_dict.get("as400_password", "").strip() or None
        if not (as400_password or ssh_key_filename):
            raise ValueError(
                "Either as400_password or ssh_key_filename must be provided"
            )

        self.ssh_key_filename = ssh_key_filename
        self.as400_password = as400_password

        from core.database.query_runner import create_query_runner_from_settings

        self._query_runner = create_query_runner_from_settings(
            settings_dict, database=database
        )
        self._db_initialized = True
        logger.debug(
            "Database connection initialized (ssh_key_filename=%s)",
            ssh_key_filename,
        )

    def close(self) -> None:
        """Close the database connection if open."""
        if self._query_runner is not None:
            try:
                self._query_runner.close()
                logger.debug("Database connection closed")
            except AttributeError:
                pass
            self._query_runner = None
            self._db_initialized = False
