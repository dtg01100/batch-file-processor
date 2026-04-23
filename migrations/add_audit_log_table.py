# migrations/add_audit_log_table.py
import logging

logger = logging.getLogger(__name__)


def apply_migration(database_connection) -> bool | None:
    """
    Migration to add audit_log table for observability.
    This migration is applied when upgrading from database version 33 to 34.
    """
    try:
        database_connection.query(
            """
            CREATE TABLE IF NOT EXISTS audit_log (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                correlation_id TEXT NOT NULL,
                folder_id INTEGER NOT NULL,
                file_name TEXT NOT NULL,
                event_type TEXT NOT NULL,
                event_status TEXT NOT NULL,
                error_type TEXT,
                error_message TEXT,
                input_path TEXT,
                output_path TEXT,
                duration_ms INTEGER,
                timestamp TEXT NOT NULL,
                details TEXT,
                FOREIGN KEY (folder_id) REFERENCES folders(id)
            )
            """
        )
        database_connection.query(
            "CREATE INDEX IF NOT EXISTS idx_audit_correlation ON audit_log(correlation_id)"
        )
        database_connection.query(
            "CREATE INDEX IF NOT EXISTS idx_audit_folder ON audit_log(folder_id, timestamp)"
        )
        return True
    except RuntimeError:
        return True
    except Exception as e:
        print(f"Migration failed: {e}")
        return False
