"""
Query Runner - Optional database access wrapper.

Supports AS400 database access when JDBC is available and BATCH_PROCESSOR_DB_ENABLED is true.
Provides a NullQueryRunner fallback that returns safe defaults when DB is disabled/unavailable.
"""

import os

# Environment variable to control database access
BATCH_PROCESSOR_DB_ENABLED = (
    os.getenv("BATCH_PROCESSOR_DB_ENABLED", "true").lower() == "true"
)

try:
    import JayDeBeApi
    import jpype

    JDBC_AVAILABLE = True
except ImportError:
    JDBC_AVAILABLE = False


class NullQueryRunner:
    """
    Fallback query runner used when database is disabled or JDBC is unavailable.
    Returns safe defaults for all database operations.
    """

    def __init__(
        self,
        username: str = "",
        password: str = "",
        as400_hostname: str = "",
        driver: str = "",
    ):
        self.username = username
        self.password = password
        self.host = as400_hostname
        self.driver = driver

    def run_arbitrary_query(self, query_string):
        """Return empty list for all queries when DB is disabled."""
        return []


class query_runner:
    """
    AS400 database query runner.

    Only connects when:
    - JDBC is available
    - BATCH_PROCESSOR_DB_ENABLED environment variable is true (default)

    Otherwise, operations are no-ops that return empty results.
    """

    def __init__(
        self,
        username: str,
        password: str,
        as400_hostname: str,
        driver: str = "",
        jdbc_url: str = "",
        jdbc_driver_class: str = "",
        jdbc_jar_path: str = "",
    ):
        self.username = ""
        self.password = ""
        self.host = ""
        self.connection = None
        self.jdbc_url = jdbc_url
        self.jdbc_driver_class = jdbc_driver_class
        self.jdbc_jar_path = jdbc_jar_path

        # Only connect if DB is enabled and JDBC is available
        if JDBC_AVAILABLE and BATCH_PROCESSOR_DB_ENABLED:
            try:
                # Start JVM if not already started
                if not jpype.isJVMStarted():
                    if self.jdbc_jar_path:
                        jpype.addClassPath(self.jdbc_jar_path)
                    jpype.startJVM()

                # Create JDBC connection
                self.connection = JayDeBeApi.connect(
                    self.jdbc_url,
                    {"user": username, "password": password},
                    jars=[self.jdbc_jar_path] if self.jdbc_jar_path else [],
                    driver=self.jdbc_driver_class,
                )
            except Exception as e:
                print(f"Failed to connect via JDBC: {e}")
                self.connection = None

    def run_arbitrary_query(self, query_string):
        """Execute query and return results, or empty list if DB is disabled."""
        if self.connection is None:
            return []

        try:
            cursor = self.connection.cursor()
            query_results = cursor.execute(query_string)
            query_return_list = []
            for entry in query_results:
                query_return_list.append(entry)
            return query_return_list
        except Exception:
            # Return empty list on any database error
            return []


def is_db_available() -> bool:
    """Check if database access is available."""
    return JDBC_AVAILABLE and BATCH_PROCESSOR_DB_ENABLED


def create_query_runner(
    username: str,
    password: str,
    as400_hostname: str,
    driver: str = "",
    jdbc_url: str = "",
    jdbc_driver_class: str = "",
    jdbc_jar_path: str = "",
):
    """
    Factory function to create appropriate query runner.

    Returns NullQueryRunner if DB is disabled/unavailable, otherwise returns real query_runner.
    """
    if is_db_available():
        return query_runner(
            username,
            password,
            as400_hostname,
            driver,
            jdbc_url,
            jdbc_driver_class,
            jdbc_jar_path,
        )
    else:
        return NullQueryRunner(username, password, as400_hostname, driver)
