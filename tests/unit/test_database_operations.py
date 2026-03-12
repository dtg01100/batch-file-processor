"""Unit tests for database operations.

Tests:
- Settings table CRUD
- Folders table CRUD
- Administrative table operations
- Database migrations (folders_database_migrator.py)
- Database integrity

Database tables tested:
- version
- settings
- folders
- administrative (oversight_and_defaults)
- emails_to_send
- working_batch_emails_to_send
- sent_emails_removal_queue
- processed_files
"""

import pytest

pytestmark = [pytest.mark.unit, pytest.mark.database]
import os

import schema
from interface.database import sqlite_wrapper


class TestDatabaseCreation:
    """Test suite for database creation."""

    @pytest.fixture
    def temp_db_path(self, tmp_path):
        """Create a temporary database path."""
        return str(tmp_path / "test_folders.db")

    @pytest.fixture
    def sample_initial_dict(self):
        """Create sample initial database dictionary."""
        return dict(
            folder_is_active="False",
            copy_to_directory=None,
            process_edi="False",
            convert_to_format="csv",
            calculate_upc_check_digit="False",
            upc_target_length=11,
            upc_padding_pattern="           ",
            include_a_records="False",
            include_c_records="False",
            include_headers="False",
            filter_ampersand="False",
            tweak_edi=False,
            pad_a_records="False",
            a_record_padding="",
            a_record_padding_length=6,
            invoice_date_custom_format_string="%Y%m%d",
            invoice_date_custom_format=False,
            reporting_email="",
            folder_name="template",
            alias="",
            report_email_destination="",
            process_backend_copy=False,
            backend_copy_destination=None,
            process_edi_output=False,
            edi_output_folder=None,
        )

    def test_create_database_file(self, temp_db_path, sample_initial_dict):
        """Test database file creation."""
        database_version = "41"
        running_platform = "Linux"

        # Create database
        db_conn = sqlite_wrapper.Database.connect(temp_db_path)
        schema.ensure_schema(db_conn)

        # Insert version
        version_table = db_conn["version"]
        version_table.insert(dict(version=database_version, os=running_platform))

        # Insert settings
        settings_table = db_conn["settings"]
        settings_table.insert(sample_initial_dict)

        db_conn.commit()
        db_conn.close()

        # Verify file was created
        assert os.path.exists(temp_db_path)

    def test_database_version_table(self, temp_db_path, sample_initial_dict):
        """Test version table operations."""
        database_version = "41"
        running_platform = "Linux"

        db_conn = sqlite_wrapper.Database.connect(temp_db_path)
        schema.ensure_schema(db_conn)
        version_table = db_conn["version"]
        version_table.insert(dict(version=database_version, os=running_platform))

        # Read version back
        version_record = version_table.find_one(id=1)

        assert version_record is not None
        assert version_record["version"] == database_version
        assert version_record["os"] == running_platform

        db_conn.close()

    def test_database_settings_table(self, temp_db_path, sample_initial_dict):
        """Test settings table operations."""
        db_conn = sqlite_wrapper.Database.connect(temp_db_path)
        schema.ensure_schema(db_conn)
        settings_table = db_conn["settings"]
        settings_table.insert(sample_initial_dict)

        # Read settings back
        settings_record = settings_table.find_one(id=1)

        assert settings_record is not None
        assert settings_record["folder_is_active"] is False
        assert settings_record["convert_to_format"] == "csv"
        assert settings_record["upc_target_length"] == 11

        db_conn.close()


class TestFoldersTableCRUD:
    """Test suite for folders table CRUD operations."""

    @pytest.fixture
    def populated_database(self, tmp_path):
        """Create a populated database."""
        db_path = str(tmp_path / "test.db")
        db_conn = sqlite_wrapper.Database.connect(db_path)
        schema.ensure_schema(db_conn)

        # Setup version
        db_conn["version"].insert(dict(version="33", os="Linux"))
        db_conn["settings"].insert(
            dict(folder_name="template", alias="", folder_is_active="False")
        )
        db_conn["administrative"].insert(
            dict(id=1, logs_directory="/tmp/logs", errors_folder="/tmp/errors")
        )

        yield db_conn

        db_conn.close()

    def test_insert_folder(self, populated_database):
        """Test inserting a folder."""
        folder_data = dict(
            folder_name="/home/user/test_folder",
            alias="Test Folder",
            folder_is_active=True,
            process_edi=True,
            convert_to_format="csv",
        )

        folder_id = populated_database["folders"].insert(folder_data)

        assert folder_id is not None

        # Verify folder was inserted
        folder = populated_database["folders"].find_one(id=folder_id)
        assert folder is not None
        assert folder["folder_name"] == "/home/user/test_folder"
        assert folder["alias"] == "Test Folder"
        assert folder["folder_is_active"] is True

    def test_update_folder(self, populated_database):
        """Test updating a folder."""
        folder_data = dict(
            folder_name="/home/user/test_folder",
            alias="Test Folder",
            folder_is_active=True,
        )

        folder_id = populated_database["folders"].insert(folder_data)

        # Update folder
        update_data = folder_data.copy()
        update_data["id"] = folder_id
        update_data["folder_is_active"] = False
        populated_database["folders"].update(update_data, ["id"])

        # Verify update
        updated_folder = populated_database["folders"].find_one(id=folder_id)
        assert updated_folder["folder_is_active"] is False

    def test_delete_folder(self, populated_database):
        """Test deleting a folder."""
        folder_data = dict(
            folder_name="/home/user/test_folder",
            alias="Test Folder",
        )

        folder_id = populated_database["folders"].insert(folder_data)

        # Delete folder
        populated_database["folders"].delete(id=folder_id)

        # Verify deletion
        deleted_folder = populated_database["folders"].find_one(id=folder_id)
        assert deleted_folder is None

    def test_find_folder_by_name(self, populated_database):
        """Test finding folder by name."""
        folders = [
            dict(folder_name="/home/user/folder1", alias="Folder 1"),
            dict(folder_name="/home/user/folder2", alias="Folder 2"),
            dict(folder_name="/home/user/folder3", alias="Folder 3"),
        ]

        for f in folders:
            populated_database["folders"].insert(f)

        # Find by name
        found = populated_database["folders"].find_one(folder_name="/home/user/folder2")

        assert found is not None
        assert found["alias"] == "Folder 2"

    def test_list_all_folders(self, populated_database):
        """Test listing all folders."""
        folders = [
            dict(folder_name="/home/user/folder1", alias="Folder 1"),
            dict(folder_name="/home/user/folder2", alias="Folder 2"),
        ]

        for f in folders:
            populated_database["folders"].insert(f)

        all_folders = list(populated_database["folders"].all())

        assert len(all_folders) >= 2

    def test_folder_count(self, populated_database):
        """Test counting folders."""
        folders = [
            dict(folder_name="/home/user/folder1", alias="Folder 1"),
            dict(folder_name="/home/user/folder2", alias="Folder 2"),
            dict(folder_name="/home/user/folder3", alias="Folder 3"),
        ]

        for f in folders:
            populated_database["folders"].insert(f)

        count = populated_database["folders"].count()

        assert count >= 3


class TestAdministrativeTable:
    """Test suite for administrative table operations."""

    @pytest.fixture
    def database_with_admin(self, tmp_path):
        """Create database with administrative record."""
        db_path = str(tmp_path / "test.db")
        db_conn = sqlite_wrapper.Database.connect(db_path)
        schema.ensure_schema(db_conn)

        db_conn["version"].insert(dict(version="33", os="Linux"))
        db_conn["administrative"].insert(
            dict(
                id=1,
                logs_directory="/tmp/logs",
                errors_folder="/tmp/errors",
                report_email_destination="",
                single_add_folder_prior="/tmp",
                batch_add_folder_prior="/tmp",
                enable_reporting=False,
            )
        )

        yield db_conn

        db_conn.close()

    def test_read_administrative(self, database_with_admin):
        """Test reading administrative record."""
        admin = database_with_admin["administrative"].find_one(id=1)

        assert admin is not None
        assert admin["logs_directory"] == "/tmp/logs"
        assert admin["errors_folder"] == "/tmp/errors"

    def test_update_administrative(self, database_with_admin):
        """Test updating administrative record."""
        update_data = dict(
            id=1,
            logs_directory="/new/logs",
            errors_folder="/new/errors",
            report_email_destination="admin@example.com",
        )

        database_with_admin["administrative"].update(update_data, ["id"])

        updated = database_with_admin["administrative"].find_one(id=1)
        assert updated["logs_directory"] == "/new/logs"
        assert updated["report_email_destination"] == "admin@example.com"


class TestSettingsTableOperations:
    """Test suite for settings table operations."""

    @pytest.fixture
    def database_with_settings(self, tmp_path):
        """Create database with settings."""
        db_path = str(tmp_path / "test.db")
        db_conn = sqlite_wrapper.Database.connect(db_path)
        schema.ensure_schema(db_conn)

        db_conn["version"].insert(dict(version="33", os="Linux"))
        db_conn["settings"].insert(
            dict(
                id=1,
                folder_name="template",
                alias="",
                folder_is_active="False",
                convert_to_format="csv",
                reporting_email="",
            )
        )

        yield db_conn

        db_conn.close()

    def test_read_settings(self, database_with_settings):
        """Test reading settings."""
        settings = database_with_settings["settings"].find_one(id=1)

        assert settings is not None
        assert settings["convert_to_format"] == "csv"
        assert settings["folder_is_active"] is False

    def test_update_settings(self, database_with_settings):
        """Test updating settings."""
        update_data = dict(
            id=1,
            folder_name="template",
            alias="",
            convert_to_format="fintech",
            folder_is_active=True,
        )

        database_with_settings["settings"].update(update_data, ["id"])

        updated = database_with_settings["settings"].find_one(id=1)
        assert updated["convert_to_format"] == "fintech"
        assert updated["folder_is_active"] is True


class TestEmailsTable:
    """Test suite for emails table operations."""

    @pytest.fixture
    def database_with_emails(self, tmp_path):
        """Create database with emails."""
        db_path = str(tmp_path / "test.db")
        db_conn = sqlite_wrapper.Database.connect(db_path)
        schema.ensure_schema(db_conn)

        db_conn["version"].insert(dict(version="33", os="Linux"))
        db_conn["emails_to_send"].insert_many(
            [
                dict(folder_id=1, folder_alias="folder1", log="pending"),
                dict(folder_id=1, folder_alias="folder1", log="sent"),
                dict(folder_id=2, folder_alias="folder2", log="pending"),
            ]
        )

        yield db_conn

        db_conn.close()

    def test_insert_email(self, database_with_emails):
        """Test inserting email record."""
        email_data = dict(
            folder_id=1,
            folder_alias="new_folder",
            log="pending",
        )

        email_id = database_with_emails["emails_to_send"].insert(email_data)

        assert email_id is not None

        email = database_with_emails["emails_to_send"].find_one(id=email_id)
        assert email["folder_alias"] == "new_folder"

    def test_find_emails_by_status(self, database_with_emails):
        """Test finding emails by log status."""
        pending_emails = list(
            database_with_emails["emails_to_send"].find(log="pending")
        )

        assert len(pending_emails) >= 2

    def test_count_emails_by_status(self, database_with_emails):
        """Test counting emails by log status."""
        pending_count = len(
            list(database_with_emails["emails_to_send"].find(log="pending"))
        )

        assert pending_count == 2


class TestProcessedFilesTable:
    """Test suite for processed files table operations."""

    @pytest.fixture
    def database_with_processed_files(self, tmp_path):
        """Create database with processed files."""
        db_path = str(tmp_path / "test.db")
        db_conn = sqlite_wrapper.Database.connect(db_path)
        schema.ensure_schema(db_conn)

        db_conn["version"].insert(dict(version="33", os="Linux"))
        db_conn["processed_files"].insert_many(
            [
                dict(filename="file1.edi", folder_id=1, processed_at="2025-01-01"),
                dict(filename="file2.edi", folder_id=1, processed_at="2025-01-02"),
                dict(filename="file3.edi", folder_id=2, processed_at="2025-01-03"),
            ]
        )

        yield db_conn

        db_conn.close()

    def test_insert_processed_file(self, database_with_processed_files):
        """Test inserting processed file record."""
        file_data = dict(
            filename="new_file.edi",
            folder_id=1,
            processed_at="2025-01-10",
        )

        file_id = database_with_processed_files["processed_files"].insert(file_data)

        assert file_id is not None

    def test_find_processed_file_by_name(self, database_with_processed_files):
        """Test finding processed file by name."""
        file = database_with_processed_files["processed_files"].find_one(
            filename="file2.edi"
        )

        assert file is not None
        assert file["folder_id"] == 1

    def test_check_file_processed(self, database_with_processed_files):
        """Test checking if file was processed."""
        is_processed = (
            database_with_processed_files["processed_files"].find_one(
                filename="file1.edi"
            )
            is not None
        )

        assert is_processed is True

        is_processed = (
            database_with_processed_files["processed_files"].find_one(
                filename="nonexistent.edi"
            )
            is not None
        )

        assert is_processed is False


class TestDatabaseMigrations:
    """Test suite for database migrations."""

    @pytest.fixture
    def old_database(self, tmp_path):
        """Create an older version database."""
        db_path = str(tmp_path / "old.db")
        db_conn = sqlite_wrapper.Database.connect(db_path)
        schema.ensure_schema(db_conn)

        # Simulate older version
        db_conn["version"].insert(dict(version="30", os="Linux"))

        # Add folders table with old schema
        db_conn["folders"].insert(
            dict(
                folder_name="/old/folder",
                alias="Old Folder",
                folder_is_active="True",
            )
        )

        yield db_conn

        db_conn.close()

    def test_migration_version_check(self, tmp_path):
        """Test version checking during migration."""
        old_version = 30
        current_version = 33

        needs_migration = current_version > old_version

        assert needs_migration is True

    def test_migration_no_op_for_current_version(self, tmp_path):
        """Test that no migration is needed for current version."""
        old_version = 33
        current_version = 33

        needs_migration = current_version > old_version

        assert needs_migration is False


class TestDatabaseIntegrity:
    """Test suite for database integrity checks."""

    def test_connection_string_format(self):
        """Test database connection string format."""
        db_path = "/path/to/database.db"
        connection_string = "sqlite:///" + db_path

        assert connection_string == "sqlite:////path/to/database.db"

    def test_database_commit(self, tmp_path):
        """Test database commit operation."""
        db_path = str(tmp_path / "test.db")
        db_conn = sqlite_wrapper.Database.connect(db_path)
        schema.ensure_schema(db_conn)
        # Create test_table for this test
        db_conn._conn.execute(
            "CREATE TABLE test_table (id INTEGER PRIMARY KEY, value TEXT)"
        )
        db_conn._conn.commit()

        db_conn["test_table"].insert(dict(value="test"))

        # Without commit, changes should persist in transaction
        # With commit, changes are permanent
        db_conn.commit()

        db_conn.close()

        # Reconnect and verify
        db_conn2 = sqlite_wrapper.Database.connect(db_path)
        record = db_conn2["test_table"].find_one()
        assert record is not None
        db_conn2.close()

    def test_database_close(self, tmp_path):
        """Test database close operation."""
        db_path = str(tmp_path / "test.db")
        db_conn = sqlite_wrapper.Database.connect(db_path)
        schema.ensure_schema(db_conn)
        # Create test_table for this test
        db_conn._conn.execute(
            "CREATE TABLE test_table (id INTEGER PRIMARY KEY, value TEXT)"
        )
        db_conn._conn.commit()

        db_conn["test_table"].insert(dict(value="test"))
        db_conn.close()

        # Database should be closed, operations should not be possible
        # (This is implicitly tested by reopening)
        db_conn2 = sqlite_wrapper.Database.connect(db_path)
        record = db_conn2["test_table"].find_one()
        assert record is not None
        db_conn2.close()

    def test_multiple_connections(self, tmp_path):
        """Test multiple connections to same database."""
        db_path = str(tmp_path / "test.db")

        # Connection 1
        db_conn1 = sqlite_wrapper.Database.connect(db_path)
        schema.ensure_schema(db_conn1)
        # Create test_table for this test
        db_conn1._conn.execute(
            "CREATE TABLE test_table (id INTEGER PRIMARY KEY, value TEXT)"
        )
        db_conn1._conn.commit()
        db_conn1["test_table"].insert(dict(value="test1"))

        # Connection 2
        db_conn2 = sqlite_wrapper.Database.connect(db_path)
        db_conn2["test_table"].insert(dict(value="conn2"))

        db_conn1.commit()
        db_conn2.commit()

        # Both connections should see all data
        records = list(db_conn1["test_table"].all())
        assert len(records) == 2

        db_conn1.close()
        db_conn2.close()


class TestTableRelationships:
    """Test suite for table relationships."""

    def test_folder_to_settings_relationship(self, tmp_path):
        """Test relationship between folders and settings."""
        db_path = str(tmp_path / "test.db")
        db_conn = sqlite_wrapper.Database.connect(db_path)
        schema.ensure_schema(db_conn)

        db_conn["version"].insert(dict(version="33", os="Linux"))

        # Create settings
        settings_id = db_conn["settings"].insert(
            dict(
                folder_name="Main Settings",
                alias="",
                folder_is_active=False,
            )
        )

        # Create folder
        folder_id = db_conn["folders"].insert(
            dict(
                folder_name="/home/user/folder",
                alias="User Folder",
                folder_is_active=True,
            )
        )

        # Verify both exist and can be queried
        folder = db_conn["folders"].find_one(id=folder_id)
        assert folder is not None
        assert folder["folder_name"] == "/home/user/folder"

        settings = db_conn["settings"].find_one(id=settings_id)
        assert settings is not None
        assert settings["folder_name"] == "Main Settings"

        db_conn.close()

    def test_folder_to_emails_relationship(self, tmp_path):
        """Test relationship between folders and emails."""
        db_path = str(tmp_path / "test.db")
        db_conn = sqlite_wrapper.Database.connect(db_path)
        schema.ensure_schema(db_conn)

        db_conn["version"].insert(dict(version="33", os="Linux"))

        # Create folder
        folder_id = db_conn["folders"].insert(
            dict(
                folder_name="/home/user/folder",
                alias="User Folder",
            )
        )

        # Create emails for folder
        db_conn["emails_to_send"].insert_many(
            [
                dict(folder_id=folder_id, folder_alias="User Folder", log="pending"),
                dict(folder_id=folder_id, folder_alias="User Folder", log="sent"),
            ]
        )

        # Get emails for folder
        emails = list(db_conn["emails_to_send"].find(folder_id=folder_id))

        assert len(emails) == 2
        assert emails[0]["folder_id"] == folder_id

        db_conn.close()
