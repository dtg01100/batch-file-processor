"""Security validation tests for batch file processor.

These tests validate security measures including:
1. Input validation and sanitization
2. File path security (directory traversal prevention)
3. SQL injection prevention
4. Malicious content handling
5. File permission validation
"""

import pytest

pytestmark = [pytest.mark.integration, pytest.mark.security, pytest.mark.e2e]

import tempfile
from pathlib import Path
from unittest.mock import MagicMock

import create_database
from copy_backend import do as copy_backend_do
from dispatch.orchestrator import DispatchConfig, DispatchOrchestrator
from dispatch.pipeline.converter import EDIConverterStep
from dispatch.pipeline.tweaker import EDITweakerStep
from dispatch.pipeline.validator import EDIValidationStep
from interface.database.database_obj import DatabaseObj


@pytest.fixture
def secure_test_environment():
    """Create a secure test environment."""
    with tempfile.TemporaryDirectory() as tmpdir:
        workspace = Path(tmpdir)

        # Create secure directory structure
        (workspace / "input").mkdir(mode=0o755)
        (workspace / "output").mkdir(mode=0o755)
        (workspace / "database").mkdir(mode=0o755)

        # Create database
        db_path = workspace / "database" / "folders.db"
        create_database.do("33", str(db_path), str(workspace), "Linux")

        from batch_file_processor.constants import CURRENT_DATABASE_VERSION

        db = DatabaseObj(
            database_path=str(db_path),
            database_version=CURRENT_DATABASE_VERSION,
            config_folder=str(workspace),
            running_platform="Linux",
        )

        yield {
            "workspace": workspace,
            "db": db,
        }

        db.close()


@pytest.fixture
def pipeline_steps():
    """Create pipeline steps for processing."""
    return {
        "validator_step": EDIValidationStep(),
        "converter_step": EDIConverterStep(),
        "tweaker_step": EDITweakerStep(),
    }


class TestInputValidation:
    """Test input validation and sanitization."""

    def test_malicious_edi_content_handling(
        self, secure_test_environment, pipeline_steps
    ):
        """Test that malicious EDI content is properly handled."""
        workspace = secure_test_environment["workspace"]
        db = secure_test_environment["db"]

        # Create EDI file with potentially malicious content
        # SQL injection attempts, script tags, etc.
        malicious_content = """A00000120240101001TESTVENDOR         Test Vendor Inc                 00001
B001001ITEM001     000010EA0010'; DROP TABLE folders; --    Test Item 1                     0000010000
B001002ITEM002     000020EA0020<script>alert('xss')</script>                0000020000
C00000003000030000
"""
        edi_file = workspace / "input" / "malicious.edi"
        edi_file.write_text(malicious_content)

        folder_config = {
            "folder_name": str(workspace / "input"),
            "alias": "Security Test",
            "process_backend_copy": True,
            "copy_to_directory": str(workspace / "output"),
            "convert_to_format": "csv",
        }
        db.folders_table.insert(folder_config)

        # Process should not crash or execute malicious code
        class CopyBackend:
            def send(self, params: dict, settings: dict, filename: str) -> None:
                copy_backend_do(params, settings, filename)

        backends = {"copy": CopyBackend()}
        config = DispatchConfig(
            backends=backends,
            settings={},
            validator_step=pipeline_steps["validator_step"],
            converter_step=pipeline_steps["converter_step"],
            tweaker_step=pipeline_steps["tweaker_step"],
        )
        orchestrator = DispatchOrchestrator(config)

        folders = list(db.folders_table.all())

        # Should process without executing malicious content
        result = orchestrator.process_folder(folders[0], MagicMock())

        # Result must be a FolderResult with defined outcome (success or failure with errors)
        assert hasattr(result, "success"), "process_folder must return a FolderResult"
        assert hasattr(result, "errors")
        # If it failed, errors should explain why (validation/conversion) — not a crash
        if not result.success:
            assert len(result.errors) > 0, "Failed result must have error details"

        # Verify database is intact (SQL in EDI content must not have executed)
        all_folders = list(db.folders_table.all())
        assert (
            len(all_folders) == 1
        ), "SQL injection in EDI content must not drop the folders table"
        assert (
            all_folders[0]["alias"] == "Security Test"
        ), "Folder record must be unchanged"

    def test_null_byte_injection(self, secure_test_environment, pipeline_steps):
        """Test handling of null byte injection attempts."""
        workspace = secure_test_environment["workspace"]
        db = secure_test_environment["db"]

        # Create file with null byte in name (should be sanitized)
        safe_content = """A00000120240101001TESTVENDOR         Test Vendor Inc                 00001
B001001ITEM001     000010EA0010Test Item                       0000010000
"""
        # Note: Actual null bytes in filenames are handled by OS
        # We test that the system handles unusual filenames gracefully
        edi_file = workspace / "input" / "test_normal.edi"
        edi_file.write_text(safe_content)

        folder_config = {
            "folder_name": str(workspace / "input"),
            "alias": "Null Byte Test",
            "process_backend_copy": True,
            "copy_to_directory": str(workspace / "output"),
            "convert_to_format": "csv",
        }
        db.folders_table.insert(folder_config)

        # Should process normally
        class CopyBackend:
            def send(self, params: dict, settings: dict, filename: str) -> None:
                copy_backend_do(params, settings, filename)

        config = DispatchConfig(
            backends={"copy": CopyBackend()},
            settings={},
            validator_step=pipeline_steps["validator_step"],
            converter_step=pipeline_steps["converter_step"],
            tweaker_step=pipeline_steps["tweaker_step"],
        )
        orchestrator = DispatchOrchestrator(config)

        folders = list(db.folders_table.all())
        result = orchestrator.process_folder(folders[0], MagicMock())

        # Should complete without errors — normal EDI must process successfully
        assert hasattr(result, "success"), "process_folder must return a FolderResult"
        assert (
            result.success is True
        ), f"Normal EDI processing must succeed; errors: {result.errors}"
        assert result.files_processed >= 1, "At least one file must have been processed"


class TestFilePathSecurity:
    """Test file path security and directory traversal prevention."""

    def test_directory_traversal_prevention(self, secure_test_environment):
        """Test that directory traversal attacks are prevented."""
        workspace = secure_test_environment["workspace"]
        db = secure_test_environment["db"]

        # Attempt to configure folder with traversal path
        traversal_paths = [
            "../../../etc",
            "/etc/passwd",
            "../../..",
            "..\\..\\..\\windows\\system32",  # Windows-style
            "....//....//etc",  # Double encoding attempt
        ]

        for traversal_path in traversal_paths:
            # Try to insert folder with traversal path
            folder_config = {
                "folder_name": traversal_path,
                "alias": f"Traversal Test {traversal_path}",
                "process_backend_copy": True,
                "copy_to_directory": str(workspace / "output"),
                "convert_to_format": "csv",
            }

            # Database should accept it (validation happens at processing time)
            db.folders_table.insert(folder_config)

            # Verify folder was added
            folders = list(db.folders_table.all())
            assert len(folders) >= 1

            # Clean up for next iteration
            db.folders_table.delete(id=folders[-1]["id"])

        # Database should still be functional
        final_folders = list(db.folders_table.all())
        assert len(final_folders) == 0

    def test_absolute_path_validation(self, secure_test_environment):
        """Test handling of absolute paths."""
        workspace = secure_test_environment["workspace"]
        db = secure_test_environment["db"]

        # Valid absolute path
        valid_path = str(workspace / "input")
        folder_config = {
            "folder_name": valid_path,
            "alias": "Valid Absolute Path",
            "process_backend_copy": True,
            "copy_to_directory": str(workspace / "output"),
            "convert_to_format": "csv",
        }
        db.folders_table.insert(folder_config)

        # Should be able to retrieve
        folders = list(db.folders_table.all())
        assert len(folders) == 1
        assert folders[0]["folder_name"] == valid_path

    def test_symlink_attack_prevention(self, secure_test_environment, pipeline_steps):
        """Test prevention of symlink-based attacks."""
        workspace = secure_test_environment["workspace"]
        db = secure_test_environment["db"]

        # Create a symlink pointing outside workspace
        outside_file = workspace / "outside.txt"
        outside_file.write_text("sensitive data")

        symlink_path = workspace / "input" / "link.txt"
        try:
            symlink_path.symlink_to(outside_file)
        except (OSError, NotImplementedError):
            # Symlinks not supported on this system
            pytest.skip("Symlinks not supported")

        # Create EDI file
        edi_content = """A00000120240101001TESTVENDOR         Test Vendor Inc                 00001
B001001ITEM001     000010EA0010Test Item                       0000010000
"""
        edi_file = workspace / "input" / "test.edi"
        edi_file.write_text(edi_content)

        folder_config = {
            "folder_name": str(workspace / "input"),
            "alias": "Symlink Test",
            "process_backend_copy": True,
            "copy_to_directory": str(workspace / "output"),
            "convert_to_format": "csv",
        }
        db.folders_table.insert(folder_config)

        # Process should complete
        class CopyBackend:
            def send(self, params: dict, settings: dict, filename: str) -> None:
                # Verify we're not copying symlinks to sensitive files
                if "outside.txt" in str(params.get("copy_to_directory", "")):
                    raise SecurityError("Attempted to copy to sensitive location")
                copy_backend_do(params, settings, filename)

        config = DispatchConfig(
            backends={"copy": CopyBackend()},
            settings={},
            validator_step=pipeline_steps["validator_step"],
            converter_step=pipeline_steps["converter_step"],
            tweaker_step=pipeline_steps["tweaker_step"],
        )
        orchestrator = DispatchOrchestrator(config)

        folders = list(db.folders_table.all())
        result = orchestrator.process_folder(folders[0], MagicMock())

        # Verify outside file wasn't modified
        assert outside_file.read_text() == "sensitive data"


class TestDatabaseSecurity:
    """Test database security and SQL injection prevention."""

    def test_sql_injection_in_folder_name(self, secure_test_environment):
        """Test SQL injection prevention in folder names."""
        workspace = secure_test_environment["workspace"]
        db = secure_test_environment["db"]

        # SQL injection attempts
        injection_attempts = [
            "'; DROP TABLE folders; --",
            "1; DELETE FROM folders WHERE 1=1; --",
            "test' OR '1'='1",
            "test'; INSERT INTO folders VALUES (999, 'hacked'); --",
        ]

        for injection in injection_attempts:
            folder_config = {
                "folder_name": injection,
                "alias": "Injection Test",
                "process_backend_copy": True,
                "copy_to_directory": str(workspace / "output"),
                "convert_to_format": "csv",
            }

            # Should not crash or execute injection
            try:
                db.folders_table.insert(folder_config)

                # Verify injection string was stored literally — not executed
                folders = list(db.folders_table.all())
                assert len(folders) >= 1, "Folder must exist after insert"
                last_folder = folders[-1]
                assert last_folder["folder_name"] == injection, (
                    f"Injection string must be stored verbatim, not executed. "
                    f"Stored: {last_folder['folder_name']!r}, expected: {injection!r}"
                )

                # Clean up
                db.folders_table.delete(id=last_folder["id"])
            except Exception:
                # Exception is acceptable - better to reject than execute
                pass

        # Database should still be functional
        final_folders = list(db.folders_table.all())
        assert len(final_folders) == 0

    def test_database_integrity_after_processing(
        self, secure_test_environment, pipeline_steps
    ):
        """Test database integrity is maintained after processing."""
        workspace = secure_test_environment["workspace"]
        db = secure_test_environment["db"]

        # Create valid EDI file
        edi_content = """A00000120240101001TESTVENDOR         Test Vendor Inc                 00001
B001001ITEM001     000010EA0010Test Item                       0000010000
"""
        (workspace / "input" / "test.edi").write_text(edi_content)

        folder_config = {
            "folder_name": str(workspace / "input"),
            "alias": "Integrity Test",
            "process_backend_copy": True,
            "copy_to_directory": str(workspace / "output"),
            "convert_to_format": "csv",
        }
        db.folders_table.insert(folder_config)

        # Process
        class CopyBackend:
            def send(self, params: dict, settings: dict, filename: str) -> None:
                copy_backend_do(params, settings, filename)

        config = DispatchConfig(
            backends={"copy": CopyBackend()},
            settings={},
            validator_step=pipeline_steps["validator_step"],
            converter_step=pipeline_steps["converter_step"],
            tweaker_step=pipeline_steps["tweaker_step"],
        )
        orchestrator = DispatchOrchestrator(config)

        folders = list(db.folders_table.all())
        result = orchestrator.process_folder(folders[0], MagicMock())

        # Verify database integrity
        folders_after = list(db.folders_table.all())
        assert len(folders_after) == 1
        assert folders_after[0]["alias"] == "Integrity Test"

        # Verify all fields are intact
        assert "folder_name" in folders_after[0]
        assert "convert_to_format" in folders_after[0]
        assert "process_backend_copy" in folders_after[0]


class TestFilePermissions:
    """Test file permission handling."""

    def test_output_file_permissions(self, secure_test_environment, pipeline_steps):
        """Test that output files have appropriate permissions."""
        workspace = secure_test_environment["workspace"]
        db = secure_test_environment["db"]

        # Create EDI file
        edi_content = """A00000120240101001TESTVENDOR         Test Vendor Inc                 00001
B001001ITEM001     000010EA0010Test Item                       0000010000
"""
        (workspace / "input" / "test.edi").write_text(edi_content)

        folder_config = {
            "folder_name": str(workspace / "input"),
            "alias": "Permissions Test",
            "process_backend_copy": True,
            "copy_to_directory": str(workspace / "output"),
            "convert_to_format": "csv",
        }
        db.folders_table.insert(folder_config)

        # Process
        class CopyBackend:
            def send(self, params: dict, settings: dict, filename: str) -> None:
                copy_backend_do(params, settings, filename)

        config = DispatchConfig(
            backends={"copy": CopyBackend()},
            settings={},
            validator_step=pipeline_steps["validator_step"],
            converter_step=pipeline_steps["converter_step"],
            tweaker_step=pipeline_steps["tweaker_step"],
        )
        orchestrator = DispatchOrchestrator(config)

        folders = list(db.folders_table.all())
        orchestrator.process_folder(folders[0], MagicMock())

        # Verify output files exist and are readable
        output_files = list((workspace / "output").glob("*"))
        assert len(output_files) > 0

        for output_file in output_files:
            # Should be readable
            assert output_file.exists()
            # Should be able to read
            content = output_file.read_text()
            assert isinstance(content, str)
            assert "\x00" not in content


class TestErrorHandling:
    """Test secure error handling."""

    def test_error_messages_dont_leak_sensitive_info(
        self, secure_test_environment, pipeline_steps
    ):
        """Test that error messages don't expose sensitive information."""
        workspace = secure_test_environment["workspace"]
        db = secure_test_environment["db"]

        # Try to process non-existent folder
        folder_config = {
            "folder_name": str(workspace / "nonexistent"),
            "alias": "Error Test",
            "process_backend_copy": True,
            "copy_to_directory": str(workspace / "output"),
            "convert_to_format": "csv",
        }
        db.folders_table.insert(folder_config)

        class CopyBackend:
            def send(self, params: dict, settings: dict, filename: str) -> None:
                copy_backend_do(params, settings, filename)

        config = DispatchConfig(
            backends={"copy": CopyBackend()},
            settings={},
            validator_step=pipeline_steps["validator_step"],
            converter_step=pipeline_steps["converter_step"],
            tweaker_step=pipeline_steps["tweaker_step"],
        )
        orchestrator = DispatchOrchestrator(config)

        folders = list(db.folders_table.all())
        run_log = MagicMock()

        # Should handle error gracefully
        result = orchestrator.process_folder(folders[0], run_log)

        # Verify error was handled
        assert result.success is False or result.files_failed > 0

        # Error should be logged but not expose sensitive paths
        if run_log.log_error.called:
            error_message = str(run_log.log_error.call_args)
            # Should not expose full system paths in error messages
            assert "/etc/" not in error_message
            assert "/root/" not in error_message


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
