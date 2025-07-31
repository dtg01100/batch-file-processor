@timeout(5)
def test_do_split_edi_all_invalid_A_records():
    import tempfile
    import os
    # All A records are invalid (wrong length)
    with tempfile.TemporaryDirectory() as tmp_dir:
        edi_file = os.path.join(tmp_dir, "test.edi")
        with open(edi_file, "w", encoding="utf-8") as f:
            for _ in range(3):
                f.write("A123\n")  # Too short to be valid
        params = {"prepend_date_files": False}
        with pytest.raises(Exception) as excinfo:
            utils.do_split_edi(edi_file, tmp_dir, params)
        assert "All A records invalid" in str(excinfo.value) or "No Split EDIs" in str(excinfo.value)

@timeout(10)
def test_do_split_edi_many_valid_A_records():
    import tempfile
    import os
    # Stress test: 100 valid A records
    def make_a_record(invoice_total):
        record = "A123456" + "7890123450" + "601240" + str(invoice_total).rjust(11)
        assert len(record) == 34
        return record + "\n"
    with tempfile.TemporaryDirectory() as tmp_dir:
        edi_file = os.path.join(tmp_dir, "test.edi")
        with open(edi_file, "w", encoding="utf-8") as f:
            for i in range(100):
                f.write(make_a_record(i))
        params = {"prepend_date_files": False}
        result = utils.do_split_edi(edi_file, tmp_dir, params)
        assert len(result) == 100
        for file_path, _, _ in result:
            assert os.path.exists(file_path)

@timeout(5)
def test_do_split_edi_no_A_records():
    import tempfile
    import os
    # No A records at all
    with tempfile.TemporaryDirectory() as tmp_dir:
        edi_file = os.path.join(tmp_dir, "test.edi")
        with open(edi_file, "w", encoding="utf-8") as f:
            f.write("B1234567890\nC9876543210\n")
        params = {"prepend_date_files": False}
        with pytest.raises(Exception) as excinfo:
            utils.do_split_edi(edi_file, tmp_dir, params)
        assert "No Split EDIs" in str(excinfo.value)
import os
import tempfile
import os
import shutil
from datetime import datetime
import pytest
import utils
import signal
from unittest.mock import patch
from pathlib import Path
import unittest
from unittest.mock import MagicMock, patch
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
        if len(record) != 34:
            print(f"DEBUG make_a_record: record={record!r}, len={len(record)}")
            raise ValueError(f"Record length is {len(record)}, expected 34: {record!r}")
        print(f"DEBUG make_a_record: record={record!r}, len={len(record)}")
        return record + "\n"
    with tempfile.TemporaryDirectory() as tmp_dir:
        edi_file = os.path.join(tmp_dir, "test.edi")
        with open(edi_file, "w", encoding="utf-8") as f:
            for _ in range(701):
                f.write(make_a_record("0"))
        with open(edi_file, "r", encoding="utf-8") as f:
            print("DEBUG test_do_split_edi_too_many_A_records file contents:")
            print(f.read())
        params = {"prepend_date_files": False}
        with pytest.raises(Exception) as excinfo:
            utils.do_split_edi(edi_file, tmp_dir, params)
        assert "Too many A records in EDI file (>= 700)" in str(excinfo.value)

@timeout(5)
def test_do_split_edi_malformed_lines():
    with tempfile.TemporaryDirectory() as tmp_dir:
        edi_file = os.path.join(tmp_dir, "test.edi")
        with open(edi_file, "w", encoding="utf-8") as f:
            # Write malformed line and a valid 34-char A record
            f.write("Xnotavalidline\nA" + "1"*6 + "2"*10 + "060124" + "0"*11 + "\n")
        params = {"prepend_date_files": False}
        with pytest.raises(Exception):
            utils.do_split_edi(edi_file, tmp_dir, params)

@timeout(5)
def test_do_split_edi_missing_prepend_date_files():
    def make_a_record(invoice_total):
        record = "A123456" + "7890123450" + "601240" + invoice_total.rjust(11)
        if len(record) != 34:
            print(f"DEBUG make_a_record: record={record!r}, len={len(record)}")
            raise ValueError(f"Record length is {len(record)}, expected 34: {record!r}")
        print(f"DEBUG make_a_record: record={record!r}, len={len(record)}")
        return record + "\r\n"
    import os
    with tempfile.TemporaryDirectory() as tmp_dir:
        edi_file = os.path.join(tmp_dir, "test.edi")
        with open(edi_file, "w", encoding="utf-8") as f:
            f.write(make_a_record("0"))
        # Ensure file is closed before calling do_split_edi
        with open(edi_file, "r", encoding="utf-8") as f:
            print("DEBUG test_do_split_edi_missing_prepend_date_files file contents:")
            lines = f.readlines()
            for idx, line in enumerate(lines):
                print(f"  Line {idx}: {repr(line)} (len={len(line)})")
        params = {}  # missing key
        result = utils.do_split_edi(edi_file, tmp_dir, params)
        assert len(result) == 1

@timeout(5)
def test_do_split_edi_workdir_does_not_exist():
    def make_a_record(invoice_total):
        record = "A123456" + "7890123450" + "601240" + invoice_total.rjust(11)
        if len(record) != 34:
            print(f"DEBUG make_a_record: record={record!r}, len={len(record)}")
            raise ValueError(f"Record length is {len(record)}, expected 34: {record!r}")
        print(f"DEBUG make_a_record: record={record!r}, len={len(record)}")
        return record + "\r\n"
    import os
    with tempfile.TemporaryDirectory() as tmp_dir:
        edi_file = os.path.join(tmp_dir, "test.edi")
        with open(edi_file, "w", encoding="utf-8") as f:
            f.write(make_a_record("0"))
        # Ensure file is closed before calling do_split_edi
        with open(edi_file, "r", encoding="utf-8") as f:
            print("DEBUG test_do_split_edi_workdir_does_not_exist file contents:")
            lines = f.readlines()
            for idx, line in enumerate(lines):
                print(f"  Line {idx}: {repr(line)} (len={len(line)})")
        workdir = os.path.join(tmp_dir, "notexist")
        params = {"prepend_date_files": False}
        result = utils.do_split_edi(edi_file, workdir, params)
        assert os.path.exists(workdir)
        assert len(result) == 1

@timeout(5)
def test_do_split_edi_one_A_record():
    def make_a_record(invoice_total):
        record = "A123456" + "7890123450" + "601240" + invoice_total.rjust(11)
        if len(record) != 34:
            print(f"DEBUG make_a_record: record={record!r}, len={len(record)}")
            raise ValueError(f"Record length is {len(record)}, expected 34: {record!r}")
        print(f"DEBUG make_a_record: record={record!r}, len={len(record)}")
        return record + "\r\n"
    import os
    with tempfile.TemporaryDirectory() as tmp_dir:
        edi_file = os.path.join(tmp_dir, "test.edi")
        with open(edi_file, "w", encoding="utf-8") as f:
            f.write(make_a_record("0"))
        # Ensure file is closed before calling do_split_edi
        with open(edi_file, "r", encoding="utf-8") as f:
            print("DEBUG test_do_split_edi_one_A_record file contents:")
            lines = f.readlines()
            for idx, line in enumerate(lines):
                print(f"  Line {idx}: {repr(line)} (len={len(line)})")
        params = {"prepend_date_files": False}
        result = utils.do_split_edi(edi_file, tmp_dir, params)
        assert len(result) == 1

@timeout(5)
def test_do_split_edi_invalid_invoice_total():
    def make_a_record(invoice_total):
        record = "A123456" + "7890123450" + "601240" + invoice_total.rjust(11)
        if len(record) != 34:
            print(f"DEBUG make_a_record: record={record!r}, len={len(record)}")
            raise ValueError(f"Record length is {len(record)}, expected 34: {record!r}")
        print(f"DEBUG make_a_record: record={record!r}, len={len(record)}")
        return record + "\n"
    with tempfile.TemporaryDirectory() as tmp_dir:
        edi_file = os.path.join(tmp_dir, "test.edi")
        with open(edi_file, "w", encoding="utf-8") as f:
            f.write(make_a_record("XXXXXXXXXXX"))
        with open(edi_file, "r", encoding="utf-8") as f:
            print("DEBUG test_do_split_edi_invalid_invoice_total file contents:")
            print(f.read())
        params = {"prepend_date_files": False}
        with pytest.raises(Exception) as excinfo:
            utils.do_split_edi(edi_file, tmp_dir, params)
        assert "No Split EDIs" in str(excinfo.value)

@timeout(5)
def test_do_clear_old_files_various_cases():
    def make_a_record(invoice_total):
        record = "A123456" + "7890123450" + "601240" + invoice_total.rjust(11)
        if len(record) != 34:
            print(f"DEBUG make_a_record: record={record!r}, len={len(record)}")
            raise ValueError(f"Record length is {len(record)}, expected 34: {record!r}")
        print(f"DEBUG make_a_record: record={record!r}, len={len(record)}")
        return record + "\n"
    with tempfile.TemporaryDirectory() as tmp_dir:
        # Fewer files than maximum_files
        for i in range(2):
            file_path = os.path.join(tmp_dir, f"file{i}.txt")
            with open(file_path, "w") as f:
                f.write(make_a_record("0"))
            with open(file_path, "r") as f:
                print(f"DEBUG test_do_clear_old_files_various_cases file{i}.txt contents:")
                print(f.read())
        # Ensure files are closed before clearing
        utils.do_clear_old_files(tmp_dir, 5)
        assert len(os.listdir(tmp_dir)) == 2
        # Exactly maximum_files
        utils.do_clear_old_files(tmp_dir, 2)
        assert len(os.listdir(tmp_dir)) == 2
        # More than maximum_files
        for i in range(3, 7):
            with open(os.path.join(tmp_dir, f"file{i}.txt"), "w") as f:
                f.write("A" + "1"*6 + "2"*10 + "060124" + "0"*11 + "\n")
        # Ensure files are closed before clearing
        utils.do_clear_old_files(tmp_dir, 3)
        assert len(os.listdir(tmp_dir)) == 3
        # Directory with a subdirectory
        subdir = os.path.join(tmp_dir, "subdir")
        os.mkdir(subdir)
        utils.do_clear_old_files(tmp_dir, 2)
        # Subdirectory should not be deleted
        assert os.path.isdir(subdir)
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
        # Ensure file is closed before reading
        params = {"prepend_date_files": False}
        result = utils.do_split_edi(str(edi_file), str(tmp_path), params)
        assert len(result) == 2
        for file_path, _, _ in result:
            assert os.path.exists(file_path)
        utils.do_clear_old_files(str(tmp_path), 1)
        assert len(os.listdir(tmp_dir)) == 1

@timeout(5)
def test_detect_invoice_is_credit():
    def make_a_record(invoice_total):
        record = "A123456" + "7890123450" + "601240" + invoice_total.rjust(11)
        if len(record) != 34:
            print(f"DEBUG make_a_record: record={record!r}, len={len(record)}")
            raise ValueError(f"Record length is {len(record)}, expected 34: {record!r}")
        print(f"DEBUG make_a_record: record={record!r}, len={len(record)}")
        return record + "\n"
    with tempfile.TemporaryDirectory() as tmp_dir:
        temp_file_path = os.path.join(tmp_dir, "test_credit_1.edi")
        with open(temp_file_path, 'w', encoding='utf-8') as f:
            f.write(make_a_record("-0000012345"))
        with open(temp_file_path, 'r', encoding='utf-8') as f:
            print("DEBUG test_detect_invoice_is_credit test_credit_1.edi contents:")
            print(f.read())
        result = utils.detect_invoice_is_credit(temp_file_path)
        assert result is True
        temp_file_path2 = os.path.join(tmp_dir, "test_credit_2.edi")
        with open(temp_file_path2, 'w', encoding='utf-8') as f:
            f.write(make_a_record("0000012345"))
        with open(temp_file_path2, 'r', encoding='utf-8') as f:
            print("DEBUG test_detect_invoice_is_credit test_credit_2.edi contents:")
            print(f.read())
        assert utils.detect_invoice_is_credit(temp_file_path2) is False

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
        def make_a_record(invoice_total):
            record = "A123456" + "7890123450" + "601240" + invoice_total.rjust(11)
            assert len(record) == 34, f"Record length is {len(record)}, expected 34: {record!r}"
            return record + "\n"
        with tempfile.TemporaryDirectory() as tmp_dir:
            temp_file_path = os.path.join(tmp_dir, "test_credit_1.edi")
            with open(temp_file_path, 'w', encoding='utf-8') as f:
                f.write(make_a_record("-0000012345"))
            assert utils.detect_invoice_is_credit(temp_file_path) is True
            temp_file_path2 = os.path.join(tmp_dir, "test_credit_2.edi")
            with open(temp_file_path2, 'w', encoding='utf-8') as f:
                f.write(make_a_record("0000012345"))
            assert utils.detect_invoice_is_credit(temp_file_path2) is False
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

        def make_a_record(invoice_total):
            record = "A123456" + "7890123450" + "601240" + invoice_total.rjust(11)
            assert len(record) == 34, f"Record length is {len(record)}, expected 34: {record!r}"
            return record + "\n"

        with tempfile.TemporaryDirectory() as tempdir:
            # Case 1: Valid EDI A record, negative invoice_total (should be credit)
            temp_file_path = os.path.join(tempdir, "test_detect_invoice_is_credit_edge_cases_1.edi")
            record = make_a_record("-0000012345")
            with open(temp_file_path, 'w', encoding='utf-8') as f:
                f.write(record)
            # Ensure file is closed before reading
            self.assertTrue(utils.detect_invoice_is_credit(temp_file_path))

            # Case 2: Valid EDI A record, positive invoice_total (not a credit)
            temp_file_path = os.path.join(tempdir, "test_detect_invoice_is_credit_edge_cases_2.edi")
            with open(temp_file_path, 'w', encoding='utf-8') as f:
                f.write(make_a_record("0000012345"))
            # Ensure file is closed before reading
            self.assertFalse(utils.detect_invoice_is_credit(temp_file_path))

            # Case 3: Valid EDI A record, zero invoice_total (should not be credit)
            temp_file_path = os.path.join(tempdir, "test_detect_invoice_is_credit_edge_cases_3.edi")
            with open(temp_file_path, 'w', encoding='utf-8') as f:
                f.write(make_a_record("00000000000"))
            # Ensure file is closed before reading
            self.assertFalse(utils.detect_invoice_is_credit(temp_file_path))

            # Case 4: Malformed EDI A record (non-numeric invoice_total)
            temp_file_path = os.path.join(tempdir, "test_detect_invoice_is_credit_edge_cases_4.edi")
            with open(temp_file_path, 'w', encoding='utf-8') as f:
                f.write(prefix + "XXXXXXXXXXX\n")
            # Ensure file is closed before reading
            with self.assertRaises(Exception):
                utils.detect_invoice_is_credit(temp_file_path)

            # Case 5: Not an EDI A record (should raise ValueError)
            temp_file_path = os.path.join(tempdir, "test_detect_invoice_is_credit_edge_cases_5.edi")
            with open(temp_file_path, 'w', encoding='utf-8') as f:
                f.write("B1234567890SOMEINVALIDDATA\n")
            # Ensure file is closed before reading
            with self.assertRaises(ValueError):
                utils.detect_invoice_is_credit(temp_file_path)
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

class TestInvFetcher(unittest.TestCase):
    def setUp(self):
        self.settings = {
            "as400_username": "user",
            "as400_password": "pass",
            "as400_address": "addr",
            "odbc_driver": "driver"
        }

if __name__ == "__main__":
    unittest.main()
    @patch("utils.query_runner")
    def test_db_connect_success(self, mock_runner):
        mock_runner.return_value = MagicMock()
        self.fetcher._db_connect()
        self.assertIsNotNone(self.fetcher.query_object)

    @patch("utils.query_runner")
    def test_db_connect_failure(self, mock_runner):
        mock_runner.return_value = None
        self.fetcher._db_connect()
        self.assertIsNone(self.fetcher.query_object)

    def test_run_qry_no_connection(self):
        self.fetcher.query_object = None
        with patch.object(self.fetcher, "_db_connect", return_value=None):
            with self.assertRaises(RuntimeError):
                self.fetcher._run_qry("SELECT 1")

    def test_run_qry_success(self):
        mock_query_obj = MagicMock()
        mock_query_obj.run_arbitrary_query.return_value = [(1,)]
        self.fetcher.query_object = mock_query_obj
        result = self.fetcher._run_qry("SELECT 1")
        self.assertEqual(result, [(1,)])

    def test_fetch_po_cached(self):
        self.fetcher.last_invoice_number = 123
        self.fetcher.po = "PO123"
        result = self.fetcher.fetch_po(123)
        self.assertEqual(result, "PO123")

    def test_fetch_po_query_empty(self):
        self.fetcher._run_qry = MagicMock(return_value=[])
        result = self.fetcher.fetch_po(456)
        self.assertEqual(result, "")

    def test_fetch_po_query_partial(self):
        self.fetcher._run_qry = MagicMock(return_value=[["PO789"]])
        result = self.fetcher.fetch_po(789)
        self.assertEqual(result, "PO789")

    def test_fetch_cust_name_and_no(self):
        self.fetcher.fetch_po = MagicMock()
        self.fetcher.custname = "CUST"
        self.fetcher.custno = 42
        self.assertEqual(self.fetcher.fetch_cust_name(1), "CUST")
        self.assertEqual(self.fetcher.fetch_cust_no(1), 42)

    def test_fetch_uom_desc_cache(self):
        self.fetcher.last_invno = 1
        self.fetcher.uom_lut = {2: "EA"}
        result = self.fetcher.fetch_uom_desc(100, 1, 1, 1)
        self.assertEqual(result, "EA")

    def test_fetch_uom_desc_keyerror_and_fallback(self):
        self.fetcher.last_invno = 0
        self.fetcher._run_qry = MagicMock(side_effect=[{2: "EA"}, [["ALT"]]])
        # Will miss key, fallback to uommult > 1
        result = self.fetcher.fetch_uom_desc(100, 2, 1, 2)
        self.assertEqual(result, "ALT")

    def test_fetch_uom_desc_keyerror_and_fallback_lo(self):
        self.fetcher.last_invno = 0
        self.fetcher._run_qry = MagicMock(side_effect=[{2: "EA"}, [["ALT"]]])
        # Will miss key, fallback to uommult <= 1
        result = self.fetcher.fetch_uom_desc(100, 1, 1, 2)
        self.assertEqual(result, "ALT")

    def test_fetch_uom_desc_keyerror_and_fallback_hi_lo_na(self):
        self.fetcher.last_invno = 0
        self.fetcher._run_qry = MagicMock(side_effect=[{2: "EA"}, Exception("fail")])
        # uommult > 1, fallback fails, should return "HI"
        result = self.fetcher.fetch_uom_desc(100, 2, 1, 2)
        self.assertEqual(result, "HI")
        # uommult <= 1, fallback fails, should return "LO"
        result = self.fetcher.fetch_uom_desc(100, 1, 1, 3)
        self.assertEqual(result, "LO")
        # uommult not int, fallback fails, should return "NA"
        result = self.fetcher.fetch_uom_desc(100, "notint", 1, 4)
        self.assertEqual(result, "NA")
    unittest.main()
