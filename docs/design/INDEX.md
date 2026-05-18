# Batch File Processor - Design Documentation Set

**Version:** 1.1  
**Date:** 2026-05-18  
**Status:** Complete - Verified Against Codebase

---

## Overview

This design documentation set provides comprehensive technical specifications for the Batch File Processor application. These documents have been **verified against the actual codebase** and corrections have been applied.

## Document Index

### 1. Architecture Foundation

| Document | Purpose | Status | Last Verified |
|----------|---------|--------|---------------|
| [SYSTEM_OVERVIEW.md](SYSTEM_OVERVIEW.md) | High-level architecture, principles, technology stack | ✅ | 2026-05-18 |
| [DATA_FLOW.md](DATA_FLOW.md) | End-to-end data flow, adapter pattern, services | ✅ | 2026-05-18 |
| [COMPONENT_MAP.md](COMPONENT_MAP.md) | Module organization and responsibilities | ✅ | 2026-05-18 |

### 2. Core Subsystems

| Document | Purpose | Status | Last Verified |
|----------|---------|--------|---------------|
| [PROCESSING_PIPELINE.md](PROCESSING_PIPELINE.md) | File processing pipeline stages | ✅ | 2026-05-18 |
| [CONVERTER_ARCHITECTURE.md](CONVERTER_ARCHITECTURE.md) | Converter plugin system design | ✅ | 2026-05-18 |
| [BACKEND_ARCHITECTURE.md](BACKEND_ARCHITECTURE.md) | Send backend architecture | ✅ | 2026-05-18 |
| [EDI_PROCESSING.md](EDI_PROCESSING.md) | EDI parsing, validation, splitting, tweaking | ✅ | 2026-05-18 |
| [ERROR_HANDLING.md](ERROR_HANDLING.md) | Error handling and logging strategy | ✅ | 2026-05-18 |

### 3. Interface Layer

| Document | Purpose | Status | Last Verified |
|----------|---------|--------|---------------|
| [GUI_ARCHITECTURE.md](GUI_ARCHITECTURE.md) | PyQt5 GUI architecture and patterns | ✅ | 2026-05-18 |
| [DIALOG_DESIGN.md](DIALOG_DESIGN.md) | Dialog components and interactions | ✅ | 2026-05-18 |
| [CONFIGURATION_SYSTEM.md](CONFIGURATION_SYSTEM.md) | Settings and folder configuration | ✅ | 2026-05-18 |

### 4. Data and Integration

| Document | Purpose | Status | Last Verified |
|----------|---------|--------|---------------|
| [DATABASE_SCHEMA.md](DATABASE_SCHEMA.md) | Database design with repository pattern | ✅ | 2026-05-18 |
| [PLUGIN_API.md](PLUGIN_API.md) | Plugin interfaces and contracts | ✅ | 2026-05-18 |

### 5. Operations and Quality

| Document | Purpose | Status | Last Verified |
|----------|---------|--------|---------------|
| [TESTING_STRATEGY.md](TESTING_STRATEGY.md) | Testing approach and test organization | ✅ | 2026-05-18 |
| [SECURITY_MODEL.md](SECURITY_MODEL.md) | Security considerations | ✅ | 2026-05-18 |

### 6. Maintenance

| Document | Purpose | Status |
|----------|---------|--------|
| [DESIGN_CORRECTIONS.md](DESIGN_CORRECTIONS.md) | Historical record of discrepancies found and fixed | ✅ |

### 7. Historical/Reference

| Document | Purpose |
|----------|---------|
| [API_INTERFACE_DESIGN.md](API_INTERFACE_DESIGN.md) | API contracts |
| [SYSTEM_ARCHITECTURE.md](SYSTEM_ARCHITECTURE.md) | Detailed system architecture |
| [UI_DECOUPLING_ANALYSIS.md](UI_DECOUPLING_ANALYSIS.md) | Tkinter→PyQt5 migration analysis |
| [USER_INTERFACE_DESIGN.md](USER_INTERFACE_DESIGN.md) | Tkinter UI reference |
| [EDIT_FOLDERS_DIALOG_DESIGN.md](EDIT_FOLDERS_DIALOG_DESIGN.md) | Edit dialog design reference |
| [OUTPUT_FORMATS_DESIGN.md](OUTPUT_FORMATS_DESIGN.md) | Output format specifications |
| [WIDGET_LAYOUT_SPECIFICATION.md](WIDGET_LAYOUT_SPECIFICATION.md) | Widget layout reference |

---

## Quick Start

**New to the codebase?** Start with:
1. [SYSTEM_OVERVIEW.md](SYSTEM_OVERVIEW.md) - Architecture principles
2. [DATA_FLOW.md](DATA_FLOW.md) - Data movement through system
3. [PROCESSING_PIPELINE.md](PROCESSING_PIPELINE.md) - Processing stages

**Working on a specific area?**
- GUI → [GUI_ARCHITECTURE.md](GUI_ARCHITECTURE.md)
- Converters → [CONVERTER_ARCHITECTURE.md](CONVERTER_ARCHITECTURE.md)
- Backends → [BACKEND_ARCHITECTURE.md](BACKEND_ARCHITECTURE.md)
- EDI → [EDI_PROCESSING.md](EDI_PROCESSING.md)
- Database → [DATABASE_SCHEMA.md](DATABASE_SCHEMA.md)

---

## Verification Process

The design documents were verified against the actual codebase on 2026-05-18:

### Key Corrections Made

1. **Database Layer**: Documented actual `DatabaseObj` class (not `DatabaseManager`)
2. **Repository Pattern**: Added adapter layer with `IFolderRepository` interface
3. **Adapter Layer**: Documented `adapters/sqlite/repositories/` 
4. **Folder Schema**: Corrected to 60+ columns (not 15)
5. **Backend Order**: Fixed to copy, ftp, email, http
6. **Missing Components**: Added dispatch services, observability, UPC service
7. **Pipeline Interface**: Documented `ErrorRecordingMixin`

### Verification Commands Used

```bash
# Database schema
grep -A 100 "CREATE TABLE.*folders" core/database/schema.py

# Backend configuration
grep -A 30 "DEFAULT_BACKENDS" dispatch/send_manager.py

# Pipeline interface
cat dispatch/pipeline/interfaces.py

# Component locations
find . -name "*.py" -path "*/dispatch/*" -o -name "*.py" -path "*/backend/*"
```

---

## Document Template

New design documents should follow this structure:

```markdown
# Document Title

**Version:** 1.0  
**Date:** YYYY-MM-DD  
**Status:** DRAFT

---

## 1. Overview
## 2. Architecture
## 3. Component Details
## 4. Data Structures
## 5. Error Handling
## 6. Testing Strategy
## 7. Related Documents
```

---

## Maintenance Guidelines

1. **Update on Change**: When modifying components, update relevant design docs
2. **Version Control**: Design docs live in git alongside code
3. **Review Process**: Major architectural changes require design doc review
4. **Consistency**: Use consistent terminology across all documents
5. **Mark Complete**: Update status to "Complete" when finalized
6. **Verify Against Code**: When updating, re-verify against actual implementation

---

## Related Documentation

- **User Guides**: `docs/user-guide/` - End-user documentation
- **Testing Guides**: `docs/testing/` - Test suite documentation
- **Migration Guides**: `docs/migrations/` - Database migration documentation
- **OpenSpecs**: `openspec/` - Feature specifications in progress
