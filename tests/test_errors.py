from business_logic.errors import format_exception


def test_format_exception_contains_type_and_message():
    try:
        raise ValueError("sample failure")
    except ValueError as exc:
        out = format_exception(exc)
    assert "ValueError" in out
    assert "sample failure" in out