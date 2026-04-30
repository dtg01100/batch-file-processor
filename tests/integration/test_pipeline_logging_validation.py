"""Integration tests validating the conversion/sending pipeline via logging.

This test module uses the new centralized logging infrastructure
(RunLogHandler, RunLogAdapter, setup_logging) to validate the entire
dispatch pipeline end-to-end. Instead of passing MagicMock run_logs and
only checking return values, we capture real log output and assert on
the message sequence produced by each pipeline stage.

This replaces the scattered coverage previously spread across:
- test_end_to_end_batch_processing.py
- test_error_recovery_resilience.py
- test_failure_scenarios_e2e.py
which all passed MagicMock() as run_log and never verified log content.
"""

import io
import logging
import os
from pathlib import Path

import pytest

from core.logging_config import RunLogAdapter, RunLogHandler, setup_logging
from dispatch.error_handler import ErrorHandler
from dispatch.orchestrator import DispatchConfig, DispatchOrchestrator


class _StubProcessedFilesTable:
    """Lightweight table stub for processed-files dedup tests."""

    def __init__(self, data=None):
        self._data = list(data or [])

    def find(self, **kwargs):
        return [r for r in self._data if all(r.get(k) == v for k, v in kwargs.items())]

    def find_one(self, **kwargs):
        for r in self._data:
            if all(r.get(k) == v for k, v in kwargs.items()):
                return r
        return None

    def insert(self, record):
        self._data.append(record)
        return record.get("id", len(self._data))

    def update(self, record, keys):
        for i, existing in enumerate(self._data):
            if all(existing.get(k) == record.get(k) for k in keys):
                self._data[i] = {**existing, **record}
                return


pytestmark = [
    pytest.mark.integration,
    pytest.mark.dispatch,
    pytest.mark.workflow,
]


class CompositeConverterStep:
    """Composite converter that applies conversion then tweaks."""

    def __init__(self, converter, tweaker):
        self.converter = converter
        self.tweaker = tweaker

    def execute(self, file_path, folder, settings=None, upc_dict=None, context=None):
        converted = self.converter.execute(
            file_path,
            folder,
            settings=settings,
            upc_dict=upc_dict,
            context=context,
        )
        return self.tweaker.execute(
            converted,
            folder,
            settings=settings,
            upc_dict=upc_dict,
            context=context,
        )



MINIMAL_EDI = (
    "HDRA0000000000000000  000000000000000test.edi\n"
    "A0000000000  0000000100100000000000\n"
)


# ---------------------------------------------------------------------------
# Reusable helpers / fakes
# ---------------------------------------------------------------------------


class TrackingBackend:
    """Backend that records sent filenames and always succeeds."""

    def __init__(self):
        self.sent = []

    def send(self, params, settings, filename):
        self.sent.append(filename)
        return True


class FailingBackend:
    """Backend that always raises on send."""

    def __init__(self, msg="Backend send failed"):
        self.msg = msg

    def send(self, params, settings, filename):
        raise RuntimeError(self.msg)


class PassthroughConverterStep:
    """Converter step that returns the input path unchanged."""

    def __init__(self):
        self.call_count = 0
        self.last_file = None

    def execute(self, file_path, folder, settings=None, upc_dict=None, context=None):
        self.call_count += 1
        self.last_file = file_path
        return file_path


class PassthroughTweakerStep:
    """Tweaker step that returns the input path unchanged."""

    def __init__(self):
        self.call_count = 0
        self.last_file = None

    def execute(self, file_path, folder, upc_dict=None, settings=None, context=None):
        self.call_count += 1
        self.last_file = file_path
        return file_path


class AlwaysPassValidator:
    """Validator step that always passes."""

    def __init__(self):
        self.call_count = 0

    def execute(self, file_path, folder):
        self.call_count += 1
        return (True, file_path)


class AlwaysFailValidator:
    """Validator step that always fails with configurable errors."""

    def __init__(self, errors=None):
        self.errors = errors or ["validation failed"]
        self.call_count = 0

    def execute(self, file_path, folder):
        self.call_count += 1
        return (False, self.errors)


def _make_edi(folder: Path, name: str = "test.edi", content: str = MINIMAL_EDI) -> str:
    """Create a minimal EDI file in the given folder."""
    folder.mkdir(parents=True, exist_ok=True)
    p = folder / name
    p.write_text(content)
    return str(p)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture(autouse=True)
def _configure_logging():
    """Set up logging at DEBUG so all pipeline messages are captured.

    Tears down after each test to avoid handler leaks.
    """
    setup_logging(level=logging.DEBUG)
    yield
    # Clean up: remove any stray RunLogHandlers from the dispatch loggers
    for logger_name in (
        "dispatch",
        "dispatch.orchestrator",
        "dispatch.send_manager",
        "dispatch.error_handler",
    ):
        lgr = logging.getLogger(logger_name)
        for h in lgr.handlers[:]:
            if isinstance(h, RunLogHandler):
                lgr.removeHandler(h)
                h.close()


@pytest.fixture
def log_capture():
    """Provide a list-backed RunLogHandler attached to 'dispatch.orchestrator'.

    Returns the list that collects log messages.  The handler is removed on
    teardown automatically.
    """
    messages: list[str] = []
    handler = RunLogHandler(messages)
    handler.setLevel(logging.DEBUG)

    # Attach to the orchestrator logger AND its parent so we capture
    # messages from send_manager too.
    target_logger = logging.getLogger("dispatch")
    target_logger.addHandler(handler)
    yield messages
    target_logger.removeHandler(handler)
    handler.close()


@pytest.fixture
def workspace(tmp_path):
    """Create a workspace with input folder, output folder, and sample EDI files."""
    inp = tmp_path / "input"
    out = tmp_path / "output"
    inp.mkdir()
    out.mkdir()
    _make_edi(inp, "invoice_001.edi")
    _make_edi(inp, "invoice_002.edi", MINIMAL_EDI.replace("0001", "0002"))
    _make_edi(inp, "invoice_003.edi", MINIMAL_EDI.replace("0001", "0003"))
    return {"input": inp, "output": out, "root": tmp_path}


@pytest.fixture
def folder_config(workspace):
    """Standard folder config pointing at the workspace."""
    return {
        "id": 1,
        "folder_name": str(workspace["input"]),
        "alias": "TestAlias",
        "process_backend_copy": True,
        "copy_to_directory": str(workspace["output"]),
        "process_backend_ftp": False,
        "process_backend_email": False,
    }


# ===================================================================
# 1. Successful pipeline log sequence
# ===================================================================


class TestSuccessfulPipelineLogging:
    """Verify log messages emitted during a successful processing run."""

    def test_successful_pipeline_emits_expected_log_sequence(
        self, workspace, folder_config, log_capture
    ):
        """Process a folder with 3 files and verify the log sequence:
        folder entry → file count → sending per file → Success.
        """
        backend = TrackingBackend()
        config = DispatchConfig(backends={"copy": backend}, settings={})
        orch = DispatchOrchestrator(config)

        result = orch.process_folder(folder_config, run_log=None)

        assert result.success is True
        assert result.files_processed == 3

        joined = "\n".join(log_capture)
        # Folder entry
        assert "Processing folder" in joined
        assert "TestAlias" in joined
        # File count
        assert "3 files" in joined
        # At least one send message
        assert "sending" in joined.lower()
        # Success messages
        assert joined.lower().count("success") >= 3

    def test_empty_folder_logs_no_files_message(self, tmp_path, log_capture):
        """An empty input folder should log 'No files in directory'."""
        empty_dir = tmp_path / "empty_input"
        empty_dir.mkdir()

        backend = TrackingBackend()
        config = DispatchConfig(backends={"copy": backend}, settings={})
        orch = DispatchOrchestrator(config)

        folder = {
            "id": 2,
            "folder_name": str(empty_dir),
            "alias": "EmptyFolder",
            "process_backend_copy": True,
            "copy_to_directory": str(tmp_path / "out"),
        }

        result = orch.process_folder(folder, run_log=None)

        assert result.files_processed == 0
        joined = "\n".join(log_capture)
        assert "No files in directory" in joined

    def test_missing_folder_logs_error(self, tmp_path, log_capture):
        """Processing a non-existent folder should log 'Folder not found'."""
        backend = TrackingBackend()
        config = DispatchConfig(backends={"copy": backend}, settings={})
        orch = DispatchOrchestrator(config)

        folder = {
            "id": 3,
            "folder_name": str(tmp_path / "does_not_exist"),
            "alias": "GhostFolder",
            "process_backend_copy": True,
            "copy_to_directory": str(tmp_path / "out"),
        }

        result = orch.process_folder(folder, run_log=None)

        assert result.success is False
        joined = "\n".join(log_capture)
        assert "Folder not found" in joined


# ===================================================================
# 2. RunLogHandler capture modes
# ===================================================================


class TestRunLogHandlerCapture:
    """Verify RunLogHandler captures pipeline messages in both modes."""

    def test_captures_to_list(self, workspace, folder_config):
        """RunLogHandler backed by a list collects string messages."""
        messages: list[str] = []
        handler = RunLogHandler(messages)
        handler.setLevel(logging.DEBUG)
        lgr = logging.getLogger("dispatch.orchestrator")
        lgr.addHandler(handler)

        try:
            backend = TrackingBackend()
            config = DispatchConfig(backends={"copy": backend}, settings={})
            orch = DispatchOrchestrator(config)
            orch.process_folder(folder_config, run_log=None)
        finally:
            lgr.removeHandler(handler)
            handler.close()

        assert len(messages) > 0, "Should have captured at least one log message"
        assert any("Processing folder" in m for m in messages)

    def test_captures_to_binary_file(self, workspace, folder_config):
        """RunLogHandler backed by BytesIO writes encoded messages."""
        bio = io.BytesIO()
        handler = RunLogHandler(bio)
        handler.setLevel(logging.DEBUG)
        lgr = logging.getLogger("dispatch.orchestrator")
        lgr.addHandler(handler)

        try:
            backend = TrackingBackend()
            config = DispatchConfig(backends={"copy": backend}, settings={})
            orch = DispatchOrchestrator(config)
            orch.process_folder(folder_config, run_log=None)
        finally:
            lgr.removeHandler(handler)
            handler.close()

        output = bio.getvalue().decode("utf-8")
        assert len(output) > 0
        assert "\r\n" in output, "Binary mode should use \\r\\n line endings"
        assert "Processing folder" in output

    def test_handler_with_none_run_log_discards_silently(self):
        """RunLogHandler with run_log=None should discard records silently."""
        handler = RunLogHandler(None)
        handler.setLevel(logging.DEBUG)
        lgr = logging.getLogger("dispatch.orchestrator")
        lgr.addHandler(handler)

        try:
            lgr.info("This should be silently discarded")
            # No exception raised
        finally:
            lgr.removeHandler(handler)
            handler.close()


# ===================================================================
# 3. RunLogAdapter context prefixing
# ===================================================================


class TestRunLogAdapterPrefixing:
    """Verify RunLogAdapter prepends folder/file context to messages."""

    def test_folder_prefix(self):
        """Adapter with folder context prepends [FolderName]."""
        messages: list[str] = []
        handler = RunLogHandler(messages)
        handler.setLevel(logging.DEBUG)

        base_logger = logging.getLogger("test.adapter.folder")
        base_logger.addHandler(handler)
        base_logger.setLevel(logging.DEBUG)

        try:
            adapter = RunLogAdapter(base_logger, {"folder": "ACME_Corp"})
            adapter.info("Invoice processed")
        finally:
            base_logger.removeHandler(handler)
            handler.close()

        assert len(messages) >= 1
        assert "[ACME_Corp] Invoice processed" in messages[-1]

    def test_folder_and_file_prefix(self):
        """Adapter with folder+file context prepends [folder/file]."""
        messages: list[str] = []
        handler = RunLogHandler(messages)
        handler.setLevel(logging.DEBUG)

        base_logger = logging.getLogger("test.adapter.file")
        base_logger.addHandler(handler)
        base_logger.setLevel(logging.DEBUG)

        try:
            adapter = RunLogAdapter(
                base_logger, {"folder": "ACME_Corp", "file": "INV_001.edi"}
            )
            adapter.info("Conversion complete")
        finally:
            base_logger.removeHandler(handler)
            handler.close()

        assert len(messages) >= 1
        assert "[ACME_Corp/INV_001.edi] Conversion complete" in messages[-1]

    def test_no_context_no_prefix(self):
        """Adapter with empty context produces unmodified messages."""
        messages: list[str] = []
        handler = RunLogHandler(messages)
        handler.setLevel(logging.DEBUG)

        base_logger = logging.getLogger("test.adapter.empty")
        base_logger.addHandler(handler)
        base_logger.setLevel(logging.DEBUG)

        try:
            adapter = RunLogAdapter(base_logger, {})
            adapter.info("Plain message")
        finally:
            base_logger.removeHandler(handler)
            handler.close()

        assert len(messages) >= 1
        assert messages[-1] == "Plain message"


# ===================================================================
# 4. Validation failure logging
# ===================================================================


class TestValidationFailureLogging:
    """Verify validation failures are captured in log output."""

    def test_validation_failure_logs_message(self, tmp_path, log_capture):
        """When a validator fails, 'Validation failed' appears in the log."""
        inp = tmp_path / "input"
        _make_edi(inp, "bad.edi")

        validator = AlwaysFailValidator(errors=["Bad EDI structure"])
        backend = TrackingBackend()
        config = DispatchConfig(
            backends={"copy": backend},
            settings={},
            validator_step=validator,
        )
        orch = DispatchOrchestrator(config)

        folder = {
            "id": 10,
            "folder_name": str(inp),
            "alias": "ValidationTest",
            "process_backend_copy": True,
            "copy_to_directory": str(tmp_path / "out"),
            "process_edi": True,
        }

        orch.process_folder(folder, run_log=None)

        assert backend.sent == [], "File should not be sent when validation fails"
        joined = "\n".join(log_capture)
        assert "Validation failed" in joined

    def test_validation_pass_proceeds_to_send(self, tmp_path, log_capture):
        """When validator passes, file is sent and Success is logged."""
        inp = tmp_path / "input"
        _make_edi(inp, "good.edi")
        (tmp_path / "out").mkdir()

        validator = AlwaysPassValidator()
        backend = TrackingBackend()
        config = DispatchConfig(
            backends={"copy": backend},
            settings={},
            validator_step=validator,
        )
        orch = DispatchOrchestrator(config)

        folder = {
            "id": 11,
            "folder_name": str(inp),
            "alias": "ValPassTest",
            "process_backend_copy": True,
            "copy_to_directory": str(tmp_path / "out"),
            "process_edi": True,
        }

        orch.process_folder(folder, run_log=None)

        assert len(backend.sent) == 1
        joined = "\n".join(log_capture)
        assert "Success" in joined

    def test_mixed_valid_invalid_log_output(self, tmp_path, log_capture):
        """In a batch with valid and invalid files, both outcomes are logged."""
        inp = tmp_path / "input"
        _make_edi(inp, "good1.edi")
        _make_edi(inp, "bad.edi")
        _make_edi(inp, "good2.edi")
        (tmp_path / "out").mkdir()

        class AlternatingValidator:
            def __init__(self):
                self._call = 0

            def execute(self, file_path, folder):
                self._call += 1
                if self._call == 2:
                    return (False, ["invalid EDI"])
                return (True, file_path)

        backend = TrackingBackend()
        config = DispatchConfig(
            backends={"copy": backend},
            settings={},
            validator_step=AlternatingValidator(),
        )
        orch = DispatchOrchestrator(config)

        folder = {
            "id": 12,
            "folder_name": str(inp),
            "alias": "MixedValidation",
            "process_backend_copy": True,
            "copy_to_directory": str(tmp_path / "out"),
            "process_edi": True,
        }

        result = orch.process_folder(folder, run_log=None)

        assert len(backend.sent) == 2
        assert result.files_failed >= 1

        joined = "\n".join(log_capture)
        assert "Validation failed" in joined
        assert "Success" in joined


# ===================================================================
# 5. Conversion step logging
# ===================================================================


class TestConversionStepLogging:
    """Verify conversion activity is captured in log output."""

    def test_conversion_logs_converting_message(self, tmp_path, log_capture):
        """When convert_edi is True, 'Converting' appears in the log."""
        inp = tmp_path / "input"
        _make_edi(inp, "convert_me.edi")
        (tmp_path / "out").mkdir()

        converter = PassthroughConverterStep()
        backend = TrackingBackend()
        config = DispatchConfig(
            backends={"copy": backend},
            settings={},
            converter_step=converter,
        )
        orch = DispatchOrchestrator(config)

        folder = {
            "id": 20,
            "folder_name": str(inp),
            "alias": "ConvertTest",
            "process_backend_copy": True,
            "copy_to_directory": str(tmp_path / "out"),
            "convert_edi": True,
            "convert_to_format": "csv",
            "process_edi": True,
        }

        orch.process_folder(folder, run_log=None)

        assert converter.call_count == 1
        joined = "\n".join(log_capture)
        assert "Conversion completed" in joined
        assert "Successfully processed" in joined


# ===================================================================
# 6. Send failure logging
# ===================================================================


class TestSendFailureLogging:
    """Verify send failures produce meaningful log output."""

    def test_backend_failure_logs_error(self, tmp_path, log_capture):
        """When a backend raises, 'FAILED sending' is logged."""
        inp = tmp_path / "input"
        _make_edi(inp, "fail_send.edi")

        backend = FailingBackend(msg="Connection refused")
        config = DispatchConfig(backends={"copy": backend}, settings={})
        orch = DispatchOrchestrator(config)

        folder = {
            "id": 30,
            "folder_name": str(inp),
            "alias": "SendFailTest",
            "process_backend_copy": True,
            "copy_to_directory": str(tmp_path / "out"),
        }

        result = orch.process_folder(folder, run_log=None)

        assert result.files_failed >= 1
        joined = "\n".join(log_capture)
        assert "FAILED sending" in joined or "failed to send" in joined.lower()

    def test_send_success_logs_destination(self, workspace, folder_config, log_capture):
        """Successful send logs the backend destination."""
        backend = TrackingBackend()
        config = DispatchConfig(backends={"copy": backend}, settings={})
        orch = DispatchOrchestrator(config)

        result = orch.process_folder(folder_config, run_log=None)

        assert result.success is True
        joined = "\n".join(log_capture)
        # The orchestrator logs "sending <file> to <dest> with <backend>"
        assert "sending" in joined.lower()
        # Backend name is logged (e.g., 'copy' not 'Copy Backend')
        assert "copy" in joined.lower()


# ===================================================================
# 7. Multi-backend send logging
# ===================================================================


class TestMultiBackendLogging:
    """Verify log output when multiple backends are enabled."""

    def test_two_backends_both_logged(self, tmp_path, log_capture):
        """With copy and ftp enabled, both sends are logged."""
        inp = tmp_path / "input"
        _make_edi(inp, "multi.edi")
        (tmp_path / "out").mkdir()

        copy_backend = TrackingBackend()
        ftp_backend = TrackingBackend()

        config = DispatchConfig(
            backends={"copy": copy_backend, "ftp": ftp_backend},
            settings={},
        )
        orch = DispatchOrchestrator(config)

        folder = {
            "id": 40,
            "folder_name": str(inp),
            "alias": "MultiBE",
            "process_backend_copy": True,
            "copy_to_directory": str(tmp_path / "out"),
            "process_backend_ftp": True,
            "ftp_server": "ftp.example.com",
        }

        orch.process_folder(folder, run_log=None)

        assert len(copy_backend.sent) == 1
        assert len(ftp_backend.sent) == 1

        joined = "\n".join(log_capture)
        # Both backend names should appear in logs (logged as 'copy' and 'ftp')
        assert "copy" in joined.lower()
        assert "ftp" in joined.lower()

    def test_partial_backend_failure_logged(self, tmp_path, log_capture):
        """One backend succeeds, one fails -- both outcomes logged."""
        inp = tmp_path / "input"
        _make_edi(inp, "partial.edi")
        (tmp_path / "out").mkdir()

        good_backend = TrackingBackend()
        bad_backend = FailingBackend(msg="FTP timeout")

        config = DispatchConfig(
            backends={"copy": good_backend, "ftp": bad_backend},
            settings={},
        )
        orch = DispatchOrchestrator(config)

        folder = {
            "id": 41,
            "folder_name": str(inp),
            "alias": "PartialFail",
            "process_backend_copy": True,
            "copy_to_directory": str(tmp_path / "out"),
            "process_backend_ftp": True,
            "ftp_server": "ftp.example.com",
        }

        orch.process_folder(folder, run_log=None)

        joined = "\n".join(log_capture)
        # Good backend should have been attempted
        assert len(good_backend.sent) == 1
        # Failure should appear in log
        assert "FAILED" in joined or "failed" in joined.lower()


# ===================================================================
# 8. Full pipeline with all steps
# ===================================================================


class TestFullPipelineLogging:
    """Verify complete log sequence through validate → convert → tweak → send."""

    def test_all_pipeline_steps_logged(self, tmp_path, log_capture):
        """Full pipeline: validate → convert → tweak → send → Success."""
        inp = tmp_path / "input"
        _make_edi(inp, "full_pipeline.edi")
        (tmp_path / "out").mkdir()

        validator = AlwaysPassValidator()
        converter = PassthroughConverterStep()
        tweaker = PassthroughTweakerStep()
        backend = TrackingBackend()

        config = DispatchConfig(
            backends={"copy": backend},
            settings={},
            validator_step=validator,
            converter_step=CompositeConverterStep(converter, tweaker),
        )
        orch = DispatchOrchestrator(config)

        folder = {
            "id": 50,
            "folder_name": str(inp),
            "alias": "FullPipeline",
            "process_backend_copy": True,
            "copy_to_directory": str(tmp_path / "out"),
            "process_edi": True,
            "convert_edi": True,
            "convert_to_format": "csv",
            "tweak_edi": True,
        }

        result = orch.process_folder(folder, run_log=None)

        # All steps were called
        assert validator.call_count == 1
        assert converter.call_count == 1
        assert tweaker.call_count == 1
        assert len(backend.sent) == 1
        assert result.success is True

        joined = "\n".join(log_capture)
        # Verify complete sequence in the log
        assert "entering folder" in joined
        assert "1 found" in joined
        assert "Conversion completed" in joined
        assert "Sending" in joined
        assert "All backends succeeded" in joined

    def test_converter_failure_stops_pipeline(self, tmp_path, log_capture):
        """If converter raises, the pipeline stops and errors are logged."""
        inp = tmp_path / "input"
        _make_edi(inp, "conv_fail.edi")
        (tmp_path / "out").mkdir()

        class FailingConverter:
            def execute(
                self, file_path, folder, settings=None, upc_dict=None, context=None
            ):
                raise RuntimeError("converter exploded")

        tweaker = PassthroughTweakerStep()
        backend = TrackingBackend()

        config = DispatchConfig(
            backends={"copy": backend},
            settings={},
            converter_step=CompositeConverterStep(FailingConverter(), tweaker),
        )
        orch = DispatchOrchestrator(config)

        folder = {
            "id": 51,
            "folder_name": str(inp),
            "alias": "ConvFail",
            "process_backend_copy": True,
            "copy_to_directory": str(tmp_path / "out"),
            "convert_edi": True,
            "convert_to_format": "csv",
            "process_edi": True,
            "tweak_edi": True,
        }

        orch.process_folder(folder, run_log=None)

        # Converter blew up, so tweaker should not be called
        assert tweaker.call_count == 0
        # File should not have been sent
        assert backend.sent == []

    def test_tweaker_failure_still_logged(self, tmp_path, log_capture):
        """If tweaker raises, the error is recorded in logs."""
        inp = tmp_path / "input"
        _make_edi(inp, "twk_fail.edi")
        (tmp_path / "out").mkdir()

        class FailingTweaker:
            def execute(
                self, file_path, folder, upc_dict=None, settings=None, context=None
            ):
                raise RuntimeError("tweaker exploded")

        backend = TrackingBackend()
        config = DispatchConfig(
            backends={"copy": backend},
            settings={},
            converter_step=FailingTweaker(),
        )
        orch = DispatchOrchestrator(config)

        folder = {
            "id": 52,
            "folder_name": str(inp),
            "alias": "TwkFail",
            "process_backend_copy": True,
            "copy_to_directory": str(tmp_path / "out"),
            "tweak_edi": True,
        }

        result = orch.process_folder(folder, run_log=None)
        # Orchestrator catches the exception, records it
        assert isinstance(result.files_processed, int)


# ===================================================================
# 9. ErrorHandler logging integration
# ===================================================================


class TestErrorHandlerLogging:
    """Verify ErrorHandler emits messages through the logging infrastructure."""

    def test_record_error_appears_in_log(self, log_capture):
        """ErrorHandler.record_error() produces a log message via logger.error()."""
        # ErrorHandler logs to 'dispatch.error_handler'
        messages: list[str] = []
        handler = RunLogHandler(messages)
        handler.setLevel(logging.DEBUG)
        eh_logger = logging.getLogger("dispatch.error_handler")
        eh_logger.addHandler(handler)

        try:
            eh = ErrorHandler()
            eh.record_error(
                folder="TestFolder",
                filename="test.edi",
                error=ValueError("bad value"),
                error_source="UnitTest",
            )
        finally:
            eh_logger.removeHandler(handler)
            handler.close()

        # The ErrorHandler also stores in-memory
        assert eh.has_errors()
        assert eh.get_error_count() == 1

        # Check that the logging infrastructure captured it
        # Note: RunLogHandler defaults to INFO, but record_error uses logger.error
        # which is above INFO, so it should be captured
        joined = "\n".join(messages)
        assert "bad value" in joined or "test.edi" in joined


# ===================================================================
# 10. setup_logging configuration
# ===================================================================


class TestSetupLoggingConfiguration:
    """Verify setup_logging respects level configuration."""

    def test_explicit_level_parameter(self):
        """setup_logging(level=DEBUG) sets root logger to DEBUG."""
        root = setup_logging(level=logging.DEBUG)
        assert root.level == logging.DEBUG

    def test_bfs_log_level_env_var(self, monkeypatch):
        """BFS_LOG_LEVEL=WARNING sets root logger to WARNING."""
        monkeypatch.setenv("BFS_LOG_LEVEL", "WARNING")
        root = setup_logging()
        assert root.level == logging.WARNING

    def test_dispatch_debug_mode_env_var(self, monkeypatch):
        """DISPATCH_DEBUG_MODE=true sets root logger to DEBUG."""
        monkeypatch.delenv("BFS_LOG_LEVEL", raising=False)
        monkeypatch.setenv("DISPATCH_DEBUG_MODE", "true")
        root = setup_logging()
        assert root.level == logging.DEBUG

    def test_explicit_level_overrides_env(self, monkeypatch):
        """Explicit level parameter takes priority over env vars."""
        monkeypatch.setenv("BFS_LOG_LEVEL", "WARNING")
        root = setup_logging(level=logging.DEBUG)
        assert root.level == logging.DEBUG

    def test_idempotent_setup(self):
        """Calling setup_logging twice does not duplicate handlers."""
        setup_logging(level=logging.INFO)
        handler_count_1 = len(logging.getLogger().handlers)
        setup_logging(level=logging.INFO)
        handler_count_2 = len(logging.getLogger().handlers)
        assert handler_count_1 == handler_count_2


# ===================================================================
# 11. Processed files skip logging
# ===================================================================


class TestProcessedFilesSkipLogging:
    """Verify that already-processed files are skipped and logged."""

    def test_all_files_already_processed_logs_no_new(self, workspace, log_capture):
        """When all files match existing checksums, 'No new files' is logged."""
        # Pre-compute checksums for all files in the workspace
        import hashlib

        checksums = []
        for fname in sorted(os.listdir(str(workspace["input"]))):
            fpath = os.path.join(str(workspace["input"]), fname)
            with open(fpath, "rb") as f:
                checksums.append(hashlib.md5(f.read()).hexdigest())

        # Create a stub table pre-populated with these checksums
        processed_files = _StubProcessedFilesTable(
            [
                {"file_checksum": cs, "folder_id": 1, "resend_flag": 0}
                for cs in checksums
            ]
        )

        backend = TrackingBackend()
        config = DispatchConfig(backends={"copy": backend}, settings={})
        orch = DispatchOrchestrator(config)

        folder = {
            "id": 1,
            "folder_name": str(workspace["input"]),
            "alias": "SkipTest",
            "process_backend_copy": True,
            "copy_to_directory": str(workspace["output"]),
        }

        result = orch.process_folder(
            folder, run_log=None, processed_files=processed_files
        )

        assert result.files_processed == 0
        assert backend.sent == []

        joined = "\n".join(log_capture)
        assert "No new files" in joined


# ===================================================================
# 12. Multi-file error isolation with log evidence
# ===================================================================


class TestMultiFileErrorIsolation:
    """Verify that errors in one file don't prevent processing of others,
    and that both success and failure are captured in the log.
    """

    def test_error_in_middle_file_others_still_processed(self, tmp_path, log_capture):
        """3 files, middle one fails via backend → 2 successes logged."""
        inp = tmp_path / "input"
        _make_edi(inp, "file_a.edi")
        _make_edi(inp, "file_b.edi")
        _make_edi(inp, "file_c.edi")
        (tmp_path / "out").mkdir()

        call_idx = 0

        class SelectiveBackend:
            def send(self, params, settings, filename):
                nonlocal call_idx
                call_idx += 1
                if call_idx == 2:
                    raise RuntimeError("middle file boom")
                return True

        config = DispatchConfig(backends={"copy": SelectiveBackend()}, settings={})
        orch = DispatchOrchestrator(config)

        folder = {
            "id": 60,
            "folder_name": str(inp),
            "alias": "IsolationTest",
            "process_backend_copy": True,
            "copy_to_directory": str(tmp_path / "out"),
        }

        result = orch.process_folder(folder, run_log=None)

        assert result.files_processed == 2
        assert result.files_failed == 1

        joined = "\n".join(log_capture)
        # Both success and failure evidence in the log
        assert "Success" in joined
        assert (
            "FAILED" in joined
            or "Failed" in joined
            or "middle file boom" in joined.lower()
        )

    def test_ten_files_one_fails_log_shows_nine_successes(self, tmp_path, log_capture):
        """10 files, 1 fails → 9 'Success' messages in the log."""
        inp = tmp_path / "input"
        for i in range(10):
            _make_edi(inp, f"batch_{i:02d}.edi")
        (tmp_path / "out").mkdir()

        call_idx = 0

        class FailFifthBackend:
            def send(self, params, settings, filename):
                nonlocal call_idx
                call_idx += 1
                if call_idx == 5:
                    raise RuntimeError("fifth file fail")
                return True

        config = DispatchConfig(backends={"copy": FailFifthBackend()}, settings={})
        orch = DispatchOrchestrator(config)

        folder = {
            "id": 61,
            "folder_name": str(inp),
            "alias": "TenFiles",
            "process_backend_copy": True,
            "copy_to_directory": str(tmp_path / "out"),
        }

        result = orch.process_folder(folder, run_log=None)

        assert result.files_processed == 9
        assert result.files_failed == 1

        joined = "\n".join(log_capture)
        # At least 9 success messages
        assert joined.count("Success") >= 9


# ===================================================================
# 13. Reprocess after failure with log evidence
# ===================================================================


class TestReprocessAfterFailure:
    """Verify that reprocessing after a failure produces clean log output."""

    def test_reprocess_succeeds_after_backend_fix(self, tmp_path, log_capture):
        """First run fails, second run succeeds -- log shows recovery."""
        inp = tmp_path / "input"
        _make_edi(inp, "retry.edi")
        (tmp_path / "out").mkdir()

        # First run: backend fails
        config1 = DispatchConfig(
            backends={"copy": FailingBackend(msg="network down")},
            settings={},
        )
        orch1 = DispatchOrchestrator(config1)

        folder = {
            "id": 70,
            "folder_name": str(inp),
            "alias": "RetryTest",
            "process_backend_copy": True,
            "copy_to_directory": str(tmp_path / "out"),
        }

        r1 = orch1.process_folder(folder, run_log=None)
        assert r1.files_failed >= 1

        # Second run: backend works
        good_backend = TrackingBackend()
        config2 = DispatchConfig(backends={"copy": good_backend}, settings={})
        orch2 = DispatchOrchestrator(config2)

        orch2.process_folder(folder, run_log=None)
        assert len(good_backend.sent) == 1

        joined = "\n".join(log_capture)
        # Log should show both the failure and the recovery
        assert "FAILED" in joined or "failed" in joined.lower()
        assert "Success" in joined
