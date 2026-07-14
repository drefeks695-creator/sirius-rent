from datetime import datetime

from app.auth import create_user
from app.dependencies import (
    equipment_to_list,
    equipment_to_str,
    has_booking_conflict,
    user_has_booking_profile,
)
from app.models import Booking, BookingStatus, Room, User


def test_equipment_conversion():
    items = ["проектор", "Wi-Fi", "доска"]
    encoded = equipment_to_str(items)
    assert equipment_to_list(encoded) == items
    assert equipment_to_list("проектор, доска") == ["проектор", "доска"]
    assert equipment_to_list("") == []


def test_user_has_booking_profile():
    user = User(username="profile", hashed_password="x")
    assert not user_has_booking_profile(user)

    user.full_name = "Иванов Иван"
    user.phone = "+79991234567"
    user.email = "ivan@example.com"
    assert user_has_booking_profile(user)

    user.email = "   "
    assert not user_has_booking_profile(user)


def test_has_booking_conflict(db_session):
    user = create_user(db_session, "conflict_user", "pass123")
    room = Room(name="Conflict room", capacity=8, equipment="[]")
    db_session.add(room)
    db_session.commit()

    start = datetime(2026, 9, 10, 10, 0)
    end = datetime(2026, 9, 10, 11, 0)
    booking = Booking(
        room_id=room.id,
        user_id=user.id,
        code="SR-20260910-ABCD",
        start_time=start,
        end_time=end,
        status=BookingStatus.active,
    )
    db_session.add(booking)
    db_session.commit()

    assert has_booking_conflict(db_session, room.id, start, end)
    assert not has_booking_conflict(
        db_session,
        room.id,
        datetime(2026, 9, 10, 11, 0),
        datetime(2026, 9, 10, 12, 0),
    )
    assert not has_booking_conflict(
        db_session,
        room.id,
        start,
        end,
        exclude_booking_id=booking.id,
    )
