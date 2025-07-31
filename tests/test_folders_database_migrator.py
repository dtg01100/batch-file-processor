import pytest
import folders_database_migrator

@pytest.mark.timeout(5)
def test_upgrade_database_invalid(tmp_path):
    with pytest.raises(Exception):
        folders_database_migrator.upgrade_database(None, str(tmp_path / "bad"), "linux")
