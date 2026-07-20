"""Timing utilities."""

from time import perf_counter


class Stopwatch:
    """Monotonic elapsed-time helper."""

    def __init__(self) -> None:
        self._start = perf_counter()

    @property
    def elapsed_ms(self) -> int:
        return round((perf_counter() - self._start) * 1000)
