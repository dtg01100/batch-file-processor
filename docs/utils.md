# utils.py

## Overview
This module provides utility functions and classes for file management and database interaction, including:
- File cleanup (keeping only the most recent files in a directory)
- Invoice fetching from a database

## Key Components

### Functions
- `do_clear_old_files(directory, maximum_files)`: Keeps at most `maximum_files` most recent files in the specified directory. Deletes older files.

### Classes
- `invFetcher`: Fetches invoice and purchase order information from a database using a `query_runner` object. Handles connection and query logic.

## Usage
Import and use the utility functions or instantiate `invFetcher` with a settings dictionary for database operations.

---

# query_runner (from query_runner.py)

## Overview
A helper class for running arbitrary SQL queries using pyodbc.

## Key Components
- `run_arbitrary_query(query_string)`: Executes the provided SQL query and returns the results as a list.

## Usage
Instantiate with credentials and call `run_arbitrary_query` to execute SQL against the configured database.
