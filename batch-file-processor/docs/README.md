# Batch File Processor

## Overview

The Batch File Processor is a PyQt5 desktop application designed to process Electronic Data Interchange (EDI) files through a configurable pipeline. This project aims to streamline the handling of EDI files by providing functionalities such as validation, splitting, conversion, and sending files via various protocols including FTP, SMTP, or local filesystem.

## Features

- **Configurable Pipeline**: Users can customize the processing pipeline to suit their specific needs.
- **File Validation**: Ensures that EDI files conform to the required formats before processing.
- **File Splitting**: Breaks down larger EDI files into manageable individual files for easier handling.
- **Format Conversion**: Converts EDI files into various formats such as CSV, Fintech, and EStore.
- **Flexible Output Options**: Supports sending processed files via FTP, SMTP, or saving to the local filesystem.

## Getting Started

To get started with the Batch File Processor, follow these steps:

1. **Clone the Repository**:
   ```bash
   git clone https://github.com/dtg01100/batch-file-processor.git
   cd batch-file-processor
   ```

2. **Set Up the Virtual Environment**:
   ```bash
   python -m venv .venv
   source .venv/bin/activate  # On Windows use `.venv\Scripts\activate`
   ```

3. **Install Dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

4. **Run the Application**:
   ```bash
   python interface/main.py
   ```

## Documentation

For detailed documentation, please refer to the following files:

- [Historical Tasks](processes/historical-tasks.md): Documents significant actions and milestones in the project.
- [Workflow](processes/workflow.md): Outlines the workflow processes used in the project.
- [Changes Log](processes/changes-log.md): Records changes made to the project over time.
- [Agents](AGENTS.md): Information about the agents used in the project.
- [Central Documentation Index](DOCUMENTATION.md): Links to various guides and references.

## Contributing

Contributions are welcome! Please see the [CONTRIBUTING.md](CONTRIBUTING.md) file for more information on how to contribute to this project.

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.