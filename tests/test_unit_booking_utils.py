from datetime import datetime, timedelta

from app.booking_utils import (
    booking_blocks_interval,
    booking_blocks_slot,
    booking_occupies_slot,
    expire_finished_bookings,
)
from app.models import Booking, BookingStatus


def _booking(start: datetime, end: datetime, status=BookingStatus.active) -> Booking:
    booking = Booking()
    booking.start_time = start
    booking.end_time = end
    booking.status = status
    return booking


def test_booking_occupies_slot_overlap():
    start = datetime(2026, 7, 15, 10, 0)
    end = datetime(2026, 7, 15, 11, 0)
    booking = _booking(start, end)

    assert booking_occupies_slot(booking, start, end)
    assert booking_occupies_slot(booking, start + timedelta(minutes=15), end - timedelta(minutes=15))
    assert not booking_occupies_slot(booking, end, end + timedelta(hours=1))
    assert not booking_occupies_slot(booking, start - timedelta(hours=1), start)


def test_cancelled_booking_does_not_occupy_slot():
    start = datetime(2026, 7, 15, 10, 0)
    end = datetime(2026, 7, 15, 11, 0)
    booking = _booking(start, end, BookingStatus.cancelled)

    assert not booking_occupies_slot(booking, start, end)


def test_booking_blocks_interval_only_active_future(db_session):
    now = datetime(2026, 7, 15, 12, 0)
    booking = _booking(
        datetime(2026, 7, 15, 10, 0),
        datetime(2026, 7, 15, 11, 0),
        BookingStatus.active,
    )

    assert not booking_blocks_interval(
        booking,
        datetime(2026, 7, 15, 10, 0),
        datetime(2026, 7, 15, 11, 0),
        now=now,
    )

    future_booking = _booking(
        datetime(2026, 7, 15, 13, 0),
        datetime(2026, 7, 15, 14, 0),
    )
    assert booking_blocks_interval(
        future_booking,
        datetime(2026, 7, 15, 13, 30),
        datetime(2026, 7, 15, 14, 30),
        now=now,
    )


def test_booking_blocks_slot_completed_vs_active(db_session):
    now = datetime(2026, 7, 15, 12, 0)
    slot_start = datetime(2026, 7, 15, 10, 0)
    slot_end = datetime(2026, 7, 15, 10, 30)

    completed = _booking(
        datetime(2026, 7, 15, 10, 0),
        datetime(2026, 7, 15, 11, 0),
        BookingStatus.completed,
    )
    assert booking_blocks_slot(completed, slot_start, slot_end, now=now)

    expired_active = _booking(
        datetime(2026, 7, 15, 10, 0),
        datetime(2026, 7, 15, 11, 0),
        BookingStatus.active,
    )
    assert not booking_blocks_slot(expired_active, slot_start, slot_end, now=now)


def test_expire_finished_bookings(db_session):
    from app.auth import create_user
    from app.models import Room

    user = create_user(db_session, "expire_user", "pass123")
    room = Room(name="Expire room", capacity=5, equipment="[]")
    db_session.add(room)
    db_session.commit()

    past = Booking(
        room_id=room.id,
        user_id=user.id,
        code="SR-TEST-001",
        start_time=datetime(2020, 1, 1, 10, 0),
        end_time=datetime(2020, 1, 1, 11, 0),
        status=BookingStatus.active,
    )
    future = Booking(
        room_id=room.id,
        user_id=user.id,
        code="SR-TEST-002",
        start_time=datetime(2099, 1, 1, 10, 0),
        end_time=datetime(2099, 1, 1, 11, 0),
        status=BookingStatus.active,
    )
    db_session.add_all([past, future])
    db_session.commit()

    updated = expire_finished_bookings(db_session, now=datetime(2026, 1, 1, 12, 0))
    assert updated == 1

    db_session.refresh(past)
    db_session.refresh(future)
    assert past.status == BookingStatus.completed
    assert future.status == BookingStatus.active
