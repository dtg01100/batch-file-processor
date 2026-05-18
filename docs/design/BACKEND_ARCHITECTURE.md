# Backend Architecture

**Version:** 1.0  
**Date:** 2026-05-18  
**Status:** DRAFT

---

## 1. Overview

Backends handle the delivery of processed files to their destinations. Each backend implements a common interface and provides its own transport mechanism.

## 2. Backend Interface

All backends implement the standard `do()` function interface:

```python
def do(
    process_parameters: dict,  # Backend-specific configuration
    settings_dict: dict,      # Global application settings
    filename: str,            # File to send
    disable_retry: bool = False,
) -> bool:
    """Send a file via backend.
    
    Returns:
        True if successful, False otherwise.
    """
```

## 3. Available Backends

### 3.1 Email Backend

**Module:** `backend/email_backend.py`  
**Protocol:** SMTP

```python
def do(process_parameters, settings_dict, filename, disable_retry=False) -> bool:
    """Send file as email attachment via SMTP."""
    with SMTP(settings_dict['email_smtp_server']) as server:
        server.starttls()
        server.login(settings_dict['email_username'], settings_dict['email_password'])
        msg = EmailMessage()
        msg['From'] = settings_dict['email_address']
        msg['To'] = process_parameters['email_recipients']
        msg['Subject'] = process_parameters.get('email_subject', 'Processed File')
        msg.attach(file_to_attach)
        server.send_message(msg)
```

### 3.2 FTP Backend

**Module:** `backend/ftp_backend.py`  
**Protocol:** FTP/FTPS

```python
def do(process_parameters, settings_dict, filename, disable_retry=False) -> bool:
    """Upload file via FTP/FTPS."""
    with FTPClient(
        host=process_parameters['ftp_host'],
        port=process_parameters.get('ftp_port', 21),
        username=process_parameters.get('ftp_username', ''),
        password=process_parameters.get('ftp_password', ''),
        use_tls=process_parameters.get('ftp_use_tls', False),
    ) as ftp:
        remote_path = process_parameters.get('ftp_remote_path', '/')
        ftp.upload(filename, remote_path)
```

### 3.3 Copy Backend

**Module:** `backend/copy_backend.py`  
**Protocol:** Local filesystem

```python
def do(process_parameters, settings_dict, filename, disable_retry=False) -> bool:
    """Copy file to local destination folder."""
    destination = process_parameters['copy_destination']
    shutil.copy2(filename, destination)
    return True
```

### 3.4 HTTP Backend

**Module:** `backend/http_backend.py`  
**Protocol:** HTTP/HTTPS POST

```python
def do(process_parameters, settings_dict, filename, disable_retry=False) -> bool:
    """Upload file via HTTP POST."""
    with open(filename, 'rb') as f:
        response = requests.post(
            process_parameters['http_url'],
            files={'file': f},
            auth=HTTPBasicAuth(
                process_parameters.get('http_username', ''),
                process_parameters.get('http_password', ''),
            ),
            timeout=30,
        )
    return response.ok
```

## 4. Backend Configuration

**Location:** `dispatch/send_manager.py` — `SendManager.DEFAULT_BACKENDS`

The available backends are defined in the `SendManager` class as a class variable.
There is **no** separate `BackendFactory` class in the codebase.

```python
# dispatch/send_manager.py
class SendManager:
    DEFAULT_BACKENDS: ClassVar[dict[str, dict[str, str]]] = {
        "copy": {       # 1st — local file copy
            "module": "backend.copy_backend",
            "setting": "copy_to_directory",
            "display_name": "Copy Backend",
            "enabled_key": "process_backend_copy",
        },
        "ftp": {        # 2nd — FTP/FTPS upload
            "module": "backend.ftp_backend",
            "setting": "ftp_server",
            "display_name": "FTP Backend",
            "enabled_key": "process_backend_ftp",
        },
        "email": {      # 3rd — SMTP email
            "module": "backend.email_backend",
            "setting": "email_to",
            "display_name": "Email Backend",
            "enabled_key": "process_backend_email",
        },
        "http": {       # 4th — HTTP POST upload
            "module": "backend.http_backend",
            "setting": "http_url",
            "display_name": "HTTP Backend",
            "enabled_key": "process_backend_http",
        },
    }
```

## 5. Send Manager

**Location:** `dispatch/send_manager.py`

The SendManager dynamically imports and calls backend modules using the configuration above.
It does **not** iterate over `self._backends` list; instead it passes a set of enabled backend names
to `send_all()` and dispatches each via `_send_via_module()`.

```python
# dispatch/send_manager.py
class SendManager:
    def __init__(self, backends: dict | None = None, use_default_backends: bool = True):
        self.backends = backends or {}
        self.use_default_backends = use_default_backends
        self.results: dict[str, bool] = {}
        self.errors: dict[str, Exception] = {}

    def get_enabled_backends(self, params: dict) -> set[str]:
        """Return the set of backend names that are enabled in the folder config."""
        ...

    def send_all(self, enabled_backends: set[str], file_path: str, params: dict, settings: dict) -> bool:
        """Send file via all enabled backends."""
        for backend_name in enabled_backends:
            self._send_via_module(backend_name, file_path, params, settings)
        ...

    def _send_via_module(self, backend_name: str, file_path: str, params: dict, settings: dict) -> bool:
        """Import and call the backend module's ``do()`` function."""
        result = module.do(params, settings, file_path)
        ...
```

## 6. Error Handling

Backends should:
- Return `False` on failure (not raise exceptions)
- Log errors before returning
- Support `disable_retry` flag for batch scenarios

```python
def do(process_parameters, settings_dict, filename, disable_retry=False) -> bool:
    try:
        # Send logic
        return True
    except Exception as e:
        logger.error(f"Backend send failed: {e}", exc_info=True)
        return False
```

## 7. Adding a New Backend

### Step 1: Create backend module

```python
# backend/my_backend.py
def do(process_parameters, settings_dict, filename, disable_retry=False) -> bool:
    """Send file via MyBackend."""
    # Implementation
    return True
```

### Step 2: Register in catalog

```python
# dispatch/send_manager.py - SendManager.DEFAULT_BACKENDS
DEFAULT_BACKENDS = {
    # ... existing backends ...
    "mybackend": {
        "module": "backend.my_backend",
        "setting": "my_backend_setting",
        "display_name": "MyBackend",
        "enabled_key": "process_backend_mybackend",
    },
}
```

### Step 3: Add tests

```python
# tests/unit/backend/test_my_backend.py
```

## 8. Related Documents

- [DATA_FLOW.md](DATA_FLOW.md) - Data flow overview
- [PROCESSING_PIPELINE.md](PROCESSING_PIPELINE.md) - Pipeline integration
- [API_INTERFACE_DESIGN.md](API_INTERFACE_DESIGN.md) - Backend protocol definitions (`FTPClientProtocol`, `SMTPClientProtocol`, `FileOperationsProtocol` in `backend/protocols.py`)
