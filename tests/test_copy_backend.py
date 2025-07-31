
import pytest
import copy_backend

@pytest.mark.timeout(5)
def test_copy_backend_missing_folder(tmp_path):
    with pytest.raises(Exception):
        copy_backend.copy(str(tmp_path / "nofolder"), str(tmp_path / "dest"))
