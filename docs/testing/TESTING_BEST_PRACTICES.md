# Testing Best Practices: Minimizing Mocks and Fakes

## Philosophy

This project follows a **"minimize mocks"** testing philosophy. The goal is to write
tests that are as close to real-world behavior as possible while maintaining speed
and isolation.

## Why Minimize Mocks?

Mocks and fakes introduce several problems:

1. **False Confidence**: Tests pass but real code fails
2. **Maintenance Burden**: Mocks must be updated when implementation changes
3. **Lost Intent**: Tests verify mock interactions rather than actual behavior
4. **Fragility**: Small refactors break many mock-based tests

## Preferred Approaches

### 1. Use Real Implementations with Isolated Fixtures

**Instead of:**
```python
@patch('os.path.exists')
@patch('builtins.open')
def test_file_processing(mock_open, mock_exists):
    mock_exists.return_value = True
    mock_open.return_value = MagicMock()
    # ... complex mock setup ...
```

**Prefer:**
```python
def test_file_processing(tmp_path):
    # Create real temporary file
    test_file = tmp_path / "test.txt"
    test_file.write_text("test content")
    
    # Use real implementation
    result = process_file(test_file)
    assert result.is_valid
```

### 2. Use In-Memory Implementations

**Instead of:**
```python
@patch('sqlite3.connect')
def test_database(mock_connect):
    mock_conn = MagicMock()
    mock_connect.return_value = mock_conn
    # ... mock cursor, execute, fetchall ...
```

**Prefer:**
```python
def test_database(tmp_path):
    # Use real in-memory SQLite
    db_path = tmp_path / "test.db"
    conn = sqlite3.connect(str(db_path))
    create_schema(conn)
    
    # Test with real database
    insert_record(conn, {"id": 1, "name": "test"})
    result = get_record(conn, 1)
    assert result.name == "test"
```

### 3. Integration Tests Over Mocked Unit Tests

**Instead of:**
```python
@patch('backend.ftp_backend.FTP')
def test_ftp_upload(mock_ftp_class):
    mock_ftp = MagicMock()
    mock_ftp_class.return_value = mock_ftp
    # ... mock storbinary, quit, etc ...
```

**Prefer:**
```python
def test_ftp_upload_integration():
    # Use a real test FTP server (e.g., pyftpdlib in test fixture)
    # Or use a backend that supports dry-run mode
    backend = FTPBackend(host="test.local", dry_run=True)
    result = backend.upload(file_path, remote_path)
    assert result.success
```

## When Mocks Are Acceptable

### 1. External Services (FTP, SMTP, HTTP)

```python
def test_smtp_backend_with_mock():
    # SMTP requires network connection - mock is appropriate
    mock_smtp = MagicMock()
    backend = SMTPBackend(smtp_client=mock_smtp)
    backend.send_email(...)
    mock_smtp.sendmail.assert_called_once()
```

### 2. UI Display Servers (PyQt5, Tkinter)

```python
def test_dialog_logic_without_display():
    # PyQt5 widgets require display server - mock for unit tests
    mock_parent = MagicMock()
    dialog = EditFolderDialog(parent=mock_parent, folder_config=config)
    # Test dialog logic without actual widget rendering
    assert dialog.validate() == True
```

### 3. Truly Expensive Operations

```python
def test_large_file_processing():
    # Processing 1GB files is too slow for tests
    mock_file = MagicMock()
    mock_file.size = 1024 * 1024 * 1024  # 1GB
    result = process_large_file(mock_file)
    assert result.chunks > 0
```

## Test Fixture Patterns

### Temporary Directory Fixture

```python
@pytest.fixture
def temp_workspace(tmp_path):
    """Create a temporary workspace with test files."""
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    
    # Create realistic test file structure
    input_dir = workspace / "input"
    input_dir.mkdir()
    (input_dir / "test.edi").write_text("A-record...")
    
    output_dir = workspace / "output"
    output_dir.mkdir()
    
    return workspace
```

### Test Database Fixture

```python
@pytest.fixture
def test_database(tmp_path):
    """Create a real test database with schema."""
    db_path = tmp_path / "test.db"
    conn = sqlite3.connect(str(db_path))
    
    # Create real schema
    schema.ensure_schema(conn)
    
    yield conn
    
    conn.close()
```

### Real Backend with Dry-Run Mode

```python
@pytest.fixture
def dry_run_ftp_backend():
    """Create FTP backend in dry-run mode (no network calls)."""
    return FTPBackend(
        host="localhost",
        username="test",
        password="test",
        dry_run=True  # Records calls without network
    )
```

## Code Review Checklist

When reviewing test code, ask:

- [ ] Could this test use a real implementation instead of a mock?
- [ ] Is this mock testing implementation details rather than behavior?
- [ ] Would an integration test be more appropriate here?
- [ ] Is this mock necessary (external service, UI, expensive operation)?
- [ ] Are we mocking too much and losing test value?

## Migration Strategy

If you encounter heavily mocked tests:

1. **Identify the boundary**: What's being mocked and why?
2. **Check if real is feasible**: Can we use a real implementation?
3. **Create fixture**: Build a pytest fixture for the real implementation
4. **Incremental refactor**: Update one test at a time
5. **Verify behavior**: Ensure refactored tests still catch bugs

## Examples from This Codebase

### Good: Real Database with Temp Copy

```python
@pytest.fixture
def legacy_v32_db(tmp_path):
    """Copy the real legacy v32 database to a temp directory."""
    if not LEGACY_DB_PATH.exists():
        pytest.skip("Legacy v32 database fixture not found")
    dest = str(tmp_path / "folders.db")
    shutil.copy2(LEGACY_DB_PATH, dest)
    return dest
```

### Good: Fake Event Object (Not Mock)

```python
@dataclass
class FakeEvent:
    """A minimal fake event object for testing event handlers."""
    x: int
    y: int
    x_root: int
    y_root: int
    num: int
    delta: int
```

### Avoid: Over-Mocked File Operations

```python
# ❌ Too many mocks - test is fragile
@patch('os.listdir')
@patch('os.path.isfile')
@patch('builtins.open')
@patch('json.load')
def test_process_files(mock_json, mock_open, mock_isfile, mock_listdir):
    # ... 50 lines of mock setup ...
```

### Prefer: Real File Operations with Temp Files

```python
# ✅ Real file operations - test is robust
def test_process_files(tmp_path):
    # Create real test files
    (tmp_path / "file1.edi").write_text("A-record...")
    (tmp_path / "file2.edi").write_text("A-record...")
    
    # Use real implementation
    results = process_folder(tmp_path)
    assert len(results) == 2
```

## Summary

**Goal:** Write tests that give you confidence the code works in production.

**Strategy:** Use real implementations whenever possible, mock only when necessary.

**Benefit:** More reliable tests, less maintenance, better bug detection.
