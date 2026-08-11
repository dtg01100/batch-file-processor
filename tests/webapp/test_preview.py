"""Tests for the EDI preview module + endpoint."""

from __future__ import annotations

from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from webapp.main import create_app
from webapp.preview import preview_edi

pytestmark = [pytest.mark.integration]


def _write_edi(tmp_path: Path, name: str, body: str) -> Path:
    p = tmp_path / name
    p.write_text(body, encoding="utf-8")
    return p


def test_preview_classifies_records(tmp_path):
    p = _write_edi(
        tmp_path,
        "sample.edi",
        "A01header1\nB02line1\nB02line2\nC03charge1\nA01header2\nT99trailer\n",
    )
    result = preview_edi(p)
    summary = result["summary"]
    assert summary["total"] == 6
    assert summary["a"] == 2
    assert summary["b"] == 2
    assert summary["c"] == 1
    assert summary["trailer"] == 1
    assert summary["unknown"] == 0
    types = [line["type"] for line in result["lines"]]
    assert types == ["a", "b", "b", "c", "a", "trailer"]


def test_preview_skips_blank_lines(tmp_path):
    p = _write_edi(
        tmp_path,
        "blank.edi",
        "A01header\n\n\nB02line\n",
    )
    result = preview_edi(p)
    assert result["summary"]["total"] == 2
    assert [line["num"] for line in result["lines"]] == [1, 4]


def test_preview_unknown_record_type(tmp_path):
    p = _write_edi(tmp_path, "x.edi", "A01ok\nQ99unknown\n")
    result = preview_edi(p)
    assert result["summary"]["unknown"] == 1


def test_preview_404_on_missing_file(tmp_path):
    with pytest.raises(FileNotFoundError):
        preview_edi(tmp_path / "nope.edi")


def test_preview_truncates_long_lines(tmp_path):
    p = _write_edi(tmp_path, "long.edi", "A" + "x" * 500 + "\n")
    result = preview_edi(p)
    assert len(result["lines"][0]["raw"]) <= 200


def test_endpoint_returns_classification(tmp_path):
    p = _write_edi(
        tmp_path,
        "x.edi",
        "A01hdr\nB02line\nT99trl\n",
    )
    app = create_app(
        settings=_settings(tmp_path),
    )
    client = TestClient(app)
    with open(p, "rb") as fh:
        r = client.post(
            "/api/preview/edi",
            files={"file": ("x.edi", fh, "application/octet-stream")},
        )
    assert r.status_code == 200
    body = r.json()
    assert body["summary"]["a"] == 1
    assert body["summary"]["b"] == 1
    assert body["summary"]["trailer"] == 1


def _settings(tmp_path):
    from webapp.config import Settings

    return Settings(base_dir=tmp_path / "data", data_dir=tmp_path / "data" / "config")
