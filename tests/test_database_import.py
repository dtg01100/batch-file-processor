
import pytest
import database_import

@pytest.mark.timeout(5)
def test_database_import_invalid_file(tmp_path):
    with pytest.raises(Exception):
        database_import.import_file(str(tmp_path / "nofile.csv"))
