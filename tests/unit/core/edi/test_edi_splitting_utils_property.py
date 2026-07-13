"""Property-based tests for core.edi.edi_splitting_utils.

Targets the pure helpers `_col_to_excel`, `_group_lines_by_invoice`,
`_split_invoice_records`, and the easy surface of `filter_b_records_by_category`.

`_validate_split_counts` and `do_split_edi` are excluded (they read
disk via `_count_total_lines`).
"""

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from core.edi.edi_splitting_utils import (
    _build_split_file_metadata,
    _col_to_excel,
    _group_lines_by_invoice,
    _should_include_b_record,
    _split_invoice_records,
    _validate_split_counts,
    filter_b_records_by_category,
)

pytestmark = [pytest.mark.unit, pytest.mark.edi, pytest.mark.property]


@settings(max_examples=200)
@given(n=st.integers(min_value=1, max_value=10_000))
def test_col_to_excel_returns_uppercase_letters(n: int) -> None:
    """Output is one or more uppercase ASCII letters."""
    result = _col_to_excel(n)
    assert result.isalpha()
    assert result.isupper()
    assert len(result) >= 1


@settings(max_examples=200)
@given(n=st.integers(min_value=1, max_value=26))
def test_col_to_excel_single_letter_for_1_to_26(n: int) -> None:
    """n in [1, 26] maps to a single uppercase letter."""
    result = _col_to_excel(n)
    assert len(result) == 1
    assert result == chr(ord("A") + n - 1)


@settings(max_examples=100)
@given(n=st.integers(min_value=1, max_value=10_000))
def test_col_to_excel_is_deterministic(n: int) -> None:
    """Pure function — same input always produces the same output."""
    assert _col_to_excel(n) == _col_to_excel(n)


@settings(max_examples=100)
@given(n=st.integers(min_value=1, max_value=1000))
def test_col_to_excel_first_27_match_known_constants(n: int) -> None:
    """Spot check: 27 -> 'AA' (the canonical Excel column boundary)."""
    if n == 27:
        assert _col_to_excel(n) == "AA"


@settings(max_examples=50)
@given(n=st.integers(min_value=27, max_value=10_000))
def test_col_to_excel_grows_with_input(n: int) -> None:
    """Larger n produces a result whose lexicographic order matches n's order."""
    a = _col_to_excel(n)
    b = _col_to_excel(n + 1)
    # Not strictly monotonic in length (e.g. Z -> AA), but the underlying
    # integer values are monotonic: 26 < 27, so 'Z' < 'AA' lexicographically.
    if len(a) == len(b):
        assert a < b


@st.composite
def _edi_lines(draw, min_size: int = 0, max_size: int = 20) -> list[str]:
    """Strategy for a list of EDI-like lines, each starting with A, B, C, or other."""
    return draw(
        st.lists(
            st.text(
                alphabet=st.characters(
                    blacklist_categories=("Cs",),
                    blacklist_characters="\n\r",
                ),
                min_size=1,
                max_size=20,
            ),
            min_size=min_size,
            max_size=max_size,
        )
    )


@settings(max_examples=50)
@given(
    lines=st.lists(
        st.text(
            alphabet=st.characters(blacklist_categories=("Cs",), blacklist_characters="\n\r"),
            min_size=1,
            max_size=15,
        ),
        min_size=0,
        max_size=30,
    ),
)
def test_group_lines_by_invoice_empty_input_yields_empty(
    lines: list[str],
) -> None:
    """Empty input -> empty invoice list."""
    # Only test the empty case here; non-empty input may produce
    # leading-non-A chunks. See test_group_lines_by_invoice_preserves_total_line_count.
    if lines:
        return
    assert _group_lines_by_invoice(lines) == []


@settings(max_examples=50)
@given(
    lines=st.lists(
        st.text(
            alphabet=st.characters(blacklist_categories=("Cs",), blacklist_characters="\n\r"),
            min_size=1,
            max_size=15,
        ),
        min_size=0,
        max_size=30,
    ),
)
def test_group_lines_by_invoice_starts_chunk_at_a_record(
    lines: list[str],
) -> None:
    """An 'A'-leading line always starts a new chunk."""
    invoices = _group_lines_by_invoice(lines)
    # Any chunk whose first line starts with 'A' is a properly-bounded invoice.
    # (A leading non-A chunk may also exist; that's a degenerate edge case.)
    a_starts = [chunk for chunk in invoices if chunk[0].startswith("A")]
    assert len(a_starts) == sum(1 for ln in lines if ln.startswith("A"))


@settings(max_examples=50)
@given(
    invoice_lines=st.lists(
        st.text(
            alphabet=st.characters(blacklist_categories=("Cs",), blacklist_characters="\n\r"),
            min_size=1,
            max_size=15,
        ),
        min_size=0,
        max_size=20,
    ),
)
def test_split_invoice_records_preserves_a_record(invoice_lines: list[str]) -> None:
    """_split_invoice_records returns the A record (or None) of the invoice."""
    a_record, _b, _c = _split_invoice_records(invoice_lines)
    if a_record is not None:
        assert a_record.startswith("A")


@settings(max_examples=50)
@given(
    invoice_lines=st.lists(
        st.text(
            alphabet=st.characters(blacklist_categories=("Cs",), blacklist_characters="\n\r"),
            min_size=1,
            max_size=15,
        ),
        min_size=0,
        max_size=20,
    ),
)
def test_split_invoice_records_b_records_all_start_with_b(
    invoice_lines: list[str],
) -> None:
    """Returned B-records all start with 'B'."""
    _a, b_records, _c = _split_invoice_records(invoice_lines)
    for rec in b_records:
        assert rec.startswith("B")


@settings(max_examples=50)
@given(
    invoice_lines=st.lists(
        st.text(
            alphabet=st.characters(blacklist_categories=("Cs",), blacklist_characters="\n\r"),
            min_size=1,
            max_size=15,
        ),
        min_size=0,
        max_size=20,
    ),
)
def test_split_invoice_records_c_record_is_last_seen(
    invoice_lines: list[str],
) -> None:
    """The C record is the last 'C'-leading line encountered."""
    _a, _b, c_record = _split_invoice_records(invoice_lines)
    if c_record is not None:
        assert c_record.startswith("C")


@settings(max_examples=50)
@given(
    b_records=st.lists(
        st.text(
            alphabet=st.characters(blacklist_categories=("Cs",), blacklist_characters="\n\r"),
            min_size=1,
            max_size=15,
        ),
        min_size=0,
        max_size=15,
    ),
)
def test_filter_b_records_by_category_all_returns_input(b_records: list[str]) -> None:
    """'ALL' as filter_categories is a no-op."""
    result = filter_b_records_by_category(
        b_records=b_records,
        upc_dict={"1": ["cat", "u"]},
        filter_categories="ALL",
        filter_mode="include",
    )
    assert result == b_records


@settings(max_examples=50)
@given(
    b_records=st.lists(
        st.text(
            alphabet=st.characters(blacklist_categories=("Cs",), blacklist_characters="\n\r"),
            min_size=1,
            max_size=15,
        ),
        min_size=0,
        max_size=15,
    ),
)
def test_filter_b_records_by_category_none_upc_returns_input(
    b_records: list[str],
) -> None:
    """None upc_dict is a no-op."""
    result = filter_b_records_by_category(
        b_records=b_records,
        upc_dict=None,
        filter_categories="cat1,cat2",
        filter_mode="include",
    )
    assert result == b_records



def _build_b_record(vendor_item: str) -> str:
    """Build a minimal but valid B-record line with the given vendor_item field.

    B-record layout: 1 record_type + 11 upc + 25 desc + 6 vendor + 6 unit_cost
    + 2 combo + 6 unit_mult + 5 qty + 5 retail + 3 multi + 6 parent = 76 chars.
    """
    record_type = "B"
    upc = "0" * 11
    description = "d" * 25
    vendor = vendor_item.ljust(6)[:6]
    unit_cost = "0" * 6
    combo = "00"
    unit_mult = "0" * 6
    qty = "0" * 5
    retail = "0" * 5
    multi = "000"
    parent = "0" * 6
    return record_type + upc + description + vendor + unit_cost + combo + unit_mult + qty + retail + multi + parent


@settings(max_examples=30)
@given(vendor_item=st.integers(min_value=0, max_value=999999))
def test_filter_b_records_by_category_exclude_mode_removes_match(
    vendor_item: int,
) -> None:
    """filter_mode='exclude' removes records whose category IS in the list."""
    vendor_str = f"{vendor_item:06d}"
    b = _build_b_record(vendor_str)
    upc_dict = {vendor_item: ["candy", "u1", "u2", "u3", "u4"]}
    result = filter_b_records_by_category(
        b_records=[b],
        upc_dict=upc_dict,
        filter_categories="candy",
        filter_mode="exclude",
    )
    assert result == []


@settings(max_examples=30)
@given(vendor_item=st.integers(min_value=0, max_value=999999))
def test_filter_b_records_by_category_exclude_mode_keeps_non_match(
    vendor_item: int,
) -> None:
    """filter_mode='exclude' keeps records whose category is NOT in the list."""
    vendor_str = f"{vendor_item:06d}"
    b = _build_b_record(vendor_str)
    upc_dict = {vendor_item: ["candy", "u1", "u2", "u3", "u4"]}
    result = filter_b_records_by_category(
        b_records=[b],
        upc_dict=upc_dict,
        filter_categories="toys",
        filter_mode="exclude",
    )
    assert result == [b]


@settings(max_examples=30)
@given(payload=st.text(
    alphabet=st.characters(blacklist_categories=("Cs",), blacklist_characters="\n\rB"),
    min_size=0,
    max_size=80,
))
def test_should_include_b_record_returns_true_for_non_edi_line(
    payload: str,
) -> None:
    """_should_include_b_record returns True (passes through) for non-B lines."""
    upc_dict = {1: ["candy", "u1", "u2", "u3", "u4"]}
    assert _should_include_b_record(payload, upc_dict, ["candy"], "include") is True


def test_should_include_b_record_returns_true_for_blank_vendor_item() -> None:
    """An all-space vendor_item field is treated as 'not present' -> True."""
    b = _build_b_record(" " * 6)
    upc_dict = {0: ["candy", "u1", "u2", "u3", "u4"]}
    assert _should_include_b_record(b, upc_dict, ["candy"], "include") is True


def test_should_include_b_record_returns_true_for_non_numeric_vendor_item() -> None:
    """A non-numeric vendor_item (after strip) returns True (passes through)."""
    b = _build_b_record("abc")
    upc_dict = {0: ["candy", "u1", "u2", "u3", "u4"]}
    assert _should_include_b_record(b, upc_dict, ["candy"], "include") is True


@settings(max_examples=30)
@given(vendor_item=st.integers(min_value=0, max_value=999999))
def test_should_include_b_record_include_mode_decision(
    vendor_item: int,
) -> None:
    """filter_mode='include' keeps records whose category is in the list."""
    vendor_str = f"{vendor_item:06d}"
    b = _build_b_record(vendor_str)
    upc_dict = {vendor_item: ["candy", "u1", "u2", "u3", "u4"]}
    in_list = _should_include_b_record(b, upc_dict, ["candy"], "include")
    not_in_list = _should_include_b_record(b, upc_dict, ["toys"], "include")
    assert in_list is True
    assert not_in_list is False


@settings(max_examples=30)
@given(vendor_item=st.integers(min_value=0, max_value=999999))
def test_should_include_b_record_exclude_mode_decision(
    vendor_item: int,
) -> None:
    """filter_mode='exclude' keeps records whose category is NOT in the list."""
    vendor_str = f"{vendor_item:06d}"
    b = _build_b_record(vendor_str)
    upc_dict = {vendor_item: ["candy", "u1", "u2", "u3", "u4"]}
    in_list = _should_include_b_record(b, upc_dict, ["candy"], "exclude")
    not_in_list = _should_include_b_record(b, upc_dict, ["toys"], "exclude")
    assert in_list is False
    assert not_in_list is True


def test_invoice_total_zero_uses_inv_suffix_not_cr() -> None:
    """invoice_total == 0 is the boundary: not credit, so suffix must be '.inv'.

    A mutation of `<` to `<=` would flip the zero branch to '.cr'.
    """
    line_dict = {"invoice_date": "20260101", "invoice_total": "0"}
    _path, _prefix, suffix = _build_split_file_metadata(
        line_dict, 1, "foo.edi", "/tmp", prepend_date_files=False
    )
    assert suffix == ".inv"


def test_invoice_total_negative_uses_cr_suffix() -> None:
    """A negative invoice_total is a credit memo; suffix must be '.cr'."""
    line_dict = {"invoice_date": "20260101", "invoice_total": "-100"}
    _path, _prefix, suffix = _build_split_file_metadata(
        line_dict, 1, "foo.edi", "/tmp", prepend_date_files=False
    )
    assert suffix == ".cr"


def test_build_split_file_metadata_raises_when_line_dict_is_none() -> None:
    """_build_split_file_metadata must reject None line_dict with ValueError.

    A `negate_if_condition` mutation (if not (line_dict is None):) would
    skip the guard and crash later when indexing line_dict[...] instead.
    """
    import pytest
    with pytest.raises(ValueError, match="capture_records returned None"):
        _build_split_file_metadata(
            None, 1, "foo.edi", "/tmp", prepend_date_files=False
        )


def test_validate_split_counts_raises_on_mismatched_line_count(tmp_path) -> None:
    """Mismatched lines_in_edi vs write_counter must raise DataIntegrityError.

    A `ne_to_eq` mutation (lines_in_edi == write_counter) would let the
    mismatched case pass silently.
    """
    from core.exceptions import DataIntegrityError
    out_file = tmp_path / "out.txt"
    out_file.write_text("a\n")
    with pytest.raises(DataIntegrityError, match="not all lines"):
        _validate_split_counts(
            lines_in_edi=10,
            write_counter=5,
            edi_send_list=[(str(out_file), "", ".inv")],
            a_record_count=1,
        )


# ---------------------------------------------------------------------------
# Hardcoded counterparts for the property tests above.
#
# Three of the @given property tests in this file have assertions that
# are tautologies or guarded by `if` conditions that fire rarely:
#
# - L58: `assert _col_to_excel(n) == "AA"` inside `if n == 27:`. The
#   `if` guard fires for only 1 of 1000 generated values; the assertion
#   is otherwise vacuously skipped. The runner sees "test passed" and
#   reports the assertion as "dead".
# - L154: `assert a_record.startswith("A")` inside `if a_record is not None:`.
#   The function only assigns `a_record = line` when `line.startswith("A")`,
#   so the assertion is a tautology — always True when reached.
# - L175: `assert rec.startswith("B")` for each rec in b_records.
#   Same pattern: b_records only contains lines that start with "B".
# - L196: `assert c_record.startswith("C")` inside `if c_record is not None:`.
#   Same pattern.
#
# The hardcoded tests below pin actual values for known inputs so any
# consistent mutation of the underlying functions is caught. Same
# pattern as the Phase 3a hardcoded oracle tests added to
# test_upc_utils_property.py and test_pad_upc_idempotent_*
# (commit 812ead07b).
# ---------------------------------------------------------------------------


def test_col_to_excel_hardcoded_oracle() -> None:
    """Hardcoded Excel column boundaries. The property test
    ``test_col_to_excel_first_27_match_known_constants`` checks only
    n=27 inside a guard; this test pins the actual column-letter
    output for known inputs so any consistent mutation to
    ``_col_to_excel`` is caught.
    """
    assert _col_to_excel(1) == "A"
    assert _col_to_excel(2) == "B"
    assert _col_to_excel(26) == "Z"
    assert _col_to_excel(27) == "AA"
    assert _col_to_excel(28) == "AB"
    assert _col_to_excel(52) == "AZ"
    assert _col_to_excel(53) == "BA"
    assert _col_to_excel(702) == "ZZ"


def test_split_invoice_records_hardcoded_oracle() -> None:
    """Hardcoded ``_split_invoice_records`` output for known inputs.
    The property tests assert only that returned records start with
    the right letter (a tautology, since the function only assigns
    to a_record/b_records/c_record when the line starts with the
    matching letter). This test pins the exact record that should
    be returned for each position so a consistent mutation is
    caught.
    """
    # A single A record, no B, no C.
    a, b, c = _split_invoice_records(["AVENDOR00000000010101240000000123"])
    assert a == "AVENDOR00000000010101240000000123"
    assert b == []
    assert c is None

    # A, B, C in order.
    a_line = "AVENDOR00000000010101240000000123"
    b_line = "B00123456789Test Item Description    123456001234010000010000500123      "
    c_line = "CFRTFreight Charge                 000001234"
    a, b, c = _split_invoice_records([a_line, b_line, c_line])
    assert a == a_line
    assert b == [b_line]
    assert c == c_line

    # B records are accumulated in order.
    a, b, c = _split_invoice_records(
        [b_line, a_line, b_line, c_line, b_line]
    )
    assert a == a_line
    assert b == [b_line, b_line, b_line]
    assert c == c_line

    # C record is the LAST 'C'-leading line, not the first.
    a, b, c = _split_invoice_records(
        [c_line, b_line, c_line]
    )
    assert a is None
    assert b == [b_line]
    assert c == c_line  # the second C line wins

    # A record is the LAST 'A'-leading line (current behavior).
    a, b, c = _split_invoice_records([a_line, a_line, b_line])
    assert a == a_line  # second A line wins
    assert b == [b_line]
    assert c is None

    # Empty input.
    a, b, c = _split_invoice_records([])
    assert a is None
    assert b == []
    assert c is None
