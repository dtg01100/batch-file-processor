"""Database object for folder configuration management.

This module provides the DatabaseObj class which manages database connections
and table access for the batch file processor application.

The class supports dependency injection through the DatabaseConnectionProtocol,
enabling testing without actual database connections.
"""

from typing import Protocol, runtime_checkable, Optional, Any
import os
import datetime
import dataset  # type: ignore


@runtime_checkable
class DatabaseConnectionProtocol(Protocol):
    """Protocol for dataset database connection.
    
    This protocol defines the interface for database connections,
    allowing for mock implementations in tests.
    """
    
    def __getitem__(self, table_name: str) -> Any:
        """Get a table by name.
        
        Args:
            table_name: Name of the table to access
            
        Returns:
            Table object for the given name
        """
        ...
    
    def close(self) -> None:
        """Close the database connection."""
        ...


@runtime_checkable  
class TableProtocol(Protocol):
    """Protocol for database table operations."""
    
    def find_one(self, **kwargs) -> Optional[dict]:
        """Find a single record matching criteria."""
        ...
    
    def find(self, **kwargs) -> list[dict]:
        """Find all records matching criteria."""
        ...
    
    def all(self) -> list[dict]:
        """Get all records from the table."""
        ...
    
    def insert(self, record: dict) -> int:
        """Insert a new record."""
        ...
    
    def update(self, record: dict, keys: list) -> None:
        """Update an existing record."""
        ...
    
    def delete(self, **kwargs) -> None:
        """Delete records matching criteria."""
        ...
    
    def count(self, **kwargs) -> int:
        """Count records matching criteria."""
        ...
    
    def upsert(self, record: dict, keys: list) -> None:
        """Insert or update a record."""
        ...


class DatabaseObj:
    """Manages database connection and table access.
    
    Provides access to folder configurations, email queues,
    and application settings with automatic migration support.
    
    Attributes:
        folders_table: Table for folder configurations
        emails_table: Table for emails to send
        emails_table_batch: Table for batch email operations
        sent_emails_removal_queue: Queue for sent email removal
        oversight_and_defaults: Administrative settings table
        processed_files: Table for processed file tracking
        settings: Application settings table
        session_database: In-memory session database
    
    Example:
        >>> db = DatabaseObj(
        ...     database_path="/path/to/db.sqlite",
        ...     database_version="33",
        ...     config_folder="/path/to/config",
        ...     running_platform="Linux"
        ... )
        >>> folder = db.folders_table.find_one(id=1)
        >>> db.close()
    """
    
    def __init__(
        self,
        database_path: str,
        database_version: str,
        config_folder: str,
        running_platform: str,
        connection: Optional[DatabaseConnectionProtocol] = None,
        create_database_func: Optional[callable] = None,
        migrator_func: Optional[callable] = None,
        backup_func: Optional[callable] = None,
        show_error_func: Optional[callable] = None,
        show_popup_func: Optional[callable] = None,
        destroy_popup_func: Optional[callable] = None,
    ):
        """Initialize the database object.
        
        Args:
            database_path: Path to the SQLite database file
            database_version: Expected database version string
            config_folder: Path to configuration folder
            running_platform: Current platform identifier (e.g., "Linux", "Windows")
            connection: Optional injectable database connection for testing
            create_database_func: Optional function to create initial database
            migrator_func: Optional function to migrate database
            backup_func: Optional function to backup database
            show_error_func: Optional function to show error dialogs
            show_popup_func: Optional function to show popup dialogs
            destroy_popup_func: Optional function to destroy popup dialogs
        """
        self._database_path = database_path
        self._database_version = database_version
        self._config_folder = config_folder
        self._running_platform = running_platform
        self._connection = connection
        self._create_database_func = create_database_func
        self._migrator_func = migrator_func
        self._backup_func = backup_func
        self._show_error_func = show_error_func
        self._show_popup_func = show_popup_func
        self._destroy_popup_func = destroy_popup_func
        
        self.database_connection = None
        self.session_database = None
        
        # Table references (will be set during initialization)
        self.folders_table = None
        self.emails_table = None
        self.emails_table_batch = None
        self.sent_emails_removal_queue = None
        self.oversight_and_defaults = None
        self.processed_files = None
        self.settings = None
        
        if self._connection is None:
            self._initialize_connection()
        else:
            self.database_connection = self._connection
            self._initialize_tables()
    
    def _initialize_connection(self) -> None:
        """Initialize the database connection.
        
        Creates the database file if it doesn't exist, then connects
        and initializes all table references.
        """
        if not os.path.isfile(self._database_path):
            self._create_database()
        
        try:
            self.database_connection = dataset.connect(
                f"sqlite:///{self._database_path}"
            )
            self.session_database = dataset.connect("sqlite:///")
            self._check_version()
            self._initialize_tables()
        except Exception as connect_error:
            self._handle_connection_error(connect_error)
    
    def _create_database(self) -> None:
        """Create the initial database file.
        
        Uses the injected create_database_func if available,
        otherwise imports and calls the create_database module.
        """
        try:
            if self._show_popup_func:
                self._show_popup_func("Creating initial database file...")
            
            if self._create_database_func:
                self._create_database_func(
                    self._database_version,
                    self._database_path,
                    self._config_folder,
                    self._running_platform
                )
            else:
                import create_database
                create_database.do(
                    self._database_version,
                    self._database_path,
                    self._config_folder,
                    self._running_platform
                )
            
            if self._destroy_popup_func:
                self._destroy_popup_func()
        except Exception as error:
            self._handle_critical_error(error)
    
    def _check_version(self) -> None:
        """Check and handle database version compatibility.
        
        Raises:
            SystemExit: If database version is incompatible
        """
        db_version = self.database_connection["version"]
        db_version_dict = db_version.find_one(id=1)
        
        if int(db_version_dict["version"]) < int(self._database_version):
            self._upgrade_database()
        
        if int(db_version_dict["version"]) > int(self._database_version):
            if self._show_error_func:
                self._show_error_func(
                    "Error",
                    "Program version too old for database version,\r\n"
                    "please install a more recent release."
                )
            raise SystemExit("Database version too new")
        
        # Check OS compatibility
        db_version_dict = db_version.find_one(id=1)
        if db_version_dict["os"] != self._running_platform:
            if self._show_error_func:
                self._show_error_func(
                    "Error",
                    f"The operating system detected is: "
                    f'"{self._running_platform}", '
                    f"this does not match the configuration creator, which is stored as: "
                    f'"{db_version_dict["os"]}".\r\n'
                    f"Folder paths are not portable between operating systems. Exiting"
                )
            raise SystemExit("OS mismatch")
    
    def _upgrade_database(self) -> None:
        """Upgrade the database to the current version."""
        if self._show_popup_func:
            self._show_popup_func("Updating database file...")
        
        if self._backup_func:
            self._backup_func(self._database_path)
        else:
            import backup_increment
            backup_increment.do_backup(self._database_path)
        
        if self._migrator_func:
            self._migrator_func(
                self.database_connection,
                self._config_folder,
                self._running_platform
            )
        else:
            import folders_database_migrator
            folders_database_migrator.upgrade_database(
                self.database_connection,
                self._config_folder,
                self._running_platform
            )
        
        if self._destroy_popup_func:
            self._destroy_popup_func()
    
    def _initialize_tables(self) -> None:
        """Initialize table references."""
        self.folders_table = self.database_connection["folders"]
        self.emails_table = self.database_connection["emails_to_send"]
        self.emails_table_batch = self.database_connection["working_batch_emails_to_send"]
        self.sent_emails_removal_queue = self.database_connection["sent_emails_removal_queue"]
        self.oversight_and_defaults = self.database_connection["administrative"]
        self.processed_files = self.database_connection["processed_files"]
        self.settings = self.database_connection["settings"]
    
    def _handle_critical_error(self, error: Exception) -> None:
        """Handle critical errors during database operations.
        
        Args:
            error: The exception that occurred
            
        Raises:
            SystemExit: Always exits the program
        """
        try:
            print(str(error))
            with open("critical_error.log", "a", encoding="utf-8") as log_file:
                log_file.write(f"program version is {self._database_version}")
                log_file.write(f"{str(datetime.datetime.now())}{str(error)}\r\n")
            raise SystemExit from error
        except Exception as log_error:
            print(
                f"error writing critical error log for error: {str(error)}\n"
                f"operation failed with error: {str(log_error)}"
            )
            raise SystemExit from log_error
    
    def _handle_connection_error(self, error: Exception) -> None:
        """Handle connection errors.
        
        Args:
            error: The exception that occurred
            
        Raises:
            SystemExit: Always exits the program
        """
        self._handle_critical_error(error)
    
    @property
    def connection(self) -> DatabaseConnectionProtocol:
        """Get the underlying database connection.
        
        Returns:
            The database connection object
        """
        return self.database_connection
    
    def reload(self) -> None:
        """Reload the database connection.
        
        Reconnects to the database and reinitializes all table references.
        """
        try:
            self.database_connection = dataset.connect(
                f"sqlite:///{self._database_path}"
            )
            self.session_database = dataset.connect("sqlite:///")
        except Exception as connect_error:
            self._handle_connection_error(connect_error)
        
        self._initialize_tables()
    
    def close(self) -> None:
        """Close the database connection."""
        if self.database_connection:
            self.database_connection.close()
    
    def get_folder(self, folder_name: str) -> Optional[dict]:
        """Get a folder configuration by name.
        
        Args:
            folder_name: Name of the folder to find
            
        Returns:
            Folder configuration dict or None if not found
        """
        return self.folders_table.find_one(folder_name=folder_name)
    
    def get_all_folders(self) -> list[dict]:
        """Get all folder configurations.
        
        Returns:
            List of all folder configuration dicts
        """
        return list(self.folders_table.all())
    
    def get_setting(self, key: str) -> Optional[Any]:
        """Get a setting value by key.
        
        Args:
            key: Setting key to look up
            
        Returns:
            Setting value or None if not found
        """
        row = self.settings.find_one(key=key)
        return row["value"] if row else None
    
    def set_setting(self, key: str, value: Any) -> None:
        """Set a setting value.
        
        Args:
            key: Setting key
            value: Setting value
        """
        self.settings.upsert({"key": key, "value": value}, ["key"])
    
    def get_default_settings(self) -> Optional[dict]:
        """Get the default settings from administrative table.
        
        Returns:
            Default settings dict or None if not found
        """
        return self.oversight_and_defaults.find_one(id=1)
    
    def update_default_settings(self, settings: dict) -> None:
        """Update default settings.
        
        Args:
            settings: Settings dict to update
        """
        settings["id"] = 1
        self.oversight_and_defaults.update(settings, ["id"])
