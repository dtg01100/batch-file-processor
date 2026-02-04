# Memories

## Patterns

## Decisions

### mem-1770214971-2971
> Designed comprehensive 4-phase refactoring approach: Phase 1 (Critical Risk: dispatch.py, folders_migrator.py), Phase 2 (High Risk: coordinator.py, processing.py), Phase 3 (Medium Risk: utils.py, convert_base.py), Phase 4 (Final Refinement: UI cleanup). Key strategies: feature flags, git rollback, <5% performance variance tolerance, backward compatibility maintained throughout. 8-week timeline with risk mitigation at each phase.
<!-- tags: refactoring-design, risk-mitigation, phase-strategy | created: 2026-02-04 -->

### mem-1770214736-f9b4
> Identified 7 complexity hotspots with risk categorization: 2 Critical (dispatch.py with 25-level nesting, folders_database_migrator.py), 2 High (coordinator.py with poor test coverage, processing.py), 3 Medium (utils.py with 66 imports, convert_base.py, edit_folder_dialog.py). Established baseline with 210+ tests passing. Critical finding: dispatch.py and coordinator.py have highest risk due to poor test coverage and central role in processing.
<!-- tags: complexity-analysis, refactoring, risk-assessment | created: 2026-02-04 -->

## Fixes

### mem-1770215048-2cf5
> Tests fail due to missing edi_tweaks module import
<!-- tags: testing, error-handling | created: 2026-02-04 -->

## Context

### mem-1770215048-7106
> Testing strategy documented in specs/refactoring-task/testing_strategy.md
<!-- tags: documentation, testing | created: 2026-02-04 -->
