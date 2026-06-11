"""Tests for core.utils.timing_utils."""

from __future__ import annotations

import time

from core.utils.timing_utils import TimerResult, context_timer


class TestTimerResult:
    """``TimerResult`` holds the duration of a timed block."""

    def test_initial_state(self):
        result = TimerResult()
        assert result.duration_ms == 0
        assert result.start_time == 0
        assert result.end_time == 0

    def test_attributes_writable(self):
        result = TimerResult()
        result.start_time = 1.0
        result.end_time = 2.0
        result.duration_ms = 1000.0
        assert result.start_time == 1.0
        assert result.end_time == 2.0
        assert result.duration_ms == 1000.0

    def test_slots(self):
        # ``__slots__`` prevents arbitrary attribute assignment
        result = TimerResult()
        import pytest

        with pytest.raises(AttributeError):
            result.unexpected = 1  # type: ignore[attr-defined]


class TestContextTimer:
    """``context_timer`` measures wall-clock duration of a code block."""

    def test_yields_timer_result(self):
        with context_timer() as timer:
            assert isinstance(timer, TimerResult)

    def test_sets_start_time_before_yield(self):
        with context_timer() as timer:
            assert timer.start_time > 0
            # end_time not yet set on enter
            assert timer.end_time == 0
            assert timer.duration_ms == 0

    def test_measures_duration(self):
        with context_timer() as timer:
            time.sleep(0.01)
        # At least the sleep duration, with some tolerance
        assert timer.duration_ms >= 5  # 5ms tolerance
        assert timer.end_time >= timer.start_time

    def test_measures_zero_duration_for_empty_block(self):
        with context_timer() as timer:
            pass
        # Both should be very close
        assert timer.end_time >= timer.start_time
        assert timer.duration_ms >= 0
        assert timer.duration_ms < 1000  # Less than a second

    def test_records_end_time_on_exit(self):
        with context_timer() as timer:
            time.sleep(0.001)
        assert timer.end_time > 0
        assert timer.end_time >= timer.start_time
        assert abs(timer.end_time - timer.start_time - timer.duration_ms / 1000) < 0.01

    def test_finalizes_on_exception(self):
        timer_holder = {}

        class _TestFailed(Exception):
            pass

        try:
            with context_timer() as timer:
                timer_holder["t"] = timer
                time.sleep(0.005)
                raise _TestFailed()
        except _TestFailed:
            pass

        timer = timer_holder["t"]
        # Even on exception, finally block must run
        assert timer.duration_ms > 0
        assert timer.end_time >= timer.start_time
