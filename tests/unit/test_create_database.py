"""
Unit tests for create_database module.

Tests database schema creation including tables, indexes, and initial data.
Note: Requires PyQt6 to be installed and working SQLite driver.
"""

import os
import tempfile
import shutil
import sqlite3
import pytest

# Skip all tests if create_database imports fail (Qt SQL driver issues)
try:
    import create_database

    CREATE_DB_AVAILABLE = True
except Exception:
    CREATE_DB_AVAILABLE = False

# Additional check: Can we actually use Qt SQL without segfault?
QT_SQL_WORKS = False
if CREATE_DB_AVAILABLE:
    try:
        from PyQt6.QtSql import QSqlDatabase

        QT_SQL_WORKS = True
    except Exception:
        pass

pytestmark = pytest.mark.skipif(
    not (CREATE_DB_AVAILABLE and QT_SQL_WORKS),
    reason="create_database or Qt SQL driver not available",
)


@pytest.fixture
def temp_dir():
    tmpdir = tempfile.mkdtemp()
    yield tmpdir
    shutil.rmtree(tmpdir, ignore_errors=True)


@pytest.fixture
def db_path(temp_dir):
    return os.path.join(temp_dir, "test.db")


def query_db(db_path, sql):
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute(sql)
    result = cursor.fetchall()
    conn.close()
    return result


class TestCreateDatabaseDo:
    def test_creates_database_file(self, db_path, temp_dir):
        create_database.do("39", db_path, temp_dir, "linux")
        assert os.path.exists(db_path)

    def test_creates_version_table(self, db_path, temp_dir):
        create_database.do("39", db_path, temp_dir, "linux")
        result = query_db(db_path, "SELECT version, os FROM version WHERE id = 1")
        assert result[0][0] == "39"
        assert result[0][1] == "linux"

    def test_creates_folders_table(self, db_path, temp_dir):
        create_database.do("39", db_path, temp_dir, "linux")
        result = query_db(db_path, "SELECT * FROM folders LIMIT 1")
        assert result is not None

    def test_creates_administrative_table(self, db_path, temp_dir):
        create_database.do("39", db_path, temp_dir, "linux")
        result = query_db(db_path, "SELECT COUNT(*) FROM administrative")
        assert result[0][0] == 1

    def test_creates_settings_table(self, db_path, temp_dir):
        create_database.do("39", db_path, temp_dir, "linux")
        result = query_db(db_path, "SELECT COUNT(*) FROM settings")
        assert result[0][0] == 1

        result = query_db(db_path, "SELECT email_smtp_server, smtp_port FROM settings")
        assert result[0][0] == "smtp.gmail.com"
        assert result[0][1] == 587

    def test_creates_processed_files_table(self, db_path, temp_dir):
        create_database.do("39", db_path, temp_dir, "linux")
        result = query_db(
            db_path,
            "SELECT folder_id, filename, status FROM processed_files LIMIT 1",
        )
        assert result is not None

    def test_creates_email_tables(self, db_path, temp_dir):
        create_database.do("39", db_path, temp_dir, "linux")
        query_db(db_path, "SELECT * FROM emails_to_send LIMIT 1")
        query_db(db_path, "SELECT * FROM working_batch_emails_to_send LIMIT 1")
        query_db(db_path, "SELECT * FROM sent_emails_removal_queue LIMIT 1")

    def test_creates_indexes(self, db_path, temp_dir):
        create_database.do("39", db_path, temp_dir, "linux")
        result = query_db(
            db_path,
            "SELECT name FROM sqlite_master WHERE type='index' AND name LIKE 'idx_%'",
        )
        indexes = [row[0] for row in result]

        assert "idx_folders_active" in indexes
        assert "idx_folders_alias" in indexes
        assert "idx_processed_files_folder" in indexes
        assert "idx_processed_files_status" in indexes
        assert "idx_processed_files_created" in indexes

    def test_folders_table_starts_empty(self, db_path, temp_dir):
        create_database.do("39", db_path, temp_dir, "linux")
        result = query_db(db_path, "SELECT COUNT(*) FROM folders")
        assert result[0][0] == 0

    def test_administrative_defaults(self, db_path, temp_dir):
        create_database.do("39", db_path, temp_dir, "linux")
        result = query_db(
            db_path,
            "SELECT folder_is_active, convert_to_format, ftp_port FROM administrative",
        )
        assert result[0][0] == "False"
        assert result[0][1] == "csv"
        assert result[0][2] == 21

    def test_logs_directory_path(self, db_path, temp_dir):
        create_database.do("39", db_path, temp_dir, "linux")
        result = query_db(
            db_path, "SELECT logs_directory, errors_folder FROM administrative"
        )
        assert result[0][0].startswith(temp_dir)
        assert result[0][1].startswith(temp_dir)

    def test_different_platform(self, db_path, temp_dir):
        create_database.do("39", db_path, temp_dir, "darwin")
        result = query_db(db_path, "SELECT os FROM version WHERE id = 1")
        assert result[0][0] == "darwin"

    def test_different_version(self, db_path, temp_dir):
        create_database.do("42", db_path, temp_dir, "linux")
        result = query_db(db_path, "SELECT version FROM version WHERE id = 1")
        assert result[0][0] == "42"


class TestDatabaseSchema:
    def test_folders_table_columns(self, db_path, temp_dir):
        create_database.do("39", db_path, temp_dir, "linux")
        result = query_db(db_path, "PRAGMA table_info(folders)")
        columns = [row[1] for row in result]

        essential_columns = [
            "folder_is_active",
            "folder_name",
            "alias",
            "convert_to_format",
            "process_backend_copy",
            "process_backend_ftp",
            "process_backend_email",
            "ftp_server",
            "ftp_port",
            "email_to",
        ]

        for col in essential_columns:
            assert col in columns, f"Missing column: {col}"

    def test_processed_files_table_columns(self, db_path, temp_dir):
        create_database.do("39", db_path, temp_dir, "linux")
        result = query_db(db_path, "PRAGMA table_info(processed_files)")
        columns = [row[1] for row in result]

        essential_columns = [
            "id",
            "folder_id",
            "filename",
            "original_path",
            "processed_path",
            "status",
            "error_message",
            "resend_flag",
        ]

        for col in essential_columns:
            assert col in columns, f"Missing column: {col}"

    def test_settings_table_columns(self, db_path, temp_dir):
        create_database.do("39", db_path, temp_dir, "linux")
        result = query_db(db_path, "PRAGMA table_info(settings)")
        columns = [row[1] for row in result]

        essential_columns = [
            "enable_email",
            "email_address",
            "email_username",
            "email_password",
            "email_smtp_server",
            "smtp_port",
        ]

        for col in essential_columns:
            assert col in columns, f"Missing column: {col}"


class TestDatabaseErrorHandling:
    def test_raises_on_invalid_path(self, temp_dir):
        invalid_path = "/nonexistent/directory/test.db"

        with pytest.raises(RuntimeError):
            create_database.do("39", invalid_path, temp_dir, "linux")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
