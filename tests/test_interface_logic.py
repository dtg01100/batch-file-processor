import pytest
from business_logic import interface_logic


@pytest.mark.parametrize(
    "email,expected",
    [
        ("user@example.com", True),
        ("user.name+tag@sub.domain.co", True),
        ("invalid-email", False),
        ("user@localhost", False),
        ("", False),
    ],
)
def test_validate_email(email, expected):
    assert interface_logic.validate_email(email) is expected