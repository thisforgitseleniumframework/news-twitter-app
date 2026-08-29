"""
Shared Chromium profile + lock for X browser automation.

Playwright persistent contexts cannot share the same user_data_dir concurrently,
so posting and trend scraping must take turns.
"""
from __future__ import annotations

import threading
from pathlib import Path
from typing import Optional

PROFILE_DIR = Path(__file__).resolve().parent.parent.parent / ".x_browser_profile"

_lock = threading.Lock()
_busy_reason: Optional[str] = None


def profile_dir() -> Path:
    PROFILE_DIR.mkdir(parents=True, exist_ok=True)
    return PROFILE_DIR


def is_browser_busy() -> bool:
    return _busy_reason is not None


def busy_reason() -> Optional[str]:
    return _busy_reason


def try_acquire(reason: str) -> Optional[str]:
    """
    Try to claim exclusive use of the X browser profile.
    Returns None on success, or an error message if busy.
    """
    global _busy_reason
    with _lock:
        if _busy_reason is not None:
            return (
                f"Browser is busy with: {_busy_reason}. "
                "Finish or close that session, then try again."
            )
        _busy_reason = reason
        return None


def release() -> None:
    global _busy_reason
    with _lock:
        _busy_reason = None
