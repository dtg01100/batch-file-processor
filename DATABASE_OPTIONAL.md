# Database Access - Optional Configuration

## Overview
Database access can be disabled to allow local testing and development without AS400/ODBC connection. This is useful for:
- Running tests without database
- Developing on machines without ODBC libraries
- Continuous integration environments without AS400 access

## Environment Variable

Set `BATCH_PROCESSOR_DB_ENABLED` to control database access:

```bash
# Disable database access (default for tests)
export BATCH_PROCESSOR_DB_ENABLED=false

# Enable database access
export BATCH_PROCESSOR_DB_ENABLED=true
```

## How It Works

### Query Runner (`query_runner.py`)
- Detects if `pyodbc` is available
- Checks `BATCH_PROCESSOR_DB_ENABLED` environment variable
- When disabled/unavailable, uses `NullQueryRunner` that returns empty results for all queries
- When enabled/available, uses real `query_runner` that connects to AS400

### Database Availability Check
```python
from query_runner import is_db_available

if is_db_available():
    # Database is available - proceed with real queries
else:
    # Database is disabled - use fallback behavior
```

### Factory Function
```python
from query_runner import create_query_runner

runner = create_query_runner(
    username="user",
    password="pass",
    as400_hostname="as400.example.com",
    driver="ODBC Driver"
)
# Returns NullQueryRunner if disabled, otherwise returns real query_runner
```

## Behavior When Disabled

### invFetcher (utils.py)
- `fetch_po()` returns empty string `""`
- `fetch_cust_name()` returns empty string `""`
- `fetch_cust_no()` returns `0`
- `fetch_uom_desc()` returns `"N/A"`

### Converters
- Converters run without database lookups
- UPC lookups are skipped (upc_lut is empty dict `{}`)
- UOM descriptions use default fallback values ("HI", "LO", "N/A")

### Tests
Tests automatically disable database access by setting `BATCH_PROCESSOR_DB_ENABLED=false` in `tests/conftest.py`.

To enable database tests:
```bash
BATCH_PROCESSOR_DB_ENABLED=true pytest tests/
```

## Benefits

1. **Local Development**: Work on code without AS400 connection
2. **Faster Tests**: No network/database overhead during test runs
3. **CI/CD Friendly**: Tests can run in any environment
4. **Gradual Migration**: Existing code continues to work with DB, new code handles missing DB gracefully

## Implementation Details

- `NullQueryRunner`: Fallback class with no-op methods returning empty results
- `is_db_available()`: Utility function to check if DB is enabled
- `create_query_runner()`: Factory function that returns appropriate runner
- All DB call sites updated to check availability before accessing database
