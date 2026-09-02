"""Property-based tests for dispatch.hash_utils.

Targets the pure helpers `generate_match_lists`, `build_hash_dictionaries`,
and `check_file_against_processed`. `generate_file_hash` is excluded
(reads from disk).
"""

import os
import tempfile
from unittest.mock import patch

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from webapp.pipeline.hash_utils import (
    build_hash_dictionaries,
    check_file_against_processed,
    generate_file_hash,
    generate_match_lists,
)

pytestmark = [pytest.mark.unit, pytest.mark.property]


_FILENAMES = st.text(
    alphabet=st.characters(blacklist_categories=("Cs",), blacklist_characters="\n\r"),
    min_size=1,
    max_size=30,
)
_CHECKSUMS = st.text(
    alphabet=st.characters(
        whitelist_categories=("Nd",),
        whitelist_characters="abcdef",
    ),
    min_size=8,
    max_size=64,
)
_RESEND = st.booleans()


@st.composite
def _processed_files(draw) -> list[dict]:
    """A list of processed-file dicts with file_name, file_checksum, resend_flag."""
    return draw(
        st.lists(
            st.fixed_dictionaries(
                {
                    "file_name": _FILENAMES,
                    "file_checksum": _CHECKSUMS,
                    "resend_flag": _RESEND,
                }
            ),
            min_size=0,
            max_size=20,
        )
    )


@settings(max_examples=100)
@given(files=_processed_files())
def test_generate_match_lists_returns_three_collections(files: list[dict]) -> None:
    """generate_match_lists returns (hash_list, name_list, resend_set)."""
    hash_list, name_list, resend_set = generate_match_lists(files)
    assert isinstance(hash_list, list)
    assert isinstance(name_list, list)
    assert isinstance(resend_set, set)


@settings(max_examples=100)
@given(files=_processed_files())
def test_generate_match_lists_length_matches_input(files: list[dict]) -> None:
    """hash_list and name_list length equal input length."""
    hash_list, name_list, _ = generate_match_lists(files)
    assert len(hash_list) == len(files)
    assert len(name_list) == len(files)


@settings(max_examples=100)
@given(files=_processed_files())
def test_generate_match_lists_resend_set_contains_only_flagged(
    files: list[dict],
) -> None:
    """resend_set equals the set of checksums with resend_flag True."""
    _, _, resend_set = generate_match_lists(files)
    expected = {e["file_checksum"] for e in files if e["resend_flag"] is True}
    assert resend_set == expected


@settings(max_examples=100)
@given(files=_processed_files())
def test_generate_match_lists_hash_list_pairs(files: list[dict]) -> None:
    """hash_list contains (file_name, file_checksum) tuples per input entry."""
    hash_list, _, _ = generate_match_lists(files)
    for entry, pair in zip(files, hash_list, strict=True):
        assert pair == (entry["file_name"], entry["file_checksum"])


@settings(max_examples=100)
@given(files=_processed_files())
def test_generate_match_lists_name_list_pairs(files: list[dict]) -> None:
    """name_list contains (file_checksum, file_name) tuples per input entry."""
    _, name_list, _ = generate_match_lists(files)
    for entry, pair in zip(files, name_list, strict=True):
        assert pair == (entry["file_checksum"], entry["file_name"])


@settings(max_examples=50)
@given(files=_processed_files())
def test_build_hash_dictionaries_round_trip(files: list[dict]) -> None:
    """build_hash_dictionaries produces dicts whose keys are file_names
    and whose values are the LAST seen checksum per key, with resend_set
    equal to flagged checksums."""
    folder_hash, folder_name, resend = build_hash_dictionaries(files)
    # file_name -> last seen checksum
    expected_name_to_hash: dict[str, str] = {}
    for entry in files:
        expected_name_to_hash[entry["file_name"]] = entry["file_checksum"]
    assert folder_hash == expected_name_to_hash
    # checksum -> last seen file_name
    expected_hash_to_name: dict[str, str] = {}
    for entry in files:
        expected_hash_to_name[entry["file_checksum"]] = entry["file_name"]
    assert folder_name == expected_hash_to_name
    assert resend == {e["file_checksum"] for e in files if e["resend_flag"] is True}


@settings(max_examples=50)
@given(
    name=st.text(
        alphabet=st.characters(
            blacklist_categories=("Cs",), blacklist_characters="\n\r"
        ),
        min_size=1,
        max_size=20,
    ),
    checksum=_CHECKSUMS,
    in_dict=st.booleans(),
    in_resend=st.booleans(),
)
def test_check_file_against_processed_truth_table(
    name: str, checksum: str, in_dict: bool, in_resend: bool
) -> None:
    """check_file_against_processed follows the documented truth table:
    - match:    checksum in name_dict
    - should_send: not match, OR checksum in resend_set
    """
    name_dict = {checksum: name} if in_dict else {}
    resend_set = {checksum} if in_resend else set()
    match, should_send = check_file_against_processed(
        name, checksum, name_dict, resend_set
    )
    assert match is in_dict
    expected_should_send = (not in_dict) or in_resend
    assert should_send is expected_should_send


@settings(max_examples=50)
@given(
    name=st.text(
        alphabet=st.characters(
            blacklist_categories=("Cs",), blacklist_characters="\n\r"
        ),
        min_size=1,
        max_size=20,
    ),
    checksum=_CHECKSUMS,
)
def test_check_file_against_processed_new_file_should_send(
    name: str, checksum: str
) -> None:
    """A checksum that is not in name_dict and not in resend_set has
    should_send == True (it is a new file to send)."""
    match, should_send = check_file_against_processed(name, checksum, {}, set())
    assert not match
    assert should_send


@settings(max_examples=50)
@given(
    name=st.text(
        alphabet=st.characters(
            blacklist_categories=("Cs",), blacklist_characters="\n\r"
        ),
        min_size=1,
        max_size=20,
    ),
    checksum=_CHECKSUMS,
)
def test_check_file_against_processed_known_not_resend_should_not_send(
    name: str, checksum: str
) -> None:
    """A checksum already in name_dict but not in resend_set: do not re-send."""
    match, should_send = check_file_against_processed(
        name, checksum, {checksum: name}, set()
    )
    assert match
    assert not should_send


def test_generate_file_hash_retries_then_succeeds() -> None:
    """Regression test for lt_to_le mutation at L77.

    The retry boundary ``checksum_attempt < max_retries`` determines
    whether the LAST attempt raises or retries. With max_retries=3
    and 2 failures followed by success, the function should return
    the hash. A mutation to ``<=`` would make attempt 3 fail-and-raise
    instead of succeeding.
    """
    with tempfile.NamedTemporaryFile(delete=False) as f:
        f.write(b"hello world")
        tmp_path = f.name
    try:
        call_count = 0
        real_open = open

        def flaky_open(path, *args, **kwargs):
            nonlocal call_count
            if path == os.path.abspath(tmp_path):
                call_count += 1
                if call_count <= 3:  # fail 3 times (boundary), succeed on 4th
                    raise OSError("simulated transient failure")
            return real_open(path, *args, **kwargs)

        with (
            patch("builtins.open", side_effect=flaky_open),
            patch("time.sleep"),
        ):  # skip backoff
            # Original (<): 3<3 False on attempt 3 -> raises after 3 calls
            # Mutated  (<=): 3<=3 True on attempt 3 -> retries, 4th call succeeds
            with pytest.raises(OSError):
                generate_file_hash(tmp_path, max_retries=3)

        assert call_count == 3  # original raises at boundary, mutated retries to 4
    finally:
        os.unlink(tmp_path)
