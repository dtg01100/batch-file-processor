# Batch File Processor

## Overview

The Batch File Processor is a PyQt5 desktop application designed to process Electronic Data Interchange (EDI) files through a configurable pipeline. This application facilitates the validation, splitting, conversion, and transmission of files via FTP, SMTP, or local filesystem.

## Purpose

The primary goal of the Batch File Processor is to streamline the handling of EDI files, making it easier for users to manage and process these files efficiently. The application is built with a focus on flexibility and extensibility, allowing users to customize their workflows according to their specific needs.

## Features

- **EDI File Validation**: Ensures that incoming EDI files conform to the required formats.
- **File Splitting**: Breaks down larger EDI files into manageable individual files.
- **Format Conversion**: Converts EDI files into various target formats, including CSV and others.
- **Configurable Pipeline**: Users can configure the processing pipeline to include or exclude specific steps based on their requirements.
- **Multiple Transmission Methods**: Supports sending processed files via FTP, SMTP, or saving them to the local filesystem.

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
   source .venv/bin/activate
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

For detailed documentation, refer to the following files:

- [Historical Tasks](docs/processes/historical-tasks.md): Documents significant actions and milestones in the project's history.
- [Workflow Processes](docs/processes/workflow.md): Outlines the workflow processes used in the project.
- [Changes Log](docs/processes/changes-log.md): Records changes made to the project over time.
- [Agents](docs/AGENTS.md): Information about the agents used in the project.
- [Central Documentation Index](docs/DOCUMENTATION.md): Links to various guides and references.

## Contribution

Contributions to the Batch File Processor are welcome! Please follow the standard GitHub workflow for submitting issues and pull requests.

## License

This project is licensed under the MIT License. See the LICENSE file for more details.