# tests/unit/dispatch/services/test_folder_processor_correlation.py
from unittest.mock import MagicMock, patch

import pytest

from dispatch.services.folder_processor import FolderPipelineExecutor


class TestFolderProcessorCorrelation:
    def test_has_set_audit_logger_method(self):
        deps = MagicMock()
        executor = FolderPipelineExecutor(deps)
        audit_logger = MagicMock()
        executor.set_audit_logger(audit_logger)
        assert executor._audit_logger is audit_logger

    def test_stores_correlation_id_after_process_folder(self):
        deps = MagicMock()
        executor = FolderPipelineExecutor(deps)
        mock_result = MagicMock()
        mock_result.files_processed = 0
        mock_result.files_failed = 0
        mock_result.errors = []

        with patch.object(executor, "_folder_exists", return_value=True):
            with patch.object(executor, "_discover_and_filter_files", return_value=["/test/file.edi"]):
                with patch.object(executor, "_process_folder_files"):
                    with patch.object(executor, "_finalize_folder_result"):
                        executor.process_folder(
                            MagicMock(
                                folder={"folder_name": "/test", "alias": "Test", "id": 1},
                                run_log=MagicMock(),
                                processed_files=None,
                            )
                        )
        assert executor._correlation_id is not None
        assert len(executor._correlation_id) > 0

    def test_sets_correlation_id_in_context_var(self):
        deps = MagicMock()
        executor = FolderPipelineExecutor(deps)
        from core.structured_logging import get_correlation_id, set_correlation_id

        with patch.object(executor, "_folder_exists", return_value=True):
            with patch.object(executor, "_discover_and_filter_files", return_value=["/test/file.edi"]):
                with patch.object(executor, "_process_folder_files"):
                    with patch.object(executor, "_finalize_folder_result"):
                        executor.process_folder(
                            MagicMock(
                                folder={"folder_name": "/test", "alias": "Test", "id": 1},
                                run_log=MagicMock(),
                                processed_files=None,
                            )
                        )
        current = get_correlation_id()
        assert current == executor._correlation_id