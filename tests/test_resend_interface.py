import pytest
import resend_interface

@pytest.mark.timeout(5)
def test_resend_interface_invalid():
    with pytest.raises(Exception):
        resend_interface.resend(None)
