# ftp_backend.py

## Overview
Handles FTP file transfers using credentials and parameters from a process dictionary.

## Key Components
- `do(process_parameters, settings_dict, filename)`: Sends the specified file to an FTP server using either FTP_TLS or FTP, with retries and fallback logic.

## Usage
Call `do` with the appropriate parameters to transfer a file via FTP. Handles up to 10 retries and falls back to non-TLS if needed.
