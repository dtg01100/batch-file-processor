"""
Legacy wrapper for create_database.

This module maintains backwards compatibility by delegating to core.database.schema.
"""

from core.database.schema import create_database


def do(database_version, database_path, config_folder, running_platform):
    create_database(database_version, database_path, config_folder, running_platform)
