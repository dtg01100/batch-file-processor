# folders_database_migrator.py

## Overview
Handles database schema migrations and upgrades for the application's folders and administrative tables.

## Key Components
- `upgrade_database(database_connection, config_folder, running_platform)`: Applies schema changes and version upgrades to the database, updating tables and fields as needed.

## Usage
Call `upgrade_database` during application startup or migration to ensure the database schema is up to date.
