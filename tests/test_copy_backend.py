import pytest
import copy_backend

def test_copy_backend_missing_folder(tmp_path):
    @pytest.mark.timeout(5)
    with pytest.raises(Exception):
        copy_backend.copy(str(tmp_path / "nofolder"), str(tmp_path / "dest"))
