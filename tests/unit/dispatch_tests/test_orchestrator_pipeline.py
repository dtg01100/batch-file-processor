"""Tests for DispatchOrchestrator pipeline integration."""

from unittest.mock import MagicMock, patch

import pytest

from dispatch.orchestrator import (
    DispatchConfig,
    DispatchOrchestrator,
    FileResult,
    FolderResult,
)


class MockFileSystem:
    """Mock file system for testing."""

    def __init__(self, files=None, dirs=None):
        self.files = files or {}
        self.dirs = set(dirs or [])

    def dir_exists(self, path: str) -> bool:
        return path in self.dirs

    def list_files(self, path: str) -> list[str]:
        return [f for f in self.files if f.startswith(path) and self.dir_exists(path)]

    def read_file(self, path: str) -> bytes:
        if path not in self.files:
            raise FileNotFoundError(path)
        return (
            self.files[path].encode()
            if isinstance(self.files[path], str)
            else self.files[path]
        )

    def makedirs(self, path: str) -> None:
        self.dirs.add(path)


class TestDispatchConfigPipelineFields:
    """Tests for DispatchConfig pipeline fields."""

    def test_default_pipeline_fields(self):
        """Test default values for pipeline fields."""
        config = DispatchConfig()

        assert config.upc_service is None
        assert config.progress_reporter is None
        assert config.validator_step is None
        assert config.splitter_step is None
        assert config.converter_step is None
        assert config.tweaker_step is None
        assert config.file_processor is None
        assert config.upc_dict == {}

    def test_set_pipeline_fields_in_constructor(self):
        """Test setting pipeline fields in constructor."""
        mock_validator = MagicMock()
        mock_splitter = MagicMock()
        mock_converter = MagicMock()
        mock_tweaker = MagicMock()
        mock_file_processor = MagicMock()
        mock_upc_service = MagicMock()
        mock_progress_reporter = MagicMock()

        config = DispatchConfig(
            validator_step=mock_validator,
            splitter_step=mock_splitter,
            converter_step=mock_converter,
            tweaker_step=mock_tweaker,
            file_processor=mock_file_processor,
            upc_service=mock_upc_service,
            progress_reporter=mock_progress_reporter,
            upc_dict={"123": "product"},
        )

        assert config.validator_step is mock_validator
        assert config.splitter_step is mock_splitter
        assert config.converter_step is mock_converter
        assert config.tweaker_step is mock_tweaker
        assert config.file_processor is mock_file_processor
        assert config.upc_service is mock_upc_service
        assert config.progress_reporter is mock_progress_reporter
        assert config.upc_dict == {"123": "product"}


class TestGetUPCDictionary:
    """Tests for _get_upc_dictionary method."""

    def test_with_cached_dictionary(self):
        """Test returning cached UPC dictionary."""
        cached_dict = {"123": "product1", "456": "product2"}
        config = DispatchConfig(upc_dict=cached_dict)
        orchestrator = DispatchOrchestrator(config)

        result = orchestrator._get_upc_dictionary({})

        assert result == cached_dict

    def test_fetch_new_dictionary_via_service(self):
        """Test fetching new dictionary via UPC service."""
        mock_upc_service = MagicMock()
        mock_upc_service.get_dictionary.return_value = {"789": "product3"}

        config = DispatchConfig(upc_service=mock_upc_service)
        orchestrator = DispatchOrchestrator(config)

        result = orchestrator._get_upc_dictionary({})

        assert result == {"789": "product3"}
        assert config.upc_dict == {"789": "product3"}
        mock_upc_service.get_dictionary.assert_called_once()

    def test_service_exception_returns_empty_dict(self, monkeypatch):
        """Test that service exception returns empty dict."""
        monkeypatch.setenv("DISPATCH_STRICT_TESTING_MODE", "false")
        mock_upc_service = MagicMock()
        mock_upc_service.get_dictionary.side_effect = Exception("Service unavailable")

        config = DispatchConfig(upc_service=mock_upc_service)
        orchestrator = DispatchOrchestrator(config)

        result = orchestrator._get_upc_dictionary({})

        assert result == {}

    def test_service_exception_raises_in_strict_testing_mode(self, monkeypatch):
        """Strict testing mode should surface UPC service failures."""
        monkeypatch.setenv("DISPATCH_STRICT_TESTING_MODE", "true")
        mock_upc_service = MagicMock()
        mock_upc_service.get_dictionary.side_effect = Exception("Service unavailable")

        config = DispatchConfig(upc_service=mock_upc_service)
        orchestrator = DispatchOrchestrator(config)

        with pytest.raises(
            RuntimeError, match="Failed to fetch UPC dictionary from upc_service"
        ):
            orchestrator._get_upc_dictionary({})

    def test_without_service_uses_settings_fallback_query(self):
        """When no upc_service is set, fallback query should populate UPC dict."""

        mock_legacy_runner_instance = MagicMock()
        mock_legacy_runner_instance.run_arbitrary_query.return_value = [
            (123456, "CAT", "11111111111", "22222222222", "", ""),
        ]

        with patch(
            "dispatch.orchestrator.LegacyQueryRunner",
            return_value=mock_legacy_runner_instance,
        ):
            config = DispatchConfig()
            orchestrator = DispatchOrchestrator(config)

            settings = {
                "as400_username": "user",
                "as400_password": "pass",
                "as400_address": "host",
                "odbc_driver": "driver",
            }

            result = orchestrator._get_upc_dictionary(settings)

        assert result == {123456: ["CAT", "11111111111", "22222222222", "", ""]}
        assert config.upc_dict == result

    def test_fallback_query_exception_returns_empty_dict_when_not_strict(
        self, monkeypatch
    ):
        """Non-strict mode should preserve legacy suppression for query failures."""
        monkeypatch.setenv("DISPATCH_STRICT_TESTING_MODE", "false")
        mock_legacy_runner_instance = MagicMock()
        mock_legacy_runner_instance.run_arbitrary_query.side_effect = RuntimeError(
            "query failed"
        )

        with patch(
            "dispatch.orchestrator.LegacyQueryRunner",
            return_value=mock_legacy_runner_instance,
        ):
            orchestrator = DispatchOrchestrator(DispatchConfig())
            result = orchestrator._get_upc_dictionary(
                {
                    "as400_username": "user",
                    "as400_password": "pass",
                    "as400_address": "host",
                    "odbc_driver": "driver",
                }
            )

        assert result == {}

    def test_fallback_query_exception_raises_in_strict_testing_mode(
        self, monkeypatch
    ):
        """Strict testing mode should surface fallback query failures."""
        monkeypatch.setenv("DISPATCH_STRICT_TESTING_MODE", "true")
        mock_legacy_runner_instance = MagicMock()
        mock_legacy_runner_instance.run_arbitrary_query.side_effect = RuntimeError(
            "query failed"
        )

        with patch(
            "dispatch.orchestrator.LegacyQueryRunner",
            return_value=mock_legacy_runner_instance,
        ):
            orchestrator = DispatchOrchestrator(DispatchConfig())
            with pytest.raises(
                RuntimeError, match="Failed to fetch UPC dictionary via fallback query"
            ):
                orchestrator._get_upc_dictionary(
                    {
                        "as400_username": "user",
                        "as400_password": "pass",
                        "as400_address": "host",
                        "odbc_driver": "driver",
                    }
                )

    def test_malformed_fallback_query_row_is_skipped_when_not_strict(self, monkeypatch):
        """Non-strict mode should keep legacy behavior for malformed UPC rows."""
        monkeypatch.setenv("DISPATCH_STRICT_TESTING_MODE", "false")
        mock_legacy_runner_instance = MagicMock()
        mock_legacy_runner_instance.run_arbitrary_query.return_value = [
            ("bad-item", "CAT", "11111111111", "22222222222", "", ""),
            (123456, "CAT", "11111111111", "22222222222", "", ""),
        ]

        with patch(
            "dispatch.orchestrator.LegacyQueryRunner",
            return_value=mock_legacy_runner_instance,
        ):
            orchestrator = DispatchOrchestrator(DispatchConfig())
            result = orchestrator._get_upc_dictionary(
                {
                    "as400_username": "user",
                    "as400_password": "pass",
                    "as400_address": "host",
                    "odbc_driver": "driver",
                }
            )

        assert result == {123456: ["CAT", "11111111111", "22222222222", "", ""]}

    def test_malformed_fallback_query_row_raises_in_strict_testing_mode(
        self, monkeypatch
    ):
        """Strict testing mode should surface malformed UPC query rows."""
        monkeypatch.setenv("DISPATCH_STRICT_TESTING_MODE", "true")
        mock_legacy_runner_instance = MagicMock()
        mock_legacy_runner_instance.run_arbitrary_query.return_value = [
            ("bad-item", "CAT", "11111111111", "22222222222", "", ""),
        ]

        with patch(
            "dispatch.orchestrator.LegacyQueryRunner",
            return_value=mock_legacy_runner_instance,
        ):
            orchestrator = DispatchOrchestrator(DispatchConfig())
            with pytest.raises(
                RuntimeError, match="Malformed UPC row returned from fallback query"
            ):
                orchestrator._get_upc_dictionary(
                    {
                        "as400_username": "user",
                        "as400_password": "pass",
                        "as400_address": "host",
                        "odbc_driver": "driver",
                    }
                )

    def test_strict_mode_raises_when_as400_settings_missing(self):
        """Strict database mode should fail fast when settings are incomplete."""
        config = DispatchConfig(settings={"database_lookup_mode": "strict"})
        orchestrator = DispatchOrchestrator(config)

        with pytest.raises(ValueError, match="AS400 settings are missing"):
            orchestrator._get_upc_dictionary(config.settings)

    def test_strict_mode_raises_when_query_returns_no_rows(self):
        """Strict mode should fail when UPC query returns an empty dataset."""
        mock_legacy_runner_instance = MagicMock()
        mock_legacy_runner_instance.run_arbitrary_query.return_value = []

        with patch(
            "dispatch.orchestrator.LegacyQueryRunner",
            return_value=mock_legacy_runner_instance,
        ):
            config = DispatchConfig(
                settings={
                    "database_lookup_mode": "strict",
                    "as400_username": "user",
                    "as400_password": "pass",
                    "as400_address": "host",
                    "odbc_driver": "driver",
                }
            )
            orchestrator = DispatchOrchestrator(config)

            with pytest.raises(LookupError, match="UPC query returned no rows"):
                orchestrator._get_upc_dictionary(config.settings)

    def test_close_failure_is_suppressed_outside_strict_testing_mode(self, monkeypatch):
        """Legacy runner close failures remain backward compatible when strict mode is off."""
        monkeypatch.setenv("DISPATCH_STRICT_TESTING_MODE", "false")
        mock_legacy_runner_instance = MagicMock()
        mock_legacy_runner_instance.run_arbitrary_query.return_value = [
            (123456, "CAT", "11111111111", "22222222222", "", ""),
        ]
        mock_legacy_runner_instance._runner.close.side_effect = RuntimeError(
            "close failed"
        )

        with patch(
            "dispatch.orchestrator.LegacyQueryRunner",
            return_value=mock_legacy_runner_instance,
        ):
            orchestrator = DispatchOrchestrator(DispatchConfig())
            result = orchestrator._get_upc_dictionary(
                {
                    "as400_username": "user",
                    "as400_password": "pass",
                    "as400_address": "host",
                    "odbc_driver": "driver",
                }
            )

        assert result == {123456: ["CAT", "11111111111", "22222222222", "", ""]}

    def test_close_failure_raises_in_strict_testing_mode(self, monkeypatch):
        """Strict testing mode should surface close failures for UPC fallback."""
        monkeypatch.setenv("DISPATCH_STRICT_TESTING_MODE", "true")
        mock_legacy_runner_instance = MagicMock()
        mock_legacy_runner_instance.run_arbitrary_query.return_value = [
            (123456, "CAT", "11111111111", "22222222222", "", ""),
        ]
        mock_legacy_runner_instance._runner.close.side_effect = RuntimeError(
            "close failed"
        )

        with patch(
            "dispatch.orchestrator.LegacyQueryRunner",
            return_value=mock_legacy_runner_instance,
        ):
            orchestrator = DispatchOrchestrator(DispatchConfig())
            with pytest.raises(
                RuntimeError, match="Failed to close legacy UPC query runner"
            ):
                orchestrator._get_upc_dictionary(
                    {
                        "as400_username": "user",
                        "as400_password": "pass",
                        "as400_address": "host",
                        "odbc_driver": "driver",
                    }
                )


class TestProcessFolderWithPipeline:
    """Tests for process_folder_with_pipeline method."""

    def test_process_folder_pipeline_enabled(self):
        """Test processing with pipeline enabled."""
        mock_fs = MockFileSystem(
            dirs=["/data/input"], files={"/data/input/file1.edi": b"content"}
        )

        mock_validator = MagicMock()
        mock_validator.execute.return_value = (True, "/data/input/file1.edi")

        mock_backend = MagicMock()
        mock_backend.send.return_value = True

        config = DispatchConfig(
            file_system=mock_fs,
            backends={"copy": mock_backend},
            validator_step=mock_validator,
            settings={},
        )
        orchestrator = DispatchOrchestrator(config)

        folder = {
            "folder_name": "/data/input",
            "alias": "Test",
            "process_backend_copy": True,
        }
        run_log = MagicMock()

        result = orchestrator.process_folder_with_pipeline(folder, run_log)

        assert result.folder_name == "/data/input"
        assert result.alias == "Test"

    def test_pipeline_steps_called_correctly(self):
        """Test that pipeline steps are called correctly."""
        mock_fs = MockFileSystem(
            dirs=["/data/input"], files={"/data/input/file.edi": b"content"}
        )

        mock_validator = MagicMock()
        mock_validator.execute.return_value = (True, "/data/input/file.edi")

        mock_converter = MagicMock()
        mock_converter.execute.return_value = "/data/input/file_converted.edi"

        mock_backend = MagicMock()
        mock_backend.send.return_value = True

        config = DispatchConfig(
            file_system=mock_fs,
            backends={"copy": mock_backend},
            validator_step=mock_validator,
            converter_step=mock_converter,
            settings={},
        )
        orchestrator = DispatchOrchestrator(config)

        folder = {
            "folder_name": "/data/input",
            "alias": "Test",
            "process_edi": "True",
            "convert_edi": True,
            "process_backend_copy": True,
        }
        run_log = MagicMock()

        result = orchestrator.process_folder_with_pipeline(folder, run_log)

        mock_validator.execute.assert_called()
        mock_converter.execute.assert_called()

    def test_pipeline_folder_not_found(self):
        """Test pipeline processing with non-existent folder."""
        mock_fs = MockFileSystem(dirs=[])

        config = DispatchConfig(file_system=mock_fs)
        orchestrator = DispatchOrchestrator(config)

        folder = {"folder_name": "/data/notexists", "alias": "Test"}
        run_log = MagicMock()

        result = orchestrator.process_folder_with_pipeline(folder, run_log)

        assert result.success is False
        assert result.files_failed == 1
        assert "not found" in result.errors[0].lower()

    def test_pipeline_empty_folder(self):
        """Test pipeline processing with empty folder."""
        mock_fs = MockFileSystem(dirs=["/data/input"])

        config = DispatchConfig(file_system=mock_fs)
        orchestrator = DispatchOrchestrator(config)

        folder = {"folder_name": "/data/input", "alias": "Test"}
        run_log = MagicMock()

        result = orchestrator.process_folder_with_pipeline(folder, run_log)

        assert result.success is True
        assert result.files_processed == 0


class TestProcessFileWithPipeline:
    """Tests for _process_file_with_pipeline method."""

    def test_full_pipeline_processing_flow(self):
        """Test full pipeline processing flow."""
        mock_fs = MockFileSystem(
            dirs=["/data/input"], files={"/data/input/file.edi": b"content"}
        )

        mock_validator = MagicMock()
        mock_validator.execute.return_value = (True, "/data/input/file.edi")

        mock_converter = MagicMock()
        mock_converter.execute.return_value = None

        mock_tweaker = MagicMock()
        mock_tweaker.execute.return_value = None

        mock_file_processor = MagicMock()
        mock_file_processor.process.return_value = None

        mock_backend = MagicMock()
        mock_backend.send.return_value = True

        config = DispatchConfig(
            file_system=mock_fs,
            backends={"copy": mock_backend},
            validator_step=mock_validator,
            converter_step=mock_converter,
            tweaker_step=mock_tweaker,
            file_processor=mock_file_processor,
            settings={},
        )
        orchestrator = DispatchOrchestrator(config)

        folder = {
            "folder_name": "/data/input",
            "process_edi": "True",
            "process_backend_copy": True,
        }

        result = orchestrator._process_file_with_pipeline(
            "/data/input/file.edi", folder, {}
        )

        assert result.file_name == "/data/input/file.edi"
        assert result.checksum is not None

    def test_pipeline_validation_failure(self):
        """Test pipeline with validation failure."""
        mock_fs = MockFileSystem(
            dirs=["/data/input"], files={"/data/input/file.edi": b"content"}
        )

        mock_validator = MagicMock()
        mock_validator.execute.return_value = (False, ["Validation error"])

        config = DispatchConfig(
            file_system=mock_fs,
            validator_step=mock_validator,
            settings={},
        )
        orchestrator = DispatchOrchestrator(config)

        folder = {"folder_name": "/data/input", "process_edi": "True"}

        result = orchestrator._process_file_with_pipeline(
            "/data/input/file.edi", folder, {}
        )

        assert result.validated is False
        assert "Validation error" in result.errors

    def test_pipeline_splitter_integration(self):
        """Test pipeline with splitter step."""
        mock_fs = MockFileSystem(
            dirs=["/data/input"], files={"/data/input/file.edi": b"content"}
        )

        mock_splitter = MagicMock()
        mock_splitter.execute.return_value = [
            "/data/input/split1.edi",
            "/data/input/split2.edi",
        ]

        mock_backend = MagicMock()
        mock_backend.send.return_value = True

        config = DispatchConfig(
            file_system=mock_fs,
            backends={"copy": mock_backend},
            splitter_step=mock_splitter,
            settings={},
        )
        orchestrator = DispatchOrchestrator(config)

        folder = {
            "folder_name": "/data/input",
            "split_edi": True,
            "process_backend_copy": True,
        }

        result = orchestrator._process_file_with_pipeline(
            "/data/input/file.edi", folder, {}
        )

        mock_splitter.split.assert_called_once()

    def test_pipeline_converter_integration(self):
        """Test pipeline with converter step."""
        mock_fs = MockFileSystem(
            dirs=["/data/input"], files={"/data/input/file.edi": b"content"}
        )

        mock_validator = MagicMock()
        mock_validator.execute.return_value = (True, "/data/input/file.edi")

        mock_converter = MagicMock()
        mock_converter.execute.return_value = "/data/input/converted.edi"

        mock_backend = MagicMock()
        mock_backend.send.return_value = True

        config = DispatchConfig(
            file_system=mock_fs,
            backends={"copy": mock_backend},
            validator_step=mock_validator,
            converter_step=mock_converter,
            settings={},
        )
        orchestrator = DispatchOrchestrator(config)

        folder = {
            "folder_name": "/data/input",
            "convert_edi": True,
            "process_backend_copy": True,
        }

        result = orchestrator._process_file_with_pipeline(
            "/data/input/file.edi", folder, {}
        )

        mock_converter.execute.assert_called_once()
        assert result.converted is True

    def test_pipeline_tweaker_integration(self):
        """Test pipeline with tweaker step."""
        mock_fs = MockFileSystem(
            dirs=["/data/input"], files={"/data/input/file.edi": b"content"}
        )

        mock_validator = MagicMock()
        mock_validator.execute.return_value = (True, "/data/input/file.edi")

        mock_tweaker = MagicMock()
        mock_tweaker.execute.return_value = "/data/input/tweaked.edi"

        mock_backend = MagicMock()
        mock_backend.send.return_value = True

        config = DispatchConfig(
            file_system=mock_fs,
            backends={"copy": mock_backend},
            validator_step=mock_validator,
            tweaker_step=mock_tweaker,
            settings={},
        )
        orchestrator = DispatchOrchestrator(config)

        folder = {
            "folder_name": "/data/input",
            "tweak_edi": True,
            "process_backend_copy": True,
        }

        result = orchestrator._process_file_with_pipeline(
            "/data/input/file.edi", folder, {"123": "product"}
        )

        mock_tweaker.execute.assert_called_once()

    def test_pipeline_sending_to_backends(self):
        """Test pipeline sending files to backends."""
        mock_fs = MockFileSystem(
            dirs=["/data/input"], files={"/data/input/file.edi": b"content"}
        )

        mock_backend = MagicMock()
        mock_backend.send.return_value = True

        config = DispatchConfig(
            file_system=mock_fs,
            backends={"copy": mock_backend},
            settings={},
        )
        orchestrator = DispatchOrchestrator(config)

        folder = {"folder_name": "/data/input", "process_backend_copy": True}

        result = orchestrator._process_file_with_pipeline(
            "/data/input/file.edi", folder, {}
        )

        assert result.sent is True

    def test_pipeline_error_handling(self):
        """Test pipeline error handling."""
        mock_fs = MockFileSystem(
            dirs=["/data/input"], files={"/data/input/file.edi": b"content"}
        )

        mock_validator = MagicMock()
        mock_validator.execute.side_effect = Exception("Validator error")

        config = DispatchConfig(
            file_system=mock_fs,
            validator_step=mock_validator,
            settings={},
        )
        orchestrator = DispatchOrchestrator(config)

        folder = {"folder_name": "/data/input", "process_edi": "True"}

        result = orchestrator._process_file_with_pipeline(
            "/data/input/file.edi", folder, {}
        )

        assert "Validator error" in result.errors


class TestProcessedFilesAndCleanupBehavior:
    """Tests for processed-file idempotency and pipeline cleanup behavior."""

    def test_filter_skips_checksum_when_resend_flag_false(self):
        """Previously processed non-resend checksum is filtered out."""
        orchestrator = DispatchOrchestrator(DispatchConfig())
        processed_files = MagicMock()
        processed_files.find.return_value = [
            {"file_checksum": "checksum-a", "resend_flag": False}
        ]

        files = ["/data/input/a.edi", "/data/input/b.edi"]
        with patch.object(
            orchestrator,
            "_calculate_checksum",
            side_effect=["checksum-a", "checksum-b"],
        ):
            filtered = orchestrator._filter_processed_files(
                files, processed_files, {"id": 42}
            )

        assert filtered == ["/data/input/b.edi"]

    def test_filter_keeps_checksum_when_resend_flag_true(self):
        """Resend-marked checksum remains eligible for processing."""
        orchestrator = DispatchOrchestrator(DispatchConfig())
        processed_files = MagicMock()
        processed_files.find.return_value = [
            {"file_checksum": "checksum-a", "resend_flag": True}
        ]

        files = ["/data/input/a.edi", "/data/input/b.edi"]
        with patch.object(
            orchestrator,
            "_calculate_checksum",
            side_effect=["checksum-a", "checksum-b"],
        ):
            filtered = orchestrator._filter_processed_files(
                files, processed_files, {"id": 42}
            )

        assert filtered == files

    def test_record_processed_file_updates_existing_resend_record_instead_of_insert(
        self,
    ):
        """Existing resend record is updated and not duplicated."""
        orchestrator = DispatchOrchestrator(DispatchConfig())
        processed_files = MagicMock()
        processed_files.find_one.return_value = {"id": 7}
        file_result = FileResult(file_name="/data/input/file.edi", checksum="abc123")

        folder = {
            "id": 99,
            "alias": "Orders",
            "process_backend_copy": True,
            "copy_to_directory": "/out/copy",
        }

        orchestrator._record_processed_file(processed_files, folder, file_result)

        processed_files.find_one.assert_called_once_with(
            file_name="/data/input/file.edi", folder_id=99, resend_flag=1
        )
        processed_files.insert.assert_not_called()
        processed_files.update.assert_called_once()
        update_payload, update_keys = processed_files.update.call_args.args
        assert update_payload["id"] == 7
        assert update_payload["resend_flag"] == 0
        assert update_payload["status"] == "processed"
        assert update_payload["sent_to"] == "Copy: /out/copy"
        assert isinstance(update_payload["processed_at"], str)
        assert update_keys == ["id"]

    def test_record_processed_file_inserts_when_no_existing_resend_record(self):
        """New processed-file record is inserted when resend match is absent."""
        orchestrator = DispatchOrchestrator(DispatchConfig())
        processed_files = MagicMock()
        processed_files.find_one.return_value = None
        file_result = FileResult(file_name="/data/input/file.edi", checksum="def456")

        folder = {
            "old_id": 123,
            "alias": "Inbound",
            "process_backend_email": True,
            "email_to": "ops@example.com",
        }

        orchestrator._record_processed_file(processed_files, folder, file_result)

        processed_files.update.assert_not_called()
        processed_files.insert.assert_called_once()
        insert_payload = processed_files.insert.call_args.args[0]
        assert insert_payload["file_name"] == "/data/input/file.edi"
        assert insert_payload["folder_id"] == 123
        assert insert_payload["folder_alias"] == "Inbound"
        assert insert_payload["file_checksum"] == "def456"
        assert "md5" not in insert_payload
        assert insert_payload["resend_flag"] == 0
        assert insert_payload["sent_to"] == "Email: ops@example.com"
        assert insert_payload["status"] == "processed"
        assert isinstance(insert_payload["processed_at"], str)

    def test_process_file_with_pipeline_cleans_context_registered_temp_dirs_in_finally(
        self,
        monkeypatch,
    ):
        """Context-tracked pipeline temp dirs are removed during finally cleanup."""
        monkeypatch.setenv("DISPATCH_STRICT_TESTING_MODE", "false")
        mock_fs = MockFileSystem(
            dirs=["/data/input"], files={"/data/input/file.edi": b"content"}
        )
        mock_converter = MagicMock()
        mock_converter.execute.return_value = None
        orchestrator = DispatchOrchestrator(
            DispatchConfig(
                file_system=mock_fs,
                converter_step=mock_converter,
                settings={},
            )
        )

        folder = {
            "folder_name": "/data/input",
            "convert_edi": True,
        }

        def converter_with_context(
            file_path, folder_cfg, settings, upc_dict, context=None
        ):
            context.temp_dirs.extend(["/tmp/pipeline-1", "/tmp/pipeline-2"])
            return None

        mock_converter.execute.side_effect = converter_with_context

        with (
            patch("os.path.exists", return_value=True),
            patch("shutil.rmtree") as mock_rmtree,
        ):
            orchestrator._process_file_with_pipeline("/data/input/file.edi", folder, {})

        assert mock_rmtree.call_count == 2
        mock_rmtree.assert_any_call("/tmp/pipeline-1", ignore_errors=True)
        mock_rmtree.assert_any_call("/tmp/pipeline-2", ignore_errors=True)
        assert "_pipeline_temp_dirs" not in folder

    def test_process_file_with_pipeline_cleanup_best_effort_when_remove_rmtree_raises(
        self,
        monkeypatch,
    ):
        """Cleanup exceptions are suppressed so processing remains best-effort."""
        monkeypatch.setenv("DISPATCH_STRICT_TESTING_MODE", "false")
        mock_fs = MockFileSystem(
            dirs=["/data/input"], files={"/data/input/file.edi": b"content"}
        )

        mock_converter = MagicMock()
        mock_converter.execute.return_value = "/tmp/converted.edi"

        orchestrator = DispatchOrchestrator(
            DispatchConfig(
                file_system=mock_fs,
                converter_step=mock_converter,
                settings={},
            )
        )

        folder = {
            "folder_name": "/data/input",
            "convert_edi": True,
        }

        def converter_with_context(
            file_path, folder_cfg, settings, upc_dict, context=None
        ):
            context.temp_dirs.append("/tmp/pipeline-dir")
            return "/tmp/converted.edi"

        mock_converter.execute.side_effect = converter_with_context

        with (
            patch("os.path.exists", return_value=True),
            patch("shutil.rmtree", side_effect=OSError("rmtree failed")) as mock_rmtree,
            patch("os.remove", side_effect=OSError("remove failed")) as mock_remove,
        ):
            result = orchestrator._process_file_with_pipeline(
                "/data/input/file.edi", folder, {}
            )

        assert "No backends enabled" in result.errors
        mock_rmtree.assert_called_once_with("/tmp/pipeline-dir", ignore_errors=True)
        mock_remove.assert_called_once_with("/tmp/converted.edi")
        assert "_pipeline_temp_dirs" not in folder

    def test_process_file_with_pipeline_cleanup_raises_in_strict_testing_mode(
        self,
        monkeypatch,
    ):
        """Strict testing mode should fail fast when temp cleanup fails."""
        monkeypatch.setenv("DISPATCH_STRICT_TESTING_MODE", "true")
        mock_fs = MockFileSystem(
            dirs=["/data/input"], files={"/data/input/file.edi": b"content"}
        )

        mock_converter = MagicMock()
        mock_converter.execute.return_value = "/tmp/converted.edi"

        orchestrator = DispatchOrchestrator(
            DispatchConfig(
                file_system=mock_fs,
                converter_step=mock_converter,
                settings={},
            )
        )

        folder = {
            "folder_name": "/data/input",
            "convert_edi": True,
        }

        def converter_with_context(
            file_path, folder_cfg, settings, upc_dict, context=None
        ):
            context.temp_dirs.append("/tmp/pipeline-dir")
            return "/tmp/converted.edi"

        mock_converter.execute.side_effect = converter_with_context

        with (
            patch("os.path.exists", return_value=True),
            patch("shutil.rmtree", side_effect=OSError("rmtree failed")),
            patch("os.remove", side_effect=OSError("remove failed")),
            pytest.raises(RuntimeError, match="Failed to clean up temporary artifacts"),
        ):
            orchestrator._process_file_with_pipeline("/data/input/file.edi", folder, {})

    def test_process_file_with_pipeline_uses_effective_folder_without_mutating_source(
        self,
    ):
        """Pipeline receives effective flags while original folder remains unchanged."""
        mock_fs = MockFileSystem(
            dirs=["/data/input"], files={"/data/input/file.edi": b"content"}
        )
        mock_converter = MagicMock()
        mock_converter.execute.return_value = None

        orchestrator = DispatchOrchestrator(
            DispatchConfig(
                file_system=mock_fs,
                converter_step=mock_converter,
                settings={},
            )
        )

        folder = {
            "folder_name": "/data/input",
            "convert_edi": True,
        }

        orchestrator._process_file_with_pipeline("/data/input/file.edi", folder, {})

        execute_args = mock_converter.execute.call_args.args
        effective_folder = execute_args[1]
        assert effective_folder.get("process_edi") is True
        assert "process_edi" not in folder
        assert "_pipeline_temp_dirs" not in folder


class TestSendPipelineFile:
    """Tests for _send_pipeline_file method."""

    def test_send_pipeline_file_success(self):
        """Test successful sending of pipeline file."""
        mock_backend = MagicMock()
        mock_backend.send.return_value = True

        config = DispatchConfig(backends={"copy": mock_backend}, settings={})
        orchestrator = DispatchOrchestrator(config)

        folder = {"process_backend_copy": True}

        result = orchestrator._send_pipeline_file("/data/input/file.edi", folder)

        assert result is True

    def test_send_pipeline_file_no_backends(self):
        """Test sending with no enabled backends."""
        config = DispatchConfig(backends={}, settings={})
        orchestrator = DispatchOrchestrator(config)

        folder = {}

        result = orchestrator._send_pipeline_file("/data/input/file.edi", folder)

        assert result is False

    def test_send_pipeline_file_partial_failure(self):
        """Test sending with partial backend failure."""
        mock_backend1 = MagicMock()
        mock_backend1.send.return_value = True

        mock_backend2 = MagicMock()
        mock_backend2.send.return_value = False

        config = DispatchConfig(
            backends={"copy1": mock_backend1, "copy2": mock_backend2}, settings={}
        )
        orchestrator = DispatchOrchestrator(config)

        folder = {"process_backend_copy1": True, "process_backend_copy2": True}

        result = orchestrator._send_pipeline_file("/data/input/file.edi", folder)

        assert result is False


class TestProcessFolderPipelineRouting:
    """Tests for routing in process_folder method."""

    def test_process_folder_routes_to_pipeline(self):
        """Test that process_folder routes to pipeline."""
        mock_fs = MockFileSystem(
            dirs=["/data/input"], files={"/data/input/file.edi": b"content"}
        )

        mock_validator = MagicMock()
        mock_validator.execute.return_value = (True, "/data/input/file.edi")

        mock_backend = MagicMock()
        mock_backend.send.return_value = True

        config = DispatchConfig(
            file_system=mock_fs,
            backends={"copy": mock_backend},
            validator_step=mock_validator,
            settings={},
        )
        orchestrator = DispatchOrchestrator(config)

        folder = {
            "folder_name": "/data/input",
            "alias": "Test",
            "process_backend_copy": True,
        }
        run_log = MagicMock()

        with patch.object(
            orchestrator, "process_folder_with_pipeline"
        ) as mock_pipeline:
            mock_pipeline.return_value = FolderResult(
                folder_name="/data/input", alias="Test", files_processed=1
            )
            result = orchestrator.process_folder(folder, run_log)

            mock_pipeline.assert_called_once()


class TestProcessFilePipelineRouting:
    """Tests for routing in process_file method."""

    def test_process_file_routes_to_pipeline(self):
        """Test that process_file routes to pipeline."""
        mock_fs = MockFileSystem(
            dirs=["/data/input"], files={"/data/input/file.edi": b"content"}
        )

        mock_validator = MagicMock()

        config = DispatchConfig(
            file_system=mock_fs,
            validator_step=mock_validator,
            settings={},
        )
        orchestrator = DispatchOrchestrator(config)

        folder = {"folder_name": "/data/input"}

        with patch.object(orchestrator, "_process_file_with_pipeline") as mock_pipeline:
            mock_pipeline.return_value = FileResult(
                file_name="/data/input/file.edi", checksum="abc123"
            )
            result = orchestrator.process_file("/data/input/file.edi", folder)

            mock_pipeline.assert_called_once()


class TestPipelineOnlyContract:
    """Tests for the pipeline-only processing contract."""

    def test_process_file_works_without_legacy_toggle(self):
        """File processing works with the default pipeline-only configuration."""
        mock_fs = MockFileSystem(
            dirs=["/data/input"], files={"/data/input/file.edi": b"content"}
        )

        mock_backend = MagicMock()
        mock_backend.send.return_value = True

        config = DispatchConfig(
            file_system=mock_fs,
            backends={"copy": mock_backend},
            settings={},
        )
        orchestrator = DispatchOrchestrator(config)

        folder = {"folder_name": "/data/input", "process_backend_copy": True}

        result = orchestrator.process_file("/data/input/file.edi", folder)

        assert result.file_name == "/data/input/file.edi"
        assert result.checksum is not None

    def test_process_file_with_validation_runs_pipeline_path(self):
        """Validation still runs through pipeline path."""
        mock_fs = MockFileSystem(
            dirs=["/data/input"], files={"/data/input/file.edi": b"valid content"}
        )

        mock_validator = MagicMock()
        mock_validator.execute.return_value = (True, "/data/input/file.edi")

        mock_backend = MagicMock()
        mock_backend.send.return_value = True

        config = DispatchConfig(
            file_system=mock_fs,
            backends={"copy": mock_backend},
            validator_step=mock_validator,
            settings={},
        )
        orchestrator = DispatchOrchestrator(config)

        folder = {
            "folder_name": "/data/input",
            "process_edi": "True",
            "process_backend_copy": True,
        }

        result = orchestrator.process_file("/data/input/file.edi", folder)

        mock_validator.execute.assert_called_once()

    def test_process_folder_routes_through_consolidated_pipeline_path(self):
        """Folder processing routes through consolidated pipeline path."""
        mock_fs = MockFileSystem(
            dirs=["/data/input"], files={"/data/input/file.edi": b"content"}
        )

        mock_backend = MagicMock()
        mock_backend.send.return_value = True

        config = DispatchConfig(
            file_system=mock_fs,
            backends={"copy": mock_backend},
            settings={},
        )
        orchestrator = DispatchOrchestrator(config)

        folder = {
            "folder_name": "/data/input",
            "alias": "Test",
            "process_backend_copy": True,
        }
        run_log = MagicMock()

        result = orchestrator.process_folder(folder, run_log)

        assert result.folder_name == "/data/input"
        assert result.alias == "Test"


class TestOrchestratorPipelineHelpers:
    """Tests for pipeline helper methods in DispatchOrchestrator."""

    def test_should_apply_tweaker_false_when_tweaker_missing(self):
        """Tweaker should not run when no step is configured."""
        orchestrator = DispatchOrchestrator(DispatchConfig())

        assert orchestrator._should_apply_tweaker(None, "/tmp/file.edi") is False

    def test_should_apply_tweaker_false_for_builtin_tweaker_on_non_edi(self):
        """Built-in EDITweakerStep should be skipped for non-EDI files."""
        orchestrator = DispatchOrchestrator(DispatchConfig())

        class EDITweakerStep:
            pass

        assert (
            orchestrator._should_apply_tweaker(EDITweakerStep(), "/tmp/file.csv")
            is False
        )

    def test_should_apply_tweaker_true_for_custom_tweaker_on_non_edi(self):
        """Custom tweakers remain eligible for converted/non-EDI outputs."""
        orchestrator = DispatchOrchestrator(DispatchConfig())

        class CustomTweaker:
            pass

        assert (
            orchestrator._should_apply_tweaker(CustomTweaker(), "/tmp/file.csv") is True
        )

    def test_build_processing_context_applies_defaults_and_normalization(self):
        """Context builder should normalize flags/defaults without mutating source."""
        orchestrator = DispatchOrchestrator(DispatchConfig(settings={"mode": "test"}))
        folder = {
            "upc_target_length": 0,
            "process_edi": "True",
            "a_record_padding": None,
            "split_edi": False,
            "tweak_edi": False,
        }

        context = orchestrator._build_processing_context(folder, {"u": "p"})

        assert context.effective_folder["a_record_padding"] == ""
        assert context.effective_folder["upc_target_length"] == 11
        assert context.effective_folder["convert_edi"] is True
        assert "convert_edi" not in folder

    def test_build_processing_context_sets_process_edi_when_pipeline_flags_enabled(
        self,
    ):
        """Missing process_edi is inferred True when split/convert/tweak is enabled."""
        orchestrator = DispatchOrchestrator(DispatchConfig())

        context = orchestrator._build_processing_context(
            {"split_edi": True, "convert_edi": False, "tweak_edi": False},
            {},
        )

        assert context.effective_folder["process_edi"] is True


class TestOrchestratorProgressPhases:
    """Tests for discovery/sending phase orchestration support."""

    def test_discover_pending_files_reports_progress_and_filters_processed(self):
        mock_fs = MockFileSystem(
            dirs=["/data/a", "/data/b"],
            files={
                "/data/a/new.edi": b"new-a",
                "/data/a/old.edi": b"old-a",
                "/data/b/new.edi": b"new-b",
            },
        )
        config = DispatchConfig(file_system=mock_fs)
        orchestrator = DispatchOrchestrator(config)

        folders = [
            {"id": 1, "folder_name": "/data/a", "alias": "A"},
            {"id": 2, "folder_name": "/data/b", "alias": "B"},
        ]

        processed_files = MagicMock()
        processed_files.find.side_effect = [
            [{"file_checksum": "old-checksum", "resend_flag": False}],
            [],
        ]

        progress = MagicMock()

        with patch.object(
            orchestrator,
            "_calculate_checksum",
            side_effect=["new-checksum", "old-checksum", "new-b-checksum"],
        ):
            pending_lists, total_pending = orchestrator.discover_pending_files(
                folders,
                processed_files=processed_files,
                progress_reporter=progress,
            )

        assert pending_lists == [["/data/a/new.edi"], ["/data/b/new.edi"]]
        assert total_pending == 2
        progress.start_discovery.assert_called_once_with(folder_total=2)
        assert progress.update_discovery_progress.call_count == 2
        progress.finish_discovery.assert_called_once_with(total_pending=2)

    def test_process_folder_uses_legacy_start_folder_signature_when_needed(self):
        class LegacyProgress:
            def __init__(self):
                self.calls = []

            def start_folder(self, folder_name: str, total_files: int) -> None:
                self.calls.append((folder_name, total_files))

            def update_file(self, current_file: int, total_files: int) -> None:
                return None

            def complete_folder(self, success: bool) -> None:
                return None

        mock_fs = MockFileSystem(
            dirs=["/data/input"],
            files={"/data/input/file.edi": b"content"},
        )
        mock_backend = MagicMock()
        mock_backend.send.return_value = True

        progress = LegacyProgress()
        orchestrator = DispatchOrchestrator(
            DispatchConfig(
                file_system=mock_fs,
                backends={"copy": mock_backend},
                progress_reporter=progress,
                settings={},
            )
        )

        folder = {
            "folder_name": "/data/input",
            "alias": "Input",
            "process_backend_copy": True,
        }

        result = orchestrator.process_folder(
            folder,
            run_log=MagicMock(),
            processed_files=None,
            pre_discovered_files=["/data/input/file.edi"],
            folder_num=1,
            folder_total=1,
        )

        assert result.files_processed == 1
        assert progress.calls == [("Input", 1)]
