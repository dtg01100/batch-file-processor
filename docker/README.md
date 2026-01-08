# Batch File Processor - Web Interface

A modern web interface for batch file processing with built-in scheduling and remote file system support.

## Features

- **Web Interface**: Modern React-based UI replacing Tkinter
- **Built-in Scheduling**: APScheduler with cron expression support
- **Remote File Access**: Connect to SMB, SFTP, and FTP servers
- **Docker-Based**: No host installation required
- **Comprehensive Testing**: Unit, integration, and E2E tests
- **Database Import**: Migrate existing configurations with Windows path conversion

## Development

### Prerequisites

- Docker
- Docker Compose

### Known Issues & Solutions

#### Dependency Issues

**Issue**: SQLAlchemy version conflicts with dataset package
**Solution**: Use SQLAlchemy 1.4.52 (dataset requires 1.3+ but SQLAlchemy 2.0+ incompatible)
```bash
# requirements.txt must have:
sqlalchemy==1.4.52  # NOT 2.0.x
dataset==1.6.2
```

**Issue**: Missing PIL (Pillow) for image processing
**Solution**: Add Pillow to requirements.txt
```bash
# requirements.txt:
Pillow==10.1.0
```

**Issue**: pyodbc requires unixODBC libraries
**Solution**: Install both runtime and headers in Dockerfile
```dockerfile
RUN apt-get update && apt-get install -y \
    unixodbc \
    unixodbc-dev
```

#### GUI Overlay (Tkinter) Issue

**Issue**: Original code imports tkinter via doingstuffoverlay.py
**Solution**: Make GUI overlay optional for Docker environments
```python
# In dispatch.py:
try:
    import doingstuffoverlay
    GUI_AVAILABLE = True
except ImportError:
    GUI_AVAILABLE = False  # OK for Docker/headless
```

#### PIL Import Error

**Issue**: `convert_to_scansheet_type_a.py` imports ImageOps incorrectly
**Solution**: Import from PIL module
```python
# Correct:
from PIL import Image as pil_Image
from PIL import ImageOps as pil_ImageOps
```

#### Python Bytecode Cache

**Issue**: Code changes not reflected due to cached .pyc files
**Solution**: Clear cache when debugging
```bash
docker exec <container> find /app -name "*.pyc" -delete
docker exec <container> find /app -type d -name __pycache__ -exec rm -rf {} +
docker-compose restart backend
```

#### Project Root Mount

**Issue**: Original docker-compose.yml only mounted backend/ and tests/
**Solution**: Mount entire project root to access conversion modules
```yaml
volumes:
  - .:/app  # Mount entire project root
  # ... other volumes
```

#### Dataset Update Syntax

**Issue**: `dataset.Database.update()` requires id field in update dict
**Solution**: Include matching criteria in update dictionary
```python
# Wrong:
folders_table.update({"schedule": job.cron_expression, "enabled": job.enabled}, ["id"])

# Correct:
folders_table.update({
    "id": job.folder_id,  # Include for matching!
    "schedule": job.cron_expression,
    "enabled": job.enabled
}, ["id"])
```

#### Job Executor Issues

**Issue**: `execute_folder_job()` function signature mismatch
**Solution**: Fix function parameters and unbound variables
```python
# Wrong:
def execute_folder_job(folder_id: int, folder_alias: str):  # Only 2 args

# Correct:
def execute_folder_job(folder_id: int, folder: dict):  # Accept full folder dict
```

**Note**: As of this writing, job_executor.py has critical bugs that need fixing before production use:
- Multiple `runs_table.update()` calls missing `id` field
- Unbound variables due to incorrect try/except block placement
- Function parameter mismatch causing runtime errors

### Testing Checklist

### Quick Start

```bash
# Start development environment
docker-compose -f docker/docker-compose.yml up

# Access applications
# Backend API: http://localhost:8000
# API Docs: http://localhost:8000/docs
# Frontend: http://localhost:5173
```

### Running Tests

```bash
# Run all backend tests
docker-compose -f docker/docker-compose.yml --profile test run --rm test

# Run specific test suites
docker-compose run --rm backend python -m pytest /app/tests/unit/test_remote_fs.py -v
docker-compose run --rm backend python -m pytest /app/tests/unit/test_encryption.py -v
docker-compose run --rm backend python -m pytest /app/tests/integration/test_api.py -v
```

### Project Structure

```
batch-file-processor/
├── backend/              # FastAPI application
│   ├── api/             # REST endpoints
│   ├── core/            # Business logic & dispatch integration
│   ├── models/          # Pydantic models
│   ├── schedulers/      # Job execution
│   └── remote_fs/       # Remote file system abstraction
├── frontend/            # React + Vite + shadcn/ui
│   ├── src/
│   │   ├── components/     # UI components
│   │   ├── pages/          # Page components
│   │   ├── services/       # API calls
│   │   └── utils/          # Helper functions
│   └── e2e/              # E2E tests
├── docker/              # Docker configurations
├── scripts/             # Utilities (import_db.py)
└── tests/              # Test suites
│       ├── unit/             # Unit tests
│       ├── integration/      # Integration tests
│       └── e2e/              # End-to-end tests
└── [existing files]     # Core processing modules
```

## Deployment

### Production Build

```bash
# Build production image
docker-compose -f docker/docker-compose.yml --profile production build

# Start production container
docker-compose -f docker/docker-compose.yml --profile production up -d
```

### Environment Variables

- `DATABASE_PATH`: Path to SQLite database (default: `/app/data/folders.db`)
- `SECRET_KEY`: Encryption key for passwords (required for production)
- `ENV`: Environment (`development` | `production`)
- `LOG_LEVEL`: Logging level (`DEBUG` | `INFO`)

### Volume Mounts

- `./data:/app/data` - SQLite database
- `./logs:/app/logs` - Run logs
- `./errors:/app/errors` - Error logs

## API Endpoints

- `GET /api/health` - Health check
- `GET /api/folders/` - List folders
- `POST /api/folders/` - Create folder
- `GET /api/folders/{id}` - Get specific folder
- `PUT /api/folders/{id}` - Update folder
- `DELETE /api/folders/{id}` - Delete folder
- `POST /api/test-connection` - Test remote connection
- `GET /api/settings` - Global settings
- `PUT /api/settings` - Update settings
- `GET /api/jobs` - List scheduled jobs
- `POST /api/jobs/` - Create job
- `PUT /api/jobs/{id}` - Update job
- `DELETE /api/jobs/{id}` - Delete (disable) job
- `POST /api/jobs/{id}/run` - Manual trigger
- `POST /api/jobs/{id}/toggle` - Enable/disable schedule
- `GET /api/runs` - Run history
- `GET /api/runs/{id}/logs` - View run logs
- `POST /api/import` - Database import

## Architecture

### Backend (FastAPI)
- FastAPI with async support
- SQLAlchemy + dataset for database
- APScheduler for job scheduling
- Cryptography for password encryption
- Integration with existing dispatch.py

### Frontend (React + Vite + shadcn/ui)
- Modern, responsive UI
- React Router for navigation
- Axios for API calls
- Real-time dashboard statistics

### Remote File Systems
- **LocalFileSystem**: For local testing/development
- **SMBFileSystem**: Windows shares (smbprotocol)
- **SFTPFileSystem**: SSH file access (paramiko)
- **FTPFileSystem**: FTP with TLS support (ftplib)

### Output Formats Preserved

All existing conversion formats are preserved:
- `convert_to_csv.py` - CSV format
- `convert_to_estore_einvoice.py` - eStore eInvoice format
- `convert_to_estore_einvoice_generic.py` - eStore eInvoice generic
- `convert_to_fintech.py` - Fintech format
- `convert_to_scannerware.py` - Scannerware format
- `convert_to_scansheet_type_a.py` - Scansheet Type A
- `convert_to_simplified_csv.py` - Simplified CSV
- `convert_to_stewarts_custom.py` - Stewart's Custom
- `convert_to_yellowdog_csv.py` - Yellowdog CSV
- All other existing converters

### Testing

**Unit Tests:**
- Remote file systems (Local, SMB, SFTP, FTP)
- Encryption/decryption
- Scheduler (cron validation, job management)
- Database operations
- API endpoints (folders, settings, jobs, runs)

**Integration Tests:**
- API request/response testing
- Job execution
- Database import
- Connection testing

**Coverage Target:** 80%+ for core logic

### Windows Path Conversion

Import wizard automatically converts:
- `\\\server\\share\\folder` → SMB (host, share, folder)
- `C:\\folder` → Local
- `//server/share` → SMB (host, share, folder)
- Network paths (//server/share) → SMB (host, share, folder)

### Key Features

- ✅ Encrypted password storage in database
- ✅ Cron expression validation
- ✅ Job enable/disable scheduling
- ✅ Manual job triggering
- ✅ Job execution in background tasks
- ✅ Run history with logs
- ✅ Error logging and reporting
- ✅ Remote connection testing
- ✅ Database import with Windows path conversion
- ✅ Duplicate file detection through processed_files table
- ✅ All existing output formats continue to work
- ✅ Settings management

## Usage

### Development

1. Clone repository
```bash
git clone <repository-url>
cd batch-file-processor
git checkout web-interface
```

2. Start development environment
```bash
docker-compose -f docker/docker-compose.yml up
```

3. Build frontend
```bash
docker-compose run --rm frontend npm run build
```

### Production Deployment

1. Create `.env` file with production secrets
```bash
# Generate secure secret key
python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"

# Create .env
cat > .env << EOF
SECRET_KEY=<generated-key>
ENV=production
LOG_LEVEL=INFO
EOF
```

2. Build and run
```bash
docker-compose -f docker/docker-compose.yml --profile production build
docker-compose -f docker/docker-compose.yml --profile production up -d
```

3. Access web interface
```
http://your-server:8000
```

## Roadmap

### Phase 2: Remote File System ✅
- [x] Implement LocalFileSystem
- [x] Implement SMBFileSystem (smbprotocol)
- [x] Implement SFTPFileSystem (paramiko)
- [x] Implement FTPFileSystem (ftplib)
- [x] Create factory pattern

### Phase 3: Core API ✅
- [x] Settings API
- [x] Jobs API
- [x] Runs API
- [x] Database import API
- [x] Connection testing endpoint
- [x] Folder CRUD API

### Phase 4: Scheduling ✅
- [x] APScheduler integration
- [x] Cron expression validation
- [x] Job execution integration
- [x] Run history tracking

### Phase 5: Frontend ✅
- [x] Dashboard page
- [x] Folders management page
- [x] Jobs scheduling page
- [x] Logs viewer page
- [x] Database import wizard

### Phase 6+: Enhancements
- [ ] Visual cron builder
- [ ] Continuous file watching
- [ ] Job dependencies
- [ ] Email notifications
- [ ] Run history export

## License

See LICENSE file in parent directory.
