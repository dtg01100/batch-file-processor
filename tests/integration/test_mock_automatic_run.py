"""Integration tests for mocked automatic run harness."""

from pathlib import Path

import pytest

from scripts.mock_automatic_run import run_mock_automatic

pytestmark = [pytest.mark.integration, pytest.mark.workflow]


def test_run_mock_automatic_creates_expected_artifacts(tmp_path: Path) -> None:
    result = run_mock_automatic(tmp_path)

    assert result.exit_code == 0
    assert result.config_dir.exists()
    assert result.database_path.exists()
    assert result.input_dir.exists()
    assert result.logs_dir.exists()
    assert len(result.run_log_files) >= 1

    run_log_text = result.run_log_files[0].read_text(encoding="utf-8")
    assert "[MOCK] dispatch.process called" in run_log_text
