"""JDBC Query Runner

This module provides JDBC connectivity using JayDeBeApi for database queries.
This is the preferred method over ODBC due to better licensing flexibility.

Compatible with:
- IBM AS400/DB2
- PostgreSQL
- MySQL
- Oracle
- SQL Server
- And any database with JDBC drivers
"""

import logging

logger = logging.getLogger(__name__)


class JDBCQueryRunner:
    """JDBC query runner using JayDeBeApi"""

    def __init__(
        self,
        jdbc_url: str,
        username: str,
        password: str,
        driver_class: str,
        jar_path: str = None,
    ):
        """
        Initialize JDBC connection

        Args:
            jdbc_url: JDBC connection URL (e.g., "jdbc:as400://host;database=dbname")
            username: Database username
            password: Database password
            driver_class: Full Java class name of JDBC driver
            jar_path: Path to JDBC driver JAR file (optional if in classpath)

        Raises:
            ImportError: If JayDeBeApi is not installed
            Exception: If connection fails
        """
        try:
            import jpype  # Required for JayDeBeApi
            import JayDeBeApi
        except ImportError as e:
            raise ImportError(
                "JayDeBeApi or jpype not installed. "
                "Install with: pip install JayDeBeApi jpype1"
            ) from e

        self.jdbc_url = jdbc_url
        self.username = username
        self.password = password
        self.driver_class = driver_class
        self.jar_path = jar_path
        self.connection = None

        logger.info(f"Initializing JDBC connection with driver: {driver_class}")

    def connect(self):
        """Establish JDBC connection"""
        try:
            import jpype
            import JayDeBeApi

            # Start JVM if not already started
            if not jpype.isJVMStarted():
                # Add JAR to classpath if specified
                if self.jar_path:
                    jpype.addClassPath(self.jar_path)

                # Start JVM
                jpype.startJVM()

            logger.info(f"Connecting to {self.jdbc_url}...")

            # Create JDBC connection
            self.connection = JayDeBeApi.connect(
                self.jdbc_url,
                {
                    "user": self.username,
                    "password": self.password,
                },
                jars=[self.jar_path] if self.jar_path else [],
                driver=self.driver_class,
            )

            logger.info("JDBC connection established successfully")
            return True

        except Exception as e:
            logger.error(f"Failed to connect via JDBC: {e}")
            raise Exception(f"JDBC connection failed: {str(e)}")

    def execute_query(self, query: str) -> list:
        """
        Execute SQL query and return results

        Args:
            query: SQL query string

        Returns:
            List of result rows (dictionaries)

        Raises:
            Exception: If query execution fails
        """
        if not self.connection:
            self.connect()

        try:
            import JayDeBeApi

            cursor = self.connection.cursor()
            cursor.execute(query)

            # Get column names
            columns = [column[0] for column in cursor.description]

            # Fetch all results
            results = []
            for row in cursor.fetchall():
                results.append(dict(zip(columns, row)))

            logger.info(f"Query executed successfully, returned {len(results)} rows")
            return results

        except Exception as e:
            logger.error(f"Query execution failed: {e}")
            raise Exception(f"Query failed: {str(e)}")
        finally:
            if cursor:
                cursor.close()

    def execute_update(self, query: str) -> int:
        """
        Execute SQL update/insert/delete and return affected rows

        Args:
            query: SQL query string

        Returns:
            Number of affected rows

        Raises:
            Exception: If query execution fails
        """
        if not self.connection:
            self.connect()

        try:
            import JayDeBeApi

            cursor = self.connection.cursor()
            affected = cursor.execute(query)

            # Commit if not autocommit
            if not self.connection.getAutoCommit():
                self.connection.commit()

            logger.info(f"Update executed successfully, affected {affected} rows")
            return affected

        except Exception as e:
            logger.error(f"Update execution failed: {e}")
            if not self.connection.getAutoCommit():
                self.connection.rollback()
            raise Exception(f"Update failed: {str(e)}")
        finally:
            if cursor:
                cursor.close()

    def test_connection(self) -> bool:
        """
        Test JDBC connection without executing queries

        Returns:
            True if connection successful, False otherwise
        """
        try:
            self.connect()
            logger.info("JDBC connection test successful")
            return True
        except Exception as e:
            logger.error(f"JDBC connection test failed: {e}")
            return False

    def close(self):
        """Close JDBC connection"""
        if self.connection:
            try:
                self.connection.close()
                logger.info("JDBC connection closed")
            except Exception as e:
                logger.error(f"Error closing JDBC connection: {e}")

    def __enter__(self):
        """Context manager entry"""
        self.connect()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit"""
        self.close()


def create_jdbc_runner(settings: dict) -> JDBCQueryRunner:
    """
    Create JDBC runner from settings dictionary

    Args:
        settings: Settings dict with jdbc_url, jdbc_username, etc.

    Returns:
        JDBCQueryRunner instance

    Raises:
        ValueError: If required settings are missing
    """
    required_fields = [
        "jdbc_url",
        "jdbc_username",
        "jdbc_password",
        "jdbc_driver_class",
    ]
    missing = [field for field in required_fields if not settings.get(field)]

    if missing:
        raise ValueError(f"Missing required JDBC settings: {', '.join(missing)}")

    return JDBCQueryRunner(
        jdbc_url=settings["jdbc_url"],
        username=settings["jdbc_username"],
        password=settings["jdbc_password"],
        driver_class=settings["jdbc_driver_class"],
        jar_path=settings.get("jdbc_jar_path"),
    )
