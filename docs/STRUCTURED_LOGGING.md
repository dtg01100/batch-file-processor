# Structured Logging Documentation

This document describes the structured logging system for the Batch File Processor application, including the logging schema, redaction rules, and configuration options.

## Overview

The structured logging system provides comprehensive instrumentation for convert and tweak code paths, enabling:
- Correlation ID propagation across threads and async boundaries
- Sensitive data redaction
- Consistent structured log output
- Performance tracking with duration metrics

## Quick Start

```python
from batch_file_processor.structured_logging import (
    get_correlation_id,
    set_correlation_id,
    redact_sensitive_data,
    logged,
    StructuredLogger,
)

# Use the @logged decorator for automatic instrumentation
@logged
def convert_edi(input_path, output_path, settings):
    # Entry, exit, and errors are automatically logged
    pass

# Or use StructuredLogger manually
logger = logging.getLogger(__name__)
StructuredLogger.log_entry(logger, "convert", __name__, args=(input_path,))
```

## Logging Schema

All structured log entries include the following fields:

| Field | Type | Description |
|-------|------|-------------|
| `timestamp` | ISO8601 | UTC timestamp of the log entry |
| `level` | string | Log level (DEBUG, INFO, WARNING, ERROR) |
| `logger` | string | Logger name (typically module name) |
| `module` | string | Module where the log originated |
| `function` | string | Function name where the log originated |
| `correlation_id` | string? | Request/correlation ID for tracing |
| `trace_id` | string? | Trace ID for distributed tracing |
| `duration_ms` | float? | Execution duration in milliseconds |
| `event` | string? | Event type (entry, exit, error, debug, intermediate) |
| `input_summary` | dict? | Sanitized input parameters |
| `output_summary` | dict? | Sanitized output/result |
| `error` | dict? | Error information (type, message) |

### Example Log Entries

**Entry Log:**
```
[ENTRY] convert_edi(input.edi, output.csv)
```

**Exit Log:**
```
[EXIT] convert_edi completed in 1234.56ms
```

**Error Log:**
```
[ERROR] convert_edi failed: ValueError: Invalid input
```

**Intermediate Step:**
```
[STEP] edi_tweak:override_upc (applied)
{'records': 50, 'type': 'list'}
```

## Correlation ID Management

Correlation IDs are used to track requests across multiple log entries and threads.

### Basic Usage

```python
from batch_file_processor.structured_logging import (
    get_correlation_id,
    set_correlation_id,
    get_or_create_correlation_id,
    CorrelationContext,
)

# Set correlation ID manually
set_correlation_id("request-123")

# Get current correlation ID
corr_id = get_correlation_id()

# Get existing or create new
corr_id = get_or_create_correlation_id()

# Context manager for automatic cleanup
with CorrelationContext("request-456"):
    # All logs within this block have correlation_id="request-456"
    process_files()
# Correlation ID is restored to previous value
```

### Thread Safety

Correlation IDs are stored in a `contextvars.ContextVar`, which provides automatic isolation between threads and async tasks:

```python
import threading

def thread_func(thread_id):
    set_correlation_id(f"id-{thread_id}")
    # Each thread has its own correlation ID
    logger.info("Processing")

threads = [threading.Thread(target=thread_func, args=(i,)) for i in range(5)]
```

## Redaction Rules

Sensitive data is automatically redacted from log entries to prevent credential leakage.

### Redacted Patterns

The following key patterns trigger automatic redaction:

- **Credentials:** `password`, `passwd`, `pwd`, `secret`, `token`, `access_token`, `refresh_token`, `api_key`, `api_secret`, `private_key`, `ssh_key`
- **Database:** `as400_password`, `db_password`, `database_password`
- **Network:** `ftp_password`, `ftp_username`
- **PII:** `ssn`, `social_security`, `credit_card`, `cc_number`, `card_number`, `bank_account`, `routing_number`
- **General:** `auth`, `authorization`, `credential`, `key`

### Redaction Functions

```python
from batch_file_processor.structured_logging import (
    redact_sensitive_data,
    redact_string,
    redact_value,
    hash_sensitive_value,
)

# Redact sensitive fields from dict
data = {"username": "john", "password": "secret123"}
result = redact_sensitive_data(data)
# result = {"username": "****ret123", "password": "****et123"}

# Redact a string (shows last 4 characters)
redact_string("mysecretpassword")  # "************word"

# Redact any value based on type
redact_value("secret")              # "*****ret"
redact_value({"key": "value"})     # {"key": "****lue"}
redact_value(["a", "b"])           # ["***", "***"]

# Hash for safe logging
hash_sensitive_value("secret")      # "a1b2c3d4e5f6g7h8"
```

## StructuredLogger API

The `StructuredLogger` class provides methods for creating consistent structured log entries:

### Methods

- `log_entry(logger, func_name, module, args, kwargs)` - Log function entry
- `log_exit(logger, func_name, module, result, duration_ms)` - Log function exit
- `log_error(logger, func_name, module, error, context, duration_ms)` - Log errors
- `log_debug(logger, func_name, module, message, **kwargs)` - Log debug info
- `log_intermediate(logger, func_name, module, step, data_shape, decision)` - Log intermediate steps

## @logged Decorator

The `@logged` decorator automatically instruments functions with entry, exit, and error logging:

```python
@logged
def my_function(arg1, arg2):
    # [ENTRY] logged automatically
    result = do_something()
    # [EXIT] logged automatically with duration
    return result
```

## Configuration

### Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `BFS_LOG_LEVEL` | Set logging level (DEBUG/INFO/WARNING/ERROR/CRITICAL) | INFO |
| `DISPATCH_DEBUG_MODE` | Enable debug mode when set to "true" | false |
| `BFS_LOG_PAYLOADS` | Enable full payload logging at DEBUG level | false |

### Programmatic Configuration

```python
from batch_file_processor.logging_config import setup_logging
import logging

# Setup with specific level
setup_logging(level=logging.DEBUG, log_file="/var/log/app.log")

# Or use structured logging directly
import logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s [%(levelname)s] %(name)s: %(message)s'
)
```

## JSON Output

For machine-readable logs, use the `JSONFormatter`:

```python
from batch_file_processor.structured_logging import JSONFormatter
import logging

handler = logging.StreamHandler()
handler.setFormatter(JSONFormatter())
logger = logging.getLogger("my_logger")
logger.addHandler(handler)
logger.setLevel(logging.DEBUG)
```

Example JSON output:
```json
{"timestamp": "2024-01-15T10:30:00+00:00", "level": "INFO", "logger": "module", 
 "function": "convert", "correlation_id": "abc123", "duration_ms": 150.5,
 "event": "entry", "message": "[ENTRY] convert(input.edi, output.csv)"}
```

## Instrumented Modules

The following modules are instrumented with structured logging:

| Module | Description |
|--------|-------------|
| `dispatch/pipeline/converter.py` | EDI conversion pipeline step |
| `dispatch/pipeline/tweaker.py` | EDI tweak pipeline step |
| `archive/edi_tweaks.py` | Core EDI tweak functions |
| `convert_to_scansheet_type_a.py` | ScanSheet Type A converter |

## Migration Plan

### Priority 1: Core Pipeline (COMPLETED)
- [x] `dispatch/pipeline/converter.py`
- [x] `dispatch/pipeline/tweaker.py`

### Priority 2: Core Functions (COMPLETED)
- [x] `archive/edi_tweaks.py`

### Priority 3: Converters (COMPLETED)
- [x] `convert_to_scansheet_type_a.py`

### Future Enhancements
- Instrument remaining converter modules
- Add correlation ID to orchestrator
- Integrate with external logging services (DataDog, Splunk, etc.)

## Troubleshooting

### Logs Not Appearing
1. Check `BFS_LOG_LEVEL` environment variable
2. Verify logger is configured with appropriate level
3. Ensure imports are from correct module

### Correlation ID Not Propagating
1. Verify using `get_or_create_correlation_id()` at entry points
2. Check that threads are using context vars correctly
3. Ensure no code is calling `clear_correlation_id()` inadvertently

### Sensitive Data Leaking
1. Verify keys are in `REDACTION_PATTERNS`
2. Check `redact_sensitive_data()` is called on input params
3. Ensure passwords aren't logged directly in messages
