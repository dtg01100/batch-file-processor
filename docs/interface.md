# interface.py

## Overview
This is the main application module for the Batch File Sender system. It manages the user interface, configuration, database setup, and orchestrates the batch file processing workflow.

## Key Features
- Cross-platform support (Windows, Linux, etc.)
- Uses Tkinter for GUI dialogs and overlays
- Handles configuration, versioning, and database migrations
- Integrates with multiple modules: backup, logging, utilities, database import, dispatch, overlays, etc.
- Provides main entry point for launching the application

## Main Classes
- `DatabaseObj`: Handles database file creation and connection logic, including user prompts if the database is missing.

## Usage
Run as a script or import as a module. The main application window and logic are initialized at the bottom of the file.

## Dependencies
- Tkinter, appdirs, pyodbc, dataset, thefuzz, and various internal modules.
