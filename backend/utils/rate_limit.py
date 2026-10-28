# rate_limit.py
# Simple in-memory limit on failed logins.

import time

MAX_FAILURES = 5
WINDOW_SECONDS = 300  # 5 minutes

_failures = {}  # key -> list of timestamps


def _recent(key):
    now = time.time()
    kept = [t for t in _failures.get(key, []) if now - t < WINDOW_SECONDS]
    _failures[key] = kept
    return kept


def is_blocked(key):
    return len(_recent(key)) >= MAX_FAILURES


def record_failure(key):
    _recent(key).append(time.time())


def clear(key):
    _failures.pop(key, None)