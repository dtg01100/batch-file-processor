"""Folders database migration orchestrator.

Thin delegating layer that coordinates legacy (v5→v32) and the
consolidated v33→current migration.

External consumers import from this module:
- `upgrade_database(database_connection, config_folder, running_platform, target_version)`
- `CURRENT_SCHEMA_VERSION` (re-exported for convenience)
- `_log_migration_step` (backward compat)
"""

import logging

from migrations.legacy_migrations import run_legacy_migrations

# Backward-compatible re-exports for external consumers
from migrations.migration_helpers import (
   CURRENT_SCHEMA_VERSION,  # noqa: F401 — re-exported for external consumers
   _log_migration_step,  # noqa: F401 — re-exported for external consumers
)
from migrations.modern_migrations import apply_v33_to_current

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

    # Consolidated v33 → current migration (replaces the previous 20
    # individual blocks). Honors target_version for test fixtures by
    # stopping the final version bump at the requested intermediate value.
    apply_v33_to_current(
        database_connection,
        config_folder,
        running_platform,
        db_version,
        db_version_dict,
        target_version,
    )
