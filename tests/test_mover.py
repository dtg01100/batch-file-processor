import pytest
import mover

@pytest.mark.timeout(5)
def test_mover_missing_file(tmp_path):
    with pytest.raises(Exception):
        mover.move(str(tmp_path / "nofile.txt"), str(tmp_path / "dest.txt"))
