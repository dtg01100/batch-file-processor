# Batch File Processor

A **local web application** (FastAPI + Docker) that processes EDI (Electronic Data Interchange) files through a configurable pipeline — validating, splitting, converting, and sending files via FTP, SMTP, HTTP, or local filesystem copy.

The processing core (`dispatch/`, `backend/`, `core/`) is the battle-tested engine from the original desktop application; the Qt interface and frozen-binary build machinery were removed in the webapp pivot.

## How it works

1. **Import** a legacy `folders.db` from the desktop app (or start fresh).
2. During import you specify a **base directory** — the root that all configured folder paths are relative to. Legacy absolute paths (`C:\Data\Incoming\X`) are stripped to relative paths (`Data/Incoming/X`) so they work inside the container.
3. The webapp resolves each relative path against the base-dir (a mounted volume) at run time.
4. **Run** the configured folders: files found in each folder's input directory are validated, converted, and delivered via the folder's configured backends.
5. Results are tracked in SQLite and shown in the UI.

## Quick Start (Docker)

```bash
# Build and start
docker compose up -d

# Open the UI
open http://localhost:8000
```

The compose file mounts `./data` as the base-dir volume (`/data`) and stores the
database in `./data/config` (`BFS_DATA_DIR`). Drop incoming files into
`./data/<relative-path>/...` so the configured folders can find them.

## Quick Start (local dev)

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

# Run the webapp (base-dir defaults to ./data; binds 127.0.0.1:8000 by default)
BFS_BASE_DIR=./data python -m webapp.main
# opt in to remote access:
uvicorn webapp.main:app --host 0.0.0.0 --port 8000
```

> **Phase 6.1 (2026-08-18):** the default bind is now `127.0.0.1:8000`
> to match the spec's single-host local-first posture. The Docker
> compose file likewise binds `127.0.0.1:8000:8000`. To expose the
> dashboard to the LAN, change the compose `ports:` line to `"8000:8000"`
> or pass `--host 0.0.0.0` to uvicorn.

### Environment variables

| Variable | Default | Purpose |
|----------|---------|---------|
| `BFS_BASE_DIR` | `./data` | Base directory that configured folder paths resolve against |
| `BFS_DATA_DIR` | `<base_dir>/config` | Where `folders.db` lives |
| `BFS_HOST` | `127.0.0.1` | Interface uvicorn binds (Phase 6.1; opt in to remote access with `0.0.0.0`) |
| `BFS_PORT` | `8000` | TCP port uvicorn binds |

### API

| Endpoint | Description |
|----------|-------------|
| `GET /api/health` | Liveness + paths |
| `GET /api/config` | Base-dir, data-dir, DB status, counts |
| `POST /api/import` | Multipart upload of a legacy `folders.db` (+ optional `base_dir`, `platform`) |
| `POST /api/preview/edi` | Classify an EDI upload (parse-only preview) |
| `GET /api/folders` | Configured folders (relative + resolved paths) |
| `GET /api/folders/{id}` | One folder (full edit schema) |
| `PUT /api/folders/{id}` | Save one folder |
| `POST /api/run` | Start a background processing run |
| `POST /api/resend` | Start a background resend run |
| `POST /api/folders/{id}/run` | Run a single folder |
| `GET /api/runs` | Recent runs |
| `GET /api/runs/{run_id}` | Run detail (poll while running; includes duration + throughput) |
| `GET /api/runs/{run_id}/log` | SSE stream of the run's per-folder logs |
| `GET /api/processed-files` | Recently processed files |
| `GET /api/processed-files/flagged` | Processed files with resend-flag info |
| `POST /api/processed-files/{id}/resend` | Flag a row for resend |
| `POST /api/processed-files/resend-batch` | Flag many rows for resend |
| `POST /api/processed-files/clear-flags` | Clear every resend flag |
| `POST /api/maintenance/clear-processed` | Bulk-delete processed rows |
| `POST /api/maintenance/mark-processed` | Record a single file as processed |
| `POST /api/maintenance/export-processed` | Write a CSV report for a folder |
| `GET /api/maintenance/download` | Download a previously-written report |
| `GET /api/schedule` | Current scheduler state + runs triggered |
| `POST /api/schedule` | Enable/disable the scheduler + set interval |
| `GET /api/watched` | Watched folders + live watcher health (last tick / last run / last error) |
| `POST /api/watcher/refresh` | Force the watcher supervisor to re-read the watch list |
| `GET /api/errors` | Error-ledger rows + per-folder counts |
| `GET /api/errors/file` | Download a raw error-text artifact |
| `GET /api/errors/folder-file` | Download one folder's full error text |
| `POST /api/errors/clear` | Delete error-ledger rows (optionally per folder) |
| `GET /api/backups` | List timestamped backup files |
| `POST /api/backup/create` | Snapshot the active DB |
| `POST /api/backup/restore` | Restore a named backup as the active DB |
| `GET /api/backup/download` | Download a backup file |

### Running Tests

```bash
# Run all tests
make test

# Webapp-specific (importer rebasing, runner, API)
pytest tests/webapp

# Unit tests
pytest -m unit
```

## Documentation

**📖 [Complete Documentation](DOCUMENTATION.md)** - Start here for comprehensive guides

### Key Documentation

- **[EDI Format Guide](docs/user-guide/EDI_FORMAT_GUIDE.md)** - Configure and understand EDI formats
- **[Testing Guide](docs/testing/TESTING.md)** - Test suite documentation
- **[Migration Guide](docs/migrations/AUTOMATIC_MIGRATION_GUIDE.md)** - Database migration
- **[Quick Reference](docs/user-guide/QUICK_REFERENCE.md)** - Fast lookup guide

## Features

- **Base-dir import**: Import legacy databases and rebase all absolute paths to a configured base-dir
- **Folder Monitoring**: Process files in configured directories
- **EDI Processing**: Parse and validate EDI format files (A/B/C record structure)
- **Format Conversion**: Transform EDI files into various business-specific formats (CSV, Excel, Fintech, E-Store, etc.)
- **Multi-Channel Delivery**: Send processed files via FTP, email, HTTP, or local file copy
- **Database Tracking**: SQLite database for configuration and processed file tracking
- **Pipeline Processing**: Configurable validation → splitting → conversion → tweaks pipeline
- **Background runs**: Each run is executed in a worker thread with a pollable status

## Project Structure

```
batch-file-processor/
├── webapp/         # FastAPI app, base-dir importer, runner, static UI
├── core/           # Core utilities, EDI parser, database abstraction
├── dispatch/       # Pipeline orchestration and file processing
├── backend/        # FTP, SMTP, HTTP, and copy backend clients
├── interface/      # Non-UI service layer (database, operations)
├── docs/           # Documentation (architecture, testing, migrations, etc.)
├── tests/          # Test suite (unit, integration, webapp)
├── migrations/     # Database migration scripts
└── edi_formats/    # EDI format configuration files
```

## Development

### Code Quality

```bash
# Lint
ruff check .

# Format
black .

# Type checking (if configured)
mypy .
```

### Adding Tests

```bash
# Run new test
pytest tests/unit/test_new_feature.py -v

# Webapp tests
pytest tests/webapp -v
```

## License

[Add your license information here]

## Support

For issues and questions, please refer to the [Documentation](DOCUMENTATION.md) or open an issue in the repository.
