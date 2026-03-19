# Legacy Dispatch Removal & Pipeline Migration Plan

**Date:** March 9, 2026  
**Priority:** High  
**Status:** In Progress

## Objective

Remove all legacy dispatch code and make the processing pipeline the sole processing mechanism.

## Current State

### Legacy Code Locations
1. `dispatch/orchestrator.py` - Contains both legacy (`_process_folder_legacy`, `_process_file_legacy`) and pipeline methods
2. `dispatch/send_manager.py` - Used by both legacy and pipeline
3. Multiple conditional checks: `if self.config.use_pipeline`

### Pipeline Components
- `dispatch/pipeline/validator.py` - EDI validation step
- `dispatch/pipeline/splitter.py` - EDI splitting step  
- `dispatch/pipeline/converter.py` - EDI conversion step
- `dispatch/pipeline/tweaker.py` - EDI tweaking step
- `dispatch/file_processor.py` - File processing step (if exists)

## Issues Identified

### 1. Pipeline Not Properly Initialized
The pipeline steps are not being initialized in the main application, causing fallback to legacy mode.

### 2. Tests Using Legacy Mode
Many tests explicitly set `use_pipeline=False` or don't configure pipeline steps.

### 3. Missing Pipeline Configuration
No centralized pipeline initialization in the application.

## Implementation Plan

### Phase 1: Make Pipeline Default (Immediate)

**Tasks:**
1. ✅ Remove `use_pipeline` configuration flag
2. ✅ Make pipeline the default processing mode
3. ✅ Initialize pipeline steps in application startup
4. ✅ Update orchestrator to always use pipeline

**Files to Modify:**
- `dispatch/orchestrator.py` - Remove legacy methods, make pipeline default
- `interface/qt/app.py` - Add pipeline initialization
- `dispatch/orchestrator.py::DispatchConfig` - Remove `use_pipeline` flag

### Phase 2: Remove Legacy Code (Short-term)

**Tasks:**
1. Delete `_process_folder_legacy()` method
2. Delete `_process_file_legacy()` method  
3. Remove `send_manager` dependency from orchestrator (keep for backends only)
4. Clean up conditional logic

**Files to Modify:**
- `dispatch/orchestrator.py` - Remove ~400 lines of legacy code
- `dispatch/send_manager.py` - Simplify (keep only backend sending)

### Phase 3: Update Tests (Short-term)

**Tasks:**
1. Update all tests to configure pipeline steps
2. Remove `use_pipeline=False` from tests
3. Create pipeline configuration fixture
4. Verify all tests pass with pipeline

**Files to Modify:**
- `tests/integration/test_complete_workflows_simple.py`
- `tests/integration/test_all_processing_flows.py`
- `tests/integration/test_real_world_scenarios.py`
- All other integration tests

### Phase 4: Pipeline Enhancement (Medium-term)

**Tasks:**
1. Add comprehensive pipeline logging
2. Improve error handling in pipeline steps
3. Add pipeline performance monitoring
4. Document pipeline architecture

## Technical Details

### Pipeline Initialization

```python
# Example pipeline initialization
from dispatch.pipeline.validator import EDIValidatorStep
from dispatch.pipeline.splitter import EDISplitterStep
from dispatch.pipeline.converter import EDIConverterStep
from dispatch.pipeline.tweaker import EDITweakerStep

# Create pipeline steps
validator_step = EDIValidatorStep()
splitter_step = EDISplitterStep()
converter_step = EDIConverterStep()
tweaker_step = EDITweakerStep()

# Configure orchestrator with pipeline
config = DispatchConfig(
    backends={'copy': CopyBackend()},
    settings={},
    validator_step=validator_step,
    splitter_step=splitter_step,
    converter_step=converter_step,
    tweaker_step=tweaker_step,
    # use_pipeline=True  # REMOVE THIS - always use pipeline
)
```

### Orchestrator Changes

**Remove:**
- `_process_folder_legacy()` method (~100 lines)
- `_process_file_legacy()` method (~150 lines)
- `use_pipeline` configuration flag
- All `if self.config.use_pipeline` conditionals

**Keep:**
- `process_folder()` - Main entry point
- `process_folder_with_pipeline()` - Rename to `process_folder()`
- `_process_file_with_pipeline()` - Rename to `_process_file()`
- Pipeline step execution logic

### Test Updates

All tests need to configure pipeline steps:

```python
@pytest.fixture
def pipeline_config():
    """Configure pipeline steps for tests."""
    from dispatch.pipeline.validator import EDIValidatorStep
    from dispatch.pipeline.converter import EDIConverterStep
    from dispatch.pipeline.tweaker import EDITweakerStep
    
    return {
        'validator_step': EDIValidatorStep(),
        'converter_step': EDIConverterStep(),
        'tweaker_step': EDITweakerStep(),
    }

def test_workflow(test_environment, pipeline_config):
    config = DispatchConfig(
        backends={'copy': CopyBackend()},
        settings={},
        **pipeline_config  # Always configure pipeline
    )
    orchestrator = DispatchOrchestrator(config)
    # ... test code
```

## Migration Checklist

### Code Changes
- [ ] Remove `use_pipeline` flag from DispatchConfig
- [ ] Delete `_process_folder_legacy()` method
- [ ] Delete `_process_file_legacy()` method
- [ ] Remove conditional logic in `process_folder()`
- [ ] Rename `process_folder_with_pipeline()` → `process_folder()`
- [ ] Rename `_process_file_with_pipeline()` → `_process_file()`
- [ ] Add pipeline initialization to main application
- [ ] Update imports to use pipeline modules

### Test Updates
- [ ] Create pipeline configuration fixture
- [ ] Update `test_complete_workflows_simple.py`
- [ ] Update `test_all_processing_flows.py`
- [ ] Update `test_real_world_scenarios.py`
- [ ] Update all other integration tests
- [ ] Verify all tests pass
- [ ] Remove legacy test code

### Documentation
- [ ] Update SYSTEM_ARCHITECTURE.md
- [ ] Document pipeline initialization
- [ ] Create pipeline usage guide
- [ ] Update API documentation

## Risks & Mitigation

### Risk 1: Pipeline Not Working
**Mitigation:** 
- Keep legacy code in a branch until all tests pass
- Test extensively with real EDI files
- Gradual rollout with feature flag

### Risk 2: Performance Regression
**Mitigation:**
- Benchmark pipeline vs legacy
- Profile pipeline execution
- Optimize hot paths

### Risk 3: Breaking Changes
**Mitigation:**
- Maintain API compatibility where possible
- Document breaking changes
- Provide migration guide

## Success Criteria

1. ✅ All legacy code removed from `orchestrator.py`
2. ✅ Pipeline is the only processing mode
3. ✅ All tests pass with pipeline
4. ✅ No performance regression
5. ✅ Documentation updated

## Timeline

- **Phase 1:** 1-2 days (Make pipeline default)
- **Phase 2:** 2-3 days (Remove legacy code)
- **Phase 3:** 3-5 days (Update all tests)
- **Phase 4:** 1-2 weeks (Enhancements & documentation)

**Total Estimated Time:** 2-3 weeks

---

**Next Steps:**
1. Review and approve this plan
2. Create feature branch for migration
3. Start with Phase 1 (make pipeline default)
4. Run full test suite after each phase
5. Deploy to staging for validation
