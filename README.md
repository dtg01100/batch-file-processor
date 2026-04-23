# Batch File Processor

A PyQt5 desktop application that processes EDI (Electronic Data Interchange) files through a configurable pipeline — validating, splitting, converting, and sending files via FTP, SMTP, or local filesystem.

## Quick Start

### Prerequisites

- Python 3.11+
- PyQt5
- SQLite3

### Installation

```bash
# Create virtual environment
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

### Running the Application

```bash
# Launch the Qt interface
python main_qt.py
```

### Running Tests

```bash
# Run all tests (with timeout)
pytest

# Run with coverage
pytest --cov=. --cov-report=html

# Run specific test categories
pytest -m unit      # Unit tests only
pytest -m integration  # Integration tests only
```

## Documentation

**📖 [Complete Documentation](DOCUMENTATION.md)** - Start here for comprehensive guides

### Key Documentation

- **[EDI Format Guide](docs/user-guide/EDI_FORMAT_GUIDE.md)** - Configure and understand EDI formats
- **[Testing Guide](docs/testing/TESTING.md)** - Test suite documentation
- **[Migration Guide](docs/migrations/AUTOMATIC_MIGRATION_GUIDE.md)** - Database migration
- **[Quick Reference](docs/user-guide/QUICK_REFERENCE.md)** - Fast lookup guide
- **[Troubleshooting](docs/user-guide/LAUNCH_TROUBLESHOOTING.md)** - Common issues

## Features

- **Folder Monitoring**: Watch configured directories for new EDI files
- **EDI Processing**: Parse and validate EDI format files (A/B/C record structure)
- **Format Conversion**: Transform EDI files into various business-specific formats (CSV, Excel, Fintech, E-Store, etc.)
- **Multi-Channel Delivery**: Send processed files via FTP, email, or local file copy
- **Database Tracking**: SQLite database for configuration and processed file tracking
- **Plugin System**: Extensible plugin architecture for custom configurations
- **Pipeline Processing**: Configurable validation → splitting → conversion → tweaks pipeline

## Project Structure

```
batch-file-processor/
├── core/           # Core utilities, EDI parser, database abstraction
├── dispatch/       # Pipeline orchestration and file processing
├── backend/        # FTP, SMTP, and copy backend clients
├── interface/      # PyQt5 UI layer
├── docs/           # Documentation (architecture, testing, migrations, etc.)
├── tests/          # Test suite (unit, integration, e2e)
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

# Run with coverage
pytest tests/ --cov=batch_file_processor --cov-report=term-missing
```

## License

[Add your license information here]

## Support

For issues and questions, please refer to the [Documentation](DOCUMENTATION.md) or open an issue in the repository.
