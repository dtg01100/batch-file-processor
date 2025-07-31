
import pytest
import create_database

@pytest.mark.timeout(5)
def test_create_database_invalid_path(tmp_path):
    bad_dir = tmp_path / "nonexistent"
    bad_path = bad_dir / "db.sqlite"
    with pytest.raises(Exception):
        create_database.do("1", str(bad_path), "", "linux")
