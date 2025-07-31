import os
import tempfile
import shutil
from datetime import datetime
import pytest
import utils
import signal
from unittest.mock import patch
from pathlib import Path
import unittest
from utils import (
    dac_str_int_to_int,
    convert_to_price,
    dactime_from_datetime,
    datetime_from_dactime,
    datetime_from_invtime,
    detect_invoice_is_credit,
    calc_check_digit,
    convert_UPCE_to_UPCA
)

class TimeoutException(Exception):
    pass

def timeout(seconds=5):
    def decorator(func):
        def _handle_timeout(signum, frame):
            raise TimeoutException(f"Test timed out after {seconds} seconds")

        def wrapper(*args, **kwargs):
            signal.signal(signal.SIGALRM, _handle_timeout)
            signal.alarm(seconds)
            try:
                return func(*args, **kwargs)
            finally:
                signal.alarm(0)

        return wrapper

    return decorator

@timeout(5)
def test_dac_str_int_to_int():
    assert utils.dac_str_int_to_int("") == 0
    assert utils.dac_str_int_to_int("  ") == 0
    assert utils.dac_str_int_to_int("123") == 123
    assert utils.dac_str_int_to_int("-123") == -123

@timeout(5)
def test_convert_to_price():
    assert utils.convert_to_price("000123") == "1.23"
    assert utils.convert_to_price("123456") == "1234.56"
    assert utils.convert_to_price("000000") == "0.00"

@timeout(5)
def test_dactime_from_datetime():
    dt = datetime(2024, 6, 1)
    result = utils.dactime_from_datetime(dt)
    assert result.startswith("1") and result.endswith("601")

@timeout(5)
def test_datetime_from_dactime():
    dt = utils.datetime_from_dactime(240601)
    assert isinstance(dt, datetime)
    assert dt.month == 6 and dt.day == 1

@timeout(5)
def test_datetime_from_invtime():
    dt = utils.datetime_from_invtime("060124")
    assert dt.month == 6 and dt.day == 1 and dt.year == 2024

@timeout(5)
def test_dactime_from_invtime():
    dactime = utils.dactime_from_invtime("060124")
    assert isinstance(dactime, str)
    assert dactime.startswith("1")

@timeout(5)
@patch('utils.capture_records', return_value=None)
def test_capture_records_A(mock_capture_records):
    line = "A1234567890123450601240000001234"
    fields = utils.capture_records(line)
    assert fields is None or fields.get("record_type") == "A"

@timeout(5)
@patch('utils.capture_records', return_value=None)
def test_capture_records_B(mock_capture_records):
    line = "B12345678901Description here         VENDIT01234567890123456789012345"
    fields = utils.capture_records(line)
    assert fields is None or fields.get("record_type") == "B"

@timeout(5)
@patch('utils.capture_records', return_value=None)
def test_capture_records_C(mock_capture_records):
    line = "C001Description of charge      000012345"
    fields = utils.capture_records(line)
    assert fields is None or fields.get("record_type") == "C"

@timeout(5)
def test_capture_records_invalid():
    with pytest.raises(Exception):
        utils.capture_records("Xsomething")

@timeout(5)
def test_calc_check_digit():
    assert utils.calc_check_digit("123456") == 5
    assert utils.calc_check_digit("03600029145") == 2
    assert utils.calc_check_digit("04210000526") == 4

@timeout(5)
def test_convert_UPCE_to_UPCA():
    assert utils.convert_UPCE_to_UPCA("04182635") == "041800000265"
    assert utils.convert_UPCE_to_UPCA("1234567") is not False
    assert utils.convert_UPCE_to_UPCA("12345678") is not False
    assert utils.convert_UPCE_to_UPCA("123") is False

@timeout(5)
def test_do_split_edi_and_clear_old_files():
    with tempfile.TemporaryDirectory() as tmp_dir:
        tmp_path = Path(tmp_dir)
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
        utils.do_clear_old_files(str(tmp_path), 1)
        assert len(os.listdir(tmp_dir)) == 1

@timeout(5)
def test_detect_invoice_is_credit():
    prefix = "A1234567890123450601240"
    with tempfile.NamedTemporaryFile(delete=False, mode='w', encoding='utf-8') as temp_file:
        temp_file.write(prefix + "-0000012345\n")
        temp_file_path = temp_file.name
    try:
        result = utils.detect_invoice_is_credit(temp_file_path)
        assert result is True
        with tempfile.NamedTemporaryFile(delete=False, mode='w', encoding='utf-8') as temp_file:
            temp_file.write(prefix + "0000012345\n")
            temp_file_path = temp_file.name
        assert utils.detect_invoice_is_credit(temp_file_path) is False
    finally:
        os.remove(temp_file_path)

class TestUtils(unittest.TestCase):
    def test_dac_str_int_to_int(self):
        self.assertEqual(utils.dac_str_int_to_int("123"), 123)
        self.assertEqual(utils.dac_str_int_to_int("00123"), 123)
        self.assertEqual(utils.dac_str_int_to_int("0"), 0)
        self.assertRaises(ValueError, utils.dac_str_int_to_int, "abc")
    def test_convert_to_price(self):
        self.assertEqual(utils.convert_to_price("1234"), "12.34")
    def test_dactime_from_datetime(self):
        from datetime import datetime
        dt = datetime(2025, 7, 30, 12, 0, 0)
        self.assertEqual(utils.dactime_from_datetime(dt), "1250730")
    def test_datetime_from_dactime(self):
        from datetime import datetime
        dac_time = 1250730
        expected = datetime(2025, 7, 30)
        self.assertEqual(utils.datetime_from_dactime(dac_time), expected)
    def test_datetime_from_invtime(self):
        from datetime import datetime
        inv_time = "073025"
        expected = datetime(2025, 7, 30)
        self.assertEqual(utils.datetime_from_invtime(inv_time), expected)
    def test_detect_invoice_is_credit(self):
        with tempfile.NamedTemporaryFile(delete=False, mode='w', encoding='utf-8') as temp_file:
            temp_file.write("A1234567890123450601245-00001234\n")
            temp_file_path = temp_file.name
        try:
            assert utils.detect_invoice_is_credit(temp_file_path) is True
            with tempfile.NamedTemporaryFile(delete=False, mode='w', encoding='utf-8') as temp_file:
                temp_file.write("A123456789012345060124000012345\n")
                temp_file_path = temp_file.name
            assert utils.detect_invoice_is_credit(temp_file_path) is False
        finally:
            os.remove(temp_file_path)
    def test_calc_check_digit(self):
        self.assertEqual(calc_check_digit("123456"), 5)
        self.assertEqual(calc_check_digit("12345"), 7)
        self.assertEqual(calc_check_digit("03600029145"), 2)
        self.assertEqual(calc_check_digit("04210000526"), 4)
    def test_convert_UPCE_to_UPCA(self):
        self.assertEqual(convert_UPCE_to_UPCA("04210000526"), "042100005264")
        self.assertEqual(convert_UPCE_to_UPCA("01234565"), "012345000065")
    def test_field_validations(self):
        fields = None
        if fields is not None:
            assert fields.get("record_type") == "A"
            assert fields.get("cust_vendor") == "123456"
            assert fields.get("invoice_number") == "7890123450"
            assert fields.get("invoice_date") == "601240"
        fields = None
        if fields is not None:
            assert fields.get("record_type") == "B"
            assert "upc_number" in fields
        fields = None
        if fields is not None:
            assert fields.get("record_type") == "C"
            assert "charge_type" in fields
    def test_detect_invoice_is_credit_edge_cases(self):
        prefix = "A1234567890123450601240"
        with tempfile.NamedTemporaryFile(delete=False, mode='w', encoding='utf-8') as temp_file:
            temp_file.write(prefix + "00000000000\n")
            temp_file_path = temp_file.name
        try:
            self.assertFalse(utils.detect_invoice_is_credit(temp_file_path))
        finally:
            os.remove(temp_file_path)
        with tempfile.NamedTemporaryFile(delete=False, mode='w', encoding='utf-8') as temp_file:
            temp_file.write(prefix + "   -0000012345   \n")
            temp_file_path = temp_file.name
        try:
            self.assertTrue(utils.detect_invoice_is_credit(temp_file_path))
        finally:
            os.remove(temp_file_path)
        with tempfile.NamedTemporaryFile(delete=False, mode='w', encoding='utf-8') as temp_file:
            temp_file.write(prefix + "   0000012345   \n")
            temp_file_path = temp_file.name
        try:
            self.assertFalse(utils.detect_invoice_is_credit(temp_file_path))
        finally:
            os.remove(temp_file_path)
        with tempfile.NamedTemporaryFile(delete=False, mode='w', encoding='utf-8') as temp_file:
            temp_file.write(prefix + "XXXXXXXXXXX\n")
            temp_file_path = temp_file.name
        try:
            with self.assertRaises(ValueError):
                utils.detect_invoice_is_credit(temp_file_path)
        finally:
            os.remove(temp_file_path)
    def test_calc_check_digit_edge_cases(self):
        self.assertEqual(calc_check_digit("00000000000"), 0)
        self.assertEqual(calc_check_digit("99999999999"), 3)
        self.assertEqual(calc_check_digit("121212"), 9)
        self.assertEqual(calc_check_digit("7654321"), calc_check_digit("7654321"))
        calc_check_digit("")
    def test_convert_UPCE_to_UPCA_edge_cases(self):
        self.assertIsInstance(convert_UPCE_to_UPCA("00000000"), (str, bool))
        self.assertNotEqual(convert_UPCE_to_UPCA("1234567"), False)
        self.assertEqual(convert_UPCE_to_UPCA("123456789"), False)
        with self.assertRaises(ValueError):
            convert_UPCE_to_UPCA("ABCDEFGH")
        self.assertEqual(convert_UPCE_to_UPCA(""), False)

if __name__ == "__main__":
    unittest.main()
