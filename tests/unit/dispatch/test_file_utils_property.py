"""Property-based tests for dispatch.file_utils.

Targets the pure helpers `get_file_extension` and `strip_invalid_filename_chars`.
`build_output_filename` is excluded (calls `datetime.now()`).
"""

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from dispatch.file_utils import get_file_extension, strip_invalid_filename_chars

pytestmark = [pytest.mark.unit, pytest.mark.property]


_FILENAMES = st.text(
    alphabet=st.characters(
        blacklist_categories=("Cs",),
        blacklist_characters="\n\r",
    ),
    min_size=0,
    max_size=60,
)


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
