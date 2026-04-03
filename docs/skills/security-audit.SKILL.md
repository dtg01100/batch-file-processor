# security-audit Skill

Workspace-scoped helper skill for security validation and vulnerability checks.

## Purpose

- Capture the security review workflow for backend services, file handling, and config inputs.
- Prevent SQL injection, path traversal, serialization risks, and credential exposure.

## When to use

- Code change touches DB query building or file path operations.
- New backend protocol support (FTP/SMTP/HTTP) is added.
- Any change to settings parsing, external input, or user-configurable paths.

## Input

- Affected modules and risk class (SQL, path, networking, auth).
- Threat model summary (e.g., remote file upload, untrusted paths, service credentials).

## Workflow

1. Review code for dangerous patterns:
   - SQL string formatting vs parameterization, unchecked path joins, dynamic imports.
2. Add unit tests for bad inputs:
   - Path traversal payloads (`..`), invalid scheme URL, missing fields.
3. Confirm use of safe libraries:
   - `sqlite3` bound params, `os.path.join`, TLS check options, `ssl.wrap_socket` features.
4. If credentials are stored, ensure secure handling and no plaintext logs.
5. Fix discovered issues and add coverage in `tests/security/`.
6. Run `pytest -m security -q --timeout=30`, `ruff check`, `black --check`.

## Decision points

- If a simple workaround is impossible, add deeper mitigation note and issue ticket.
- Prefer failing safe over attempting partial behavior in insecure cases.

## Output

- Security test suite and code fixes with documented risk mitigations.
