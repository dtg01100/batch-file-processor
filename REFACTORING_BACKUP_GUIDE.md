# Refactoring Backup & Rollback Guide

**Purpose**: This document provides procedures for creating backups and rolling back during the major refactoring initiative.

## Current Status: Phase 1 Complete ✅

- **Baseline**: 177 core integration tests passing
- **Smoke Tests**: 10/10 passing
- **Git Tags**: `phase-1-start`, `phase-1-complete` created
- **Environment**: PyQt6 dependencies installed and working

## Rollback Procedures

### 1. Quick Rollback to Any Phase

```bash
# Rollback to specific phase completion
git checkout phase-1-complete    # Rollback to end of Phase 1
git checkout phase-2-complete    # Rollback to end of Phase 2 (when created)
git checkout phase-3-complete    # Rollback to end of Phase 3 (when created)

# Continue working from rollback point
git checkout -b rollback-branch-name
```

### 2. Emergency Rollback to Master

```bash
# If all else fails, return to stable master
git checkout master
git pull origin master
```

## Backup Procedures (Each Phase)

### Before Each Phase Start
```bash
# Create database backup
cp database.db database.db.phase-X-start.backup

# Tag current state
git tag -a phase-X-start -m "Phase X start point"
```

### After Each Phase Complete
```bash
# Create database backup
cp database.db database.db.phase-X-complete.backup

# Tag current state
git tag -a phase-X-complete -m "Phase X complete point"

# Verify tests still pass
./run_tests.sh
```

## Phase-Specific Rollback Notes

### Phase 1 (Risk Assessment) ✅
- **Rollback**: Use `git checkout phase-1-start`
- **Data**: No database changes expected
- **Impact**: Minimal

### Phase 2 (Utils Refactoring) - RISK: MEDIUM
- **Rollback**: Use `git checkout phase-1-complete`
- **Data**: No database schema changes
- **Impact**: Import statement changes across 140+ files
- **Verification**: Run core smoke tests first

### Phase 3 (Legacy Dispatch Migration) - RISK: HIGH
- **Rollback**: Use `git checkout phase-2-complete`  
- **Data**: No database schema changes
- **Impact**: Core processing functionality
- **Verification**: Run integration tests first

### Phase 4 (Large File Refactoring) - RISK: HIGH
- **Rollback**: Use `git checkout phase-3-complete`
- **Data**: No database schema changes  
- **Impact**: Major architectural changes
- **Verification**: Full test suite required

## Emergency Contacts & Procedures

### If Tests Fail During Refactoring
1. **Stop immediately** - Don't commit broken code
2. **Assess impact** - Is it core functionality or edge case?
3. **Rollback if needed** - Use appropriate phase tag
4. **Document the issue** - Add to this guide

### Critical Failure Paths
1. **Database corruption** (unlikely, no schema changes planned)
   ```bash
   cp database.db.phase-X-complete.backup database.db
   ```

2. **Import system broken** (likely during Phase 2)
   ```bash
   git checkout phase-1-complete
   # Run: python -c "import utils; print('Utils OK')"
   ```

3. **Processing pipeline broken** (likely during Phase 3)
   ```bash
   git checkout phase-2-complete  
   # Run: python -c "import dispatch; print('Dispatch OK')"
   ```

## Recovery Testing After Rollback

### Minimal Smoke Test (Quick)
```bash
source .venv/bin/activate
python -m pytest tests/test_smoke.py -v
```

### Integration Test (Medium)
```bash  
source .venv/bin/activate
python -m pytest tests/operations/ tests/integration/ -v --tb=short
```

### Full Test Suite (Comprehensive)
```bash
./run_tests.sh
```

## Phase Progress Tracking

| Phase | Status | Rollback Point | Verification |
|-------|--------|----------------|--------------|
| Phase 1 | ✅ Complete | `phase-1-complete` | Smoke tests pass |
| Phase 2 | 🚧 Not Started | `phase-1-complete` | TBD |
| Phase 3 | ⏳ Pending | `phase-2-complete` | TBD |
| Phase 4 | ⏳ Pending | `phase-3-complete` | TBD |
| Phase 5 | ⏳ Pending | `phase-4-complete` | TBD |

## Automation Scripts (Optional)

### Create Phase Backup Script
```bash
#!/bin/bash
# backup_phase.sh
PHASE=$1
echo "Creating backup for Phase $PHASE..."
cp database.db database.db.phase-$PHASE-start.backup
git tag -a phase-$PHASE-start -m "Phase $PHASE start point"
echo "Phase $PHASE backup complete."
```

### Complete Phase Script  
```bash
#!/bin/bash
# complete_phase.sh
PHASE=$1
echo "Completing Phase $PHASE..."
cp database.db database.db.phase-$PHASE-complete.backup
git tag -a phase-$PHASE-complete -m "Phase $PHASE complete point"
./run_tests.sh
echo "Phase $PHASE complete with tests passing."
```

## Decision Points

### When to Rollback vs Continue
- **Rollback**: Critical functionality broken, tests failing > 10%
- **Continue**: Minor issues, edge cases, < 5% test failures
- **Document**: Any rollback reasons for future reference

### When to Create Additional Backups
- Before any risky refactoring step
- After any successful major milestone  
- When uncertain about next steps

---

**Remember**: The goal is progress, not perfection. It's better to rollback and try a different approach than to push forward with broken functionality.

**Last Updated**: 2026-02-09  
**Current Phase**: Phase 2 (Utils Refactoring)