"""Property-based tests for core.edi.edi_splitter.

Targets the pure helpers `_ensure_crlf` and `_build_split_filename`.
The `EDISplitter` class itself is excluded (filesystem-bound).
"""

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from core.edi.edi_splitter import EDISplitter, SplitConfig, _build_split_filename, _ensure_crlf

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


def test_build_split_filename_prepend_date_true_puts_date_in_prefix() -> None:
    """Regression test for the meta-test finding (Phase 3, 2026-07-13).

    The mutation runner's ``negate_if_condition`` at edi_splitter.py:72
    (flipping ``if config.prepend_date:`` to ``if not (config.prepend_date):``)
    was not caught by the existing test pair. Every property test used
    ``prepend_date=False``, so the date-prefix branch was untested.

    This test pins the date-prefix behavior: with ``prepend_date=True``,
    the file name's prefix segment must contain the formatted date and
    a different value than the ``prepend_date=False`` prefix. A
    consistent mutation that swapped the if/else would change which
    branch fires and this test would fail.
    """
    # A fixed valid date: 011226 (Jan 12, 2026) — parse_edi_date uses %m%d%y.
    line_dict = {
        "invoice_total": "0000000123",
        "invoice_date": "011226",
    }
    cfg = SplitConfig(
        output_directory="/tmp/out", filename_stem="inp", prepend_date=True
    )
    output_path, prefix, suffix = _build_split_filename(line_dict, 1, cfg)
    # prefix must contain the formatted date "12 Jan, 2026" (%d %b, %Y)
    assert "12 Jan, 2026" in prefix, (
        f"expected date '12 Jan, 2026' in prefix, got {prefix!r}"
    )
    # prefix must contain the column-letter segment (count=1 -> "A_")
    assert prefix.endswith("A_"), (
        f"expected prefix to end with column-letter 'A_', got {prefix!r}"
    )
    # suffix unchanged regardless of prepend_date
    assert suffix == ".inv"
    # output_path structure: {output_dir}/{date}_{col_letter}_{stem}{suffix}
    assert output_path.startswith("/tmp/out/12 Jan, 2026_A_inp")
    assert output_path.endswith(".inv")

    # Sanity check: with prepend_date=False, the date MUST NOT be in prefix.
    cfg_no_date = SplitConfig(
        output_directory="/tmp/out", filename_stem="inp", prepend_date=False
    )
    output_path_no_date, prefix_no_date, _ = _build_split_filename(
        line_dict, 1, cfg_no_date
    )
    assert "12 Jan, 2026" not in prefix_no_date
    assert prefix_no_date == "A_"
    assert not output_path_no_date.startswith("/tmp/out/12 Jan, 2026")


def test_split_edi_max_invoices_zero_means_no_limit() -> None:
    """Regression test for gt_to_ge mutation at L264.

    When max_invoices=0, the condition ``max_invoices > 0`` is False,
    so the limit check is skipped and all invoices are processed.
    """
    class MockFS:
        def __init__(self):
            self.written = []
            self.dirs = set()

        def write_file(self, path, data):
            self.written.append((path, data))

        def write_file_text(self, path, data, encoding="utf-8"):
            self.written.append((path, data.encode()))

        def read_file(self, path):
            return b""

        def read_file_text(self, path, encoding="utf-8"):
            return ""

        def file_exists(self, path):
            return False

        def dir_exists(self, path):
            return path in self.dirs

        def mkdir(self, path):
            self.dirs.add(path)

        def makedirs(self, path):
            self.dirs.add(path)

        def list_files(self, path):
            return []

        def copy_file(self, src, dst):
            pass

        def remove_file(self, path):
            pass

        def get_absolute_path(self, path):
            return path

    fs = MockFS()
    splitter = EDISplitter(fs)
    config = SplitConfig(output_directory="/tmp/out", prepend_date=False)
    config.max_invoices = 0  # 0 means no limit

    # 3 invoices
    content = (
        "AINVOICE1  00000101012026000000010000\r\n"
        "B12345678901Item 1                     001234010000010000010000500123      \r\n"
        "AINVOICE2  00000201012026000000020000\r\n"
        "B12345678901Item 2                     001234010000010000010000500123      \r\n"
        "AINVOICE3  00000301012026000000030000\r\n"
        "B12345678901Item 3                     001234010000010000010000500123      \r\n"
    )

    result = splitter.split_edi(content, config)

    # All 3 invoices should be processed
    assert len(result.output_files) == 3
    assert len(fs.written) == 3
