# Legacy vs Refactored Architecture

## Dual Dispatch Structure

The codebase contains both legacy and refactored dispatch components:

### Legacy: dispatch.py (569 lines)
- Single file with deeply nested logic (max indent 100)
- Monolithic functions handling multiple concerns
- Direct imports and tight coupling
- **Issues**: Hard to maintain, test, and extend

### Refactored: dispatch/ package
- **coordinator.py** (893 lines) - Main orchestration
- **edi_processor.py** - EDI file processing
- **file_processor.py** - General file processing
- **send_manager.py** - Output delivery management
- **error_handler.py** - Error processing and logging
- **db_manager.py** - Database operations
- **edi_validator.py** - EDI validation logic

## Migration Strategy

**Current State**: Both systems coexist
- New code should use dispatch/ package
- Legacy dispatch.py still referenced in some places
- Need to identify and migrate remaining dependencies

**Refactoring Opportunity**:
1. Audit all imports of dispatch.py
2. Gradually migrate callers to dispatch/ package
3. Eventually deprecate dispatch.py

## Plugin Architecture Consistency

### Converters (11 plugins)
- Pattern: `convert_to_<format>.py`
- Base class: `BaseConverter` from convert_base.py
- Discovery: Filesystem glob-based
- **Consistency**: Good, follows established pattern

### Send Backends (3 plugins)
- Pattern: `<name>_backend.py`
- Base class: `BaseSendBackend` from send_base.py
- Discovery: Filesystem glob-based
- **Consistency**: Good, follows established pattern

## Cross-Cutting Concerns

### Widely Used Utilities
- **utils.py**: EDI parsing, UPC helpers, date/price conversions (674 lines)
- **convert_base.py**: BaseConverter, CSVConverter, DBEnabledConverter (607 lines)
- **plugin_config.py**: PluginConfigMixin, PluginRegistry
- **edi_format_parser.py**: EDI format loading/parsing
- **query_runner.py**: DB query helper (UPC lookups)

### Code Organization Issues
1. **Mixed responsibilities** in utility modules
2. **Domain separation needed** in utils.py
3. **Potential duplication** between convert_base.py and individual converters
4. **Inconsistent error handling** patterns across modules

## Database Layer

### Current Access Patterns
- **interface/database/database_manager.py** - QtSql wrapper
- **dispatch/db_manager.py** - Refactored database operations
- **query_runner.py** - Direct SQL query helper
- **Legacy code** with direct QSqlQuery usage

**Refactoring Opportunity**: Standardize on single database access pattern