import time
from collections import defaultdict

from fastapi import HTTPException, status

_WINDOW_SEC = 300
_MAX_ATTEMPTS = 5
_failures: dict[str, list[float]] = defaultdict(list)


def _prune(key: str, now: float) -> None:
    _failures[key] = [stamp for stamp in _failures[key] if now - stamp < _WINDOW_SEC]


def check_login_allowed(key: str) -> None:
    now = time.time()
    _prune(key, now)
    if len(_failures[key]) >= _MAX_ATTEMPTS:
        raise HTTPException(
            status.HTTP_429_TOO_MANY_REQUESTS,
            "Слишком много неудачных попыток входа. Подождите 5 минут.",
        )


def record_login_failure(key: str) -> None:
    now = time.time()
    _prune(key, now)
    _failures[key].append(now)


def clear_login_failures(key: str) -> None:
    _failures.pop(key, None)
