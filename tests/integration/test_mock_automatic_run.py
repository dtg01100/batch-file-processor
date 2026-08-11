"""Integration tests for mocked automatic run harness (webapp runner)."""

from pathlib import Path

import pytest

from scripts.mock_automatic_run import run_mock_automatic

pytestmark = [pytest.mark.integration, pytest.mark.workflow]


def test_run_mock_automatic_creates_expected_artifacts(tmp_path: Path) -> None:
    result = run_mock_automatic(tmp_path)

    assert result.exit_code == 0
    assert result.base_dir.exists()
    assert result.database_path.exists()
    assert result.input_dir.exists()
    assert result.logs_dir.exists()

    # The copy backend should have delivered the sample files into output/.
    assert result.total_processed >= 1
    assert result.total_failed == 0

    output_dir = result.base_dir / "output"
    copied = sorted(p.name for p in output_dir.iterdir()) if output_dir.exists() else []
    assert len(copied) >= 1, f"expected copied files in {output_dir}, got {copied}"
