# System Overview

**Version:** 1.0  
**Date:** 2026-05-18  
**Status:** DRAFT

---

## 1. Purpose

The Batch File Processor is a Python-based desktop application that automates the processing, conversion, and distribution of EDI (Electronic Data Interchange) files. It monitors configured folders for incoming files, processes them through a configurable pipeline, and delivers the results to various destinations.

## 2. Technology Stack

| Component | Technology | Version |
|-----------|------------|---------|
| GUI Framework | PyQt5 | 5.15.x |
| Database | SQLite | 3.x (Python stdlib) |
| Python | CPython | 3.11 |
| Testing | pytest | 7.x |

### Constraints

- **Python 3.11 maximum** - Target system limitation
- **Qt5 maximum** - PyQt6/Qt6 not supported
- **No external database servers** - SQLite only for local storage

## 3. Architecture Principles

1. **Separation of Concerns** - UI, business logic, and data layers are clearly separated
2. **Dependency Injection** - Components depend on abstractions (Protocols), not concretions
3. **Pipeline Pattern** - Processing stages are composable, pluggable steps
4. **Plugin Architecture** - Converters and backends are discoverable plugins
5. **Protocol-Based Design** - Extensive use of Python Protocol classes for interfaces

## 4. Package Structure

```
batch-file-processor/
├── interface/          # GUI layer (PyQt5)
│   ├── qt/            # Qt widgets and dialogs
│   ├── form/          # Form generation
│   ├── models/        # Data models
│   ├── operations/    # Business logic
│   ├── plugins/       # Plugin configuration
│   ├── services/      # Application services
│   └── validation/    # Input validation
│
├── dispatch/          # Core processing orchestration
│   ├── converters/    # Output format converters
│   ├── pipeline/      # Processing pipeline steps
│   ├── services/      # File/folder processing services
│   └── observability/ # Logging and monitoring
│
├── backend/           # Output delivery backends
│   ├── database/      # Database utilities
│   └── protocols.py   # Backend interface definitions
│
├── core/              # Shared utilities and EDI processing
│   ├── database/      # Database layer
│   ├── edi/           # EDI parsing and manipulation
│   ├── domain/        # Domain models
│   ├── ports/         # Port interfaces
│   └── utils/         # Utility functions
│
└── tests/             # Test suite (~4757 tests)
    ├── unit/          # Unit tests
    ├── integration/    # Integration tests
    └── qt/            # GUI tests
```

## 5. Layer Responsibilities

### Interface Layer (interface/)

**Responsibilities:**
- PyQt5 GUI implementation
- User interaction handling
- Form configuration and validation
- Dialog management
- Application bootstrap

**Key Modules:**
- `interface/qt/app.py` - Main application window
- `interface/qt/dialogs/` - Edit folders, settings, maintenance dialogs
- `interface/form/` - Dynamic form generation
- `interface/plugins/` - Plugin configuration management

### Dispatch Layer (dispatch/)

**Responsibilities:**
- File discovery and processing orchestration
- Pipeline execution coordination
- Send backend management
- Error handling and logging
- Progress reporting

**Key Modules:**
- `dispatch/orchestrator.py` - Main processing coordinator
- `dispatch/services/file_processor.py` - Per-file processing
- `dispatch/services/folder_processor.py` - Per-folder processing
- `dispatch/pipeline/` - Processing step implementations
- `dispatch/send_manager.py` - Backend dispatch

### Backend Layer (backend/)

**Responsibilities:**
- Output file delivery (FTP, Email, Copy)
- HTTP/HTTPS file upload
- Network protocol handling

**Key Modules:**
- `backend/email_backend.py` - SMTP email sending
- `backend/ftp_backend.py` - FTP/FTPS file transfer
- `backend/copy_backend.py` - Local file copy
- `backend/http_backend.py` - HTTP file upload

### Core Layer (core/)

**Responsibilities:**
- EDI file parsing and validation
- EDI splitting and transformation
- Database access abstractions
- Shared utilities

**Key Modules:**
- `core/edi/edi_parser.py` - EDI format parsing
- `core/edi/edi_splitter.py` - Multi-transaction splitting
- `core/edi/edi_tweaker.py` - Field-level modifications
- `core/database/` - Database abstractions

## 6. Key Entry Points

| Entry Point | File | Purpose |
|-------------|------|---------|
| GUI Mode | `main_interface.py` | Full PyQt5 application |
| Automatic Mode | `main_interface.py -a` | Headless batch processing |
| Qt Tests | `pytest -m qt` | Single-threaded Qt tests |

## 7. Related Documents

- [DATA_FLOW.md](DATA_FLOW.md) - Detailed data flow
- [COMPONENT_MAP.md](COMPONENT_MAP.md) - Component responsibilities
- [PROCESSING_PIPELINE.md](PROCESSING_PIPELINE.md) - Processing stages
- [GUI_ARCHITECTURE.md](GUI_ARCHITECTURE.md) - GUI layer design
