"""Stub for 1.47 ``mtc_edi_validator.py``.

Reports "valid" (no issues) unless a test installs a faulty validator via
``monkeypatch.setattr``. The validator is exercised in ``dispatch.py:140-149``
inside ``validate_file()``; routing tests do not need it to do anything
real — we want ``convert_to_*.edi_convert`` to be reached with a valid file.
"""


def report_edi_issues(input_file):  # noqa: ARG001
    """Return ``(stringio, False, False)`` -> no validator errors, file is valid."""
    from io import StringIO

    return StringIO(), False, False


__all__ = ["report_edi_issues"]
