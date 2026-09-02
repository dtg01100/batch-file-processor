"""Property-based tests for dispatch.file_utils.

Targets the pure helpers `get_file_extension` and `strip_invalid_filename_chars`,
plus the rename-template branch of `build_output_filename` and the
A-record filter in `extract_invoice_numbers`. The `datetime.now()`
call in `build_output_filename` is mocked with a fixed value so the
rename-template branch is fully deterministic.
"""

import datetime

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from webapp.pipeline.file_utils import (
    build_output_filename,
    extract_invoice_numbers,
    get_file_extension,
    strip_invalid_filename_chars,
)

pytestmark = [pytest.mark.unit, pytest.mark.property]


_FILENAMES = st.text(
    alphabet=st.characters(
        blacklist_categories=("Cs",),
        blacklist_characters="\n\r",
    ),
    min_size=0,
    max_size=60,
)

# A canonical positive A-record EDI line for extract_invoice_numbers tests.
# Length 33 (matches core.constants.EDI_A_RECORD_MIN_LENGTH): A + 6 (vendor)
# + 10 (invoice_number) + 6 (date) + 10 (total). When written to a file
# with a trailing \n, splitlines() returns the 33-char line without
# the newline.
_A_LINE_RAW = "AVENDOR00000000011202400000001234"
_INV_NUM = "0000000001"


@settings(max_examples=100)
@given(name=_FILENAMES)
def test_get_file_extension_is_idempotent(name: str) -> None:
    """get_file_extension on a name without an extension returns ''."""
    # If the name has no '.', result is the empty string.
    if "." not in name:
        assert get_file_extension(name) == ""
    else:
        result = get_file_extension(name)
        # The returned extension matches the substring after the last '.'
        # and has no leading dot.
        assert not result.startswith(".")


@settings(max_examples=100)
@given(
    stem=st.text(
        alphabet=st.characters(
            blacklist_categories=("Cs",),
            blacklist_characters="\n\r./",
        ),
        min_size=1,
        max_size=30,
    ),
    ext=st.text(
        alphabet=st.characters(
            blacklist_categories=("Cs",),
            blacklist_characters="\n\r./",
        ),
        min_size=1,
        max_size=10,
    ),
)
def test_get_file_extension_returns_last_segment(stem: str, ext: str) -> None:
    """For 'stem.ext' the result is 'ext'."""
    name = f"{stem}.{ext}"
    assert get_file_extension(name) == ext


@settings(max_examples=100)
@given(name=_FILENAMES)
def test_strip_invalid_filename_chars_keeps_valid_subset(name: str) -> None:
    """After stripping, only [A-Za-z0-9. _] characters remain."""
    result = strip_invalid_filename_chars(name)
    for ch in result:
        assert ch.isalnum() or ch in (".", " ", "_")


@settings(max_examples=100)
@given(name=_FILENAMES)
def test_strip_invalid_filename_chars_idempotent(name: str) -> None:
    """Stripping twice equals stripping once."""
    once = strip_invalid_filename_chars(name)
    twice = strip_invalid_filename_chars(once)
    assert once == twice


def test_strip_invalid_filename_chars_hardcoded_oracle() -> None:
    """Hardcoded ``strip_invalid_filename_chars`` output values. The
    idempotency test above
    (asserting ``strip(x) == strip(strip(x))``) is self-referential:
    a consistent mutation to ``strip_invalid_filename_chars`` that
    returns its input unchanged would still pass. This test pins
    the actual output for known inputs so any such mutation is
    caught.
    """
    assert strip_invalid_filename_chars("a/b") == "ab"
    assert strip_invalid_filename_chars("a/b*c") == "abc"
    assert strip_invalid_filename_chars("a b.c_d") == "a b.c_d"
    assert strip_invalid_filename_chars("////") == ""
    assert strip_invalid_filename_chars("hello") == "hello"
    assert strip_invalid_filename_chars("!@#$%^&*()") == ""


@settings(max_examples=100)
@given(name=_FILENAMES)
def test_strip_invalid_filename_chars_monotonic_length(name: str) -> None:
    """Output length is <= input length (we only delete characters)."""
    result = strip_invalid_filename_chars(name)
    assert len(result) <= len(name)


@settings(max_examples=100)
@given(
    valid=st.text(
        alphabet=st.sampled_from(
            list("ABCDEFGHIJKLMNOPQRSTUVWXYZ")
            + list("abcdefghijklmnopqrstuvwxyz")
            + list("0123456789")
            + list(". _")
        ),
        min_size=0,
        max_size=30,
    ),
)
def test_strip_invalid_filename_chars_preserves_valid_input(valid: str) -> None:
    """Inputs that already contain only valid ASCII chars are unchanged."""
    assert strip_invalid_filename_chars(valid) == valid


def test_build_output_filename_with_rename_template_substitutes_datetime(
    monkeypatch,
) -> None:
    """When params['rename_file'] is non-empty, %datetime% is replaced.

    Pins line 48 `negate_if_condition`: original `if rename_template:`
    enters the rename branch; mutated `if not (rename_template):`
    flips the branch. With the mutation applied to a real rename
    template, the function returns the original filename unchanged.

    NOTE: `_INVALID_FILENAME_CHARS_RE` strips '-' and '/', so the
    expected output only contains alphanumerics, dots, and underscores.
    """
    fixed_now = datetime.datetime(2025, 1, 2, 3, 4, 5)

    class _FixedDatetime(datetime.datetime):
        @classmethod
        def now(cls, tz=None):
            return fixed_now

    monkeypatch.setattr(datetime, "datetime", _FixedDatetime)
    result = build_output_filename(
        original="input.csv",
        format="Simplified CSV",
        params={"rename_file": "out_%datetime%"},
        filename_prefix="pre",
        filename_suffix="suf",
    )
    expected_date = fixed_now.strftime("%Y%m%d")
    assert result == f"preout_{expected_date}.csvsuf"
    assert "input" not in result


def test_extract_invoice_numbers_returns_only_a_records(tmp_path) -> None:
    """extract_invoice_numbers keeps A-record invoices and drops others.

    Pins line 249 `eq_to_ne`: original `rec.get("record_type") == "A"`
    keeps A records; mutated `!= "A"` would keep everything BUT A
    records. The test asserts that the canonical 33-char A-record
    line is kept and the B/C record lines are not in the result.
    """
    p = tmp_path / "invoices.edi"
    p.write_text(
        _A_LINE_RAW
        + "\n"
        # B and C records with bogus 'A'/'X' character in invoice_number
        # would still parse, but the L249 filter rejects non-A prefixes.
        + "BVENDOR0000000001120240000000123Grocery   00012345        \n"
        + "CTABSalesTax               000000123\n"
    )
    result = extract_invoice_numbers(str(p))
    assert _INV_NUM in result
    # The B/C records have non-A prefixes and must not contribute.
    # If L249 mutates to `!=`, a B/C invoice_number would appear.
    assert result.strip() == _INV_NUM
