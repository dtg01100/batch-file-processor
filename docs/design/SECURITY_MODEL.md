# Security Model

**Version:** 1.0  
**Date:** 2026-05-18  
**Status:** DRAFT

---

## 1. Overview

Security considerations for the Batch File Processor application.

## 2. Credential Storage

### 2.1 Database Storage

Credentials stored in `settings` table:
- email_password
- ftp_password
- http_password

### 2.2 Encryption at Rest

Credential values (email/ftp/http passwords and API keys) are stored as plain text in the SQLite database file. No at-rest encryption is currently applied.

Future enhancement: encrypt credential values with a user-derived key or OS keychain before persisting to the database (e.g., using `cryptography.fernet`).

- Use OS-level encryption (Windows EFS, macOS Keychain, Linux LUKS)
- Consider `cryptography.fernet` for application-level encryption
- Handle key management carefully (do not hardcode keys)

### 2.3 Recommendations

- Use environment variables for sensitive configs in production
- Consider encryption at rest for credential fields
- Rotate credentials periodically

## 3. Network Security

### 3.1 FTP/FTPS

```python
# Use TLS when available
ftp.use_tls = settings.get('ftp_use_tls', False)
```

### 3.2 SMTP

```python
# Use STARTTLS for secure email
server.starttls()
```

### 3.3 HTTP

```python
# HTTPS recommended
# Use authentication headers
```

## 4. File System Security

### 4.1 Path Validation

```python
# Validate folder paths before processing
def validate_folder_path(path: str) -> bool:
    """Ensure path is within allowed directory tree."""
    resolved = os.path.realpath(path)
    allowed = os.path.realpath(ALLOWED_ROOT)
    return resolved.startswith(allowed)
```

### 4.2 File Access

- Minimize file permissions on processed files
- Use secure temp directory for intermediate files
- Clean up temp files after processing

## 5. EDI Validation

### 5.1 Input Validation

- Validate EDI structure before processing
- Reject malformed files early
- Log validation failures

### 5.2 Content Sanitization

- Avoid executing content as code
- Use parameterized queries for database access
- Validate all external data

## 6. Database Security

### 6.1 SQL Injection Prevention

```python
# Use parameterized queries
cursor.execute("SELECT * FROM folders WHERE id = ?", (id,))
```

### 6.2 SQLite Security

- PRAGMA foreign_keys = ON
- Use WAL mode for concurrent access
- Regular backups

## 7. Logging and Auditing

```python
# Structured logging for audit trail
logger.info(
    "File processed",
    extra={
        "folder_id": folder_id,
        "file_hash": file_hash,
        "action": "processed",
    }
)
```

## 8. Related Documents

- [DATABASE_SCHEMA.md](DATABASE_SCHEMA.md) - Database design
- [ERROR_HANDLING.md](ERROR_HANDLING.md) - Error handling
- [TESTING_STRATEGY.md](TESTING_STRATEGY.md) - Testing
