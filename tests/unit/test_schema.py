"""Unit tests for schema.py module.

Tests:
- ensure_schema() creates all tables
- ensure_schema() handles existing tables gracefully
- ensure_schema() creates all indexes
- ensure_schema() adds plugin_configurations column to folders table
- ensure_schema() initializes plugin_configurations for existing rows
- ensure_schema() handles errors gracefully
- Foreign key constraints are enabled
- All normalized tables are created correctly

Tables tested:
- version
- settings
- administrative
- folders
- processed_files
- users
- organizations
- projects
- files
- batches
- processors
- processing_jobs
- job_logs
- tags
- file_tags
"""

import pytest

pytestmark = [pytest.mark.unit, pytest.mark.database]
from unittest.mock import MagicMock

import schema
from backend.database import sqlite_wrapper


class TestSchemaCreation:
    """Test suite for schema.ensure_schema() function."""

    @pytest.fixture
    def temp_db_path(self, tmp_path):
        """Create a temporary database path."""
        return str(tmp_path / "test_schema.db")

    @pytest.fixture
    def fresh_database(self, temp_db_path):
        """Create a fresh database connection."""
        db_conn = sqlite_wrapper.Database.connect(temp_db_path)
        yield db_conn
        db_conn.close()

    def test_ensure_schema_creates_version_table(self, fresh_database):
        """Test that ensure_schema creates the version table."""
        schema.ensure_schema(fresh_database)

        # Verify table exists by querying it
        version_table = fresh_database["version"]
        # Should be able to insert without error
        version_table.insert(dict(version="1.0", os="Linux", notes="Test"))
        fresh_database.commit()

        # Verify we can read it back
        record = version_table.find_one(id=1)
        assert record is not None
        assert record["version"] == "1.0"
        assert record["os"] == "Linux"

    def test_ensure_schema_creates_settings_table(self, fresh_database):
        """Test that ensure_schema creates the settings table."""
        schema.ensure_schema(fresh_database)

        settings_table = fresh_database["settings"]
        settings_table.insert(
            dict(
                folder_name="test",
                alias="Test",
                folder_is_active=1,
                convert_to_format="csv",
            )
        )
        fresh_database.commit()

        record = settings_table.find_one(id=1)
        assert record is not None
        assert record["folder_name"] == "test"

    def test_ensure_schema_creates_administrative_table(self, fresh_database):
        """Test that ensure_schema creates the administrative table."""
        schema.ensure_schema(fresh_database)

        admin_table = fresh_database["administrative"]
        admin_table.insert(
            dict(logs_directory="/tmp/logs", errors_folder="/tmp/errors")
        )
        fresh_database.commit()

        record = admin_table.find_one(id=1)
        assert record is not None
        assert record["logs_directory"] == "/tmp/logs"

    def test_ensure_schema_creates_folders_table(self, fresh_database):
        """Test that ensure_schema creates the folders table."""
        schema.ensure_schema(fresh_database)

        folders_table = fresh_database["folders"]
        folders_table.insert(
            dict(
                folder_name="/home/user/test",
                alias="Test Folder",
                folder_is_active=1,
                convert_to_format="csv",
            )
        )
        fresh_database.commit()

        record = folders_table.find_one(id=1)
        assert record is not None
        assert record["folder_name"] == "/home/user/test"

    def test_ensure_schema_creates_processed_files_table(self, fresh_database):
        """Test that ensure_schema creates the processed_files table."""
        schema.ensure_schema(fresh_database)

        processed_table = fresh_database["processed_files"]
        processed_table.insert(dict(file_name="test.edi", md5="abc123", folder_id=1))
        fresh_database.commit()

        record = processed_table.find_one(id=1)
        assert record is not None
        assert record["file_name"] == "test.edi"

    def test_ensure_schema_creates_users_table(self, fresh_database):
        """Test that ensure_schema creates the users table."""
        schema.ensure_schema(fresh_database)

        users_table = fresh_database["users"]
        users_table.insert(
            dict(id="user1", email="user@example.com", display_name="Test User")
        )
        fresh_database.commit()

        record = users_table.find_one(id="user1")
        assert record is not None
        assert record["email"] == "user@example.com"

    def test_ensure_schema_creates_organizations_table(self, fresh_database):
        """Test that ensure_schema creates the organizations table."""
        schema.ensure_schema(fresh_database)

        orgs_table = fresh_database["organizations"]
        orgs_table.insert(dict(id="org1", name="Test Organization"))
        fresh_database.commit()

        record = orgs_table.find_one(id="org1")
        assert record is not None
        assert record["name"] == "Test Organization"

    def test_ensure_schema_creates_projects_table(self, fresh_database):
        """Test that ensure_schema creates the projects table."""
        schema.ensure_schema(fresh_database)

        # First create an organization
        orgs_table = fresh_database["organizations"]
        orgs_table.insert(dict(id="org1", name="Test Org"))

        projects_table = fresh_database["projects"]
        projects_table.insert(dict(id="proj1", org_id="org1", name="Test Project"))
        fresh_database.commit()

        record = projects_table.find_one(id="proj1")
        assert record is not None
        assert record["org_id"] == "org1"

    def test_ensure_schema_creates_files_table(self, fresh_database):
        """Test that ensure_schema creates the files table."""
        schema.ensure_schema(fresh_database)

        # Create organization and project first
        fresh_database["organizations"].insert(dict(id="org1", name="Test Org"))
        fresh_database["projects"].insert(
            dict(id="proj1", org_id="org1", name="Test Project")
        )
        fresh_database["users"].insert(dict(id="user1", email="user@example.com"))

        files_table = fresh_database["files"]
        files_table.insert(
            dict(
                id="file1",
                project_id="proj1",
                original_filename="test.edi",
                storage_path="/tmp/test.edi",
                created_by="user1",
            )
        )
        fresh_database.commit()

        record = files_table.find_one(id="file1")
        assert record is not None
        assert record["original_filename"] == "test.edi"

    def test_ensure_schema_creates_batches_table(self, fresh_database):
        """Test that ensure_schema creates the batches table."""
        schema.ensure_schema(fresh_database)

        fresh_database["organizations"].insert(dict(id="org1", name="Test Org"))
        fresh_database["projects"].insert(
            dict(id="proj1", org_id="org1", name="Test Project")
        )
        fresh_database["users"].insert(dict(id="user1", email="user@example.com"))

        batches_table = fresh_database["batches"]
        batches_table.insert(
            dict(
                id="batch1",
                project_id="proj1",
                name="Test Batch",
                status="pending",
                created_by="user1",
            )
        )
        fresh_database.commit()

        record = batches_table.find_one(id="batch1")
        assert record is not None
        assert record["project_id"] == "proj1"

    def test_ensure_schema_creates_processors_table(self, fresh_database):
        """Test that ensure_schema creates the processors table."""
        schema.ensure_schema(fresh_database)

        processors_table = fresh_database["processors"]
        processors_table.insert(dict(id="proc1", name="Test Processor", version="1.0"))
        fresh_database.commit()

        record = processors_table.find_one(id="proc1")
        assert record is not None
        assert record["name"] == "Test Processor"

    def test_ensure_schema_creates_processing_jobs_table(self, fresh_database):
        """Test that ensure_schema creates the processing_jobs table."""
        schema.ensure_schema(fresh_database)

        fresh_database["organizations"].insert(dict(id="org1", name="Test Org"))
        fresh_database["projects"].insert(
            dict(id="proj1", org_id="org1", name="Test Project")
        )
        fresh_database["files"].insert(
            dict(
                id="file1",
                project_id="proj1",
                original_filename="test.edi",
                storage_path="/tmp/test.edi",
            )
        )
        fresh_database["batches"].insert(
            dict(id="batch1", project_id="proj1", name="Test Batch")
        )
        fresh_database["processors"].insert(dict(id="proc1", name="Test Processor"))

        jobs_table = fresh_database["processing_jobs"]
        jobs_table.insert(
            dict(
                id="job1",
                batch_id="batch1",
                file_id="file1",
                processor_id="proc1",
                status="pending",
            )
        )
        fresh_database.commit()

        record = jobs_table.find_one(id="job1")
        assert record is not None
        assert record["batch_id"] == "batch1"

    def test_ensure_schema_creates_job_logs_table(self, fresh_database):
        """Test that ensure_schema creates the job_logs table."""
        schema.ensure_schema(fresh_database)

        fresh_database["organizations"].insert(dict(id="org1", name="Test Org"))
        fresh_database["projects"].insert(
            dict(id="proj1", org_id="org1", name="Test Project")
        )
        fresh_database["files"].insert(
            dict(
                id="file1",
                project_id="proj1",
                original_filename="test.edi",
                storage_path="/tmp/test.edi",
            )
        )
        fresh_database["batches"].insert(
            dict(id="batch1", project_id="proj1", name="Test Batch")
        )
        fresh_database["processors"].insert(dict(id="proc1", name="Test Processor"))
        fresh_database["processing_jobs"].insert(
            dict(
                id="job1",
                batch_id="batch1",
                file_id="file1",
                processor_id="proc1",
                status="pending",
            )
        )

        logs_table = fresh_database["job_logs"]
        logs_table.insert(dict(job_id="job1", level="INFO", message="Test message"))
        fresh_database.commit()

        record = logs_table.find_one(id=1)
        assert record is not None
        assert record["job_id"] == "job1"

    def test_ensure_schema_creates_tags_table(self, fresh_database):
        """Test that ensure_schema creates the tags table."""
        schema.ensure_schema(fresh_database)

        tags_table = fresh_database["tags"]
        tags_table.insert(dict(id="tag1", name="important"))
        fresh_database.commit()

        record = tags_table.find_one(id="tag1")
        assert record is not None
        assert record["name"] == "important"

    def test_ensure_schema_creates_file_tags_table(self, fresh_database):
        """Test that ensure_schema creates the file_tags table."""
        schema.ensure_schema(fresh_database)

        fresh_database["organizations"].insert(dict(id="org1", name="Test Org"))
        fresh_database["projects"].insert(
            dict(id="proj1", org_id="org1", name="Test Project")
        )
        fresh_database["files"].insert(
            dict(
                id="file1",
                project_id="proj1",
                original_filename="test.edi",
                storage_path="/tmp/test.edi",
            )
        )
        fresh_database["tags"].insert(dict(id="tag1", name="important"))

        file_tags_table = fresh_database["file_tags"]
        file_tags_table.insert(dict(file_id="file1", tag_id="tag1"))
        fresh_database.commit()

        record = file_tags_table.find_one(file_id="file1", tag_id="tag1")
        assert record is not None


class TestSchemaIndexes:
    """Test suite for schema indexes."""

    @pytest.fixture
    def database_with_indexes(self, tmp_path):
        """Create a database with schema and indexes."""
        db_path = str(tmp_path / "test_indexes.db")
        db_conn = sqlite_wrapper.Database.connect(db_path)
        schema.ensure_schema(db_conn)
        yield db_conn
        db_conn.close()

    def test_index_on_files_project_id(self, database_with_indexes):
        """Test that idx_files_project_id index is created."""
        # Check if index exists by querying sqlite_master
        indexes = database_with_indexes.query(
            "SELECT name FROM sqlite_master WHERE type='index' AND name='idx_files_project_id'"
        )
        assert len(indexes) > 0

    def test_index_on_batches_project_id(self, database_with_indexes):
        """Test that idx_batches_project_id index is created."""
        indexes = database_with_indexes.query(
            "SELECT name FROM sqlite_master WHERE type='index' AND name='idx_batches_project_id'"
        )
        assert len(indexes) > 0

    def test_index_on_jobs_status(self, database_with_indexes):
        """Test that idx_jobs_status index is created."""
        indexes = database_with_indexes.query(
            "SELECT name FROM sqlite_master WHERE type='index' AND name='idx_jobs_status'"
        )
        assert len(indexes) > 0

    def test_index_on_jobs_file_id(self, database_with_indexes):
        """Test that idx_jobs_file_id index is created."""
        indexes = database_with_indexes.query(
            "SELECT name FROM sqlite_master WHERE type='index' AND name='idx_jobs_file_id'"
        )
        assert len(indexes) > 0


class TestSchemaForeignKeys:
    """Test suite for foreign key constraints."""

    @pytest.fixture
    def database_with_fk(self, tmp_path):
        """Create a database with foreign keys enabled."""
        db_path = str(tmp_path / "test_fk.db")
        db_conn = sqlite_wrapper.Database.connect(db_path)
        schema.ensure_schema(db_conn)
        yield db_conn
        db_conn.close()

    def test_foreign_keys_enabled(self, database_with_fk):
        """Test that foreign keys are enabled."""
        result = database_with_fk.query("PRAGMA foreign_keys")
        assert len(result) > 0
        assert result[0]["foreign_keys"] == 1

    def test_cascade_delete_projects_to_files(self, database_with_fk):
        """Test CASCADE DELETE from projects to files."""
        database_with_fk["organizations"].insert(dict(id="org1", name="Test Org"))
        database_with_fk["projects"].insert(
            dict(id="proj1", org_id="org1", name="Test Project")
        )
        database_with_fk["files"].insert(
            dict(
                id="file1",
                project_id="proj1",
                original_filename="test.edi",
                storage_path="/tmp/test.edi",
            )
        )

        # Delete project
        database_with_fk["projects"].delete(id="proj1")

        # File should be deleted due to CASCADE
        file = database_with_fk["files"].find_one(id="file1")
        assert file is None

    def test_set_null_organizations_to_projects(self, database_with_fk):
        """Test SET NULL from organizations to projects."""
        database_with_fk["organizations"].insert(dict(id="org1", name="Test Org"))
        database_with_fk["projects"].insert(
            dict(id="proj1", org_id="org1", name="Test Project")
        )

        # Delete organization
        database_with_fk["organizations"].delete(id="org1")

        # Project should have NULL org_id
        project = database_with_fk["projects"].find_one(id="proj1")
        assert project is not None
        assert project["org_id"] is None


class TestSchemaBackwardCompatibility:
    """Test suite for backward compatibility features."""

    @pytest.fixture
    def old_folders_database(self, tmp_path):
        """Create a database with old folders schema (without plugin_configurations)."""
        db_path = str(tmp_path / "old_folders.db")
        db_conn = sqlite_wrapper.Database.connect(db_path)

        # Create folders table without plugin_configurations column
        db_conn.query(
            """
            CREATE TABLE folders (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                folder_name TEXT,
                alias TEXT
            )
        """
        )

        # Insert some data
        db_conn["folders"].insert_many(
            [
                dict(folder_name="/folder1", alias="Folder 1"),
                dict(folder_name="/folder2", alias="Folder 2"),
            ]
        )

        yield db_conn
        db_conn.close()

    def test_adds_plugin_configurations_column(self, old_folders_database):
        """Test that ensure_schema adds plugin_configurations column."""
        # Run ensure_schema on old database
        schema.ensure_schema(old_folders_database)

        # Check that column exists
        columns = old_folders_database.query("PRAGMA table_info(folders)")
        column_names = [col["name"] for col in columns]
        assert "plugin_configurations" in column_names

    def test_initializes_plugin_configurations_for_existing_rows(
        self, old_folders_database
    ):
        """Test that ensure_schema initializes plugin_configurations for existing rows."""
        # Run ensure_schema on old database
        schema.ensure_schema(old_folders_database)

        # Check that existing rows have plugin_configurations set to {} (dict)
        folders = list(old_folders_database["folders"].all())
        for folder in folders:
            # The column value is stored as a JSON string in the database
            # but sqlite_wrapper may deserialize it
            pc = folder["plugin_configurations"]
            if isinstance(pc, str):
                assert pc == "{}"
            else:
                assert pc == {}

    def test_handles_existing_plugin_configurations_column(self, tmp_path):
        """Test that ensure_schema handles existing plugin_configurations column gracefully."""
        db_path = str(tmp_path / "existing_column.db")
        db_conn = sqlite_wrapper.Database.connect(db_path)

        # Create folders table with plugin_configurations column
        db_conn.query(
            """
            CREATE TABLE folders (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                folder_name TEXT,
                plugin_configurations TEXT
            )
        """
        )

        # Run ensure_schema - should not fail
        schema.ensure_schema(db_conn)

        db_conn.close()


class TestSchemaErrorHandling:
    """Test suite for error handling in ensure_schema."""

    @pytest.fixture
    def mock_database(self):
        """Create a mock database connection."""
        mock_db = MagicMock()
        return mock_db

    def test_handles_query_error_gracefully(self, mock_database):
        """Test that ensure_schema handles query errors gracefully."""
        # Make query raise an exception
        mock_database.query.side_effect = Exception("Database error")

        # Should not raise exception
        schema.ensure_schema(mock_database)

    def test_handles_raw_connection_fallback(self, mock_database):
        """Test that ensure_schema falls back to raw connection when needed."""
        # Make query raise an exception
        mock_database.query.side_effect = Exception("Query error")

        # Provide a raw connection
        mock_conn = MagicMock()
        mock_database._conn = mock_conn

        # Should use raw connection
        schema.ensure_schema(mock_database)

        # Verify raw connection was used
        assert mock_conn.execute.called or mock_conn.commit.called

    def test_handles_all_errors_silently(self, mock_database):
        """Test that ensure_schema handles all errors silently."""
        # Make both query and raw connection fail
        mock_database.query.side_effect = Exception("Query error")
        mock_database._conn = MagicMock()
        mock_database._conn.execute.side_effect = Exception("Raw connection error")

        # Should not raise exception
        schema.ensure_schema(mock_database)


class TestSchemaIdempotency:
    """Test suite for ensure_schema idempotency."""

    @pytest.fixture
    def database(self, tmp_path):
        """Create a database connection."""
        db_path = str(tmp_path / "test_idempotent.db")
        db_conn = sqlite_wrapper.Database.connect(db_path)
        yield db_conn
        db_conn.close()

    def test_multiple_calls_dont_fail(self, database):
        """Test that calling ensure_schema multiple times doesn't fail."""
        schema.ensure_schema(database)
        schema.ensure_schema(database)
        schema.ensure_schema(database)

        # Should still be able to use the database
        database["version"].insert(dict(version="1.0", os="Linux"))
        database.commit()

        record = database["version"].find_one(id=1)
        assert record is not None

    def test_multiple_calls_preserve_data(self, database):
        """Test that calling ensure_schema multiple times preserves existing data."""
        # Create schema and insert data
        schema.ensure_schema(database)
        database["folders"].insert(dict(folder_name="/test", alias="Test"))
        database.commit()

        # Call ensure_schema again
        schema.ensure_schema(database)

        # Data should still be there
        record = database["folders"].find_one(id=1)
        assert record is not None
        assert record["folder_name"] == "/test"


class TestSchemaColumnDefinitions:
    """Test suite for column definitions."""

    @pytest.fixture
    def database(self, tmp_path):
        """Create a database connection."""
        db_path = str(tmp_path / "test_columns.db")
        db_conn = sqlite_wrapper.Database.connect(db_path)
        schema.ensure_schema(db_conn)
        yield db_conn
        db_conn.close()

    def test_version_table_columns(self, database):
        """Test that version table has correct columns."""
        columns = database.query("PRAGMA table_info(version)")
        column_names = [col["name"] for col in columns]
        expected = ["id", "version", "os", "notes"]
        for col in expected:
            assert col in column_names

    def test_settings_table_columns(self, database):
        """Test that settings table has key columns."""
        columns = database.query("PRAGMA table_info(settings)")
        column_names = [col["name"] for col in columns]
        assert "folder_name" in column_names
        assert "alias" in column_names
        assert "folder_is_active" in column_names
        assert "convert_to_format" in column_names

    def test_folders_table_columns(self, database):
        """Test that folders table has key columns."""
        columns = database.query("PRAGMA table_info(folders)")
        column_names = [col["name"] for col in columns]
        assert "folder_name" in column_names
        assert "alias" in column_names
        assert "folder_is_active" in column_names
        assert "plugin_configurations" in column_names

    def test_processed_files_table_columns(self, database):
        """Test that processed_files table has key columns."""
        columns = database.query("PRAGMA table_info(processed_files)")
        column_names = [col["name"] for col in columns]
        assert "file_name" in column_names
        assert "md5" in column_names
        assert "folder_id" in column_names

    def test_users_table_columns(self, database):
        """Test that users table has correct columns."""
        columns = database.query("PRAGMA table_info(users)")
        column_names = [col["name"] for col in columns]
        expected = ["id", "email", "display_name", "created_at", "updated_at"]
        for col in expected:
            assert col in column_names

    def test_organizations_table_columns(self, database):
        """Test that organizations table has correct columns."""
        columns = database.query("PRAGMA table_info(organizations)")
        column_names = [col["name"] for col in columns]
        expected = ["id", "name", "created_at"]
        for col in expected:
            assert col in column_names

    def test_projects_table_columns(self, database):
        """Test that projects table has correct columns."""
        columns = database.query("PRAGMA table_info(projects)")
        column_names = [col["name"] for col in columns]
        assert "id" in column_names
        assert "org_id" in column_names
        assert "name" in column_names

    def test_files_table_columns(self, database):
        """Test that files table has correct columns."""
        columns = database.query("PRAGMA table_info(files)")
        column_names = [col["name"] for col in columns]
        assert "id" in column_names
        assert "project_id" in column_names
        assert "original_filename" in column_names
        assert "storage_path" in column_names

    def test_batches_table_columns(self, database):
        """Test that batches table has correct columns."""
        columns = database.query("PRAGMA table_info(batches)")
        column_names = [col["name"] for col in columns]
        assert "id" in column_names
        assert "project_id" in column_names
        assert "status" in column_names

    def test_processing_jobs_table_columns(self, database):
        """Test that processing_jobs table has correct columns."""
        columns = database.query("PRAGMA table_info(processing_jobs)")
        column_names = [col["name"] for col in columns]
        assert "id" in column_names
        assert "batch_id" in column_names
        assert "file_id" in column_names
        assert "processor_id" in column_names
        assert "status" in column_names

    def test_job_logs_table_columns(self, database):
        """Test that job_logs table has correct columns."""
        columns = database.query("PRAGMA table_info(job_logs)")
        column_names = [col["name"] for col in columns]
        assert "job_id" in column_names
        assert "level" in column_names
        assert "message" in column_names


class TestSchemaConstraints:
    """Test that schema constraints are actually enforced."""

    @pytest.fixture
    def database(self, tmp_path):
        """Create a database with schema applied."""
        db_path = str(tmp_path / "constraints_test.db")
        db_conn = sqlite_wrapper.Database.connect(db_path)
        schema.ensure_schema(db_conn)
        yield db_conn
        db_conn.close()

    def test_users_email_unique_constraint(self, database):
        """Duplicate user emails must be rejected."""
        import sqlite3

        database["users"].insert(
            dict(id="u1", email="dup@example.com", display_name="A")
        )
        with pytest.raises((Exception, sqlite3.IntegrityError)):
            database["users"].insert(
                dict(id="u2", email="dup@example.com", display_name="B")
            )

        # Only the first insert must be present
        users = list(
            database.query("SELECT * FROM users WHERE email = 'dup@example.com'")
        )
        assert len(users) == 1
        assert users[0]["id"] == "u1"

    def test_organizations_name_not_null_constraint(self, database):
        """Organization name must not be null (NOT NULL constraint)."""
        import sqlite3

        with pytest.raises((Exception, sqlite3.IntegrityError)):
            database["organizations"].insert(dict(id="org1", name=None))

        orgs = list(database["organizations"].all())
        assert len(orgs) == 0, "Failed insert must not persist partial data"

    def test_processed_files_table_accepts_multiple_files_same_folder(self, database):
        """Multiple processed files for the same folder must be allowed."""
        for i in range(3):
            database["processed_files"].insert(
                dict(file_name=f"file{i}.edi", md5=f"hash{i}", folder_id=1)
            )
        records = list(database["processed_files"].all())
        assert len(records) == 3

    def test_schema_idempotent_with_existing_users(self, database):
        """ensure_schema() called twice must not lose existing user data."""
        database["users"].insert(
            dict(id="persist", email="keep@example.com", display_name="Keep")
        )
        schema.ensure_schema(database)
        user = database["users"].find_one(id="persist")
        assert user is not None
        assert user["email"] == "keep@example.com"
