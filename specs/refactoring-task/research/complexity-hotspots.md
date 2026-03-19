# Complexity Hotspots Analysis

## Large Files (>500 LOC)

Based on line count analysis, the following files are complexity hotspots requiring refactoring attention:

1. **folders_database_migrator.py** (1056 lines)
   - Long migration script with many conditional branches
   - Handles database schema evolution from v5 to v40
   - Sequential migration logic makes file difficult to maintain
   - **Refactoring opportunity**: Split into individual migration modules

2. **dispatch/coordinator.py** (893 lines)
   - Main orchestration logic mixing multiple concerns
   - Handles file processing workflow coordination
   - **Refactoring opportunity**: Extract separate workflow, state management, and orchestration components

3. **utils.py** (674 lines)
   - Grab-bag utility functions across multiple domains
   - Contains EDI parsing, UPC helpers, date/price conversions, boolean normalization
   - **Refactoring opportunity**: Split by domain into separate utility modules

4. **interface/operations/processing.py** (675 lines)
   - Processing orchestration with mixed responsibilities
   - **Refactoring opportunity**: Separate concerns into workflow managers

5. **interface/ui/dialogs/edit_folder_dialog.py** (614 lines)
   - Large dialog builder with complex UI generation
   - **Refactoring opportunity**: Extract dialog components and validation logic

6. **convert_base.py** (607 lines)
   - Base converter class plus helper utilities
   - Mixes abstractions with concrete implementations
   - **Refactoring opportunity**: Separate base classes from utility helpers

7. **dispatch.py** (569 lines, **max indent 100**)
   - Legacy dispatch module with deep nesting
   - **Refactoring opportunity**: Consolidate with dispatch/ package or phase out

## Priority Assessment

**High Priority (Immediate Impact)**
- dispatch.py (deep nesting, legacy code)
- utils.py (cross-cutting utility, widely used)
- folders_database_migrator.py (maintenance bottleneck)

**Medium Priority (Maintainability)**
- dispatch/coordinator.py (core orchestration)
- interface/operations/processing.py (workflow complexity)
- convert_base.py (plugin architecture foundation)

**Lower Priority (UI Complexity)**
- interface/ui/dialogs/edit_folder_dialog.py (UI can tolerate more complexity)

## Refactoring Strategy

1. **Preserve Output Formats**: Ensure all converters and backends maintain identical output
2. **Incremental Approach**: Refactor one hotspot at a time with comprehensive testing
3. **Backward Compatibility**: Maintain existing APIs during transition
4. **Test Coverage**: Leverage 1600+ existing tests to prevent regressions