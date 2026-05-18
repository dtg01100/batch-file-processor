# Error Handling Design Document

**Version:** 1.0  
**Date:** 2026-05-18  
**Status:** DRAFT

---

## 1. Overview

The error handling system provides logging, error recording, and report generation capabilities.

## 2. Core Components

### 2.1 record_error.do() — Legacy

**Module:** `scripts/record_error.py`

Legacy error logging wrapper. Delegates to `python_utilities.loudlogger.do()`.

```python
def do(
    run_log: csv.DictWriter,
    errors_log: io.StringIO,
    error_message: str,
    filename: str,
    module: str,
) -> None:
    """Record error to run log and errors log buffer.

    Note: ``ErrorLogger.log_error()`` in `dispatch/error_handler.py`
    wraps this call.  New code should call ``ErrorHandler.record_error()``
    which delegates to it indirectly.
    """
```

### 2.2 ErrorHandler

**Module:** `dispatch/error_handler.py`

Central error management — records to log file, database, in-memory buffer, and alerts:

```python
class ErrorHandler:
    def __init__(
        self,
        errors_folder: str | None = None,
        run_log: RunLog | None = None,
        run_log_directory: str | None = None,
        database: DatabaseInterface | None = None,
        log_path: str | None = None,
        file_system: FileSystemInterface | None = None,
        alert_dispatcher: Any = None,
    ) -> None:

    def record_error(
        self,
        folder: str,
        filename: str,
        error: Exception,
        context: dict | None = None,
        error_source: str = "Dispatch",
    ) -> None:
        """Record an error to all configured destinations."""

    def get_errors(self) -> list[dict]: ...
    def get_error_log(self) -> str: ...
    def clear_errors(self) -> None: ...
    def has_errors(self) -> bool: ...
```

`ErrorHandler` creates an `ErrorLogger` internally for legacy logging:

```python
# dispatch/error_handler.py
class ErrorHandler:
    def __init__(self, ...):
        ...
        self.logger = ErrorLogger(self.errors_folder, self.run_log)
        self.report_generator = ReportGenerator()
```

### 2.3 ErrorLogger — Legacy Logger

**Module:** `dispatch/error_handler.py`

Legacy thin wrapper over `scripts/record_error.do()`.  Kept for backward
compatibility but new code should use `ErrorHandler.record_error()` instead.

```python
class ErrorLogger:
    def __init__(self, errors_folder: str = "", run_log: RunLog | None = None): ...

    def log_error(self, error_message: str, filename: str, module: str) -> None:
        """Delegate to scripts/record_error.do()."""

    def log_folder_error(self, error_message: str, folder_name: str,
                         module: str = "Dispatch") -> None: ...
    def log_file_error(self, error_message: str, filename: str,
                       module: str = "Dispatch") -> None: ...
    def get_errors(self) -> str: ...
    def has_errors(self) -> bool: ...
    def close(self) -> None: ...
```

## 3. Error Flow

```
1. Exception raised in processing
      ↓
2. Exception caught at pipeline level
      ↓
3. ErrorHandler.record_error() called
      ↓
4. Error logged to file (record_error.do)
      ↓
5. Error buffered for UI display
      ↓
6. Error email sent (if configured)
      ↓
7. Processing continues with next file
```

## 4. Error Categories

| Category | Handling |
|----------|----------|
| ValidationError | Log, skip file, continue |
| ConversionError | Log, skip file, continue |
| SendError | Log, retry if enabled |
| DatabaseError | Log, pause processing |
| ConfigurationError | Log, abort folder |

## 5. Error Report Generation

**Module:** `dispatch/error_handler.py`

`ErrorHandler` delegates report generation to `ReportGenerator`:

```python
class ReportGenerator:
    """Generates simple text-based validation and processing error reports."""

    def generate_edi_validation_report(errors: str) -> str:
        """Generate ASCII error report from EDI validation errors string."""

    def generate_processing_report(errors: str, version: str) -> str:
        """Generate ASCII error report from processing errors string."""
```

`ErrorHandler` exposes these as:
```
error_handler.write_validation_report(errors: str) -> str
error_handler.write_processing_report(errors: str, version: str) -> str
```

## 6. Logging Integration

```python
# Use structured logging for error context
logger.error(
    "Backend send failed",
    exc_info=True,
    extra={
        "folder_alias": folder_config.alias,
        "backend_type": backend_type,
        "file_path": file_path,
    }
)
```

## 7. Related Documents

- [DATA_FLOW.md](DATA_FLOW.md) - Data flow
- [SYSTEM_OVERVIEW.md](SYSTEM_OVERVIEW.md) - Architecture
