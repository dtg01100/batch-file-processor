# Utils Module Refactoring Plan

## Overview
The `utils.py` file has grown into a 26,426-character monolithic catch-all utility module. This plan outlines the refactoring to organize its diverse functionality into smaller, focused modules.

## Current State
- Location: `/workspaces/batch-file-processor/utils.py`
- Size: 26,426 characters (798 lines)
- Usage: Imported by 72 files across the codebase

## Analysis Results

### Existing Duplicate Code
1. **`invFetcher` → `core/edi/inv_fetcher.py`** - Better dependency injection
2. **`cRecGenerator` → `core/edi/c_rec_generator.py`** - Same as above
3. **`calc_check_digit()` / `convert_UPCE_to_UPCA()` → `core/edi/upc_utils.py`** - Pure functions, better structured

### Categories Identified
| Category | Functions | Destination |
|---|---|---|
| Boolean Normalization | `normalize_bool()`, `to_db_bool()`, `from_db_bool()` | `core/utils/bool_utils.py` |
| EDI Data Parsing | `capture_records()`, `_get_default_parser()` | `core/edi/edi_parser.py` (merge with existing) |
| Date/Time Conversion | `dactime_from_datetime()`, `datetime_from_dactime()`, `datetime_from_invtime()`, `dactime_from_invtime()` | `core/utils/date_utils.py` |
| Data Transformation | `dac_str_int_to_int()`, `convert_to_price()`, `convert_to_price_decimal()`, `detect_invoice_is_credit()` | `core/edi/edi_transformer.py` |
| EDI Processing | `do_split_edi()` | `core/edi/edi_splitter.py` (merge with existing) |
| EDI Filtering | `filter_edi_file_by_category()` | `core/edi/edi_splitter.py` (merge with existing) |
| UOM & UPC Operations | `apply_retail_uom_transform()`, `apply_upc_override()` | `core/edi/upc_utils.py` |
| File Management | `do_clear_old_files()` | `core/utils/file_utils.py` (merge with existing in dispatch/file_utils.py) |

## Refactoring Strategy

### Phase 1: Create New Module Structure
1. Create `core/utils/` directory for general utilities
2. Create `core/utils/bool_utils.py` - boolean normalization
3. Create `core/utils/date_utils.py` - date/time conversion
4. Create `core/edi/edi_transformer.py` - data transformation functions
5. Enhance existing `core/edi/edi_splitter.py` - add EDI processing
6. Enhance existing `core/edi/upc_utils.py` - add UOM/UPC operations

### Phase 2: Migrate Functions
1. **Boolean Normalization** - Move from utils.py to bool_utils.py
2. **Date/Time Conversion** - Move from utils.py to date_utils.py
3. **Data Transformation** - Move from utils.py to edi_transformer.py
4. **EDI Processing** - Move do_split_edi() to edi_splitter.py
5. **EDI Filtering** - Move filter_edi_file_by_category() to edi_splitter.py
6. **UOM & UPC Operations** - Move apply_retail_uom_transform() and apply_upc_override() to upc_utils.py
7. **File Management** - Move do_clear_old_files() to dispatch/file_utils.py

### Phase 3: Remove Duplicates
1. Remove invFetcher class - use core/edi/inv_fetcher.py instead
2. Remove cRecGenerator class - use core/edi/c_rec_generator.py instead
3. Remove calc_check_digit() and convert_UPCE_to_UPCA() - use core/edi/upc_utils.py instead

### Phase 4: Update Imports
1. Replace all imports from `utils` with new module imports
2. Update tests to import from correct locations
3. Create compatibility layer in utils.py for gradual migration

### Phase 5: Cleanup
1. Remove old functions from utils.py
2. Add proper __init__.py files for new modules
3. Run all tests to verify functionality

## Implementation Timeline

### Week 1
- Create new module structure
- Migrate boolean normalization and date/time conversion functions
- Update imports in affected files
- Run tests

### Week 2
- Migrate data transformation and UOM/UPC operations
- Update EDI splitter module
- Remove duplicate fetcher and generator classes
- Run tests

### Week 3
- Migrate file management function
- Update all remaining imports
- Remove compatibility layer
- Run comprehensive tests

## Benefits

1. **Improved Maintainability**: Smaller, focused modules are easier to understand and modify
2. **Better Testability**: Each module can be tested independently
3. **Reduced Duplication**: Eliminates duplicate functionality across modules
4. **Clearer Architecture**: Well-defined module boundaries based on functionality
5. **Easier Navigation**: Developers can find related functions more easily

## Risks & Mitigation

- **Breaking Changes**: Use compatibility layer to allow gradual migration
- **Test Coverage**: Ensure all existing tests are updated and pass
- **Performance**: Monitor for any performance impacts

## Acceptance Criteria

1. All existing functionality remains intact
2. All tests pass
3. Code compiles without errors
4. Imports are correctly updated across all files
5. New module structure is documented
