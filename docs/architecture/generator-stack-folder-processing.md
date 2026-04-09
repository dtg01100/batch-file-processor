# Generator Stack Architecture for Folder Processing

**Date**: 2026-04-09  
**Request**: "look into using a stack of generators, instead of processing each folder one by one"

## Current Architecture (Sequential Processing)

### Flow Diagram
```
process() 
  → _prepare_processing() → loads ALL folders into memory: list(folders_database.find(...))
  → _iterate_folders() → for folder in folders:
    → orchestrator.process_folder()
      → FolderExecutor.process_folder()
        → Pipeline (validate → split → convert → send)
```

### Current Implementation (orchestrator.py:1688-1706)
```python
@staticmethod
def _iterate_folders(
    orchestrator: "DispatchOrchestrator", folders: list, run_log, processed_files
) -> bool:
    """Iterate over folders and run processing, returning whether any errors occurred."""
    has_errors = False
    for folder in folders:  # ← Eager list iteration
        try:
            result = orchestrator.process_folder(folder, run_log, processed_files)
            if not result.success:
                has_errors = True
        except Exception as folder_error:
            has_errors = True
            # Error handling...
    return has_errors
```

### Problems with Current Approach

1. **Eager Loading**: All folders loaded into memory upfront via `list(folders_database.find(...))`
2. **No Early Termination**: Cannot easily stop/pause/resume mid-processing
3. **Pre-discovery Overhead**: `FolderDiscoveryService.discover_pending_files()` scans ALL folders before any processing starts
4. **Blocking UI**: Must wait for entire folder list processing to complete before getting results
5. **Memory Inefficiency**: For large folder counts, all folder configs + discovered files held in memory
6. **Tight Coupling**: Folder iteration logic mixed with processing and error aggregation

## Proposed Generator Stack Architecture

### Concept: Lazy Generator Chain

```
┌─────────────────────┐
│  folder_generator   │ ← Lazy folder loading from DB
└──────────┬──────────┘
           │ yields one folder at a time
           ▼
┌─────────────────────────┐
│  discovery_generator    │ ← Discovers files for current folder only
└──────────┬──────────────┘
           │ yields (folder, pending_files)
           ▼
┌─────────────────────────┐
│  processing_generator   │ ← Executes pipeline for current folder
└──────────┬──────────────┘
           │ yields FolderResult immediately
           ▼
┌─────────────────────┐
│  result_consumer    │ ← Aggregates results, streams to UI
└─────────────────────┘
```

### Implementation Design

#### 1. Folder Generator (Lazy Loading)
```python
def folder_generator(folders_database, **query_kwargs):
    """Yield folders one at a time from database query.
    
    Args:
        folders_database: Database interface with find() method
        **query_kwargs: Filters like folder_is_active=True, order_by="alias"
    
    Yields:
        dict: Folder configuration
    """
    # Assuming folders_database.find() can return an iterator
    for folder in folders_database.find(**query_kwargs):
        yield folder
```

**Benefits**:
- No upfront `list()` conversion
- Database cursor stays open, rows fetched on-demand
- Can support millions of folders without memory issues

#### 2. File Discovery Generator (Lazy Discovery)
```python
def file_discovery_generator(
    folder_gen: Iterator[dict],
    processed_files_db: Optional[DatabaseInterface],
    discovery_service: FolderDiscoveryService
) -> Iterator[Tuple[dict, List[str]]]:
    """Yield (folder, pending_files) tuples lazily.
    
    Instead of pre-discovering ALL files for ALL folders,
    discover files only when we're about to process that folder.
    
    Args:
        folder_gen: Generator yielding folder configs
        processed_files_db: Processed files database for filtering
        discovery_service: Service for file discovery
    
    Yields:
        Tuple of (folder_config, list_of_pending_files)
    """
    for folder in folder_gen:
        folder_path = folder.get("folder_name", "")
        
        # Discover files for THIS folder only
        pending_files = discovery_service.discover_for_folder(
            folder_path,
            processed_files=processed_files_db,
            folder=folder
        )
        
        yield folder, pending_files or []
```

**Benefits**:
- File discovery happens just-in-time
- No wasted work if processing stops early
- Can skip expensive hash calculations for folders that won't be processed

#### 3. Processing Generator (Lazy Execution)
```python
def processing_generator(
    discovery_gen: Iterator[Tuple[dict, List[str]]],
    orchestrator: "DispatchOrchestrator",
    run_log: Any
) -> Iterator[FolderResult]:
    """Yield FolderResult as each folder completes.
    
    Args:
        discovery_gen: Generator yielding (folder, pending_files)
        orchestrator: DispatchOrchestrator instance
        run_log: Run log for recording activity
    
    Yields:
        FolderResult for each processed folder
    """
    for folder, pending_files in discovery_gen:
        try:
            # Process with pre-discovered files
            result = orchestrator.process_folder(
                folder,
                run_log,
                pre_discovered_files=pending_files or None
            )
            yield result  # ← Stream result immediately to consumer
            
        except Exception as e:
            # Yield error result instead of raising
            yield FolderResult(
                folder_name=folder.get("folder_name", "unknown"),
                alias=folder.get("alias", ""),
                files_processed=0,
                files_failed=1,
                errors=[str(e)],
                success=False
            )
```

**Benefits**:
- Results available immediately after each folder
- Exceptions converted to error results (non-blocking)
- Consumer can aggregate, filter, or stream to UI

#### 4. Consumer (Final Aggregation)
```python
def process_folders_generator(
    self,
    folders_database,
    run_log,
    processed_files=None,
    stop_on_error: bool = False
) -> Iterator[FolderResult]:
    """Main entry point: generator-based folder processing.
    
    Args:
        folders_database: Database interface for folder queries
        run_log: Run log for recording activity
        processed_files: Optional processed files database
        stop_on_error: If True, stop processing after first error
    
    Yields:
        FolderResult for each folder as it completes
    """
    # Build generator chain
    folder_gen = self.folder_generator(folders_database, folder_is_active=True)
    discovery_gen = self.file_discovery_generator(
        folder_gen, processed_files, self.discovery_service
    )
    result_gen = self.processing_generator(discovery_gen, run_log)
    
    # Consume and optionally yield results
    for result in result_gen:
        yield result  # ← Stream to caller (UI can update in real-time)
        
        if stop_on_error and not result.success:
            logger.warning("Stopping processing due to error in folder: %s", 
                          result.folder_name)
            break
```

### Usage Examples

#### Example 1: Simple Iteration (Backward Compatible)
```python
# Old way (still works)
has_errors = orchestrator.process(folders_db, run_log, processed_files)

# New way (generator, same behavior)
results = list(orchestrator.process_folders_generator(folders_db, run_log, processed_files))
has_errors = any(not r.success for r in results)
```

#### Example 2: Streaming to UI (Real-time Updates)
```python
# Stream results to UI as they complete
for result in orchestrator.process_folders_generator(folders_db, run_log, processed_files):
    progress_callback.update(
        folder=result.alias,
        files_processed=result.files_processed,
        files_failed=result.files_failed,
        success=result.success
    )
    # UI updates immediately, no waiting for all folders!
```

#### Example 3: Early Termination
```python
# Stop after first critical error
for result in orchestrator.process_folders_generator(
    folders_db, run_log, processed_files, stop_on_error=True
):
    if not result.success:
        logger.error(f"Critical error in {result.folder_name}, stopping")
        break
```

#### Example 4: Pause/Resume Support
```python
# Save state for resume later
def process_with_checkpoint(orchestrator, folders_db, checkpoint_file):
    checkpoint = load_checkpoint(checkpoint_file)
    last_folder = checkpoint.get("last_folder")
    
    folder_gen = orchestrator.folder_generator(
        folders_db, 
        folder_is_active=True,
        after_alias=last_folder  # Skip already-processed
    )
    
    for result in orchestrator.process_folders_generator_from(folder_gen):
        save_checkpoint(checkpoint_file, last_folder=result.alias)
        yield result
```

## Benefits Comparison

| Aspect | Current (Sequential) | Generator Stack |
|--------|---------------------|-----------------|
| **Memory Usage** | O(n) for all folders + files | O(1) per folder |
| **Time to First Result** | Wait for ALL folders | Immediate (after 1st folder) |
| **Early Termination** | Requires exception or flag | Natural with `break` |
| **Pause/Resume** | Not supported | Easy with generator state |
| **Lazy Discovery** | No (pre-discovers all) | Yes (JIT discovery) |
| **UI Responsiveness** | Blocking updates | Real-time streaming |
| **Testability** | Must mock entire flow | Test each generator independently |
| **Composability** | Tightly coupled | Chain/filter/map generators |

## Trade-offs and Considerations

### ⚠️ Complexity
- **Concern**: More abstract than simple for-loop
- **Mitigation**: Well-named generators with clear responsibilities; comprehensive docstrings

### ⚠️ Debugging
- **Concern**: Stack traces less intuitive with generators
- **Mitigation**: Use `yield from` carefully; add logging at each generator boundary

### ⚠️ State Management
- **Concern**: Mutable state across yields can cause bugs
- **Mitigation**: Generators should be stateless or use explicit state objects

### ⚠️ Database Connections
- **Concern**: Connection must stay open during iteration
- **Mitigation**: Use context managers; ensure connection pooling handles long-lived cursors

### ⚠️ Backward Compatibility
- **Concern**: Existing code expects `process()` to return `(has_errors, summary)`
- **Mitigation**: Keep `process()` method, add new generator method as alternative

## Recommended Implementation Strategy

### Phase 1: Foundation (Low Risk, Additive)
1. Create `folder_generator()` function
2. Create `file_discovery_generator()` function
3. Create `processing_generator()` function
4. Add unit tests for each generator in isolation

**Estimated Effort**: 2-3 hours  
**Risk**: Very Low (additive, no existing code changed)

### Phase 2: Integration (Medium Risk)
1. Refactor `_iterate_folders()` to use generator chain internally
2. Keep same return signature for backward compatibility
3. Add integration tests comparing old vs new behavior

**Estimated Effort**: 3-4 hours  
**Risk**: Medium (modifies existing flow, but keeps API)

### Phase 3: Streaming API (Optional Enhancement)
1. Make `process()` itself a generator method
2. Update UI code to consume streaming results
3. Add pause/resume checkpoint support

**Estimated Effort**: 4-6 hours  
**Risk**: Medium-High (changes public API, requires UI updates)

## Minimal Proof of Concept

Here's a minimal implementation that demonstrates the concept:

```python
def process_folders_streaming(
    self,
    folders_database,
    run_log,
    processed_files=None
) -> Iterator[FolderResult]:
    """Generator-based folder processing with streaming results.
    
    This is a drop-in replacement for the folder iteration loop
    that yields results as each folder completes.
    """
    # Lazy folder loading (assumes find() returns iterator)
    folders = folders_database.find(folder_is_active=True, order_by="alias")
    
    for folder in folders:
        alias = folder.get("alias", "unknown")
        try:
            logger.debug("Processing folder: %s", alias)
            
            # Process single folder
            result = self.process_folder(folder, run_log, processed_files)
            
            # Yield result immediately
            yield result
            
        except Exception as e:
            logger.exception("Error processing folder %s", alias)
            yield FolderResult(
                folder_name=alias,
                alias=alias,
                files_processed=0,
                files_failed=1,
                errors=[str(e)],
                success=False
            )

# Usage:
# for result in orchestrator.process_folders_streaming(db, run_log, processed_files):
#     print(f"{result.alias}: {result.files_processed} files, success={result.success}")
```

## Next Steps

1. **Review this design** with team/stakeholders
2. **Implement Phase 1** generators with tests
3. **Benchmark** memory usage and time-to-first-result vs current approach
4. **Decide** whether to proceed with Phase 2/3 based on results

## References

- Python Generator Documentation: https://docs.python.org/3/howto/functional.html#generators
- Iterator vs Iterable: https://docs.python.org/3/library/stdtypes.html#iterator-types
- `yield from` Syntax: https://peps.python.org/pep-0380/
- Coroutines and Async: https://docs.python.org/3/library/asyncio-task.html
