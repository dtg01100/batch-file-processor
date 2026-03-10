# Processing Pipeline Documentation

This document describes the architecture and flow of the batch file processing pipeline.

## Overview

The batch file processor is a desktop application that processes EDI (Electronic Data Interchange) files through a configurable pipeline, supporting validation, splitting, conversion, and sending to various backends.

## Architecture Layers

```
┌─────────────────────────────────────────────────────────────┐
│                    INTERFACE LAYER                          │
│         (UI, Dialogs, Widgets, Application)                │
├─────────────────────────────────────────────────────────────┤
│                    DISPATCH LAYER                          │
│      (Orchestrator, Pipeline Steps, Send, Errors)          │
├─────────────────────────────────────────────────────────────┤
│                    BACKEND LAYER                           │
│        (FTP Client, SMTP Client, File Operations)          │
├─────────────────────────────────────────────────────────────┤
│                    CORE LAYER                               │
│          (EDI Parser, Splitter, Utilities)                │
└─────────────────────────────────────────────────────────────┘
```

## Entry Points

| Entry Point | File | Purpose |
|------------|------|---------|
| Qt UI | `main_qt.py` | Qt-based GUI application entry point |
| Tkinter UI | `main_interface.py` | Tkinter-based GUI application entry point |

Both create a `QtBatchFileSenderApp` instance from `interface/qt/app.py`.

---

## Processing Pipeline

The pipeline processes files through sequential stages:

```
┌──────────┐   ┌──────────┐   ┌──────────┐   ┌──────────┐   ┌──────────┐
│  Input   │──▶│ Validate │──▶│  Split   │──▶│ Convert  │──▶│   Send   │
│  File    │   │          │   │          │   │          │   │          │
└──────────┘   └──────────┘   └──────────┘   └──────────┘   └──────────┘
```

### Pipeline Steps

| Step | Module | Purpose |
|------|--------|---------|
| **Validation** | `dispatch/pipeline/validator.py` | Validates EDI file structure and content |
| **Splitting** | `dispatch/pipeline/splitter.py` | Splits multi-invoice files into individual files |
| **Conversion** | `dispatch/pipeline/converter.py` | Converts EDI to target formats |
| **Tweaking** | `dispatch/pipeline/tweaker.py` | Applies post-conversion modifications |

### Step Details

#### 1. EDIValidationStep
- Wraps `EDIValidator` for pipeline integration
- Validates EDI format and record structure
- Returns `ValidationResult` with `is_valid`, `errors`, `warnings`

#### 2. EDISplitterStep
- Splits multi-invoice EDI files into individual invoices
- Supports category filtering (UPC-based)
- Credit memo detection and filtering
- Returns `SplitterResult` with list of output files

#### 3. EDIConverterStep
- Converts EDI to multiple output formats via dynamic module loading
- Returns `ConverterResult` with output path

#### 4. EDITweakerStep
- Applies modifications using `edi_tweaks` module
- Date offsets, padding, filtering
- Returns `TweakerResult` with tweaked output path

---

## Supported Conversion Formats

| Format | Description |
|--------|-------------|
| `csv` | Standard CSV |
| `estore_einvoice` | eStore eInvoice |
| `estore_einvoice_generic` | Generic eStore format |
| `fintech` | Fintech format |
| `jolley_custom` | Jolley custom |
| `scannerware` | Scannerware |
| `scansheet_type_a` | ScanSheet Type A |
| `simplified_csv` | Simplified CSV |
| `stewarts_custom` | Stewart's custom |
| `yellowdog_csv` | YellowDog CSV |

---

## Dispatch Orchestrator

The `DispatchOrchestrator` (`dispatch/orchestrator.py`) is the central coordination class.

### Configuration (DispatchConfig)

| Field | Type | Purpose |
|-------|------|---------|
| `database` | `DatabaseInterface` | Persistence interface |
| `file_system` | `FileSystemInterface` | File operations abstraction |
| `backends` | `dict` | Send backends (FTP, email, copy) |
| `validator_step` | `ValidatorInterface` | Validation step |
| `splitter_step` | `SplitterInterface` | Splitting step |
| `converter_step` | `ConverterInterface` | Conversion step |
| `tweaker_step` | `TweakerInterface` | Tweaking step |
| `settings` | `dict` | Global application settings |
| `progress_reporter` | `callable` | UI progress callbacks |

### Key Methods

- `process_folder()` - Process all files in a folder
- `process_file()` - Process a single file
- `_process_file_with_pipeline()` - Core file processing with pipeline steps
- `_send_pipeline_file()` - Send processed file to backends

---

## Send Backends

The `SendManager` (`dispatch/send_manager.py`) manages sending processed files.

| Backend | Module | Protocol |
|---------|--------|----------|
| FTP/FTPS | `ftp_backend.py` | FTPClientProtocol |
| Email | `email_backend.py` | SMTPClientProtocol |
| File Copy | `copy_backend.py` | FileOperationsProtocol |

All backends support retry logic (10 attempts with exponential backoff).

---

## File Processing Flow

```
1. User clicks "Process" in UI
2. App loads folder configurations from database
3. For each folder:
   a. Orchestrator.process_folder() called
   b. Get list of files in folder
   c. Filter already-processed files (by checksum)
   d. For each file:
      - Calculate MD5 checksum
      - Validate (if process_edi or tweak_edi or split_edi enabled)
      - Split (if split_edi enabled)
      - Convert (if convert_edi enabled)
      - Tweak (if tweak_edi enabled)
      - Send to enabled backends (copy/FTP/email)
      - Record processed file in database
   e. Report folder result
4. UI displays processing results
```

---

## Interfaces/Protocols

Defined in `dispatch/interfaces.py`:

| Protocol | Purpose |
|---------|---------|
| `DatabaseInterface` | CRUD operations for persistence |
| `FileSystemInterface` | File/directory operations abstraction |
| `BackendInterface` | Send backend abstraction |
| `ValidatorInterface` | File validation abstraction |
| `ErrorHandlerInterface` | Error recording abstraction |

---

## Folder Configuration

Configuration fields stored in database:

| Field | Purpose |
|-------|---------|
| `folder_name` | Path to input folder |
| `alias` | Display name |
| `process_backend_copy` | Enable file copy backend |
| `process_backend_ftp` | Enable FTP backend |
| `process_backend_email` | Enable email backend |
| `copy_to_directory` | Destination directory for copy |
| `ftp_*` | FTP connection settings |
| `email_to` | Email recipients |
| `convert_to_format` | Output format (csv, fintech, etc.) |
| `split_edi` | Enable invoice splitting |
| `convert_edi` | Enable format conversion |
| `tweak_edi` | Enable EDI tweaks |
| `process_edi` | Enable EDI processing |
| `split_edi_filter_categories` | UPC categories to filter |
| `prepend_date_files` | Prepend date to output filenames |

---

## Error Handling

The `ErrorHandler` class records errors to:
- In-memory buffer
- Database (if configured)
- Log files (via `write_error_log_file()`)

All pipeline steps integrate with the error handler.

---

## Test Support

Mock implementations for all components:
- `MockValidator`, `MockSplitter`, `MockConverter`, `MockTweaker`
- `MockBackend` for send operations
- `MockDatabase`, `MockFileSystem` for persistence

Protocol-based design enables easy dependency injection for testing.
