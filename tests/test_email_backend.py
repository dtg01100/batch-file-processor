import pytest
import email_backend

def test_email_backend_invalid_address():
    with pytest.raises(Exception):
        email_backend.send_email("notanemail", "user", "pass", "smtp", 25, "msg")
