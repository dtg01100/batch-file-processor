# BATCH FILE PROCESSOR KNOWLEDGE BASE

**Generated:** 2026-01-30  
**Commit:** c2898be44  
**Branch:** cleanup-refactoring

## OVERVIEW

PyQt6 GUI application for processing EDI/batch files with pluggable converters and send backends. Core: EDI parsing → format conversion → delivery (FTP/Email/Copy).

## STRUCTURE

```
batch-file-processor/
├── interface/          # PyQt6 GUI (models, operations, UI, database)
├── dispatch/          # Core processing (coordinator, EDI processor, send manager, file processor)
├── tests/             # 1600+ tests (unit, integration, operations, ui, convert_backends)
├── migrations/        # DB migration helpers
├── convert_*.py       # Converter plugins (10 at root: csv, fintech, scannerware, etc.)
├── *_backend.py       # Send backends (3 at root: email, ftp, copy)
├── utils.py           # Cross-cutting helpers (EDI parsing, UPC, date/price conversions)
├── create_database.py # Schema creation
├── folders_database_migrator.py  # Sequential migration system
└── run.sh / run_tests.sh         # Entry points
```

## CRITICAL ANTI-PATTERNS

**🚨 SPEC-FIRST DEVELOPMENT (MANDATORY)**  
- ❌ DO NOT implement changes without a spec (except trivial bug fixes)
- ✅ ALWAYS create a spec in `specs/` before implementing new features
- ✅ Spec must be reviewed/approved before implementation begins
- ✅ Use `specs/TEMPLATE.md` as the starting point for all specs
- ✅ Reference the relevant docs in `docs/` for architectural alignment

**Spec is required for:**
- New features or capabilities
- Changes to existing APIs or interfaces
- Database schema changes (migrations)
- New plugins (converters or backends)
- UI changes that affect user workflows
- Refactoring that changes module boundaries
- Changes affecting multiple files/modules

**Spec is NOT required for:**
- Bug fixes with clear root cause
- Documentation updates
- Test additions/improvements
- Code formatting/linting
- Dependency updates (unless breaking changes)

**Never commit when tests are failing**  
- Run `./run_tests.sh` before commit
- Smoke tests must always pass: `pytest -m smoke`

**Commit in logical chunks**  
- ❌ DO NOT create large monolithic commits mixing unrelated changes
- ✅ Separate commits by concern: tests, refactoring, features, docs
- ✅ Each commit should be independently reviewable and revertable
- ✅ Commit message should accurately describe ALL changes in that commit
- ✅ Commit regularly during work; use `wip:` prefix for incomplete work
- ✅ Example: `wip: Add validation logic (error handling pending)`

**Database migrations (SQLite constraints)**  
- ❌ DO NOT delete columns (SQLite limitation)
- ❌ DO NOT skip version numbers (migrations are sequential)
- ❌ DO NOT modify existing migrations (append only)
- ✅ ALWAYS create backup before migration (automatic)

**Virtual environment**  
- ❌ DO NOT run Python commands without activating `.venv`
- ✅ ALWAYS `source .venv/bin/activate` first
- Scripts `run.sh` and `run_tests.sh` handle this internally

**Corpus files**  
- ❌ DO NOT commit `alledi/` directory (production EDI samples, gitignored)

## WHERE TO LOOK

| Task | Location | Notes |
|------|----------|-------|
| Add converter | `convert_to_<format>.py` at root | Inherit `BaseConverter`, define process_record_* methods |
| Add send backend | `<name>_backend.py` at root | Inherit `BaseSendBackend`, implement `_send()` |
| Modify UI | `interface/ui/` | Dialogs, widgets, main_window |
| Change processing logic | `dispatch/coordinator.py` | Main orchestration |
| Add DB migration | `folders_database_migrator.py` | Sequential version blocks |
| Shared utilities | `utils.py`, `convert_base.py` | EDI parsing, converters base |
| Database schema | `create_database.py` | Initial schema creation |
| Validation | `interface/utils/` | Qt validators, validation feedback |
| Tests | `tests/` | Organized by: unit, integration, operations, ui, convert_backends |

## PLUGIN ARCHITECTURE

**Discovery**: Filesystem glob-based  
- Converters: `convert_to_*.py` at root
- Backends: `*_backend.py` at root
- Registry: `plugin_config.PluginRegistry.discover_plugins()`

**Converter pattern**:
```python
# convert_to_myformat.py
from convert_base import BaseConverter, create_edi_convert_wrapper

class MyFormatConverter(BaseConverter):
    PLUGIN_ID = "myformat"
    PLUGIN_NAME = "My Format"
    CONFIG_FIELDS = [...]  # Optional
    
    def initialize_output(self): ...
    def process_record_a(self, record): ...
    def process_record_b(self, record): ...
    def process_record_c(self, record): ...
    def finalize_output(self): ...

edi_convert = create_edi_convert_wrapper(MyFormatConverter)
```

**Backend pattern**:
```python
# mybackend_backend.py
from send_base import BaseSendBackend, create_send_wrapper

class MyBackend(BaseSendBackend):
    PLUGIN_ID = "mybackend"
    PLUGIN_NAME = "My Backend"
    
    def _send(self): ...

do = create_send_wrapper(MyBackend)
```

## DATABASE

**Technology**: SQLite via PyQt6 QtSql  
**Wrapper**: `interface/database/database_manager.DatabaseManager` + `Table` (dataset-like API)  
**Schema**: `create_database.py` builds initial schema  
**Migrations**: Sequential numeric versions in `folders_database_migrator.py`  
**Version storage**: Table `version`, row id=1

**Key tables**: `folders`, `settings`, `processed_files`, `version`  
**Access pattern**: `db["folders"].find(active=True)` or raw SQL via `db.query()`

## TESTING

**Test count**: 1600+ tests  
**Organization**:
- `tests/test_smoke.py` — utility smoke tests
- `tests/test_app_smoke.py` — app startup (31 tests)
- `tests/unit/` — unit tests
- `tests/integration/` — DB migrations, schema
- `tests/operations/` — folder/maintenance ops
- `tests/ui/` — PyQt6 UI tests
- `tests/convert_backends/` — converter parity/baselines

**Quick commands**:
```bash
# Smoke tests (~0.2s)
pytest tests/test_app_smoke.py tests/test_smoke.py -v -m smoke

# Core integration (~7s)
pytest tests/operations/ tests/integration/ -v

# Full suite
./run_tests.sh
```

**Markers**: `smoke`, `unit`, `integration`, `qt`, `convert_backend`, `parity`, `db`  
**Fixtures**: `qapp`, `qtbot` (with fallback), `temp_dir`, `mock_db_manager`, corpus fixtures (skip if missing)

## UI ARCHITECTURE (PyQt6)

**Entry**: `interface/main.py` → creates Application + MainWindow  
**Pattern**: Three-layer signal propagation
1. **Widgets** emit local signals (`ButtonPanel.process_clicked`)
2. **MainWindow** re-emits as window-level API (`main_window.process_requested`)
3. **ApplicationController** connects to business logic

**Key components**:
- `Application` (app.py): Global signals, stylesheet
- `MainWindow` (main_window.py): Composes ButtonPanel + FolderListWidget
- `BaseDialog` (base_dialog.py): validate()/apply() pattern for dialogs
- `FolderListWidget` (widgets/folder_list.py): Active/inactive lists, per-item actions
- Validators: `interface/utils/qt_validators.py` (EMAIL_VALIDATOR, PORT_VALIDATOR)
- Feedback: `interface/utils/validation_feedback.py` (visual styling)
- Dynamic UI: `interface/ui/plugin_ui_generator.py` (builds UI from ConfigField)

## CONVENTIONS

**Python**: 3.11–3.13 (pyproject.toml: `>=3.11,<3.14`)  
**Dependencies**: `requirements.txt` (exact pins) + `pyproject.toml` (ranges)  
**Qt API**: PyQt6 (pytest.ini: `qt_api = pyqt6`)

**Non-standard project layout**:
- No `src/` package — functional modules at root
- Converters/backends live as top-level .py files (plugin convention)
- Dual module+package: `dispatch.py` (legacy) + `dispatch/` (refactored)
- Mixed UI: `dialog.py` (legacy) + `interface/` (refactored GUI)

**Code organization deviations**:
- Multiple venvs committed (`.venv`, `venv`, `test_venv`) — should be gitignored
- Build artifacts present (`htmlcov`, `__pycache__`) — should be gitignored
- Dual packaging metadata (`setup.py` + `pyproject.toml` + `requirements.txt`)

## CROSS-CUTTING CONCERNS

**Widely-used utilities** (multi-module imports):
- `utils.py` — EDI parsing, UPC helpers, date/price conversions (used by all converters/dispatch)
- `convert_base.py` — BaseConverter, CSVConverter, DBEnabledConverter (all converter plugins)
- `send_base.py` — BaseSendBackend (all send backends)
- `plugin_config.py` — PluginConfigMixin, PluginRegistry
- `edi_format_parser.py` — EDI format loading/parsing
- `query_runner.py` — DB query helper (UPC lookups)
- `record_error.py` — Error logging/recording
- `interface/utils/` — Validation helpers for UI
- `interface/database/database_manager.py` — DB access wrapper

**Reuse pattern**: Template Method (base classes) + single-file grab-bag helpers

## BUILD & CI

**No CI configured** (no `.github/workflows`, no `.gitlab-ci.yml`)

**Local automation**:
- `run.sh` — bootstraps `.venv`, installs deps, runs `interface/main.py`
  - Usage: `./run.sh` (GUI) or `./run.sh -a` (automatic/headless)
- `run_tests.sh` — runs pytest with xvfb fallback, includes coverage
  - Usage: `./run_tests.sh`

**Docker**: `Dockerfile` present (devcontainer base, installs ibm-iaccess .deb, uses `--break-system-packages`)

**Qt tests**: Require xvfb or `QT_QPA_PLATFORM=offscreen`

## COMMANDS

```bash
# Run app (GUI)
./run.sh

# Run app (automatic/headless)
./run.sh -a

# Run tests
./run_tests.sh

# Quick smoke tests
pytest -m smoke

# Qt tests headless
QT_QPA_PLATFORM=offscreen pytest tests/ui/ -v

# Coverage
pytest --cov=interface --cov-report=html

# Install deps
pip install -r requirements.txt
```

## COMPLEXITY HOTSPOTS

**Large files (>500 LOC)** requiring attention:
1. `folders_database_migrator.py` (896 lines) — long migration script, many branches
2. `dispatch/coordinator.py` (893 lines) — orchestration, mixes concerns
3. `interface/ui/dialogs/edit_folder_dialog.py` (730 lines) — dialog builder
4. `interface/operations/processing.py` (625 lines) — processing orchestration
5. `convert_base.py` (607 lines) — converter base + helpers
6. `utils.py` (582 lines) — grab-bag utilities
7. `dispatch.py` (569 lines, **max indent 100**) — legacy dispatch, deep nesting

**Refactor candidates**: dispatch modules, utils.py (split by domain), large dialogs

## MIGRATION RULES

**Version storage**: Table `version`, column `version` (TEXT), id=1  
**Current version**: 40  
**Supported range**: v5–v40

**Adding migration**:
1. Edit `folders_database_migrator.py`, add version block:
   ```python
   if db_version_dict["version"] == "40":
       # Apply changes
       db_version.update(dict(id=1, version="41", os=running_platform), ["id"])
       _log_migration_step("40", "41")
   ```
2. Update `create_database.py` if new columns should be in initial schema
3. Update `tests/integration/database_schema_versions.py`: `ALL_VERSIONS`, `CURRENT_VERSION`
4. Add migration tests

**Enforcement**:
- Backup created automatically (`backup_increment.do_backup`)
- PRAGMA foreign_keys ON enforced
- SystemExit if DB newer than app

## DOCUMENTATION

**Design documents** (in `docs/`):
- `ARCHITECTURE.md` — system overview, directory structure, key decisions
- `PLUGIN_DESIGN.md` — converter and backend plugin patterns
- `DATABASE_DESIGN.md` — schema, migrations, access patterns
- `TESTING_DESIGN.md` — testing strategy, patterns, fixtures
- `GUI_DESIGN.md` — UI architecture, signal propagation
- `PROCESSING_DESIGN.md` — file processing pipeline
- `VALIDATION_DESIGN.md` — EDI validation rules
- `ERROR_HANDLING_DESIGN.md` — error handling patterns
- `CONFIGURATION_DESIGN.md` — settings and configuration
- `EDI_FORMAT_DESIGN.md` — EDI format specifications
- `MIGRATION_DESIGN.md` — database migration strategy

**Specs** (in `specs/`):
- `TEMPLATE.md` — template for new feature specs
- `*.md` — approved specs for features/changes

**Test docs**:
- `TEST_STATUS.md` — current test status, known issues
- `tests/README.md` — testing guide
- `tests/SMOKE_TESTS_README.md` — smoke test documentation

**Migration docs**:
- `DATABASE_MIGRATION_GUIDE.md` — migration conventions
- `AUTOMATIC_MIGRATION_GUIDE.md` — DO/DON'T rules

**Other**:
- `ALLEDI_CORPUS_README.md` — corpus usage (never commit)
- `PARITY_VERIFICATION.md` — converter output baseline testing
- Many `*_SUMMARY.md`, `*_COMPLETE.md` files documenting past work

## SPEC WORKFLOW

**Creating a spec**:
1. Copy `specs/TEMPLATE.md` to `specs/<feature-name>.md`
2. Fill in all required sections
3. Reference relevant design docs from `docs/`
4. Include test plan with specific test cases
5. Get spec reviewed/approved before implementing

**Spec structure**:
- **Summary**: What and why (1-2 sentences)
- **Background**: Context and motivation
- **Design**: Technical approach aligned with `docs/`
- **Implementation Plan**: Phased steps with deliverables
- **Testing Strategy**: Test cases, coverage expectations
- **Risk Assessment**: Potential issues and mitigations
- **Success Criteria**: Measurable completion criteria

**During implementation**:
- Reference the spec in commit messages: `feat: Add X (spec: feature-name)`
- Update spec if design changes during implementation
- Mark spec as IMPLEMENTED when complete

**Spec lifecycle**:
```
DRAFT → REVIEW → APPROVED → IN_PROGRESS → IMPLEMENTED
```

## NOTES

**Version mismatches**:
- `pytest`: pyproject wants `>=8.0.0`, requirements.txt pins `==7.4.3`
- `PyQt6`: pyproject wants `>=6.7.0,<6.10`, requirements.txt wants `>=6.6.0`
- `python_requires`: setup.py says `>=3.7`, pyproject says `>=3.11,<3.14`
- **Recommendation**: Treat pyproject.toml as authoritative

**Parity testing**: `tests/convert_backends/test_parity_verification.py`  
- Compares converter outputs to baseline files
- Baselines in `tests/convert_backends/baselines/<backend>/`
- Metadata JSON files enumerate fixtures
- Regenerate with special test flag when intentional changes made

**Deep nesting** (depth 4+):
- Intentional: `tests/convert_backends/baselines/<backend>/` — test fixtures with metadata
- Incidental: venv directories, `__pycache__` — ignore in scans
