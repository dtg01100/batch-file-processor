import os
import tempfile
import shutil
from datetime import datetime
import pytest
import utils

def test_dac_str_int_to_int():
    assert utils.dac_str_int_to_int("") == 0
    assert utils.dac_str_int_to_int("  ") == 0
    assert utils.dac_str_int_to_int("123") == 123
    assert utils.dac_str_int_to_int("-123") == -123

def test_convert_to_price():
    assert utils.convert_to_price("000123") == "1.23"
    assert utils.convert_to_price("123456") == "1234.56"
    assert utils.convert_to_price("000000") == "0.00"

def test_dactime_from_datetime():
    dt = datetime(2024, 6, 1)
    result = utils.dactime_from_datetime(dt)
    assert result.startswith("1") and result.endswith("601")

def test_datetime_from_dactime():
    dt = utils.datetime_from_dactime(240601)
    assert isinstance(dt, datetime)
    assert dt.month == 6 and dt.day == 1

def test_datetime_from_invtime():
    dt = utils.datetime_from_invtime("060124")
    assert dt.month == 6 and dt.day == 1 and dt.year == 2024

def test_dactime_from_invtime():
    dactime = utils.dactime_from_invtime("060124")
    assert isinstance(dactime, str)
    assert dactime.startswith("1")

def test_capture_records_A():
    line = "A12345678901234506012400000012345"
    fields = utils.capture_records(line)
    assert fields["record_type"] == "A"
    assert fields["cust_vendor"] == "123456"
    assert fields["invoice_number"] == "7890123450"
    assert fields["invoice_date"] == "601240"
    assert fields["invoice_total"] == "0000012345"

def test_capture_records_B():
    line = "B12345678901Description here         VENDIT01234567890123456789012345"
    fields = utils.capture_records(line)
    assert fields["record_type"] == "B"
    assert "upc_number" in fields

def test_capture_records_C():
    line = "C001Description of charge      000012345"
    fields = utils.capture_records(line)
    assert fields["record_type"] == "C"
    assert "charge_type" in fields

def test_capture_records_invalid():
    with pytest.raises(Exception):
        utils.capture_records("Xsomething")

def test_calc_check_digit():
    assert utils.calc_check_digit("03600029145") == 2
    assert utils.calc_check_digit("04210000526") == 4

def test_convert_UPCE_to_UPCA():
    assert utils.convert_UPCE_to_UPCA("04182635") == "041800000265"
    assert utils.convert_UPCE_to_UPCA("1234567") is not False
    assert utils.convert_UPCE_to_UPCA("12345678") is not False
    assert utils.convert_UPCE_to_UPCA("123") is False

def test_do_split_edi_and_clear_old_files(tmp_path):
    edi_content = (
        "A1234567890123450601240000001234\n"
        "B12345678901Description here         VENDIT01234567890123456789012345\n"
        "A6543210987654320601240000005678\n"
        "B98765432109Another description     VENDIT01234567890123456789012345\n"
    )
    edi_file = tmp_path / "test.edi"
    with open(edi_file, "w", encoding="utf-8") as f:
        f.write(edi_content)
    params = {"prepend_date_files": False}
    result = utils.do_split_edi(str(edi_file), str(tmp_path), params)
    assert len(result) == 2
    for file_path, _, _ in result:
        assert os.path.exists(file_path)
    # Test do_clear_old_files
    utils.do_clear_old_files(str(tmp_path), 1)
    assert len(os.listdir(tmp_path)) == 1

def test_detect_invoice_is_credit(tmp_path):
    edi_content = "A1234567890123450601240-0000001234\n"
    edi_file = tmp_path / "credit.edi"
    with open(edi_file, "w", encoding="utf-8") as f:
        f.write(edi_content)
    assert utils.detect_invoice_is_credit(str(edi_file)) is True

    edi_content = "A12345678901234506012400000012345\n"
    edi_file = tmp_path / "invoice.edi"
    with open(edi_file, "w", encoding="utf-8") as f:
        f.write(edi_content)
    assert utils.detect_invoice_is_credit(str(edi_file)) is False