from datetime import date, datetime, time, timedelta

import pytest

from app.models import Booking, BookingStatus, Room
from app.schedule import (
    day_calendar_status,
    get_current_status,
    get_room_hours,
    parse_hm,
    validate_booking_within_hours,
    working_hours_bounds,
)


def _room(name: str, open_time: str = "08:00", close_time: str = "22:00") -> Room:
    room = Room()
    room.name = name
    room.open_time = open_time
    room.close_time = close_time
    return room


def test_parse_hm():
    assert parse_hm("08:00") == time(8, 0)
    assert parse_hm("21:30") == time(21, 30)


def test_get_room_hours_known_and_default():
    room = _room("Аудитория Б-205", "08:00", "21:00")
    hours = get_room_hours(room)
    assert hours["open"] == "08:00"
    assert hours["close"] == "21:00"

    default = get_room_hours(_room("Неизвестная комната"))
    assert default["open"] == "08:00"
    assert default["close"] == "22:00"


def test_validate_booking_within_hours():
    room = _room("Переговорная А-101")
    future = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0) + timedelta(days=2)
    start = future.replace(hour=10, minute=0)
    end = future.replace(hour=11, minute=0)
    validate_booking_within_hours(room, start, end)

    with pytest.raises(ValueError, match="08:00"):
        validate_booking_within_hours(
            room,
            future.replace(hour=7, minute=0),
            future.replace(hour=8, minute=0),
        )

    with pytest.raises(ValueError, match="один день"):
        validate_booking_within_hours(
            room,
            datetime(2026, 7, 15, 22, 0),
            datetime(2026, 7, 16, 1, 0),
        )


def test_working_hours_bounds():
    room = _room("Коворкинг С-12", "08:00", "23:00")
    day_open, day_close = working_hours_bounds(room, date(2026, 7, 15))
    assert day_open == datetime(2026, 7, 15, 8, 0)
    assert day_close == datetime(2026, 7, 15, 23, 0)


def test_day_calendar_status():
    now = datetime(2026, 7, 15, 12, 0)

    assert day_calendar_status(date(2026, 7, 14), 10, 0, now=now) == "closed"
    assert day_calendar_status(date(2026, 7, 16), 10, 0, now=now) == "free"
    assert day_calendar_status(date(2026, 7, 16), 0, 10, now=now) == "busy"
    assert day_calendar_status(date(2026, 7, 16), 5, 5, now=now) == "partial"


def _booking(start: datetime, end: datetime, status=BookingStatus.active) -> Booking:
    booking = Booking()
    booking.status = status
    booking.start_time = start
    booking.end_time = end
    return booking


def test_get_current_status():
    room = _room("Переговорная А-101")
    now = datetime(2026, 7, 15, 12, 0)
    bookings = [
        _booking(
            datetime(2026, 7, 15, 11, 30),
            datetime(2026, 7, 15, 13, 0),
        )
    ]

    assert get_current_status(room, bookings, now) == "busy"
    assert get_current_status(room, [], now) == "free"
    assert get_current_status(room, [], datetime(2026, 7, 15, 7, 0)) == "closed"
    assert get_current_status(room, [], datetime(2026, 7, 15, 23, 0)) == "closed"
