# Spec: [Feature Name]

**Status:** DRAFT | REVIEW | APPROVED | IN_PROGRESS | IMPLEMENTED  
**Author:** [Name]  
**Created:** YYYY-MM-DD  
**Updated:** YYYY-MM-DD

---

## 1. Summary

[1-2 sentence description of what this change does and why it's needed]

---

## 2. Background

### 2.1 Problem Statement

[What problem does this solve? What's the current limitation or issue?]

### 2.2 Motivation

[Why is this important? What's the business value or user benefit?]

### 2.3 Prior Art

[Have similar solutions been attempted? What can we learn from existing approaches?]

---

## 3. Design

### 3.1 Architecture Alignment

[How does this align with the existing architecture? Reference relevant docs:]

- [ ] Reviewed `docs/ARCHITECTURE.md`
- [ ] Reviewed `docs/PLUGIN_DESIGN.md` (if adding plugins)
- [ ] Reviewed `docs/DATABASE_DESIGN.md` (if changing schema)
- [ ] Reviewed `docs/GUI_DESIGN.md` (if changing UI)
- [ ] Reviewed `docs/TESTING_DESIGN.md` (for test patterns)
- [ ] Reviewed `docs/PROCESSING_DESIGN.md` (if changing processing)
- [ ] Other relevant docs: [list]

### 3.2 Technical Approach

[Describe the technical solution. Include:]

**Components affected:**
- [ ] `interface/` — [describe changes]
- [ ] `dispatch/` — [describe changes]
- [ ] `convert_*.py` — [describe changes]
- [ ] `*_backend.py` — [describe changes]
- [ ] `utils.py` — [describe changes]
- [ ] Database schema — [describe changes]
- [ ] Other: [list]

**API changes:**
```python
# Show function signatures, class interfaces, or schema changes
```

**Data flow:**
```
[Diagram or description of data flow changes]
```

### 3.3 Alternatives Considered

| Alternative | Pros | Cons | Why Not Chosen |
|-------------|------|------|----------------|
| [Option 1] | | | |
| [Option 2] | | | |

---

## 4. Implementation Plan

### Phase 1: [Name] (Estimated: X days)

- [ ] Task 1.1: [Description]
- [ ] Task 1.2: [Description]
- [ ] Deliverable: [What's completed at end of phase]

### Phase 2: [Name] (Estimated: X days)

- [ ] Task 2.1: [Description]
- [ ] Task 2.2: [Description]
- [ ] Deliverable: [What's completed at end of phase]

### Phase 3: Testing & Documentation (Estimated: X days)

- [ ] Write unit tests
- [ ] Write integration tests
- [ ] Update documentation
- [ ] Deliverable: All tests passing, docs updated

---

## 5. Database Changes (if applicable)

### 5.1 Schema Changes

```sql
-- New columns/tables
ALTER TABLE folders ADD COLUMN new_column TEXT DEFAULT '';
```

### 5.2 Migration Strategy

- Current version: 39
- Target version: 40
- Migration file: `folders_database_migrator.py`
- Backup: Automatic via `backup_increment.do_backup`

### 5.3 Migration Checklist

- [ ] Add migration block to `folders_database_migrator.py`
- [ ] Update `create_database.py` for fresh installs
- [ ] Update `tests/integration/database_schema_versions.py`
- [ ] Add migration tests

---

## 6. Testing Strategy

### 6.1 Test Cases

| Test Case | Type | Description | Expected Result |
|-----------|------|-------------|-----------------|
| test_feature_basic | unit | Basic functionality | [Expected] |
| test_feature_edge | unit | Edge case handling | [Expected] |
| test_feature_integration | integration | End-to-end flow | [Expected] |

### 6.2 Test File Locations

- Unit tests: `tests/unit/test_[feature].py`
- Integration tests: `tests/integration/test_[feature].py`
- UI tests: `tests/ui/test_[feature].py` (if applicable)

### 6.3 Coverage Requirements

- [ ] New code covered by tests
- [ ] Existing tests still pass
- [ ] Smoke tests pass: `pytest -m smoke`

---

## 7. Risk Assessment

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| [Risk 1] | Low/Med/High | Low/Med/High | [Mitigation] |
| [Risk 2] | Low/Med/High | Low/Med/High | [Mitigation] |

### 7.1 Rollback Plan

[How to revert if something goes wrong]

---

## 8. Success Criteria

- [ ] All existing tests pass
- [ ] New tests pass with [X]% coverage
- [ ] No functionality regression
- [ ] Documentation updated
- [ ] [Feature-specific criterion]
- [ ] [Feature-specific criterion]

---

## 9. Open Questions

1. [Question that needs resolution before/during implementation]
2. [Question that needs resolution before/during implementation]

---

## 10. Appendix

### 10.1 References

- [Link to relevant issue/ticket]
- [Link to related discussion]
- [Link to external documentation]

### 10.2 Changelog

| Date | Author | Change |
|------|--------|--------|
| YYYY-MM-DD | [Name] | Initial draft |
| YYYY-MM-DD | [Name] | [Change description] |
