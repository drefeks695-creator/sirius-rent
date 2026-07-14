"""Datetime helpers: naive local time for bookings, aware UTC for JWT."""

from datetime import datetime, timezone


def local_now() -> datetime:
    """Naive local time for booking slots and business rules."""
    return datetime.now()


def utc_now() -> datetime:
    """Aware UTC for JWT expiration."""
    return datetime.now(timezone.utc)
