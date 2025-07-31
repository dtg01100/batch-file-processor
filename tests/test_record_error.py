import pytest
import record_error

def test_record_error_invalid():
    with pytest.raises(Exception):
        record_error.record(None)
