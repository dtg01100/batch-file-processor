"""Protocol-compliant fake implementations for testing.

This module provides fake classes that implement the protocols defined in the
application, allowing tests to use real-like objects instead of MagicMocks.

Benefits over MagicMock:
1. Runtime protocol checking works correctly (isinstance() returns True)
2. Better IDE support and type checking
3. More explicit test intent
4. Catches protocol violations at test time
"""

from typing import Optional, Any, Callable
from collections.abc import Iterator


class FakeTable:
    """A fake table implementation that satisfies TableProtocol.
    
    Stores data in memory and provides all required table operations.
    Can be pre-populated with test data.
    """
    
    def __init__(self, initial_data: list[dict] | None = None):
        """Initialize the fake table with optional initial data.
        
        Args:
            initial_data: List of dicts to pre-populate the table
        """
        self._data: list[dict] = []
        self._next_id = 1
        self._call_tracker: dict[str, int] = {}
        
        if initial_data:
            for record in initial_data:
                if "id" not in record:
                    record = {**record, "id": self._next_id}
                    self._next_id += 1
                self._data.append(record.copy())
    
    def _track_call(self, method: str) -> None:
        """Track method calls for assertion purposes."""
        self._call_tracker[method] = self._call_tracker.get(method, 0) + 1
    
    def find_one(self, **kwargs) -> Optional[dict]:
        """Find a single record matching criteria."""
        self._track_call("find_one")
        for record in self._data:
            if all(record.get(k) == v for k, v in kwargs.items()):
                return record.copy()
        return None
    
    def find(self, **kwargs) -> list[dict]:
        """Find all records matching criteria."""
        self._track_call("find")
        _limit = kwargs.pop("_limit", None)
        results = []
        for record in self._data:
            if all(record.get(k) == v for k, v in kwargs.items()):
                results.append(record.copy())
        if _limit is not None:
            results = results[:_limit]
        return results
    
    def all(self) -> list[dict]:
        """Get all records from the table."""
        self._track_call("all")
        return [r.copy() for r in self._data]
    
    def insert(self, record: dict) -> int:
        """Insert a new record and return its ID."""
        self._track_call("insert")
        record = record.copy()
        if "id" not in record:
            record["id"] = self._next_id
            self._next_id += 1
        self._data.append(record)
        return record["id"]
    
    def update(self, record: dict, keys: list) -> None:
        """Update an existing record."""
        self._track_call("update")
        for i, existing in enumerate(self._data):
            if all(existing.get(k) == record.get(k) for k in keys):
                self._data[i] = {**existing, **record}
                return
    
    def delete(self, **kwargs) -> None:
        """Delete records matching criteria."""
        self._track_call("delete")
        self._data = [
            r for r in self._data
            if not all(r.get(k) == v for k, v in kwargs.items())
        ]
    
    def count(self, **kwargs) -> int:
        """Count records matching criteria."""
        self._track_call("count")
        return len(self.find(**kwargs))
    
    def upsert(self, record: dict, keys: list) -> None:
        """Insert or update a record."""
        self._track_call("upsert")
        for i, existing in enumerate(self._data):
            if all(existing.get(k) == record.get(k) for k in keys):
                self._data[i] = {**existing, **record}
                return
        self.insert(record)
    
    def distinct(self, column: str) -> list[dict]:
        """Get distinct values for a column (used in processed_files).
        
        Returns a list of dicts with the column as key, matching dataset behavior.
        """
        self._track_call("distinct")
        seen = set()
        results = []
        for record in self._data:
            if column in record:
                val = record[column]
                if val not in seen:
                    seen.add(val)
                    results.append({column: val})
        return results
    
    def reset_mock(self) -> None:
        """Reset call tracker (for compatibility with test patterns)."""
        self._call_tracker.clear()
    
    @property
    def call_count(self) -> int:
        """Total number of calls (for compatibility with test patterns)."""
        return sum(self._call_tracker.values())


class FakeConnection:
    """A fake database connection that satisfies DatabaseConnectionProtocol.
    
    Provides table access via __getitem__ and manages tables in memory.
    """
    
    def __init__(self, tables: dict[str, FakeTable] | None = None):
        """Initialize with optional pre-configured tables.
        
        Args:
            tables: Dict mapping table names to FakeTable instances
        """
        self._tables: dict[str, FakeTable] = tables or {}
        self._closed = False
        self._call_tracker: dict[str, int] = {}
    
    def _track_call(self, method: str) -> None:
        """Track method calls for assertion purposes."""
        self._call_tracker[method] = self._call_tracker.get(method, 0) + 1
    
    def __getitem__(self, table_name: str) -> FakeTable:
        """Get a table by name, creating it if it doesn't exist."""
        self._track_call(f"__getitem__:{table_name}")
        if table_name not in self._tables:
            self._tables[table_name] = FakeTable()
        return self._tables[table_name]
    
    def close(self) -> None:
        """Close the database connection."""
        self._track_call("close")
        self._closed = True
    
    @property
    def closed(self) -> bool:
        """Check if the connection is closed."""
        return self._closed
    
    def reset_mock(self) -> None:
        """Reset call tracker (for compatibility with test patterns)."""
        self._call_tracker.clear()


class FakeDatabaseObj:
    """A fake DatabaseObj that provides table access with realistic behavior.
    
    This class mimics the interface of DatabaseObj without requiring an actual
    database connection. It uses FakeTable instances for all tables.
    """
    
    def __init__(self, data: dict[str, list[dict]] | None = None):
        """Initialize with optional pre-populated data.
        
        Args:
            data: Dict mapping table names to lists of records
        """
        self._connection = FakeConnection()
        self._tables: dict[str, FakeTable] = {}
        
        # Initialize standard tables
        self.folders_table = FakeTable(data.get("folders") if data else None)
        self.emails_table = FakeTable(data.get("emails_to_send") if data else None)
        self.emails_table_batch = FakeTable(data.get("working_batch_emails_to_send") if data else None)
        self.sent_emails_removal_queue = FakeTable(data.get("sent_emails_removal_queue") if data else None)
        self.oversight_and_defaults = FakeTable(data.get("administrative") if data else None)
        self.processed_files = FakeTable(data.get("processed_files") if data else None)
        self.settings = FakeTable(data.get("settings") if data else None)
        self.session_database = FakeTable()
        
        # Version table for compatibility
        self._version_table = FakeTable([{"version": "42", "os": "Linux"}])
    
    @property
    def connection(self) -> FakeConnection:
        """Get the underlying connection."""
        return self._connection
    
    @property
    def database_connection(self) -> FakeConnection:
        """Alias for connection (for compatibility)."""
        return self._connection
    
    def get_folder(self, folder_name: str) -> Optional[dict]:
        """Get a folder by name."""
        return self.folders_table.find_one(folder_name=folder_name)
    
    def get_all_folders(self) -> list[dict]:
        """Get all folders."""
        return self.folders_table.all()
    
    def get_setting(self, key: str) -> Optional[str]:
        """Get a setting by key."""
        result = self.settings.find_one(key=key)
        return result.get("value") if result else None
    
    def set_setting(self, key: str, value: str) -> None:
        """Set a setting value."""
        self.settings.upsert({"key": key, "value": value}, ["key"])
    
    def get_default_settings(self) -> Optional[dict]:
        """Get default settings."""
        return self.oversight_and_defaults.find_one(id=1)
    
    def update_default_settings(self, settings: dict) -> None:
        """Update default settings."""
        self.oversight_and_defaults.update({**settings, "id": 1}, ["id"])
    
    def get_oversight_or_default(self) -> dict:
        """Get oversight settings or return empty dict."""
        result = self.oversight_and_defaults.find_one(id=1)
        return result if result else {}
    
    def __getitem__(self, table_name: str) -> FakeTable:
        """Get a table by name (for compatibility with dataset-like access).
        
        This allows FakeDatabaseObj to be used as a drop-in replacement
        for the raw database connection in services like ResendService.
        """
        table_map = {
            "folders": self.folders_table,
            "processed_files": self.processed_files,
            "emails_to_send": self.emails_table,
            "working_batch_emails_to_send": self.emails_table_batch,
            "sent_emails_removal_queue": self.sent_emails_removal_queue,
            "administrative": self.oversight_and_defaults,
            "settings": self.settings,
        }
        if table_name in table_map:
            return table_map[table_name]
        # Fall back to connection's __getitem__ for unknown tables
        return self._connection[table_name]
    
    def close(self) -> None:
        """Close the database connection."""
        self._connection.close()


class FakeEvent:
    """A fake Qt event for testing event handlers.
    
    Provides realistic event attributes without requiring Qt.
    """
    
    def __init__(
        self,
        x: int = 10,
        y: int = 20,
        x_root: int = 100,
        y_root: int = 200,
        num: int = 4,
        delta: int = 120,
    ):
        """Initialize the fake event with realistic defaults."""
        self.x = x
        self.y = y
        self.x_root = x_root
        self.y_root = y_root
        self.num = num
        self.delta = delta
        self.widget = FakeWidget()


class FakeWidget:
    """A fake Qt widget for testing."""
    
    def __init__(self):
        """Initialize the fake widget."""
        self._visible = True
        self._enabled = True
        self._text = ""
    
    def isVisible(self) -> bool:
        return self._visible
    
    def setVisible(self, visible: bool) -> None:
        self._visible = visible
    
    def isEnabled(self) -> bool:
        return self._enabled
    
    def setEnabled(self, enabled: bool) -> None:
        self._enabled = enabled
    
    def text(self) -> str:
        return self._text
    
    def setText(self, text: str) -> None:
        self._text = text


class FakeUIService:
    """A fake UI service that satisfies UIServiceProtocol.
    
    Records all interactions for test assertions.
    """
    
    def __init__(self):
        """Initialize the fake UI service."""
        self._calls: dict[str, list[tuple]] = {}
        self._return_values: dict[str, Any] = {
            "ask_yes_no": False,
            "ask_ok_cancel": False,
            "ask_directory": "",
            "ask_open_filename": "",
            "ask_save_filename": "",
        }
    
    def _record_call(self, method: str, *args, **kwargs) -> None:
        """Record a method call."""
        if method not in self._calls:
            self._calls[method] = []
        self._calls[method].append((args, kwargs))
    
    def set_return_value(self, method: str, value: Any) -> None:
        """Set a return value for a method."""
        self._return_values[method] = value
    
    def show_info(self, title: str, message: str) -> None:
        self._record_call("show_info", title=title, message=message)
    
    def show_error(self, title: str, message: str) -> None:
        self._record_call("show_error", title=title, message=message)
    
    def show_warning(self, title: str, message: str) -> None:
        self._record_call("show_warning", title=title, message=message)
    
    def ask_yes_no(self, title: str, message: str) -> bool:
        self._record_call("ask_yes_no", title=title, message=message)
        return self._return_values.get("ask_yes_no", False)
    
    def ask_ok_cancel(self, title: str, message: str) -> bool:
        self._record_call("ask_ok_cancel", title=title, message=message)
        return self._return_values.get("ask_ok_cancel", False)
    
    def ask_directory(self, title: str = "") -> str:
        self._record_call("ask_directory", title=title)
        return self._return_values.get("ask_directory", "")
    
    def ask_open_filename(self, title: str = "", filter: str = "") -> str:
        self._record_call("ask_open_filename", title=title, filter=filter)
        return self._return_values.get("ask_open_filename", "")
    
    def ask_save_filename(self, title: str = "", filter: str = "") -> str:
        self._record_call("ask_save_filename", title=title, filter=filter)
        return self._return_values.get("ask_save_filename", "")
    
    def pump_events(self) -> None:
        self._record_call("pump_events")
    
    def get_calls(self, method: str) -> list[tuple]:
        """Get all calls to a method."""
        return self._calls.get(method, [])
    
    def was_called(self, method: str) -> bool:
        """Check if a method was called."""
        return method in self._calls and len(self._calls[method]) > 0
    
    def reset(self) -> None:
        """Reset all recorded calls."""
        self._calls.clear()


class FakeProgressService:
    """A fake progress service that satisfies ProgressServiceProtocol."""
    
    def __init__(self):
        """Initialize the fake progress service."""
        self._visible = False
        self._message = ""
        self._calls: dict[str, list[tuple]] = {}
    
    def _record_call(self, method: str, *args, **kwargs) -> None:
        """Record a method call."""
        if method not in self._calls:
            self._calls[method] = []
        self._calls[method].append((args, kwargs))
    
    def show(self, message: str = "") -> None:
        self._record_call("show", message=message)
        self._visible = True
        self._message = message
    
    def hide(self) -> None:
        self._record_call("hide")
        self._visible = False
    
    def update_message(self, message: str) -> None:
        self._record_call("update_message", message=message)
        self._message = message
    
    def is_visible(self) -> bool:
        return self._visible
    
    def get_message(self) -> str:
        return self._message
    
    def reset(self) -> None:
        """Reset all state."""
        self._visible = False
        self._message = ""
        self._calls.clear()


class FakeMaintenanceFunctions:
    """A fake MaintenanceFunctions for testing maintenance dialogs."""
    
    def __init__(self, database_obj: FakeDatabaseObj | None = None):
        """Initialize the fake maintenance functions."""
        self._calls: dict[str, int] = {}
        self._database_obj: FakeDatabaseObj = database_obj or FakeDatabaseObj()
    
    def _track_call(self, method: str) -> None:
        """Track a method call."""
        self._calls[method] = self._calls.get(method, 0) + 1
    
    def set_all_active(self) -> None:
        self._track_call("set_all_active")
    
    def set_all_inactive(self) -> None:
        self._track_call("set_all_inactive")
    
    def clear_resend_flags(self) -> None:
        self._track_call("clear_resend_flags")
    
    def clear_processed_files_log(self) -> None:
        self._track_call("clear_processed_files_log")
    
    def remove_inactive_folders(self) -> None:
        self._track_call("remove_inactive_folders")
    
    def mark_active_as_processed(self, selected_folder=None) -> None:
        self._track_call("mark_active_as_processed")
    
    def database_import_wrapper(self, *args, **kwargs) -> None:
        """Import wrapper for database import."""
        self._track_call("database_import_wrapper")
    
    def was_called(self, method: str) -> bool:
        """Check if a method was called."""
        return self._calls.get(method, 0) > 0
    
    def call_count(self, method: str) -> int:
        """Get the number of times a method was called."""
        return self._calls.get(method, 0)
    
    def reset(self) -> None:
        """Reset all tracked calls."""
        self._calls.clear()


class FakeResendService:
    """A fake ResendService for testing resend dialogs."""
    
    def __init__(self, database_obj: FakeDatabaseObj | None = None):
        """Initialize with optional database."""
        self._database_obj = database_obj or FakeDatabaseObj()
        self._calls: dict[str, int] = {}
        self._has_processed_files = True
        self._folder_list: list[tuple[int, str]] = []
        self._files: list[dict] = []
    
    def _track_call(self, method: str) -> None:
        """Track a method call."""
        self._calls[method] = self._calls.get(method, 0) + 1
    
    def has_processed_files(self) -> bool:
        """Check if there are processed files."""
        self._track_call("has_processed_files")
        return self._has_processed_files
    
    def get_folder_list(self) -> list[tuple[int, str]]:
        """Get list of folders with processed files."""
        self._track_call("get_folder_list")
        return self._folder_list
    
    def get_files_for_folder(self, folder_id: int, limit: int = 100) -> list[dict]:
        """Get processed files for a folder."""
        self._track_call("get_files_for_folder")
        return self._files[:limit]
    
    def count_files_for_folder(self, folder_id: int) -> int:
        """Count files for a folder."""
        self._track_call("count_files_for_folder")
        return len(self._files)
    
    def set_resend_flag(self, file_id: int, flag: bool) -> None:
        """Set resend flag for a file."""
        self._track_call("set_resend_flag")
    
    def reset(self) -> None:
        """Reset all tracked calls."""
        self._calls.clear()
