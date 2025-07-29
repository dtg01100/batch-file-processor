# Batch File Processor

This project is a batch file processing and distribution system, designed to automate the handling, conversion, and delivery of files (such as EDI, CSV, and custom formats) between local directories, FTP servers, and email recipients. It supports a variety of file formats and workflows, including database management, error logging, and user interface components for configuration and monitoring.

## Features

- **Automated File Processing:** Handles batch conversion and distribution of files based on configurable rules.
- **Multi-format Support:** Converts EDI files to various formats (CSV, custom, etc.) using modular converters.
- **Flexible Delivery:** Supports file delivery via local copy, FTP, and email.
- **Database Integration:** Uses SQLite for tracking processed files, folders, and configuration.
- **User Interface:** Tkinter-based GUI for managing folders, settings, logs, and error reporting.
- **Error Handling:** Robust logging and error recording for troubleshooting and auditing.
- **Extensible Architecture:** Modular design allows for easy addition of new converters and delivery backends.

## Getting Started

### Prerequisites

- Python 3.11+
- Docker (optional, for containerized development)
- Required Python packages (see `requirements.txt`)

### Setup

1. **Clone the repository:**
    ```sh
    git clone https://github.com/your-org/batch-file-processor.git
    cd batch-file-processor
    ```

2. **Install dependencies:**
    ```sh
    pip install -r requirements.txt
    ```

3. **(Optional) Build and run with Docker:**
    ```sh
    docker build -t batch-file-processor .
    docker run -it batch-file-processor
    ```

### Usage

- Launch the main interface:
  ```sh
  python interface.py
  ```
- Configure folders, processing rules, and delivery methods via the GUI.
- Monitor logs and errors from the interface.

## Project Structure

- `interface.py` — Main GUI application.
- `dispatch.py` — Core batch processing logic.
- `convert_to_*.py` — File format converters.
- `ftp_backend.py`, `email_backend.py`, `copy_backend.py` — Delivery backends.
- `utils.py` — Utility functions and helpers.
- `database_import.py`, `folders_database_migrator.py` — Database management.
- `doingstuffoverlay.py`, `dialog.py`, `tk_extra_widgets.py` — UI components.
- `record_error.py`, `print_run_log.py` — Logging and error handling.

## Contributing

Contributions are welcome! Please open issues or pull requests for bug fixes, enhancements, or new features.

## License

This project is licensed under the GPL 3 License.
