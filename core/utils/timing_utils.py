"""Timing utilities for performance measurement."""

import time
from contextlib import contextmanager


class TimerResult:
    """Result of a timed operation."""

    __slots__ = ("duration_ms", "start_time", "end_time")

    def __init__(self) -> None:
        self.duration_ms: float = 0
        self.start_time: float = 0
        self.end_time: float = 0


@contextmanager
def context_timer():
    """Context manager for timing code blocks.

    Usage:
        with context_timer() as timer:
            # code to time
            do_work()
        print(f"Duration: {timer.duration_ms}ms")

    Yields:
        TimerResult with duration_ms, start_time, and end_time attributes
    """
    timer = TimerResult()
    timer.start_time = time.perf_counter()
    try:
        yield timer
    finally:
        end = time.perf_counter()
        timer.end_time = end
        timer.duration_ms = (end - timer.start_time) * 1000
