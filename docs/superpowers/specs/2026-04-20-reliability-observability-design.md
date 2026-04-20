# Reliability & Observability Enhancement

**Date**: 2026-04-20
**Status**: Approved
**Scope**: Debugging in production, proactive alerting, file-level audit trail

---

## 1. Overview

This design adds structured observability to the Batch File Processor without disrupting existing functionality. The three pillars are:

1. **Debugging** — Correlation IDs propagated through the entire pipeline, enabling `grep correlation_id=XYZ *.log` to trace a file through every step
2. **Alerting** — Email sent immediately on each processing failure, with full context (stack trace, EDI errors, processing settings, correlation ID)
3. **Audit trail** — Async writes to `audit_log` table recording every pipeline step outcome per file

**Design principle**: Errors and audit events are never dropped. Alerting is bulletproof (queued on SMTP failure, never blocks processing).

---

## 2. Architecture

```
FileProcessor / FolderPipelineExecutor
       │
       ▼
ErrorHandler.record_error()
       │
       ├──▶ AlertDispatcher ──▶ SMTPService ──▶ Email (per failure)
       │                              │
       │                              └──▶ AlertQueueFile (on SMTP failure)
       │
       └──▶ AuditLogger ──▶ AuditQueue ──▶ Background Thread ──▶ audit_log table
```

### 2.1 New Components

| Component | Location | Responsibility |
|-----------|----------|----------------|
| `AlertDispatcher` | `dispatch/observability/alert_dispatcher.py` | Orchestrates alert delivery with bulletproof queue |
| `AlertQueue` | `dispatch/observability/alert_queue.py` | Persistent JSON queue for failed alert deliveries |
| `AuditLogger` | `dispatch/observability/audit_logger.py` | Queues audit events for async background write |
| `SMTPAlertService` | `interface/services/smtp_alert_service.py` | Email-specific alert formatting and delivery |

### 2.2 Integration Points

| File | Change |
|------|--------|
| `dispatch/error_handler.py` | Call `AlertDispatcher.dispatch_error_alert()` on each error |
| `dispatch/services/file_processor.py` | Propagate correlation_id through pipeline steps, emit audit events |
| `dispatch/services/folder_processor.py` | Generate per-run correlation_id |
| `core/structured_logging.py` | No changes — existing infrastructure sufficient |
| `dispatch/__init__.py` | Export new observability components |
| `interface/models/folder_configuration.py` | Add `alert_on_failure: bool` per folder |
| `backend/database/database_obj.py` | Add `audit_log` table accessor |

---

## 3. Correlation ID Propagation

### 3.1 Current State

`core/structured_logging.py` already provides:
- `set_correlation_id()` / `get_correlation_id()` via ContextVars
- `StructuredLogAdapter` for auto-injection into log records
- `CorrelationContext` context manager

### 3.2 Changes Required

1. **`FolderPipelineExecutor`** generates a correlation ID at the start of each folder run:
   ```python
   correlation_id = generate_correlation_id()  # from structured_logging
   set_correlation_id(correlation_id)
   ```

2. **`FileProcessor`** propagates the correlation_id through all pipeline steps:
   ```python
   correlation_id = get_correlation_id()
   context["correlation_id"] = correlation_id
   # Pass context to each step
   ```

3. **Every log call** within a processing run automatically includes the correlation_id via `StructuredLogAdapter`.

### 3.3 Result

All log entries for a file's processing share the same `correlation_id`. Debugging workflow:

```bash
grep "correlation_id=abc123def456" logs/*.log
```

---

## 4. Alerting — Email Per Failure

### 4.1 AlertDispatcher

```python
class AlertDispatcher:
    def __init__(
        self,
        smtp_service: SMTPAlertService,
        alert_queue: AlertQueue,
        settings: dict,
    ):
        self._smtp = smtp_service
        self._queue = alert_queue
        self._settings = settings

    def dispatch_error_alert(
        self,
        error_record: dict,
        correlation_id: str,
        folder_alias: str,
        file_path: str,
        processing_context: dict,
    ) -> None:
        try:
            self._smtp.send_alert(...)
        except Exception:
            # Bulletproof: never let alerting break processing
            self._queue.enqueue(error_record)
```

### 4.2 Alert Trigger Points

Alerts fire immediately on:

| Event | Trigger |
|-------|---------|
| EDI validation failure | `EDIValidationStep.execute()` returns `success=False` |
| Conversion failure | `EDIConverterStep.execute()` raises exception |
| Split failure | `EDISplitterStep.execute()` raises exception |
| Tweaks failure | `EDITweakerStep.execute()` raises exception |
| Backend send failure | All retries exhausted in `BackendAdapter.send()` |

### 4.3 Per-Folder Control

```python
@dataclass
class FolderConfig:
    # ... existing fields ...
    alert_on_failure: bool = True  # Default enabled
```

Folder setting controls whether alerts fire. Some folders (low-priority test folders) can have alerting disabled.

### 4.4 Email Content

**Subject**: `[BFS ALERT] {folder_alias} — {error_type} — {filename}`

**Body** (plain text, maximum detail):

```
BATCH FILE PROCESSOR — PROCESSING FAILURE ALERT
================================================
Timestamp: {timestamp}
Correlation ID: {correlation_id}

FOLDER
------
{full folder path}

FILE
----
{filename}

ERROR
-----
Type: {error_type}
Message: {error_message}
Stack Trace:
{formatted_traceback}

EDI VALIDATION ERRORS (if applicable)
-------------------------------------
{validation_error_details}

PROCESSING CONTEXT
------------------
Pipeline Step: {step_name}
Input Path: {input_path}
Output Path: {output_path}
Settings: {sanitized_settings}

RETRY HISTORY
-------------
Attempts made: {attempt_count}
Final attempt timestamp: {timestamp}

This is an automated alert from Batch File Processor.
```

### 4.5 Alert Queue — Bulletproof Delivery

**Problem**: SMTP can fail (network issues, server downtime). We must never drop an alert.

**Solution**: `AlertQueue` persists failed alerts to JSON file.

```python
# ~/.local/share/Batch File Sender/alert_queue.jsonl
{"timestamp": "...", "error_record": {...}, "retry_count": 0}
{"timestamp": "...", "error_record": {...}, "retry_count": 1}
```

**Queue processing**:
1. On SMTP failure → append to queue file (one JSON line per alert)
2. On next processing run → attempt to send queued alerts before new alerts
3. After 5 retry failures → move to `alert_failures.log` and stop retrying

**Alert never dropped** — at minimum, it's in the queue file.

---

## 5. Audit Trail — Async File Lineage

### 5.1 Database Schema

```sql
CREATE TABLE audit_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    correlation_id TEXT NOT NULL,
    folder_id INTEGER NOT NULL,
    file_name TEXT NOT NULL,
    event_type TEXT NOT NULL,          -- 'validation', 'split', 'convert', 'tweak', 'send'
    event_status TEXT NOT NULL,        -- 'success', 'failure', 'skipped'
    error_type TEXT,
    error_message TEXT,
    input_path TEXT,
    output_path TEXT,
    duration_ms INTEGER,
    timestamp TEXT NOT NULL,           -- ISO 8601
    details TEXT,                      -- JSON blob for step-specific data
    FOREIGN KEY (folder_id) REFERENCES folders(id)
);

CREATE INDEX idx_audit_correlation ON audit_log(correlation_id);
CREATE INDEX idx_audit_folder ON audit_log(folder_id, timestamp);
```

### 5.2 AuditLogger

```python
class AuditLogger:
    def __init__(self, audit_queue: AuditQueue):
        self._queue = audit_queue  # thread-safe queue

    def log_event(self, event: AuditEvent) -> None:
        """Non-blocking — always succeeds, queues for background write."""
        self._queue.put(event)

    def log_step(
        self,
        correlation_id: str,
        folder_id: int,
        file_name: str,
        step: str,
        status: str,
        duration_ms: int,
        error: Exception | None = None,
        details: dict | None = None,
    ) -> None:
        event = AuditEvent(
            correlation_id=correlation_id,
            folder_id=folder_id,
            file_name=file_name,
            event_type=step,
            event_status=status,
            duration_ms=duration_ms,
            error_type=type(error).__name__ if error else None,
            error_message=str(error) if error else None,
            details=details,
        )
        self.log_event(event)
```

### 5.3 Background Writer

```python
class AuditBackgroundWriter:
    """Background thread that drains the audit queue and writes to DB."""

    def __init__(self, audit_queue: AuditQueue, db: DatabaseInterface):
        self._queue = audit_queue
        self._db = db

    def run(self) -> None:
        while True:
            event = self._queue.get()  # blocks
            try:
                self._db.audit_log_table.insert(event.to_dict())
            except Exception:
                # Log but never crash — audit must not break processing
                logger.error("Failed to write audit event", exc_info=True)
```

### 5.4 Audit Events Recorded

| Step | Events Logged |
|------|--------------|
| Validation | `enter`, `success`, `failure` with error details |
| Split | `enter`, `success`, `failure`, `skipped` (if no split needed) |
| Convert | `enter`, `success`, `failure` with output path |
| Tweaks | `enter`, `success`, `failure` |
| Send (per backend) | `attempt`, `success`, `failure` with retry count |

---

## 6. Settings / Configuration

### 6.1 New Global Settings

| Setting | Type | Default | Description |
|---------|------|---------|-------------|
| `alert_on_failure_global` | bool | `True` | Master switch for alerting |
| `alert_email_recipients` | str | `""` | Comma-separated email addresses |
| `alert_retry_max` | int | `5` | Max retry attempts for failed alerts |
| `audit_enabled` | bool | `True` | Master switch for audit logging |

### 6.2 Per-Folder Settings

| Setting | Type | Default | Description |
|---------|------|---------|-------------|
| `alert_on_failure` | bool | `True` | Enable/disable alerting for this folder |

---

## 7. Error Handling Strategy

### 7.1 Never Break Processing

All observability components are fire-and-forget with internal queues:

- `AlertDispatcher.dispatch_error_alert()` wrapped in try/except
- `AuditLogger.log_event()` is non-blocking, queues immediately
- Background writer catches all exceptions internally

### 7.2 Graceful Degradation

| Component Failure | Behavior |
|------------------|----------|
| SMTP down | Alert queued, processing continues |
| Queue file full | Write to `alert_failures.log`, continue processing |
| Database down | Audit events logged to `audit_failures.log` |
| Background writer crashes | Auto-restart on next processing run |

---

## 8. File Locations

| File | Purpose |
|------|---------|
| `dispatch/observability/alert_dispatcher.py` | Alert orchestration |
| `dispatch/observability/alert_queue.py` | Persistent alert queue |
| `dispatch/observability/audit_logger.py` | Audit event logger |
| `dispatch/observability/__init__.py` | Package exports |
| `interface/services/smtp_alert_service.py` | Email formatting and delivery |
| `alert_queue.jsonl` | Queued failed alerts (in app data dir) |
| `alert_failures.log` | Permanently failed alerts |
| `audit_failures.log` | Permanently failed audit writes |

---

## 9. Backward Compatibility

- **Existing logs**: Unchanged format, new fields added via `extra` dict
- **Existing database**: `audit_log` table added via migration
- **Existing settings**: New settings have safe defaults
- **Existing error handling**: `ErrorHandler` gains new behavior but preserves existing interface

---

## 10. Implementation Phases

### Phase 1: Core Infrastructure
1. Create `dispatch/observability/` package structure
2. Implement `AlertQueue` (persistent JSON queue)
3. Implement `AuditLogger` with thread-safe queue
4. Add `audit_log` table migration

### Phase 2: Alerting
5. Implement `SMTPAlertService` (email formatting)
6. Implement `AlertDispatcher` with bulletproof wrapper
7. Integrate into `ErrorHandler`
8. Add per-folder `alert_on_failure` setting

### Phase 3: Correlation IDs
9. Propagate correlation IDs through `FolderPipelineExecutor`
10. Propagate through `FileProcessor` and pipeline steps
11. Add correlation ID to all existing log calls

### Phase 4: Audit Trail
12. Implement `AuditBackgroundWriter`
13. Add audit event emission to all pipeline steps
14. Wire up background writer startup/shutdown

### Phase 5: Testing & Polish
15. Unit tests for alert queue, audit logger
16. Integration tests for end-to-end correlation
17. Error injection tests (SMTP down, DB down)
18. Documentation updates

---

## 11. Out of Scope

- Slack/webhook alerting (email only for v1)
- Real-time dashboards (file-based logs remain the debugging interface)
- Log rotation policies (handled externally by logrotate)
- Cloud log aggregation (ELK/Splunk integration)
- Performance profiling / metrics graphs
