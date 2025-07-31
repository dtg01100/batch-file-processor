import pytest
import database_import

def test_database_import_invalid_file(tmp_path):
    @pytest.mark.timeout(5)
    with pytest.raises(Exception):
        database_import.import_file(str(tmp_path / "nofile.csv"))
