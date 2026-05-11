"""Folders database migration orchestrator.

Thin delegating layer that coordinates legacy (v5→v32) and modern (v33→v50)
migrations extracted into focused modules.

External consumers import from this module:
- `upgrade_database(database_connection, config_folder, running_platform, target_version)`
- `CURRENT_SCHEMA_VERSION` (re-exported for convenience)
- `_log_migration_step`, `_normalize_legacy_v32_values` (backward compat)
"""

import logging

from migrations.legacy_migrations import run_legacy_migrations

# Backward-compatible re-exports for external consumers
from migrations.migration_helpers import (  # noqa: F401 - re-exports for backward compat
    CSV_SORT_ORDER,
    CURRENT_SCHEMA_VERSION,
    REPLACEME_PLACEHOLDER,
    _normalize_legacy_v32_values,
)
from migrations.modern_migrations import migrate_v33_to_v50, run_modern_migrations

logger = logging.getLogger(__name__)


def upgrade_database(
    database_connection, config_folder, running_platform, target_version=None
) -> None:
    """Upgrade the folders database to the current schema version.

    Args:
        database_connection: Database connection object
        config_folder: Path to configuration folder
        running_platform: Platform identifier
        target_version: Optional target version for testing (stops at this version)

    """
    db_version = database_connection["version"]
    db_version_dict = db_version.find_one(id=1)
    if target_version and int(db_version_dict["version"]) >= int(target_version):
        return

    # Run legacy migrations (v5→v32)
    db_version_dict = run_legacy_migrations(
        database_connection,
        config_folder,
        running_platform,
        db_version,
        db_version_dict,
        target_version,
    )

    # Check if we've reached the target version after legacy migrations
    if target_version and int(db_version_dict["version"]) >= int(target_version):
        return

    # Fast-path: jump from v32 directly to v50 for production databases
    # (skip when target_version is set for testing intermediate versions)
    if str(db_version_dict["version"]) == "32" and target_version is None:
        logger.info(
            "Production database at v32, applying consolidated v33→v50 migration"
        )
        _normalize_legacy_v32_values(database_connection)
        migrate_v33_to_v50(database_connection, db_version, running_platform)
        return

    # Run individual modern migrations (v33→v50) for test fixtures at intermediate versions
    run_modern_migrations(
        database_connection,
        config_folder,
        running_platform,
        db_version,
        db_version_dict,
        target_version,
    )
