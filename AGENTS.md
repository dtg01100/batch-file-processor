# AGENTS.md

This file contains guidelines for agentic coding assistants working in this repository.

## Build/Test/Lint Commands

### Python Environment Setup
```bash
# Create and activate virtual environment with uv
uv venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Install Python dependencies from requirements.txt
uv pip install -r requirements.txt

# All Python commands must be run with the virtual environment activated
```

### Backend (Python)
```bash
# Run all tests
pytest -v

# Run single test file
pytest tests/unit/test_encryption.py -v

# Run specific test function
pytest tests/unit/test_encryption.py::TestEncryptionManager::test_encrypt_decrypt -v

# Run unit tests only
pytest tests/unit/ -v

# Run integration tests only
pytest tests/integration/ -v

# Run with coverage
pytest --cov=backend --cov-report=html

# Run backend (development)
uvicorn backend.main:app --reload --host 0.0.0.0 --port 8000
```

### Frontend (React)
```bash
# Install dependencies (in frontend/ directory)
npm install

# Run development server
npm run dev

# Build for production
npm run build

# Run unit tests
npm run test

# Run E2E tests
npm run test:e2e
```

### Docker
```bash
# Development: Build and start all services
docker-compose -f docker/docker-compose.yml up

# Production: Build production images
docker-compose -f docker/docker-compose.yml --profile production build

# Production: Start production services
docker-compose -f docker/docker-compose.yml --profile production up -d

# Start frontend build container (standalone)
docker-compose run --rm frontend npm run build

# View logs
docker-compose -f docker/docker-compose.yml logs -f

# Stop services
docker-compose -f docker/docker-compose.yml down
```

## Code Style Guidelines

### Python (Backend)

#### Imports
- Group imports in order: standard library, third-party, local
- Use absolute imports: `from backend.core.database import get_database`
- Import FastAPI components: `from fastapi import APIRouter, HTTPException`
- Use type hints from `typing`: `Optional`, `List`, `Dict`, `Any`

#### File Structure
```python
"""
Module docstring (triple quotes, describe purpose)
"""

import standard_library
import third_party_library
from local_module import LocalClass

logger = logging.getLogger(__name__)  # Standard logging setup

# Constants (UPPER_CASE)
DATABASE_PATH = "/app/data/folders.db"

# Global variables (lowercase with leading underscore if private)
_db = None

# Classes
class ClassName:
    """Class docstring"""
    def __init__(self, param: str):
        self.param = param

    def method(self) -> None:
        """Method docstring"""
        pass

# Functions
def function_name(param: str, optional: Optional[str] = None) -> Dict[str, Any]:
    """Function docstring with Args and Returns sections"""
    return {"key": "value"}
```

#### Pydantic Models (FastAPI)
```python
from pydantic import BaseModel
from typing import Optional, List, Dict, Any

class ModelName(BaseModel):
    """Model description"""
    field_name: str
    optional_field: Optional[str] = None
    numeric_field: int = 0
```

#### API Endpoints
```python
from fastapi import APIRouter, HTTPException
from backend.core.database import get_database

router = APIRouter(tags=["resource"])

@router.get("/")
def list_items():
    """List all items"""
    db = get_database()
    return list(db["table"].find())

@router.post("/")
def create_item(item: ItemModel):
    """Create new item"""
    db = get_database()
    item_id = db["table"].insert(item.dict())
    return {**item.dict(), "id": item_id}

@router.get("/{item_id}")
def get_item(item_id: int):
    """Get item by ID"""
    db = get_database()
    item = db["table"].find_one(id=item_id)
    if not item:
        raise HTTPException(status_code=404, detail="Item not found")
    return dict(item)
```

#### Error Handling
- Use `HTTPException` for API errors: `raise HTTPException(status_code=404, detail="Not found")`
- Use logging: `logger.error(f"Error: {e}")`
- Catch specific exceptions: `except Exception as e:`
- Use `try/except/finally` for cleanup operations

#### Database Operations (Dataset)
```python
from backend.core.database import get_database

db = get_database()
table = db["table_name"]

# Create
item_id = table.insert({"name": "value"})

# Read
items = list(table.find())
item = table.find_one(id=item_id)

# Update
table.update({"name": "new_value"}, ["id"])

# Delete
table.delete(id=item_id)
```

#### Encryption
- Encrypt sensitive data: `from backend.core.encryption import encrypt_password, decrypt_password`
- Always encrypt passwords before storage
- Mask passwords in responses: `"***"`

### Frontend (React)

#### Imports
```jsx
import { useState, useEffect } from 'react'
import axios from 'axios'
import { LayoutDashboard, LayoutFolder } from 'lucide-react'
```

#### Components
```jsx
import { Link } from 'react-router-dom'

export default function ComponentName({ prop }) {
  const [state, setState] = useState(null)

  return (
    <div className="component">
      <h1>Title</h1>
    </div>
  )
}
```

#### API Calls
```jsx
import { foldersApi } from '../services/api'

// Get data
const response = await foldersApi.list()
setData(response.data)

// Create data
await foldersApi.create(data)
```

#### Styling
- Use Tailwind CSS classes
- Use lucide-react icons
- Maintain consistent layout with sidebar navigation

## Testing Guidelines

**CRITICAL: This project requires comprehensive automated testing for all features. No code should be merged without adequate test coverage.**

### Testing Requirements

- **All new features must have corresponding tests**
- **Unit tests for individual functions and components**
- **Integration tests for API endpoints and database operations**
- **E2E tests for critical user workflows**
- **Target test coverage: 80%+ for all modules**
- **All tests must pass before any commit or merge**

### Backend Tests (Python)
- Use `pytest` framework with coverage reporting
- Create test files: `tests/unit/test_module.py` or `tests/integration/test_api.py`
- Use TestClient for API tests: `from fastapi.testclient import TestClient`
- Use fixtures for setup: `@pytest.fixture`
- Clear database state between tests
- Test both success and error paths
- Mock external dependencies (file systems, databases)
- Test edge cases and boundary conditions
- Verify security measures (password encryption, validation)

```bash
# Run with coverage report
pytest --cov=backend --cov-report=html --cov-report=term

# Check coverage meets threshold
pytest --cov=backend --cov-fail-under=80
```

### Frontend Tests (React)
- Use Vitest for unit/component tests
- Use Playwright for E2E tests
- Use Testing Library for component testing
- Test user interactions and state changes
- Mock API calls for unit tests
- Test responsive design where applicable

```bash
# Run all frontend tests
cd frontend && npm run test

# Run E2E tests
cd frontend && npm run test:e2e
```

### Test Organization

**Unit Tests** (`tests/unit/`)
- Test individual functions and methods
- Test Pydantic models and validation
- Test encryption/decryption logic
- Test utility functions
- Mock all external dependencies

**Integration Tests** (`tests/integration/`)
- Test API endpoints with real database
- Test database operations
- Test authentication/authorization
- Test file system operations
- Test scheduler functionality

**Pipeline Tests** (`tests/pipeline/`)
- Test pipeline execution logic
- Test trigger functionality
- Test node execution in pipelines
- Test error handling in workflows

**E2E Tests** (`tests/e2e/` or `frontend/e2e/`)
- Test complete user workflows
- Test form submissions
- Test navigation and routing
- Test file upload/download
- Test scheduled job execution

## Database Schema

### Key Tables
- `folders`: Folder configurations with connection params
- `output_profiles`: Output format configurations
- `settings`: Global application settings
- `jobs`: Scheduled jobs
- `runs`: Job execution history
- `pipelines`: Pipeline definitions (JSON nodes/edges)
- `global_triggers`: Cron triggers for pipelines

## Important Patterns

### Password Handling
- Always encrypt before database storage
- Mask in API responses with `"***"`
- Use Fernet encryption from `backend.core.encryption`

### JSON Fields
- Store JSON as strings in SQLite
- Parse with `json.loads()` on read
- Serialize with `json.dumps()` on write

### File Uploads
- Use `UploadFile = File(...)` in FastAPI
- Validate file extensions
- Store in `/app/drivers/` for JARs or `/app/data/` for other files

### Remote File Systems
- Use factory pattern: `from backend.remote_fs.factory import create_file_system`
- Supports: local, smb, sftp, ftp
- All implement same interface from `remote_fs/base.py`

## Environment Variables

- `DATABASE_PATH`: Path to SQLite database (default: `/app/data/folders.db`)
- `SECRET_KEY`: Encryption key for password encryption
- `LOG_LEVEL`: Logging level (DEBUG, INFO, WARNING, ERROR)
- `ENV`: Environment (development, production)

## Security Considerations

- Never log passwords or sensitive data
- Always encrypt passwords at rest
- Use path sanitization: `os.path.basename(filename)` to prevent directory traversal
- Mask passwords in API responses
- Validate file uploads by extension

## Development Workflow

### Local Development
1. Make changes to backend or frontend code
2. **Write or update tests for all changes** (see Testing Requirements below)
3. Run tests: `pytest -v` (backend) or `npm run test` (frontend)
4. Verify test coverage: `pytest --cov=backend --cov-report=html`
5. Build frontend: `npm run build` in `frontend/` directory
6. Test changes in development environment
7. **All tests must pass before committing**
8. Commit changes with descriptive messages
9. Update documentation if API changes were made

### Production Deployment
1. **Ensure all tests pass locally (100% required)**
2. Review test coverage meets requirements
3. Build production Docker images: `docker-compose -f docker/docker-compose.yml --profile production build`
4. Test production build locally: `docker-compose -f docker/docker-compose.yml --profile production up -d`
5. Push images to registry (if applicable)
6. Deploy to production environment using Docker Compose
7. Monitor logs: `docker-compose -f docker/docker-compose.yml logs -f`

## Notes

- This is a monorepo with backend (FastAPI) and frontend (React/Vite)
- Legacy files (convert_to_*.py, interface.py) are preserved but being replaced
- All new features should be web-based, not Tkinter
- Use pytest.ini configuration for test settings
- No explicit linting configuration - write clean, readable code
- Follow existing patterns from `backend/core/` and `backend/api/` modules
- **Final deployment is via Docker Compose in production mode**
- **Comprehensive automated testing is REQUIRED for all features**

## Environment Management

### Python (Backend)
- **MUST** use `uv` for Python environment and dependency management
- Create virtual environment: `uv venv .venv`
- All Python dependencies must be installed in `.venv/` directory
- Never install to system or user directories (`--system` or `--user` flags)
- Always activate virtual environment before running Python commands
- Available tools: `uv`, `brew`, `npm`, `java`

### Frontend (React)
- Use `npm` for dependency management
- Install in `frontend/` directory only
- Dependencies go to `frontend/node_modules/`
- Never use `npm install -g` for global packages

### Project Isolation
- All dependencies must stay within the project directory
- Python: `.venv/`
- Node.js: `frontend/node_modules/`
- Java: JAR files stored in `/app/drivers/` or project-local paths
- Docker containers provide additional isolation

### Available Tools
- `uv` - Python package and environment manager
- `brew` - macOS/Linux package manager (use sparingly)
- `npm` - Node.js package manager
- `java` - Java runtime for JDBC connections
