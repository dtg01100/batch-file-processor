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
    # Simulate file open error and patch time.sleep to avoid delay
    monkeypatch.setattr('time.sleep', lambda x: None)
    print("About to call report_edi_issues with nonexistent file...")
    # Patch open to always raise FileNotFoundError
    monkeypatch.setattr("builtins.open", lambda *a, **kw: (_ for _ in ()).throw(FileNotFoundError("mocked error")))
    with pytest.raises(FileNotFoundError):
        mtc_edi_validator.report_edi_issues("/nonexistent/file.edi")
