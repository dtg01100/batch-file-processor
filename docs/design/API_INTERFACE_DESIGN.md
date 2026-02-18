# API/Interface Design Document

This document outlines the internal interfaces and protocols used within the Batch File Processor application. The application utilizes a protocol-based design to ensure loose coupling between components, facilitate dependency injection, and enable comprehensive testing through mocking.

## 1. Overview

The application employs Python's `typing.Protocol` to define structural subtyping interfaces. This approach allows any class that implements the required methods to be used as a dependency, without requiring explicit inheritance. This is particularly useful for:

*   **Dependency Injection**: Components receive their dependencies (like database connections or file system operations) at initialization, rather than instantiating them directly.
*   **Testing**: Real implementations can be easily swapped with mock objects that adhere to the same protocol, allowing for isolated unit testing.
*   **Modularity**: Different implementations of a protocol can be used interchangeably (e.g., different database backends or file transfer methods).

## 2. Backend Protocols

Defined in [`backend/protocols.py`](backend/protocols.py), these protocols abstract external client dependencies for send backends.

### `FTPClientProtocol`

Abstracts FTP client operations, typically wrapping `ftplib.FTP` or `ftplib.FTP_TLS`.

*   **`connect(host: str, port: int, timeout: Optional[float] = None) -> None`**: Connect to the FTP server.
*   **`login(user: str, password: str) -> None`**: Authenticate with the FTP server.
*   **`cwd(directory: str) -> None`**: Change the working directory on the server.
*   **`storbinary(cmd: str, fp: Any, blocksize: int = 8192) -> None`**: Store a file in binary mode.
*   **`quit() -> None`**: Send QUIT command and close connection gracefully.
*   **`close() -> None`**: Close connection unconditionally.
*   **`set_pasv(passive: bool) -> None`**: Set passive mode for data transfers.

### `SMTPClientProtocol`

Abstracts SMTP client operations, typically wrapping `smtplib.SMTP`.

*   **`connect(host: str, port: int) -> None`**: Connect to the SMTP server.
*   **`starttls() -> None`**: Upgrade connection to TLS.
*   **`login(user: str, password: str) -> None`**: Authenticate with the SMTP server.
*   **`sendmail(from_addr: str, to_addrs: list, msg: str) -> dict`**: Send an email message.
*   **`send_message(msg: Any) -> dict`**: Send an `EmailMessage` object.
*   **`quit() -> None`**: Send QUIT command and close connection gracefully.
*   **`close() -> None`**: Close connection unconditionally.
*   **`ehlo() -> None`**: Send EHLO command to server.
*   **`set_debuglevel(level: int) -> None`**: Set debug output level.

### `FileOperationsProtocol`

Abstracts file system operations for backends, typically wrapping `shutil` and `os`.

*   **`copy(src: str, dst: str) -> None`**: Copy a file.
*   **`exists(path: str) -> bool`**: Check if a path exists.
*   **`makedirs(path: str, exist_ok: bool = False) -> None`**: Create a directory and all parent directories.
*   **`remove(path: str) -> None`**: Remove a file.
*   **`rmtree(path: str) -> None`**: Remove a directory and all its contents.
*   **`basename(path: str) -> str`**: Get the base name of a path.
*   **`dirname(path: str) -> str`**: Get the directory name of a path.
*   **`join(*paths: str) -> str`**: Join path components.

## 3. Dispatch Interfaces

Defined in [`dispatch/interfaces.py`](dispatch/interfaces.py), these protocols define the main dependencies for the dispatch system.

### `DatabaseInterface`

Protocol for database operations, providing CRUD functionality.

*   **`find(**kwargs) -> list[dict]`**: Find records matching the given criteria.
*   **`find_one(**kwargs) -> Optional[dict]`**: Find a single record matching the given criteria.
*   **`insert(record: dict) -> None`**: Insert a new record.
*   **`insert_many(records: list[dict]) -> None`**: Insert multiple records.
*   **`update(record: dict, keys: list) -> None`**: Update an existing record.
*   **`count(**kwargs) -> int`**: Count records matching the given criteria.
*   **`query(sql: str) -> Any`**: Execute a raw SQL query.

### `FileSystemInterface`

Protocol for file system operations, abstracting direct access.

*   **`list_files(path: str) -> list[str]`**: List all files in a directory.
*   **`read_file(path: str) -> bytes`**: Read file contents as bytes.
*   **`read_file_text(path: str, encoding: str = 'utf-8') -> str`**: Read file contents as text.
*   **`write_file(path: str, data: bytes) -> None`**: Write bytes to a file.
*   **`write_file_text(path: str, data: str, encoding: str = 'utf-8') -> None`**: Write text to a file.
*   **`file_exists(path: str) -> bool`**: Check if a file exists.
*   **`dir_exists(path: str) -> bool`**: Check if a directory exists.
*   **`mkdir(path: str) -> None`**: Create a directory.
*   **`makedirs(path: str) -> None`**: Create a directory and all parent directories.
*   **`copy_file(src: str, dst: str) -> None`**: Copy a file.
*   **`remove_file(path: str) -> None`**: Remove a file.
*   **`get_absolute_path(path: str) -> str`**: Get the absolute path.

### `BackendInterface`

Protocol for send backends (e.g., FTP, Email, Copy).

*   **`send(params: dict, settings: dict, filename: str) -> None`**: Send a file using this backend.
*   **`validate(params: dict) -> list[str]`**: Validate backend configuration.
*   **`get_name() -> str`**: Get the backend name for logging.

### `ValidatorInterface`

Protocol for file validators.

*   **`validate(file_path: str) -> tuple[bool, list[str]]`**: Validate a file, returning validity and errors.
*   **`validate_with_warnings(file_path: str) -> tuple[bool, list[str], list[str]]`**: Validate a file, returning validity, errors, and warnings.

### `ErrorHandlerInterface`

Protocol for error handling.

*   **`record_error(folder: str, filename: str, error: Exception, context: Optional[dict] = None) -> None`**: Record an error.
*   **`get_errors() -> list[dict]`**: Get all recorded errors.
*   **`clear_errors() -> None`**: Clear all recorded errors.

### `LogInterface`

Protocol for logging operations.

*   **`write(message: str) -> None`**: Write a message to the log.
*   **`writelines(lines: list[str]) -> None`**: Write multiple lines to the log.
*   **`get_value() -> str`**: Get the current log contents.
*   **`close() -> None`**: Close the log.

## 4. UI Interfaces

Defined in [`interface/interfaces.py`](interface/interfaces.py), these protocols abstract UI components, enabling testing without actual GUI elements.

### `MessageBoxProtocol`

Abstracts message dialogs.

*   **`showinfo(title: str, message: str) -> None`**: Show an information message box.
*   **`showwarning(title: str, message: str) -> None`**: Show a warning message box.
*   **`showerror(title: str, message: str) -> None`**: Show an error message box.
*   **`askyesno(title: str, message: str) -> bool`**: Show a yes/no dialog.
*   **`askokcancel(title: str, message: str) -> bool`**: Show an ok/cancel dialog.
*   **`askyesnocancel(title: str, message: str) -> Optional[bool]`**: Show a yes/no/cancel dialog.

### `FileDialogProtocol`

Abstracts file and directory selection dialogs.

*   **`askdirectory(title: str = "Select Directory", initialdir: Optional[str] = None) -> str`**: Show a directory selection dialog.
*   **`askopenfilename(...) -> str`**: Show an open file dialog.
*   **`asksaveasfilename(...) -> str`**: Show a save file dialog.
*   **`askopenfilenames(...) -> tuple[str, ...]`**: Show an open files dialog (multiple selection).

### `WidgetProtocol`

Abstracts basic widget operations.

*   **`pack(**kwargs) -> None`**: Pack the widget.
*   **`grid(**kwargs) -> None`**: Grid the widget.
*   **`destroy() -> None`**: Destroy the widget.
*   **`update() -> None`**: Update the widget display.
*   **`update_idletasks() -> None`**: Update idle tasks.

### `TkinterProtocol`

Abstracts the main application window (root).

*   **`title(title: str) -> None`**: Set window title.
*   **`mainloop() -> None`**: Start the main event loop.
*   **`after(ms: int, func: Callable) -> str`**: Schedule a function.
*   **`after_cancel(timer_id: str) -> None`**: Cancel a scheduled function.
*   **`withdraw() -> None`**: Hide the window.
*   **`deiconify() -> None`**: Show the window.
*   **`destroy() -> None`**: Destroy the window.
*   **`update() -> None`**: Process pending events.

### `OverlayProtocol`

Abstracts overlay/loading screens.

*   **`make_overlay(parent: Any, text: str) -> None`**: Create and show the overlay.
*   **`update_overlay(parent: Any, text: str) -> None`**: Update the overlay text.
*   **`destroy_overlay() -> None`**: Destroy the overlay.

### `VariableProtocol`

Abstracts Tkinter variables (StringVar, IntVar, etc.).

*   **`get() -> Any`**: Get the variable value.
*   **`set(value: Any) -> None`**: Set the variable value.

### `EntryWidgetProtocol`

Abstracts text entry widgets.

*   **`get() -> str`**: Get the current text.
*   **`insert(index: int, text: str) -> None`**: Insert text.
*   **`delete(start: int, end: Optional[int] = None) -> None`**: Delete text.
*   **`config(**kwargs) -> None`**: Configure widget options.

### `ListboxProtocol`

Abstracts listbox widgets.

*   **`get(start: int, end: Optional[int] = None) -> tuple[str, ...]`**: Get items.
*   **`curselection() -> tuple[int, ...]`**: Get selected indices.
*   **`insert(index: int, *items: str) -> None`**: Insert items.
*   **`delete(start: int, end: Optional[int] = None) -> None`**: Delete items.
*   **`size() -> int`**: Get the number of items.

## 5. Database Interface

Defined in [`core/database/query_runner.py`](core/database/query_runner.py), this module handles database interactions.

### `DatabaseConnectionProtocol`

Abstracts the raw database connection.

*   **`execute(query: str, params: tuple = None) -> list[dict]`**: Execute a query and return results.
*   **`close() -> None`**: Close the database connection.

### `QueryRunner`

A high-level class that uses a `DatabaseConnectionProtocol` to execute queries. It is not a protocol itself but a concrete class designed for dependency injection.

*   **`__init__(connection: DatabaseConnectionProtocol)`**: Initialize with a connection object.
*   **`run_query(query: str, params: tuple = None) -> list[dict]`**: Execute a query and return results.
*   **`run_query_single(query: str, params: tuple = None) -> Optional[dict]`**: Execute a query and return a single result.
*   **`close() -> None`**: Close the underlying connection.

## 6. Dependency Injection

The application uses dependency injection to decouple components. Instead of classes creating their own dependencies, they are passed in via the constructor.

**Example: `QueryRunner`**

The `QueryRunner` class accepts any object that satisfies the `DatabaseConnectionProtocol`.

```python
# Real implementation
config = ConnectionConfig(...)
real_connection = PyODBCConnection(config)
runner = QueryRunner(real_connection)

# Mock implementation for testing
mock_connection = MockConnection()
runner = QueryRunner(mock_connection)
```

**Example: `FTPBackend`**

The `FTPBackend` (implied consumer of `FTPClientProtocol`) would accept a factory or instance that adheres to `FTPClientProtocol`, allowing tests to verify FTP operations without connecting to a real server.

This pattern is applied across the application, particularly in the `dispatch` and `interface` modules, ensuring that business logic can be tested in isolation from external systems (file system, database, network services, UI framework).
