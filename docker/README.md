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
# Run backend tests
docker-compose -f docker/docker-compose.yml --profile test run --rm test

# Run frontend tests
docker-compose -f docker/docker-compose.yml run --rm frontend npm run test
```

### Project Structure

```
batch-file-processor/
├── backend/              # FastAPI backend
│   ├── api/             # REST endpoints
│   ├── core/            # Database & scheduling
│   ├── models/          # Pydantic models
│   ├── schedulers/      # Job execution
│   └── remote_fs/       # Remote file systems
├── frontend/            # React + Vite + shadcn/ui
├── docker/              # Docker configurations
├── scripts/             # Utilities (import_db.py)
└── tests/              # Test suites
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
- `GET /api/folders` - List folders
- `POST /api/folders` - Create folder
- `PUT /api/folders/{id}` - Update folder
- `DELETE /api/folders/{id}` - Delete folder
- `GET /api/jobs` - List scheduled jobs
- `POST /api/jobs/{id}/run` - Manual trigger
- `GET /api/runs` - Run history
- `POST /api/test-connection` - Test remote connection

## Roadmap

### Phase 2: Remote File System
- [ ] Implement LocalFileSystem
- [ ] Implement SMBFileSystem
- [ ] Implement SFTPFileSystem
- [ ] Implement FTPFileSystem

### Phase 3: API Endpoints
- [ ] Folders CRUD
- [ ] Settings management
- [ ] Jobs management
- [ ] Run history
- [ ] Database import

### Phase 4: Scheduling
- [ ] Cron expression validation
- [ ] Job execution
- [ ] Manual triggers
- [ ] Run history tracking

### Phase 5: Frontend Components
- [ ] Dashboard
- [ ] Folder forms
- [ ] Job scheduler UI
- [ ] Log viewer
- [ ] Import wizard

### Phase 6+: Enhancements
- [ ] Visual cron builder
- [ ] Continuous file watching
- [ ] Job dependencies
- [ ] Email notifications

## License

See LICENSE file in parent directory.
