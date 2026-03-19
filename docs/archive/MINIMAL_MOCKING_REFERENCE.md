# Minimal Mocking Quick Reference

## Project Requirement

**Keep mocks and fakes to a bare minimum.** This is a core project requirement
documented in:
- `AGENTS.md` - Agent instructions
- `.github/copilot-instructions.md` - Copilot guidance
- `TESTING_BEST_PRACTICES.md` - Detailed best practices

## Quick Decision Tree

```
Need to test something?
│
├─ External service (FTP/SMTP/HTTP)?
│  └─ ✅ Mock is OK
│
├─ UI widget requiring display server?
│  └─ ✅ Mock is OK
│
├─ Expensive operation (large files, network)?
│  └─ ✅ Mock is OK
│
└─ Everything else
   └─ ❌ Use real implementation with fixtures
```

## Preferred Patterns

### ✅ DO: Real File Operations
```python
def test_file_processing(tmp_path):
    test_file = tmp_path / "input.txt"
    test_file.write_text("content")
    result = process_file(test_file)
    assert result.success
```

### ❌ DON'T: Over-Mocked Files
```python
@patch('builtins.open')
@patch('os.path.exists')
def test_file_processing(mock_exists, mock_open):
    # Too much mock setup
```

### ✅ DO: Real Database
```python
def test_queries(test_database):
    # test_database is a real SQLite connection
    insert_record(test_database, data)
    result = get_record(test_database, id)
    assert result matches data
```

### ❌ DON'T: Mocked Database
```python
@patch('sqlite3.connect')
def test_queries(mock_connect):
    mock_conn = MagicMock()
    # Mocking DB is unnecessary
```

## When Mocks Are Acceptable

| Scenario | Example | Why OK |
|----------|---------|--------|
| **External Services** | FTP, SMTP, HTTP APIs | Network dependencies |
| **UI Display** | PyQt6 widgets | Require display server |
| **Expensive Ops** | 1GB+ file processing | Performance |
| **Time-Dependent** | Scheduled tasks | Cannot wait hours/days |

## Common Fixtures

### Temporary Files
```python
def test_with_real_files(tmp_path):
    # tmp_path is pytest's built-in temp directory
    file = tmp_path / "test.txt"
    file.write_text("data")
```

### Test Database
```python
# See tests/conftest.py for database fixtures
def test_with_db(test_database):
    # Real SQLite connection, isolated per test
```

### Legacy Database Copy
```python
def test_migration(legacy_v32_db):
    # Real copy of production DB schema
    # Each test gets fresh copy
```

## Code Review Questions

Before submitting test code:

1. **Can I use a real implementation?**
   - If yes, do it
   - Use pytest fixtures for isolation

2. **Is this mock testing behavior or implementation?**
   - Behavior: Good
   - Implementation: Probably over-mocked

3. **Would this test catch real bugs?**
   - Mocks can give false confidence
   - Real implementations catch more issues

4. **Is the mock necessary?**
   - External service? ✅
   - UI component? ✅
   - Pure logic? ❌ Use real code

## Migration Examples

### Before (Over-Mocked)
```python
@patch('os.listdir')
@patch('os.path.isfile')
@patch('builtins.open')
@patch('json.load')
def test_process(mock_json, mock_open, mock_isfile, mock_listdir):
    mock_listdir.return_value = ['file1.txt', 'file2.txt']
    mock_isfile.return_value = True
    mock_open.return_value.__enter__.return_value = MagicMock()
    mock_json.load.return_value = {'key': 'value'}
    # ... 30 more lines of mock setup ...
```

### After (Real Implementation)
```python
def test_process(tmp_path):
    # Create real test files
    (tmp_path / 'file1.txt').write_text('content1')
    (tmp_path / 'file2.txt').write_text('content2')
    
    # Use real implementation
    results = process_folder(tmp_path)
    
    # Verify actual behavior
    assert len(results) == 2
    assert results[0].processed == True
```

## Benefits

✅ **More Reliable Tests** - Catch real bugs, not mock mismatches  
✅ **Less Maintenance** - No mock updates when implementation changes  
✅ **Better Confidence** - Tests mirror production behavior  
✅ **Clearer Intent** - Tests show what code does, not how it's mocked  

## Resources

- `TESTING_BEST_PRACTICES.md` - Comprehensive guide
- `tests/conftest.py` - Shared fixtures
- `tests/fixtures/` - Test data files
- `AGENTS.md` - Agent instructions
- `.github/copilot-instructions.md` - Copilot guidance
