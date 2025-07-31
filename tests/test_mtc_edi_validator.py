import os
import tempfile
import pytest
import mtc_edi_validator

def test_check_invalid_first_char(tmp_path):
    edi_file = tmp_path / "bad.edi"
    edi_file.write_text("Zbadline\n")
    result, line = mtc_edi_validator.check(str(edi_file))
    assert result is False

def test_check_wrong_length(tmp_path):
    edi_file = tmp_path / "badlen.edi"
    edi_file.write_text("Ashort\n")
    result, line = mtc_edi_validator.check(str(edi_file))
    assert result is False

def test_check_invalid_upc(tmp_path):
    edi_file = tmp_path / "badupc.edi"
    edi_file.write_text("Bbadupc     moredata\n")
    result, line = mtc_edi_validator.check(str(edi_file))
    assert result is False

def test_report_edi_issues_file_open_error(monkeypatch):
    # Simulate file open error
    with pytest.raises(Exception):
        mtc_edi_validator.report_edi_issues("/nonexistent/file.edi")
