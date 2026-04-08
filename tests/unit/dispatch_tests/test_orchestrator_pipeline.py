"""Tests for DispatchOrchestrator pipeline integration.

These tests use real implementations and lightweight test doubles instead of MagicMock:
- Real filesystem operations via tmp_path
- Real pipeline step implementations (MockValidator, MockConverter, etc.)
- CaptureBackend for capturing backend calls
- Real database operations via temp_database fixture
"""

from __future__ import annotations

import logging
from pathlib import Path

import pytest

from dispatch.orchestrator import DispatchConfig, DispatchOrchestrator, FileResult

# =============================================================================
# Test Doubles (Lightweight, no MagicMock)
# =============================================================================


class FakeValidationStep:
    """Fake validation step for testing."""

    def __init__(self, should_pass: bool = True, errors: list[str] | None = None):
        self.should_pass = should_pass
        self.errors = errors or ["Validation error"]
        self.call_count = 0
        self.last_file_path: str | None = None
        self.last_folder: dict | None = None

    def execute(self, file_path: str, folder: dict) -> tuple[bool, list[str] | str]:
        self.call_count += 1
        self.last_file_path = file_path
        self.last_folder = folder
        if self.should_pass:
            return True, file_path
        return False, self.errors

    def validate(self, file_path: str, filename_for_log: str):
        """For compatibility with legacy interface."""
        pass


class FakeConverterStep:
    """Fake converter step for testing."""

    def __init__(self, output_path: str | None = None):
        self.output_path = output_path
        self.call_count = 0
        self.last_file_path: str | None = None
        self.last_folder: dict | None = None

    def execute(
        self,
        file_path: str,
        folder: dict,
        settings: dict | None = None,
        upc_dict: dict | None = None,
        context=None,
    ) -> str | None:
        self.call_count += 1
        self.last_file_path = file_path
        self.last_folder = folder
        if context is not None and hasattr(context, "temp_dirs"):
            # Track any temp dirs that would be created
            pass
        return self.output_path


class FakeTweakerStep:
    """Fake tweaker step for testing."""

    def __init__(self, output_path: str | None = None):
        self.output_path = output_path
        self.call_count = 0
        self.last_file_path: str | None = None
        self.last_folder: dict | None = None

    def execute(
        self,
        file_path: str,
        folder: dict,
        upc_dict: dict,
        settings: dict | None = None,
        context=None,
    ) -> str | None:
        self.call_count += 1
        self.last_file_path = file_path
        self.last_folder = folder
        return self.output_path


class ErrorValidator:
    """Validator that always raises an exception."""

    def __init__(self, message: str = "Validator error"):
        self.message = message
        self.call_count = 0

    def execute(self, file_path: str, folder: dict):
        self.call_count += 1
        raise Exception(self.message)


class ConverterWithTempDirs:
    """Converter that adds temp dirs to context."""

    def __init__(self, temp_dirs: list[str]):
        self.temp_dirs = temp_dirs
        self.call_count = 0

    def execute(
        self,
        file_path: str,
        folder: dict,
        settings: dict | None = None,
        upc_dict: dict | None = None,
        context=None,
    ) -> None:
        self.call_count += 1
        if context is not None and hasattr(context, "temp_dirs"):
            context.temp_dirs.extend(self.temp_dirs)
        return None


class CaptureBackend:
    """Backend that captures the content of each file it receives."""

    def __init__(self, name: str = "CaptureBackend"):
        self._name = name
        self.received: list[tuple[str, bytes]] = []

    def send(self, params: dict, settings: dict, filename: str) -> None:
        with open(filename, "rb") as f:
            content = f.read()
        self.received.append((filename, content))

    def validate(self, params: dict) -> list[str]:
        return []

    def get_name(self) -> str:
        return self._name

    @property
    def first_content(self) -> bytes:
        if not self.received:
            raise AssertionError("Backend received no files")
        return self.received[0][1]

    @property
    def first_filename(self) -> str:
        if not self.received:
            raise AssertionError("Backend received no files")
        return self.received[0][0]


class FailingBackend:
    """Backend that always fails to send."""

    def __init__(
        self, error_message: str = "Send failed", name: str = "FailingBackend"
    ):
        self.error_message = error_message
        self._name = name
        self.received: list[tuple[str, bytes]] = []

    def send(self, params: dict, settings: dict, filename: str) -> None:
        raise Exception(self.error_message)

    def validate(self, params: dict) -> list[str]:
        return []

    def get_name(self) -> str:
        return self._name


class PartialFailBackend:
    """Backend that can be configured to succeed or fail."""

    def __init__(self, should_succeed: bool = True, name: str = "PartialFailBackend"):
        self.should_succeed = should_succeed
        self._name = name
        self.received: list[tuple[str, bytes]] = []

    def send(self, params: dict, settings: dict, filename: str) -> None:
        if not self.should_succeed:
            raise Exception("Send failed")
        with open(filename, "rb") as f:
            content = f.read()
        self.received.append((filename, content))

    def validate(self, params: dict) -> list[str]:
        return []

    def get_name(self) -> str:
        return self._name


class SimpleRunLog:
    """Simple run log that collects messages."""

    def __init__(self):
        self.messages: list[str] = []

    def write(self, message: bytes) -> None:
        self.messages.append(message.decode("utf-8", errors="replace").strip())

    def append(self, message: str) -> None:
        self.messages.append(message)


class SimpleProgressReporter:
    """Simple progress reporter that tracks calls."""

    def __init__(self):
        self.start_folder_calls: list[tuple] = []
        self.update_file_calls: list[tuple] = []
        self.complete_folder_calls: list[bool] = []
        self.start_discovery_calls: list[dict] = []
        self.update_discovery_calls: list[dict] = []
        self.finish_discovery_calls: list[dict] = []

    def start_folder(self, folder_name: str, total_files: int, **kwargs) -> None:
        self.start_folder_calls.append((folder_name, total_files, kwargs))

    def update_file(self, current_file: int, total_files: int) -> None:
        self.update_file_calls.append((current_file, total_files))

    def complete_folder(self, success: bool) -> None:
        self.complete_folder_calls.append(success)

    def start_discovery(self, folder_total: int) -> None:
        self.start_discovery_calls.append({"folder_total": folder_total})

    def update_discovery_progress(
        self,
        folder_num: int,
        folder_total: int,
        folder_name: str,
        pending_for_folder: int,
        pending_total: int,
    ) -> None:
        self.update_discovery_calls.append(
            {
                "folder_num": folder_num,
                "folder_total": folder_total,
                "folder_name": folder_name,
                "pending_for_folder": pending_for_folder,
                "pending_total": pending_total,
            }
        )

    def finish_discovery(self, total_pending: int) -> None:
        self.finish_discovery_calls.append({"total_pending": total_pending})


class SimpleUPCService:
    """Simple UPC service that returns a fixed dictionary."""

    def __init__(self, upc_dict: dict | None = None):
        self.upc_dict = upc_dict or {
            "123456": ["CAT", "11111111111", "22222222222", "", ""]
        }
        self.call_count = 0

    def get_dictionary(self) -> dict:
        self.call_count += 1
        return self.upc_dict


class ErrorUPCService:
    """UPC service that always raises an exception."""

    def __init__(self, message: str = "Service unavailable"):
        self.message = message

    def get_dictionary(self) -> dict:
        raise Exception(self.message)


# =============================================================================
# Fixtures
# =============================================================================


@pytest.fixture
def sample_edi_content() -> str:
    """Sample EDI content for testing."""
    header = "A" + "VENDOR" + "0000000001" + "010125" + "0000010000"
    detail = (
        "B"
        + "01234567890"
        + "Test Item Description    "
        + "123456"
        + "001050"
        + "01"
        + "000001"
        + "00010"
        + "00199"
        + "001"
        + "000000"
    )
    tax = "C" + "TAB" + "Sales Tax                " + "000010000"
    return "\n".join([header, detail, tax]) + "\n"


@pytest.fixture
def input_folder(tmp_path: Path, sample_edi_content: str) -> Path:
    """Create an input folder with a sample EDI file."""
    folder = tmp_path / "input"
    folder.mkdir()
    (folder / "test.edi").write_text(sample_edi_content, encoding="utf-8")
    return folder


@pytest.fixture
def base_settings() -> dict:
    """Base settings for testing."""
    return {
        "as400_username": "test_user",
        "as400_password": "test_pass",
        "as400_address": "test.example.com",
    }


@pytest.fixture
def base_folder_config(input_folder: Path) -> dict:
    """Base folder configuration for testing."""
    return {
        "folder_name": str(input_folder),
        "alias": "test_folder",
        "folder_is_active": True,
        "process_edi": False,
        "convert_edi": False,
        "tweak_edi": False,
        "split_edi": False,
        "process_backend_copy": True,
        "copy_to_directory": str(input_folder / "output"),
    }


# =============================================================================
# Tests: DispatchConfig Pipeline Fields
# =============================================================================


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
        assert config.converter_step is None
        assert config.file_processor is None
        assert config.upc_dict == {}

    def test_set_pipeline_fields_in_constructor(self):
        """Test setting pipeline fields in constructor."""
        validator = FakeValidationStep(should_pass=True)
        converter = FakeConverterStep()
        upc_service = SimpleUPCService()
        progress = SimpleProgressReporter()

        config = DispatchConfig(
            validator_step=validator,
            converter_step=converter,
            upc_service=upc_service,
            progress_reporter=progress,
            upc_dict={"123": "product"},
        )

        assert config.validator_step is validator
        assert config.converter_step is converter
        assert config.upc_service is upc_service
        assert config.progress_reporter is progress
        assert config.upc_dict == {"123": "product"}


# =============================================================================
# Tests: Get UPC Dictionary
# =============================================================================


class TestGetUPCDictionary:
    """Tests for _get_upc_dictionary method."""

    class _StubQueryRunner:
        """Simple stub query runner for fallback UPC query tests."""

        def __init__(self, rows):
            self._rows = rows
            self.closed = False

        def run_query(self, query, params=None):
            return self._rows

        def close(self):
            self.closed = True

    def test_with_cached_dictionary(self):
        """Test returning cached UPC dictionary."""
        cached_dict = {"123": "product1", "456": "product2"}
        config = DispatchConfig(upc_dict=cached_dict)
        orchestrator = DispatchOrchestrator(config)

        result = orchestrator._get_upc_dictionary({})

        assert result == cached_dict

    def test_fetch_new_dictionary_via_service(self):
        """Test fetching new dictionary via UPC service."""
        upc_service = SimpleUPCService({"789": "product3"})

        config = DispatchConfig(upc_service=upc_service)
        orchestrator = DispatchOrchestrator(config)

        result = orchestrator._get_upc_dictionary({})

        assert result == {"789": "product3"}
        assert config.upc_dict == {"789": "product3"}
        assert upc_service.call_count == 1

    def test_service_exception_returns_empty_dict(self, monkeypatch):
        """Test that service exception returns empty dict."""
        monkeypatch.setenv("DISPATCH_STRICT_TESTING_MODE", "false")
        upc_service = ErrorUPCService("Service unavailable")

        config = DispatchConfig(upc_service=upc_service)
        orchestrator = DispatchOrchestrator(config)

        result = orchestrator._get_upc_dictionary({})

        assert result == {}

    def test_service_exception_raises_in_strict_testing_mode(self, monkeypatch):
        """Strict testing mode should surface UPC service failures."""
        monkeypatch.setenv("DISPATCH_STRICT_TESTING_MODE", "true")
        upc_service = ErrorUPCService("Service unavailable")

        config = DispatchConfig(upc_service=upc_service)
        orchestrator = DispatchOrchestrator(config)

        with pytest.raises(
            RuntimeError, match="Failed to fetch UPC dictionary from upc_service"
        ):
            orchestrator._get_upc_dictionary({})

    def test_fallback_parses_uppercase_column_names(self, monkeypatch):
        """Fallback parser should accept dict rows with uppercase column names."""
        rows = [
            {
                "ANBACD": "123456",
                "ANBBCD": "CAT1",
                "ANBGCD": "11111111111",
                "ANBHCD": "22222222222",
                "ANBICD": "33333333333",
                "ANBJCD": "44444444444",
            }
        ]
        stub_runner = self._StubQueryRunner(rows)
        monkeypatch.setattr(
            "dispatch.services.upc_service.create_query_runner_from_settings",
            lambda settings_dict, database="QGPL": stub_runner,
        )

        orchestrator = DispatchOrchestrator(DispatchConfig())
        settings = {
            "as400_username": "u",
            "as400_password": "p",
            "as400_address": "host",
            "database_lookup_mode": "optional",
        }

        result = orchestrator._get_upc_dictionary(settings)

        assert 123456 in result
        assert result[123456] == [
            "CAT1",
            "11111111111",
            "22222222222",
            "33333333333",
            "44444444444",
        ]
        assert stub_runner.closed is True

    def test_fallback_parses_tuple_rows(self, monkeypatch):
        """Fallback parser should accept positional tuple/list rows."""
        rows = [
            (
                987654,
                "CAT2",
                "55555555555",
                "66666666666",
                "77777777777",
                "88888888888",
            )
        ]
        stub_runner = self._StubQueryRunner(rows)
        monkeypatch.setattr(
            "dispatch.services.upc_service.create_query_runner_from_settings",
            lambda settings_dict, database="QGPL": stub_runner,
        )

        orchestrator = DispatchOrchestrator(DispatchConfig())
        settings = {
            "as400_username": "u",
            "as400_password": "p",
            "as400_address": "host",
            "database_lookup_mode": "optional",
        }

        result = orchestrator._get_upc_dictionary(settings)

        assert result[987654] == [
            "CAT2",
            "55555555555",
            "66666666666",
            "77777777777",
            "88888888888",
        ]
        assert stub_runner.closed is True

    def test_strict_mode_raises_when_rows_are_unparseable(self, monkeypatch):
        """Strict database mode should fail if query returns no parseable UPC rows."""
        monkeypatch.setenv("DISPATCH_STRICT_TESTING_MODE", "false")
        rows = [{"bad_key": "bad_value"}]
        stub_runner = self._StubQueryRunner(rows)
        monkeypatch.setattr(
            "dispatch.services.upc_service.create_query_runner_from_settings",
            lambda settings_dict, database="QGPL": stub_runner,
        )

        orchestrator = DispatchOrchestrator(DispatchConfig())
        settings = {
            "as400_username": "u",
            "as400_password": "p",
            "as400_address": "host",
            "database_lookup_mode": "strict",
        }

        with pytest.raises(LookupError, match="no parseable rows"):
            orchestrator._get_upc_dictionary(settings)

    def test_optional_mode_logs_reason_for_unparseable_rows(self, monkeypatch, caplog):
        """Optional mode should return empty dict and log preserved failure reason."""
        monkeypatch.setenv("DISPATCH_STRICT_TESTING_MODE", "false")
        rows = [{"bad_key": "bad_value"}]
        stub_runner = self._StubQueryRunner(rows)
        monkeypatch.setattr(
            "dispatch.services.upc_service.create_query_runner_from_settings",
            lambda settings_dict, database="QGPL": stub_runner,
        )

        orchestrator = DispatchOrchestrator(DispatchConfig())
        settings = {
            "as400_username": "u",
            "as400_password": "p",
            "as400_address": "host",
            "database_lookup_mode": "optional",
        }

        caplog.set_level(logging.WARNING)
        result = orchestrator._get_upc_dictionary(settings)

        assert result == {}
        assert (
            orchestrator._last_upc_lookup_error
            == "fallback UPC query returned rows, but none were parseable"
        )
        assert "none were parseable" in caplog.text
        assert stub_runner.closed is True


# =============================================================================
# Tests: Process Folder With Pipeline
# =============================================================================


class TestProcessFolderWithPipeline:
    """Tests for process_folder_with_pipeline method."""

    def test_process_folder_pipeline_enabled(self, input_folder: Path):
        """Test processing with pipeline enabled."""
        backend = CaptureBackend()

        config = DispatchConfig(
            backends={"copy": backend},
            settings={},
        )
        orchestrator = DispatchOrchestrator(config)

        folder = {
            "folder_name": str(input_folder),
            "alias": "Test",
            "process_backend_copy": True,
        }
        run_log = SimpleRunLog()

        result = orchestrator.process_folder_with_pipeline(folder, run_log)

        assert result.folder_name == str(input_folder)
        assert result.alias == "Test"
        assert result.files_processed == 1
        assert result.success is True
        assert len(backend.received) == 1

    def test_pipeline_steps_called_correctly(self, input_folder: Path):
        """Test that pipeline steps are called correctly."""
        validator = FakeValidationStep(should_pass=True)
        converter = FakeConverterStep(output_path=str(input_folder / "converted.edi"))
        backend = CaptureBackend()

        config = DispatchConfig(
            backends={"copy": backend},
            validator_step=validator,
            converter_step=converter,
            settings={},
        )
        orchestrator = DispatchOrchestrator(config)

        folder = {
            "folder_name": str(input_folder),
            "alias": "Test",
            "process_edi": "True",
            "convert_edi": True,
            "process_backend_copy": True,
        }
        run_log = SimpleRunLog()

        orchestrator.process_folder_with_pipeline(folder, run_log)

        assert validator.call_count == 1
        assert converter.call_count == 1

    def test_pipeline_folder_not_found(self, tmp_path: Path):
        """Test pipeline processing with non-existent folder."""
        config = DispatchConfig()
        orchestrator = DispatchOrchestrator(config)

        folder = {"folder_name": str(tmp_path / "notexists"), "alias": "Test"}
        run_log = SimpleRunLog()

        result = orchestrator.process_folder_with_pipeline(folder, run_log)

        assert result.success is False
        assert result.files_failed == 1
        assert "not found" in result.errors[0].lower()

    def test_pipeline_empty_folder(self, tmp_path: Path):
        """Test pipeline processing with empty folder."""
        empty_folder = tmp_path / "empty"
        empty_folder.mkdir()

        config = DispatchConfig()
        orchestrator = DispatchOrchestrator(config)

        folder = {"folder_name": str(empty_folder), "alias": "Test"}
        run_log = SimpleRunLog()

        result = orchestrator.process_folder_with_pipeline(folder, run_log)

        assert result.success is True
        assert result.files_processed == 0


# =============================================================================
# Tests: Process File With Pipeline
# =============================================================================


class TestProcessFileWithPipeline:
    """Tests for _process_file_with_pipeline method."""

    def test_full_pipeline_processing_flow(self, input_folder: Path):
        """Test full pipeline processing flow."""
        validator = FakeValidationStep(should_pass=True)
        converter = FakeConverterStep()
        backend = CaptureBackend()

        config = DispatchConfig(
            backends={"copy": backend},
            validator_step=validator,
            converter_step=converter,
            settings={},
        )
        orchestrator = DispatchOrchestrator(config)

        folder = {
            "folder_name": str(input_folder),
            "process_edi": "True",
            "process_backend_copy": True,
        }

        result = orchestrator._process_file_with_pipeline(
            str(input_folder / "test.edi"), folder, {}
        )

        assert result.file_name == str(input_folder / "test.edi")
        assert result.checksum is not None
        assert len(result.checksum) == 32  # MD5 hex

    def test_pipeline_validation_failure(self, input_folder: Path):
        """Test pipeline with validation failure."""
        validator = FakeValidationStep(should_pass=False, errors=["Validation error"])

        config = DispatchConfig(
            validator_step=validator,
            settings={},
        )
        orchestrator = DispatchOrchestrator(config)

        folder = {"folder_name": str(input_folder), "process_edi": "True"}

        result = orchestrator._process_file_with_pipeline(
            str(input_folder / "test.edi"), folder, {}
        )

        assert result.validated is False
        assert "Validation error" in result.errors

    def test_pipeline_converter_integration(self, input_folder: Path):
        """Test pipeline with converter step."""
        validator = FakeValidationStep(should_pass=True)
        converter = FakeConverterStep(output_path=str(input_folder / "converted.edi"))
        backend = CaptureBackend()

        config = DispatchConfig(
            backends={"copy": backend},
            validator_step=validator,
            converter_step=converter,
            settings={},
        )
        orchestrator = DispatchOrchestrator(config)

        folder = {
            "folder_name": str(input_folder),
            "convert_edi": True,
            "process_backend_copy": True,
        }

        result = orchestrator._process_file_with_pipeline(
            str(input_folder / "test.edi"), folder, {}
        )

        assert converter.call_count == 1
        assert result.converted is True

    def test_pipeline_converter_missing_output_fails_file(self, input_folder: Path):
        """Conversion target set but converter returns no output -> file fails."""
        validator = FakeValidationStep(should_pass=True)
        converter = FakeConverterStep(output_path=None)
        backend = CaptureBackend()

        config = DispatchConfig(
            backends={"copy": backend},
            validator_step=validator,
            converter_step=converter,
            settings={},
        )
        orchestrator = DispatchOrchestrator(config)

        folder = {
            "folder_name": str(input_folder),
            "convert_edi": True,
            "convert_to_format": "csv",
            "process_backend_copy": True,
        }

        result = orchestrator._process_file_with_pipeline(
            str(input_folder / "test.edi"), folder, {}
        )

        assert converter.call_count == 1
        assert result.sent is False
        assert result.converted is False
        assert any(
            "no converted output was produced" in err.lower() for err in result.errors
        )
        assert len(backend.received) == 0

    def test_pipeline_tweaker_integration(self, input_folder: Path):
        """Test pipeline with tweak_edi=True routes to converter via convert_to_tweaks."""
        validator = FakeValidationStep(should_pass=True)
        converter = FakeConverterStep(output_path=str(input_folder / "tweaked.edi"))
        backend = CaptureBackend()

        config = DispatchConfig(
            backends={"copy": backend},
            validator_step=validator,
            converter_step=converter,
            settings={},
        )
        orchestrator = DispatchOrchestrator(config)

        folder = {
            "folder_name": str(input_folder),
            "convert_to_format": "tweaks",
            "process_edi": True,
            "process_backend_copy": True,
        }

        orchestrator._process_file_with_pipeline(
            str(input_folder / "test.edi"), folder, {"123": "product"}
        )

        # Tweaks are handled by converter step via convert_to_tweaks module;
        # convert_to_format is the source of truth (tweak_edi is deprecated).
        assert converter.call_count == 1

    def test_pipeline_sending_to_backends(self, input_folder: Path):
        """Test pipeline sending files to backends."""
        backend = CaptureBackend()

        config = DispatchConfig(
            backends={"copy": backend},
            settings={},
        )
        orchestrator = DispatchOrchestrator(config)

        folder = {"folder_name": str(input_folder), "process_backend_copy": True}

        result = orchestrator._process_file_with_pipeline(
            str(input_folder / "test.edi"), folder, {}
        )

        assert result.sent is True
        assert len(backend.received) == 1

    def test_pipeline_error_handling(self, input_folder: Path):
        """Test pipeline error handling."""
        validator = ErrorValidator("Validator error")

        config = DispatchConfig(
            validator_step=validator,
            settings={},
        )
        orchestrator = DispatchOrchestrator(config)

        folder = {"folder_name": str(input_folder), "process_edi": "True"}

        result = orchestrator._process_file_with_pipeline(
            str(input_folder / "test.edi"), folder, {}
        )

        assert "Validator error" in result.errors


# =============================================================================
# Tests: Processed Files and Cleanup Behavior
# =============================================================================


class TestProcessedFilesAndCleanupBehavior:
    """Tests for processed-file idempotency and pipeline cleanup behavior."""

    def test_filter_skips_checksum_when_resend_flag_false(
        self, input_folder: Path, temp_database
    ):
        """Previously processed non-resend checksum is filtered out."""
        orchestrator = DispatchOrchestrator(DispatchConfig())

        # Insert a processed file record with resend_flag=False
        temp_database.processed_files.insert(
            {
                "file_name": str(input_folder / "a.edi"),
                "folder_id": 42,
                "folder_alias": "Test",
                "file_checksum": "checksum-a",
                "processed_at": "2024-01-01T00:00:00",
                "resend_flag": 0,
                "sent_to": "Copy",
                "status": "processed",
            }
        )

        # Create test files
        (input_folder / "a.edi").write_text("content a", encoding="utf-8")
        (input_folder / "b.edi").write_text("content b", encoding="utf-8")

        files = [str(input_folder / "a.edi"), str(input_folder / "b.edi")]

        # Mock checksum calculation to return predictable values
        original_calculate = orchestrator._calculate_checksum
        checksums = {
            "checksum-a": str(input_folder / "a.edi"),
            "checksum-b": str(input_folder / "b.edi"),
        }
        file_to_checksum = {v: k for k, v in checksums.items()}

        def mock_calculate(file_path):
            return file_to_checksum.get(file_path, original_calculate(file_path))

        orchestrator._calculate_checksum = mock_calculate

        filtered = orchestrator._filter_processed_files(
            files, temp_database.processed_files, {"id": 42}
        )

        assert filtered == [str(input_folder / "b.edi")]

    def test_filter_keeps_checksum_when_resend_flag_true(
        self, input_folder: Path, temp_database
    ):
        """Resend-marked checksum remains eligible for processing."""
        orchestrator = DispatchOrchestrator(DispatchConfig())

        # Insert a processed file record with resend_flag=True
        temp_database.processed_files.insert(
            {
                "file_name": str(input_folder / "a.edi"),
                "folder_id": 42,
                "folder_alias": "Test",
                "file_checksum": "checksum-a",
                "processed_at": "2024-01-01T00:00:00",
                "resend_flag": 1,
                "sent_to": "Copy",
                "status": "processed",
            }
        )

        # Create test files
        (input_folder / "a.edi").write_text("content a", encoding="utf-8")
        (input_folder / "b.edi").write_text("content b", encoding="utf-8")

        files = [str(input_folder / "a.edi"), str(input_folder / "b.edi")]

        # Mock checksum calculation
        file_to_checksum = {
            str(input_folder / "a.edi"): "checksum-a",
            str(input_folder / "b.edi"): "checksum-b",
        }

        def mock_calculate(file_path):
            return file_to_checksum.get(file_path, "other")

        orchestrator._calculate_checksum = mock_calculate

        filtered = orchestrator._filter_processed_files(
            files, temp_database.processed_files, {"id": 42}
        )

        assert filtered == files

    def test_record_processed_file_updates_existing_resend_record_instead_of_insert(
        self, input_folder: Path, temp_database
    ):
        """Existing resend record is updated and not duplicated."""
        orchestrator = DispatchOrchestrator(DispatchConfig())

        # Insert an existing resend record
        temp_database.processed_files.insert(
            {
                "file_name": str(input_folder / "file.edi"),
                "folder_id": 99,
                "folder_alias": "Orders",
                "file_checksum": "old-checksum",
                "processed_at": "2024-01-01T00:00:00",
                "resend_flag": 1,
                "sent_to": "Old",
                "status": "resend",
            }
        )

        file_result = FileResult(
            file_name=str(input_folder / "file.edi"), checksum="abc123"
        )

        folder = {
            "id": 99,
            "alias": "Orders",
            "process_backend_copy": True,
            "copy_to_directory": "/out/copy",
        }

        orchestrator._record_processed_file(
            temp_database.processed_files, folder, file_result
        )

        # Check that the record was updated, not duplicated
        records = list(temp_database.processed_files.find(folder_id=99))
        assert len(records) == 1
        assert records[0]["resend_flag"] == 0
        assert records[0]["status"] == "processed"
        assert records[0]["sent_to"] == "Copy: /out/copy"

    def test_record_processed_file_inserts_when_no_existing_resend_record(
        self, input_folder: Path, temp_database
    ):
        """New processed-file record is inserted when resend match is absent."""
        orchestrator = DispatchOrchestrator(DispatchConfig())

        file_result = FileResult(
            file_name=str(input_folder / "file.edi"), checksum="def456"
        )

        folder = {
            "old_id": 123,
            "alias": "Inbound",
            "process_backend_email": True,
            "email_to": "ops@example.com",
        }

        orchestrator._record_processed_file(
            temp_database.processed_files, folder, file_result
        )

        # Check that a new record was inserted
        records = list(temp_database.processed_files.find(folder_id=123))
        assert len(records) == 1
        assert records[0]["file_name"] == str(input_folder / "file.edi")
        assert records[0]["folder_alias"] == "Inbound"
        assert records[0]["file_checksum"] == "def456"
        assert records[0]["resend_flag"] == 0
        assert records[0]["sent_to"] == "Email: ops@example.com"
        assert records[0]["status"] == "processed"

    def test_process_file_with_pipeline_cleans_context_registered_temp_dirs_in_finally(
        self, monkeypatch, input_folder: Path
    ):
        """Context-tracked pipeline temp dirs are removed during finally cleanup."""
        monkeypatch.setenv("DISPATCH_STRICT_TESTING_MODE", "false")

        # Create temp dirs that will be tracked
        temp_dir1 = input_folder / "pipeline-1"
        temp_dir2 = input_folder / "pipeline-2"
        temp_dir1.mkdir()
        temp_dir2.mkdir()

        # Use a converter that adds temp dirs to context
        converter = ConverterWithTempDirs([str(temp_dir1), str(temp_dir2)])

        orchestrator = DispatchOrchestrator(
            DispatchConfig(
                converter_step=converter,
                settings={},
            )
        )

        folder = {
            "folder_name": str(input_folder),
            "convert_edi": True,
        }

        orchestrator._process_file_with_pipeline(
            str(input_folder / "test.edi"), folder, {}
        )

        # Temp dirs should be cleaned up
        assert not temp_dir1.exists()
        assert not temp_dir2.exists()


# =============================================================================
# Tests: Send Pipeline File
# =============================================================================


class TestSendPipelineFile:
    """Tests for _send_pipeline_file method."""

    def test_send_pipeline_file_success(self, input_folder: Path):
        """Test successful sending of pipeline file."""
        backend = CaptureBackend()

        config = DispatchConfig(backends={"copy": backend}, settings={})
        orchestrator = DispatchOrchestrator(config)

        folder = {"process_backend_copy": True}

        result = orchestrator._send_pipeline_file(
            str(input_folder / "test.edi"), folder
        )

        assert result is True
        assert len(backend.received) == 1

    def test_send_pipeline_file_no_backends(self, input_folder: Path):
        """Test sending with no enabled backends."""
        config = DispatchConfig(backends={}, settings={})
        orchestrator = DispatchOrchestrator(config)

        folder = {}

        result = orchestrator._send_pipeline_file(
            str(input_folder / "test.edi"), folder
        )

        assert result is False

    def test_send_pipeline_file_partial_failure(self, input_folder: Path):
        """Test sending with partial backend failure."""
        backend1 = CaptureBackend()
        backend2 = FailingBackend()

        config = DispatchConfig(
            backends={"copy1": backend1, "copy2": backend2}, settings={}
        )
        orchestrator = DispatchOrchestrator(config)

        folder = {"process_backend_copy1": True, "process_backend_copy2": True}

        result = orchestrator._send_pipeline_file(
            str(input_folder / "test.edi"), folder
        )

        assert result is False


# =============================================================================
# Tests: Process Folder Pipeline Routing
# =============================================================================


class TestProcessFolderPipelineRouting:
    """Tests for routing in process_folder method."""

    def test_process_folder_routes_to_pipeline(self, input_folder: Path):
        """Test that process_folder routes to pipeline."""
        backend = CaptureBackend()

        config = DispatchConfig(
            backends={"copy": backend},
            settings={},
        )
        orchestrator = DispatchOrchestrator(config)

        folder = {
            "folder_name": str(input_folder),
            "alias": "Test",
            "process_backend_copy": True,
        }
        run_log = SimpleRunLog()

        result = orchestrator.process_folder(folder, run_log)

        assert result.files_processed == 1
        assert result.success is True


# =============================================================================
# Tests: Process File Pipeline Routing
# =============================================================================


class TestProcessFilePipelineRouting:
    """Tests for routing in process_file method."""

    def test_process_file_routes_to_pipeline(self, input_folder: Path):
        """Test that process_file routes to pipeline."""
        validator = FakeValidationStep(should_pass=True)
        backend = CaptureBackend()

        config = DispatchConfig(
            backends={"copy": backend},
            validator_step=validator,
            settings={},
        )
        orchestrator = DispatchOrchestrator(config)

        folder = {"folder_name": str(input_folder)}

        result = orchestrator.process_file(str(input_folder / "test.edi"), folder)

        assert result.file_name == str(input_folder / "test.edi")
        assert result.checksum is not None


# =============================================================================
# Tests: Pipeline Only Contract
# =============================================================================


class TestPipelineOnlyContract:
    """Tests for the pipeline-only processing contract."""

    def test_process_file_works_without_legacy_toggle(self, input_folder: Path):
        """File processing works with the default pipeline-only configuration."""
        backend = CaptureBackend()

        config = DispatchConfig(
            backends={"copy": backend},
            settings={},
        )
        orchestrator = DispatchOrchestrator(config)

        folder = {"folder_name": str(input_folder), "process_backend_copy": True}

        result = orchestrator.process_file(str(input_folder / "test.edi"), folder)

        assert result.file_name == str(input_folder / "test.edi")
        assert result.checksum is not None

    def test_process_file_with_validation_runs_pipeline_path(self, input_folder: Path):
        """Validation still runs through pipeline path."""
        validator = FakeValidationStep(should_pass=True)
        backend = CaptureBackend()

        config = DispatchConfig(
            backends={"copy": backend},
            validator_step=validator,
            settings={},
        )
        orchestrator = DispatchOrchestrator(config)

        folder = {
            "folder_name": str(input_folder),
            "process_edi": "True",
            "process_backend_copy": True,
        }

        orchestrator.process_file(str(input_folder / "test.edi"), folder)

        assert validator.call_count == 1

    def test_process_folder_routes_through_consolidated_pipeline_path(
        self, input_folder: Path
    ):
        """Folder processing routes through consolidated pipeline path."""
        backend = CaptureBackend()

        config = DispatchConfig(
            backends={"copy": backend},
            settings={},
        )
        orchestrator = DispatchOrchestrator(config)

        folder = {
            "folder_name": str(input_folder),
            "alias": "Test",
            "process_backend_copy": True,
        }
        run_log = SimpleRunLog()

        result = orchestrator.process_folder(folder, run_log)

        assert result.folder_name == str(input_folder)
        assert result.alias == "Test"


# =============================================================================
# Tests: Orchestrator Pipeline Helpers
# =============================================================================


class TestOrchestratorPipelineHelpers:
    """Tests for pipeline helper methods in DispatchOrchestrator."""

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

    def test_build_processing_context_respects_explicit_passthrough_mode(self):
        """Explicit process_edi=False remains passthrough even with stale format.

        Legacy rows can retain a non-empty convert_to_format from a previous
        selection while mode is explicitly set to Do Nothing/Passthrough.
        Runtime must honor explicit mode and avoid inferring conversion.
        """
        orchestrator = DispatchOrchestrator(DispatchConfig())

        context = orchestrator._build_processing_context(
            {
                "process_edi": "False",
                "convert_to_format": "Tweaks",
            },
            {},
        )

        assert context.effective_folder["convert_to_format"] == "tweaks"
        assert context.effective_folder["convert_edi"] is False
        assert context.effective_folder["process_edi"] == "False"

    def test_build_processing_context_legacy_tweak_enables_tweaks_converter(self):
        """Legacy tweak_edi=True must route through tweaks converter.

        This preserves old "Enable Tweaks" behavior from legacy configs, even
        when process_edi is stale/False.
        """
        orchestrator = DispatchOrchestrator(DispatchConfig())

        context = orchestrator._build_processing_context(
            {
                "process_edi": "False",
                "tweak_edi": True,
                "convert_to_format": "Tweaks",
            },
            {},
        )

        assert context.effective_folder["convert_to_format"] == "tweaks"
        assert context.effective_folder["convert_edi"] is True
        assert context.effective_folder["process_edi"] is True

    def test_build_processing_context_maps_legacy_tweak_flag_to_tweaks_format(self):
        """Legacy tweak_edi=True is normalized to 'tweaks'."""
        orchestrator = DispatchOrchestrator(DispatchConfig())

        context = orchestrator._build_processing_context(
            {
                "process_edi": None,
                "tweak_edi": True,
                "convert_to_format": "",
            },
            {},
        )

        assert context.effective_folder["convert_to_format"] == "tweaks"
        # Missing mode + mapped format should infer conversion.
        assert context.effective_folder["convert_edi"] is True
        assert context.effective_folder["process_edi"] is True

    def test_build_processing_context_legacy_tweak_flag_overrides_explicit_format(
        self,
    ):
        """Legacy tweak_edi=True must route through tweaks converter.

        Old rows can contain stale convert_to_format values from prior mode
        switches. To preserve old behavior, tweak mode remains authoritative
        and routes through the tweaks converter.
        """
        orchestrator = DispatchOrchestrator(DispatchConfig())

        context = orchestrator._build_processing_context(
            {
                "process_edi": None,
                "tweak_edi": True,
                "convert_to_format": "csv",
            },
            {},
        )

        assert context.effective_folder["convert_to_format"] == "tweaks"
        assert context.effective_folder["convert_edi"] is True
        assert context.effective_folder["process_edi"] is True

    def test_build_processing_context_infers_convert_when_mode_missing_both_gates(
        self, tmp_path
    ):
        """Legacy rows missing mode infer conversion from format and align gates.

        EDIConverterStep.convert() reads process_edi directly from the params
        dict (effective_folder).  If _normalize_edi_flags only set
        convert_edi=True without also updating process_edi, the converter would
        still see False and skip conversion silently. This test catches that
        double-gate bug for mode-missing legacy rows.
        """
        import textwrap

        edi_file = tmp_path / "test.edi"
        edi_file.write_text(textwrap.dedent("""\
            HDR*TEST
            """))

        captured_params: dict = {}

        class CapturingConverter:
            """Records the params dict it receives."""

            call_count = 0

            def execute(
                self, file_path, folder, settings=None, upc_dict=None, context=None
            ):
                CapturingConverter.call_count += 1
                captured_params.update(folder)
                return file_path  # pass-through

        orchestrator = DispatchOrchestrator(
            DispatchConfig(converter_step=CapturingConverter())
        )
        folder = {
            "process_edi": None,
            "convert_to_format": "csv",
            "process_backend_copy": True,
            "copy_to_directory": str(tmp_path / "out"),
        }
        (tmp_path / "out").mkdir()

        orchestrator.process_file(str(edi_file), folder)

        assert CapturingConverter.call_count == 1, (
            "Converter was not called — missing legacy mode should infer convert "
            "from convert_to_format (double-gate bug)"
        )
        assert captured_params.get("process_edi") is True, (
            "Converter received process_edi!=True; inferred convert mode did not "
            "write through to effective_folder (double-gate bug)"
        )

    def test_build_processing_context_normalizes_noisy_convert_format(self):
        """Noisy legacy convert format strings should be canonicalized for runtime use."""
        orchestrator = DispatchOrchestrator(DispatchConfig())

        context = orchestrator._build_processing_context(
            {
                "process_edi": True,
                "convert_to_format": " eStore / eInvoice Generic ",
            },
            {},
        )

        assert (
            context.effective_folder["convert_to_format"] == "estore_einvoice_generic"
        )


# =============================================================================
# Tests: Orchestrator Progress Phases
# =============================================================================


class TestOrchestratorProgressPhases:
    """Tests for discovery/sending phase orchestration support."""

    def test_discover_pending_files_reports_progress_and_filters_processed(
        self, tmp_path: Path, temp_database
    ):
        # Create two folders with files
        folder_a = tmp_path / "a"
        folder_b = tmp_path / "b"
        folder_a.mkdir()
        folder_b.mkdir()

        # Create files
        (folder_a / "new.edi").write_text("new-a-content", encoding="utf-8")
        (folder_a / "old.edi").write_text("old-a-content", encoding="utf-8")
        (folder_b / "new.edi").write_text("new-b-content", encoding="utf-8")

        config = DispatchConfig()
        orchestrator = DispatchOrchestrator(config)

        folders = [
            {"id": 1, "folder_name": str(folder_a), "alias": "A"},
            {"id": 2, "folder_name": str(folder_b), "alias": "B"},
        ]

        # Insert processed record for folder A's old file
        temp_database.processed_files.insert(
            {
                "file_name": str(folder_a / "old.edi"),
                "folder_id": 1,
                "folder_alias": "A",
                "file_checksum": "old-checksum",
                "processed_at": "2024-01-01T00:00:00",
                "resend_flag": 0,
                "sent_to": "Copy",
                "status": "processed",
            }
        )

        progress = SimpleProgressReporter()

        # Mock checksum calculation
        file_to_checksum = {
            str(folder_a / "new.edi"): "new-checksum",
            str(folder_a / "old.edi"): "old-checksum",
            str(folder_b / "new.edi"): "new-b-checksum",
        }

        def mock_calculate(file_path):
            return file_to_checksum.get(file_path, "other")

        orchestrator._calculate_checksum = mock_calculate

        pending_lists, total_pending = orchestrator.discover_pending_files(
            folders,
            processed_files=temp_database.processed_files,
            progress_reporter=progress,
        )

        assert pending_lists == [
            [str(folder_a / "new.edi")],
            [str(folder_b / "new.edi")],
        ]
        assert total_pending == 2
        assert len(progress.start_discovery_calls) == 1
        assert len(progress.update_discovery_calls) == 2
        assert len(progress.finish_discovery_calls) == 1

    def test_process_folder_uses_legacy_start_folder_signature_when_needed(
        self, input_folder: Path
    ):
        class LegacyProgress:
            def __init__(self):
                self.calls = []

            def start_folder(self, folder_name: str, total_files: int) -> None:
                self.calls.append((folder_name, total_files))

            def update_file(self, current_file: int, total_files: int) -> None:
                return None

            def complete_folder(self, success: bool) -> None:
                return None

        backend = CaptureBackend()

        progress = LegacyProgress()
        orchestrator = DispatchOrchestrator(
            DispatchConfig(
                backends={"copy": backend},
                progress_reporter=progress,
                settings={},
            )
        )

        folder = {
            "folder_name": str(input_folder),
            "alias": "Input",
            "process_backend_copy": True,
        }

        result = orchestrator.process_folder(
            folder,
            run_log=SimpleRunLog(),
            processed_files=None,
            pre_discovered_files=[str(input_folder / "test.edi")],
            folder_num=1,
            folder_total=1,
        )

        assert result.files_processed == 1
        assert progress.calls == [("Input", 1)]


class TestExtractInvoiceNumbers:
    """Regression tests for _extract_invoice_numbers method."""

    def test_extract_invoice_numbers_handles_missing_invoice_number_key(self, tmp_path):
        """Regression: A record without invoice_number key should not raise KeyError.

        Previously the code used rec["invoice_number"] directly which would raise
        KeyError if the key was missing. Now it uses rec.get("invoice_number", "").
        """
        # Create a test EDI file with an A record that has all fields
        edi_content = "AVENDOR12345678901234567890123456\n"
        test_file = tmp_path / "test.edi"
        test_file.write_text(edi_content)

        orchestrator = DispatchOrchestrator(DispatchConfig())
        result = orchestrator._extract_invoice_numbers(str(test_file))

        # Should return the invoice number, not raise KeyError
        assert result == "1234567890"

    def test_extract_invoice_numbers_handles_duplicate_invoices(self, tmp_path):
        """Test that duplicate invoice numbers are deduplicated."""
        # Two A records with the same invoice number
        edi_content = (
            "AVENDOR12345678901234567890123456\n"
            "BVENDOR_ITEM                     \n"
            "AVENDOR12345678901234567890123456\n"
            "BVENDOR_ITEM                     \n"
        )
        test_file = tmp_path / "test.edi"
        test_file.write_text(edi_content)

        orchestrator = DispatchOrchestrator(DispatchConfig())
        result = orchestrator._extract_invoice_numbers(str(test_file))

        # Should only return one instance of the duplicate
        assert result == "1234567890"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
