"""Unit tests for date utility functions."""

from datetime import datetime

import pytest

from core.utils.date_utils import (
    dactime_from_datetime,
    dactime_from_invtime,
    datetime_from_dactime,
    datetime_from_invtime,
    prettify_dates,
)


class TestDactimeRoundTrips:
    """Roundtrip tests for DAC/invoice date helpers."""

    def test_datetime_to_dactime_and_back(self):
        """datetime -> dactime -> datetime preserves date."""
        original = datetime(2024, 1, 24)

        dactime = dactime_from_datetime(original)
        parsed = datetime_from_dactime(int(dactime))

        assert dactime == "1240124"
        assert parsed == datetime(2024, 1, 24)

    def test_invtime_to_datetime(self):
        """MMDDYY invoice time parses correctly."""
        assert datetime_from_invtime("012424") == datetime(2024, 1, 24)

    def test_invtime_to_dactime(self):
        """Invoice time converts to expected DAC format."""
        assert dactime_from_invtime("012424") == "1240124"


class TestPrettifyDates:
    """Tests for prettify_dates."""

    def test_prettify_valid_date(self):
        """Valid DAC date is formatted to mm/dd/yy."""
        assert prettify_dates("1240124") == "01/24/24"

    def test_prettify_with_whitespace(self):
        """Leading/trailing whitespace is handled."""
        assert prettify_dates(" 1240124 ") == "01/24/24"

    @pytest.mark.parametrize(
        "offset,adj_offset,expected",
        [
            (1, 0, "01/25/24"),
            (-1, 0, "01/23/24"),
            (0, 2, "01/26/24"),
            (1, -1, "01/24/24"),
            ("2", 1, "01/27/24"),
        ],
    )
    def test_prettify_offsets(self, offset, adj_offset, expected):
        """Offsets and adjustment offsets are applied deterministically."""
        assert (
            prettify_dates("1240124", offset=offset, adj_offset=adj_offset) == expected
        )

    @pytest.mark.parametrize(
        "bad_value",
        ["", "abc", "9050132", None],
    )
    def test_prettify_invalid_date_returns_not_available(self, bad_value):
        """Invalid inputs safely return fallback string."""
        assert prettify_dates(bad_value) == "Not Available"
