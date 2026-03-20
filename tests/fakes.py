"""Protocol-compliant fake implementations for testing.

.. deprecated::
    These fakes are deprecated in favor of real implementations.
    Use real Qt widgets (with QT_QPA_PLATFORM=offscreen) and real DatabaseObj
    with temporary databases instead of these fakes.

    See:
    - tests/conftest.py for temp_database fixture
    - pytest.ini for qt marker with offscreen mode
    - tests/qt/test_qt_widgets.py for examples using real widgets

Remaining classes and migration path:
- FakeTable: Used in test_pipeline_logging_validation.py, test_gui_stress_and_edge_cases.py.
  Migrate to: Simple dict-like objects or real database tables via temp_database fixture.
- FakeDatabaseObj: Used in test_dialog_contracts_wave4.py, test_gui_stress_and_edge_cases.py.
  Migrate to: temp_database fixture from conftest.py.
- FakeMaintenanceFunctions: Used in test_maintenance_dialog_extra.py, test_dialog_contracts_wave4.py.
  Migrate to: Real MaintenanceFunctions with temp_database fixture.

This module provides fake classes that implement the protocols defined in the
application, allowing tests to use real-like objects instead of MagicMocks.
"""

import warnings
from typing import Callable, Optional

# Emit deprecation warning when this module is imported
warnings.warn(
    "tests.fakes is deprecated. Use real implementations instead: "
    "temp_database fixture for database, real Qt widgets with qtbot for UI. "
    "See tests/qt/test_qt_widgets.py for examples.",
    DeprecationWarning,
    stacklevel=2,
)


class FakeTable:
    """A fake table implementation that satisfies TableProtocol.

    .. deprecated:: Use real database via temp_database fixture instead.
    """

    def __init__(self, initial_data: list[dict] | None = None):
        warnings.warn(
            "FakeTable is deprecated. Use temp_database fixture instead.",
            DeprecationWarning,
            stacklevel=2,
        )
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
        kwargs.pop("order_by", None)  # dataset-compatible: ignore ordering
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
        if not kwargs:
            self._data = []
        else:
            self._data = [
                r
                for r in self._data
                if not all(r.get(k) == v for k, v in kwargs.items())
            ]

    def delete_all(self) -> None:
        """Delete all records from the table."""
        self._track_call("delete_all")
        self._data = []

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
        """Get distinct values for a column."""
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
        """Reset call tracker."""
        self._call_tracker.clear()

    @property
    def call_count(self) -> int:
        """Total number of calls."""
        return sum(self._call_tracker.values())


class FakeConnection:
    """A fake database connection.

    .. deprecated:: Use real database via temp_database fixture instead.
    """

    def __init__(self, tables: dict[str, FakeTable] | None = None):
        self._tables: dict[str, FakeTable] = tables or {}
        self._closed = False
        self._call_tracker: dict[str, int] = {}

    def _track_call(self, method: str) -> None:
        self._call_tracker[method] = self._call_tracker.get(method, 0) + 1

    def __getitem__(self, table_name: str) -> FakeTable:
        self._track_call(f"__getitem__:{table_name}")
        if table_name not in self._tables:
            self._tables[table_name] = FakeTable()
        return self._tables[table_name]

    def close(self) -> None:
        self._track_call("close")
        self._closed = True

    @property
    def closed(self) -> bool:
        return self._closed

    def reset_mock(self) -> None:
        self._call_tracker.clear()


class FakeDatabaseObj:
    """A fake DatabaseObj.

    .. deprecated:: Use temp_database fixture instead for real database testing.
    """

    def __init__(self, data: dict[str, list[dict]] | None = None):
        warnings.warn(
            "FakeDatabaseObj is deprecated. Use temp_database fixture instead.",
            DeprecationWarning,
            stacklevel=2,
        )
        self._connection = FakeConnection()
        self._tables: dict[str, FakeTable] = {}

        self.folders_table = FakeTable(data.get("folders") if data else None)
        self.emails_table = FakeTable(data.get("emails_to_send") if data else None)
        self.emails_table_batch = FakeTable(
            data.get("working_batch_emails_to_send") if data else None
        )
        self.sent_emails_removal_queue = FakeTable(
            data.get("sent_emails_removal_queue") if data else None
        )
        self.oversight_and_defaults = FakeTable(
            data.get("administrative") if data else None
        )
        self.processed_files = FakeTable(data.get("processed_files") if data else None)
        self.settings = FakeTable(data.get("settings") if data else None)
        self.session_database = FakeTable()
        self._version_table = FakeTable([{"version": "42", "os": "Linux"}])

    @property
    def connection(self) -> FakeConnection:
        return self._connection

    @property
    def database_connection(self) -> FakeConnection:
        return self._connection

    def get_folder(self, folder_name: str) -> Optional[dict]:
        return self.folders_table.find_one(folder_name=folder_name)

    def get_all_folders(self) -> list[dict]:
        return self.folders_table.all()

    def get_setting(self, key: str) -> Optional[str]:
        result = self.settings.find_one(key=key)
        return result.get("value") if result else None

    def set_setting(self, key: str, value: str) -> None:
        self.settings.upsert({"key": key, "value": value}, ["key"])

    def get_default_settings(self) -> Optional[dict]:
        return self.oversight_and_defaults.find_one(id=1)

    def update_default_settings(self, settings: dict) -> None:
        self.oversight_and_defaults.update({**settings, "id": 1}, ["id"])

    def get_oversight_or_default(self) -> dict:
        result = self.oversight_and_defaults.find_one(id=1)
        return result if result else {}

    def __getitem__(self, table_name: str) -> FakeTable:
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
        return self._connection[table_name]

    def close(self) -> None:
        self._connection.close()


class FakeMaintenanceFunctions:
    """A fake MaintenanceFunctions for testing maintenance dialogs.

    .. deprecated:: Use real MaintenanceFunctions with temp_database instead.
    """

    def __init__(self, database_obj: FakeDatabaseObj | None = None):
        self._calls: dict[str, int] = {}
        self._database_obj: FakeDatabaseObj = database_obj or FakeDatabaseObj()

    def _track_call(self, method: str) -> None:
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
        self._track_call("database_import_wrapper")

    def was_called(self, method: str) -> bool:
        return self._calls.get(method, 0) > 0

    def call_count(self, method: str) -> int:
        return self._calls.get(method, 0)

    def set_operation_callbacks(
        self,
        on_start: Optional[Callable[[], None]],
        on_end: Optional[Callable[[], None]],
    ) -> None:
        self._on_operation_start = on_start
        self._on_operation_end = on_end

    def get_database(self) -> "FakeDatabaseObj":
        return self._database_obj

    def reset(self) -> None:
        self._calls.clear()
