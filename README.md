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
database in `./data/config` (`BFS_CONFIG_DIR`). Drop incoming files into
`./data/<relative-path>/...` so the configured folders can find them.

## Quick Start (local dev)

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

# Run the webapp (base-dir defaults to ./data)
BFS_BASE_DIR=./data python -m webapp.main
# or
uvicorn webapp.main:app --host 0.0.0.0 --port 8000
```

### Environment variables

| Variable | Default | Purpose |
|----------|---------|---------|
| `BFS_BASE_DIR` | `./data` | Base directory that configured folder paths resolve against |
| `BFS_DATA_DIR` | `<base_dir>/config` | Where `folders.db` lives |

### API

| Endpoint | Description |
|----------|-------------|
| `GET /api/health` | Liveness + paths |
| `GET /api/config` | Base-dir, data-dir, DB status, counts |
| `POST /api/import` | Multipart upload of a legacy `folders.db` (+ optional `base_dir`, `platform`) |
| `GET /api/folders` | Configured folders (relative + resolved paths) |
| `POST /api/run` | Start a background processing run |
| `GET /api/runs` | Recent runs |
| `GET /api/runs/{run_id}` | Run detail (poll while running) |
| `GET /api/processed-files` | Recently processed files |

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
