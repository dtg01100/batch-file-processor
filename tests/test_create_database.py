import pytest
import create_database

def test_create_database_invalid_path(tmp_path):
    @pytest.mark.timeout(5)
    with pytest.raises(Exception):
        create_database.do("1", str(tmp_path / "nonexistent"), "", "linux")
