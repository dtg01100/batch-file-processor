# print_run_log.py

## Overview
Handles platform-specific printing of log files, supporting both Windows and Unix-like systems.

## Key Components
- `do(filename)`: Reads and word-wraps the log file, then prints it using the system's print service (Windows: win32print, Unix: lpr).

## Usage
Call `do` with a file object to print its contents. Handles platform differences internally.
