# Code Duplication and Patterns Analysis

## Import Pattern Analysis

### Cross-Cutting Utilities (High Import Frequency)
Based on codebase analysis, these utilities are imported across multiple modules:

1. **utils.py** - Used by virtually all converters and dispatch modules
   - EDI parsing functions
   - UPC validation helpers
   - Date/price conversion utilities
   - Boolean normalization functions

2. **convert_base.py** - Base classes for all 11 converters
   - BaseConverter, CSVConverter, DBEnabledConverter
   - Template method pattern implementation

3. **query_runner.py** - Database access for UPC lookups
   - Used by converters needing product data

## Potential Duplications

### Database Access Patterns
- **interface/database/database_manager.py** (QtSql wrapper)
- **dispatch/db_manager.py** (refactored operations)
- **query_runner.py** (direct SQL helper)
- Direct QSqlQuery usage in legacy code

**Opportunity**: Standardize on single database access pattern

### EDI Processing Logic
- **utils.py** contains EDI parsing functions
- **edi_format_parser.py** handles format loading
- **dispatch/edi_processor.py** processes EDI files
- Individual converters may have EDI-specific logic

**Opportunity**: Consolidate EDI processing into single, well-defined module

### Error Handling
- **record_error.py** for error logging
- **dispatch/error_handler.py** for structured error processing
- Various try/catch blocks throughout codebase

**Opportunity**: Standardize error handling patterns

## Plugin Architecture Patterns

### Consistent Patterns (Good)
1. **Discovery Mechanism**: Filesystem glob-based
   - Converters: `convert_to_*.py`
   - Backends: `*_backend.py`

2. **Base Class Inheritance**
   - All inherit from appropriate base classes
   - Consistent method signatures

3. **Wrapper Pattern**
   - `create_edi_convert_wrapper()` for converters
   - `create_send_wrapper()` for backends

4. **Plugin Registry**: plugin_config.py manages discovery

## Code Organization Issues

### Mixed Responsibilities
1. **utils.py (674 lines)** - Functions across multiple domains:
   - Boolean normalization
   - EDI parsing
   - UPC validation
   - Date/price conversions
   - Database query utilities

2. **convert_base.py (607 lines)** - Base classes + utility helpers
   - Abstract base classes
   - Concrete helper functions
   - Mix of patterns

### Inconsistent Patterns
1. **Legacy vs Refactored**
   - dispatch.py (monolithic) vs dispatch/ package (modular)
   - Different error handling approaches
   - Inconsistent logging patterns

2. **Database Access**
   - Multiple ways to access the same data
   - Different abstractions for similar operations

## Refactoring Opportunities

### Immediate Wins
1. **Split utils.py by domain**:
   - utils/edi.py - EDI parsing functions
   - utils/upc.py - UPC validation helpers
   - utils/datetime.py - Date/time utilities
   - utils/validation.py - General validation helpers

2. **Standardize database access**:
   - Choose single access pattern (prefer dispatch/db_manager.py)
   - Migrate legacy database calls
   - Remove redundant query_runner.py if needed

3. **Consolidate error handling**:
   - Standardize on dispatch/error_handler.py patterns
   - Remove ad-hoc error handling throughout codebase

### Larger Structural Changes
1. **Complete dispatch.py migration**
2. **UI dialog component extraction**
3. **Processing workflow simplification**