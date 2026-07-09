"""Property-based tests for core.edi.edi_splitter.

Targets the pure helpers `_ensure_crlf` and `_build_split_filename`.
The `EDISplitter` class itself is excluded (filesystem-bound).
"""

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from core.edi.edi_splitter import SplitConfig, _build_split_filename, _ensure_crlf

pytestmark = [pytest.mark.unit, pytest.mark.edi, pytest.mark.property]


@settings(max_examples=100)
@given(
    s=st.text(
        alphabet=st.characters(blacklist_categories=("Cs",), blacklist_characters="\r\n"),
        min_size=0,
        max_size=80,
    ),
)
def test_ensure_crlf_appends_crlf_to_unterminated_line(s: str) -> None:
    """Lines without any terminator get '\\r\\n' appended."""
    result = _ensure_crlf(s)
    assert result.endswith("\r\n")
    assert result == s + "\r\n"


@settings(max_examples=100)
@given(
    s=st.text(
        alphabet=st.characters(blacklist_categories=("Cs",)),
        min_size=0,
        max_size=80,
    ),
)
def test_ensure_crlf_idempotent(s: str) -> None:
    """Re-ensuring CRLF does not change the value."""
    once = _ensure_crlf(s)
    twice = _ensure_crlf(once)
    assert once == twice


@settings(max_examples=50)
@given(
    s=st.text(
        alphabet=st.characters(blacklist_categories=("Cs",), blacklist_characters="\r"),
        min_size=1,
        max_size=40,
    ),
)
def test_ensure_crlf_lf_only_replaces_lf(s: str) -> None:
    """Lines ending in LF get the LF replaced by CRLF (no double-newline)."""
    result = _ensure_crlf(s + "\n")
    assert result.endswith("\r\n")
    assert not result.endswith("\n\n")


@settings(max_examples=50)
@given(
    s=st.text(
        alphabet=st.characters(blacklist_categories=("Cs",), blacklist_characters="\n"),
        min_size=1,
        max_size=40,
    ),
)
def test_ensure_crlf_cr_only_appends_lf(s: str) -> None:
    """Lines ending in CR (no LF) get an LF appended (CRLF)."""
    result = _ensure_crlf(s + "\r")
    assert result.endswith("\r\n")
    assert not result.endswith("\r\r")


@settings(max_examples=100)
@given(
    s=st.text(
        alphabet=st.characters(blacklist_categories=("Cs",), blacklist_characters="\r\n"),
        min_size=0,
        max_size=80,
    ),
)
def test_ensure_crlf_preserves_content_before_terminator(s: str) -> None:
    """For unterminated input, content is preserved verbatim before CRLF."""
    result = _ensure_crlf(s)
    assert result == s + "\r\n"
    assert result.startswith(s)


_DIGITS = st.characters(whitelist_categories=("Nd",))
_INVOICE_DATE_STRINGS = st.text(alphabet=_DIGITS, min_size=6, max_size=6)


@settings(max_examples=50)
@given(
    count=st.integers(min_value=1, max_value=1000),
    nonzero=st.text(alphabet=st.characters(whitelist_categories=("Nd",), whitelist_characters=""), min_size=1, max_size=9).filter(lambda s: int(s) != 0),
    invoice_date=_INVOICE_DATE_STRINGS,
)
def test_build_split_filename_uses_cr_for_negative_total(
    count: int, nonzero: str, invoice_date: str
) -> None:
    """A strictly-negative invoice total picks the '.cr' suffix."""
    line_dict = {
        "invoice_total": "-" + nonzero,
        "invoice_date": invoice_date,
    }
    cfg = SplitConfig(output_directory="/tmp/out", filename_stem="inp", prepend_date=False)
    output_path, _prefix, suffix = _build_split_filename(line_dict, count, cfg)
    assert suffix == ".cr"
    assert output_path.endswith(".cr")
    assert output_path.startswith("/tmp/out/")


@settings(max_examples=50)
@given(
    count=st.integers(min_value=1, max_value=1000),
    invoice_total=st.text(alphabet=_DIGITS, min_size=1, max_size=10),
    invoice_date=_INVOICE_DATE_STRINGS,
)
def test_build_split_filename_uses_inv_for_non_negative_total(
    count: int, invoice_total: str, invoice_date: str
) -> None:
    """Non-negative invoice total picks the '.inv' suffix."""
    line_dict = {
        "invoice_total": invoice_total,
        "invoice_date": invoice_date,
    }
    cfg = SplitConfig(output_directory="/tmp/out", filename_stem="inp", prepend_date=False)
    output_path, _prefix, suffix = _build_split_filename(line_dict, count, cfg)
    assert suffix == ".inv"
    assert output_path.endswith(".inv")


@settings(max_examples=20)
@given(
    count=st.integers(min_value=1, max_value=1000),
    invoice_date=_INVOICE_DATE_STRINGS,
)
def test_build_split_filename_zero_total_picks_inv(
    count: int, invoice_date: str
) -> None:
    """The literal '0' total picks '.inv' (zero is non-negative, code uses `< 0`)."""
    line_dict = {"invoice_total": "0", "invoice_date": invoice_date}
    cfg = SplitConfig(output_directory="/tmp/out", filename_stem="inp", prepend_date=False)
    _path, _prefix, suffix = _build_split_filename(line_dict, count, cfg)
    assert suffix == ".inv"


@settings(max_examples=20)
@given(
    count=st.integers(min_value=1, max_value=1000),
    nonzero=st.text(
        alphabet=st.characters(whitelist_categories=("Nd",)),
        min_size=1,
        max_size=9,
    ),
    invoice_date=_INVOICE_DATE_STRINGS,
)
def test_build_split_filename_negative_zero_picks_inv(
    count: int, nonzero: str, invoice_date: str
) -> None:
    """'-0' (or '-0...0' trailing zeros) is `int()` == 0, so picks '.inv'.

    This guards against a mutation that flips `< 0` to `<= 0`.
    """
    line_dict = {
        "invoice_total": "-" + nonzero,
        "invoice_date": invoice_date,
    }
    cfg = SplitConfig(output_directory="/tmp/out", filename_stem="inp", prepend_date=False)
    _path, _prefix, suffix = _build_split_filename(line_dict, count, cfg)
    # int("-0...0n") is 0 for n>0; int("-000123") is -123. So:
    total_int = int("-" + nonzero)
    expected = ".cr" if total_int < 0 else ".inv"
    assert suffix == expected


@settings(max_examples=50)
@given(
    count=st.integers(min_value=1, max_value=1000),
    invoice_date=_INVOICE_DATE_STRINGS,
)
def test_build_split_filename_unparseable_total_becomes_inv(
    count: int, invoice_date: str
) -> None:
    """An unparseable invoice_total defaults to 0 and picks '.inv'."""
    line_dict = {
        "invoice_total": "not-a-number",
        "invoice_date": invoice_date,
    }
    cfg = SplitConfig(output_directory="/tmp/out", filename_stem="inp", prepend_date=False)
    _path, _prefix, suffix = _build_split_filename(line_dict, count, cfg)
    assert suffix == ".inv"


@settings(max_examples=50)
@given(
    count=st.integers(min_value=1, max_value=1000),
    invoice_total=st.text(alphabet=_DIGITS, min_size=1, max_size=10),
    invoice_date=_INVOICE_DATE_STRINGS,
)
def test_build_split_filename_uses_filename_stem_when_provided(
    count: int, invoice_total: str, invoice_date: str
) -> None:
    """When filename_stem is set, it appears in the output path."""
    line_dict = {
        "invoice_total": invoice_total,
        "invoice_date": invoice_date,
    }
    cfg = SplitConfig(output_directory="/tmp/out", filename_stem="myfile", prepend_date=False)
    output_path, _prefix, _suffix = _build_split_filename(line_dict, count, cfg)
    assert "myfile" in output_path


@settings(max_examples=50)
@given(
    count=st.integers(min_value=1, max_value=1000),
    invoice_total=st.text(alphabet=_DIGITS, min_size=1, max_size=10),
    invoice_date=_INVOICE_DATE_STRINGS,
)
def test_build_split_filename_default_stem_is_split(
    count: int, invoice_total: str, invoice_date: str
) -> None:
    """When filename_stem is empty, the literal 'split' is used."""
    line_dict = {
        "invoice_total": invoice_total,
        "invoice_date": invoice_date,
    }
    cfg = SplitConfig(output_directory="/tmp/out", prepend_date=False)
    output_path, _prefix, _suffix = _build_split_filename(line_dict, count, cfg)
    assert "split" in output_path
