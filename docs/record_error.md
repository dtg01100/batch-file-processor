# record_error.py

## Overview
Handles error logging for the application, recording errors to both run and error logs.

## Key Components
- `do(run_log, errors_log, error_message, filename, error_source, threaded=False)`: Formats and writes error messages to the provided log files, supporting both direct and threaded logging.

## Usage
Call `do` with the relevant logs and error details to record errors during processing.
