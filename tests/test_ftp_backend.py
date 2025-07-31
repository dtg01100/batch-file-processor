import pytest
import ftp_backend

def test_ftp_backend_invalid_host():
    with pytest.raises(Exception):
        ftp_backend.send_file("nofile.txt", "badhost", 21, "user", "pass", "dest")
