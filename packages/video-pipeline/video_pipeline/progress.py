"""Progress callback utilities."""

from typing import Callable, Optional


ProgressCallback = Optional[Callable[[int, str], None]]


def report_progress(callback: ProgressCallback, percent: int, message: str):
    """Report progress if callback exists."""
    if callback:
        callback(percent, message)
