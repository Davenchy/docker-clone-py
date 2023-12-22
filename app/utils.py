"""This module contains some utility functions"""
from typing import Any, Callable, TypeVar


def format_size(size: float) -> str:
    """Convert size from bytes into human readable format"""
    isN: bool = size < 0
    size = abs(size)
    for unit in ("", "Ki", "Mi", "Gi", "Ti", "Pi", "Ei", "Zi"):
        if size < 1024.0:
            return f"{'-' if isN else ''}{size:3.1f}{unit}B"
        size /= 1024.0
    return f"{'-' if isN else ''}{size:.1f}YiB"


def format_time(time: int) -> str:
    """gets time in seconds and returns it into human readable format"""
    # !TODO: improve this function to work like real time formatters
    for unit in ("s", "m"):
        if time < 60:
            return f"{time:.1f}{unit}"
        time //= 60
    return f"{time:.1f}h"


T = TypeVar("T")


def load_and_cache(obj: Any, name: str, generator: Callable[[], T]) -> T:
    """generate, load and cache a property"""
    if hasattr(obj, name):
        return getattr(obj, name)
    val = generator()
    setattr(obj, name, val)
    return val
