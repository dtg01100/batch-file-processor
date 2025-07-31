import pytest
import print_run_log

def test_print_run_log_missing_file(tmp_path):
    with pytest.raises(Exception):
        print_run_log.print_log(str(tmp_path / "nofile.log"))
