"""
Database connection and initialization
"""

import os
from typing import Optional
from contextlib import contextmanager

import dataset
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker


# Get database path from environment variable
DATABASE_PATH = os.environ.get("DATABASE_PATH", "/app/data/folders.db")


# Database connection URL
DATABASE_URL = f"sqlite:///{DATABASE_PATH}"


# Global database connection
_db: Optional[dataset.Database] = None
_engine = None


def get_database() -> dataset.Database:
    """Get or create database connection"""
    global _db, _engine

    if _db is None:
        # Create database connection using URL string
        _db = dataset.Database(DATABASE_URL)

        # Create engine separately for SQLAlchemy operations
        _engine = create_engine(DATABASE_URL)

        # Initialize tables if they don't exist
        initialize_database()

    return _db


def initialize_database():
    """Initialize database tables with schema"""
    db = get_database()

    # Create folders table with extended schema for web interface
    if "folders" not in db.tables:
        db["folders"].insert(
            {
                "folder_name": "template",
                "alias": "",
                "folder_is_active": "False",
                "connection_type": "local",
                "connection_params": "{}",
                "schedule": "",
                "enabled": "False",
            }
        )
        db.query('DELETE FROM "folders"')

    # Ensure new columns exist for web interface
    try:
        db["folders"].create_column("connection_type", db.types.string(50))
        db["folders"].create_column("connection_params", db.types.string(1000))
        db["folders"].create_column("schedule", db.types.string(100))
        db["folders"].create_column("enabled", db.types.boolean)
    except Exception:
        # Columns may already exist
        pass

    # Create settings table if it doesn't exist
    if "settings" not in db.tables:
        db["settings"].insert(
            {
                "enable_email": False,
                "email_address": "",
                "email_username": "",
                "email_password": "",
                "email_smtp_server": "smtp.gmail.com",
                "smtp_port": 587,
                "backup_counter": 0,
                "backup_counter_maximum": 200,
                "enable_interval_backups": True,
                # Connection method
                "connection_method": "odbc",  # Default to ODBC for compatibility
                # ODBC settings (legacy)
                "odbc_driver": "Select ODBC Driver...",
                "as400_address": "",
                "as400_username": "",
                "as400_password": "",
                # JDBC settings (preferred)
                "jdbc_url": "",
                "jdbc_driver_class": "",
                "jdbc_jar_path": "",
                "jdbc_username": "",
                "jdbc_password": "",
                "encryption_key": "",  # For password encryption
            }
        )

    # Ensure processed_files table exists
    if "processed_files" not in db.tables:
        db["processed_files"].create_column("file_name", db.types.string(500))
        db["processed_files"].create_column("file_checksum", db.types.string(100))
        db["processed_files"].create_column("copy_destination", db.types.string(500))
        db["processed_files"].create_column("ftp_destination", db.types.string(500))
        db["processed_files"].create_column("email_destination", db.types.string(500))
        db["processed_files"].create_column("resend_flag", db.types.boolean)
        db["processed_files"].create_column("folder_id", db.types.integer)
        db["processed_files"].create_column("sent_date_time", db.types.datetime)

    # Create runs table for job history
    if "runs" not in db.tables:
        db["runs"].create_column("folder_id", db.types.integer)
        db["runs"].create_column("folder_alias", db.types.string(200))
        db["runs"].create_column("started_at", db.types.datetime)
        db["runs"].create_column("completed_at", db.types.datetime)
        db["runs"].create_column(
            "status", db.types.string(50)
        )  # running, completed, failed
        db["runs"].create_column("files_processed", db.types.integer)
        db["runs"].create_column("files_failed", db.types.integer)
        db["runs"].create_column("error_message", db.types.text)

    print(f"Database initialized: {DATABASE_PATH}")


def get_engine():
    """Get SQLAlchemy engine"""
    get_database()
    return _engine


@contextmanager
def session_scope():
    """Provide a transactional scope around a series of operations"""
    Session = sessionmaker(bind=get_engine())
    session = Session()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()
