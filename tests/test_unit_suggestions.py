from datetime import datetime

from app.auth import create_user
from app.models import Booking, BookingStatus, Room
from app.suggestions import build_booking_suggestions, find_free_intervals


def test_find_free_intervals_merges_gaps(db_session):
    user = create_user(db_session, "suggest_user", "pass123")
    room = Room(name="Suggest room", capacity=10, equipment="[]")
    db_session.add(room)
    db_session.commit()

    busy_start = datetime(2026, 8, 20, 10, 0)
    busy_end = datetime(2026, 8, 20, 11, 0)
    db_session.add(
        Booking(
            room_id=room.id,
            user_id=user.id,
            code="SR-20260820-BUSY",
            start_time=busy_start,
            end_time=busy_end,
            status=BookingStatus.active,
        )
    )
    db_session.commit()

    intervals = find_free_intervals(room, busy_start.date(), db_session)
    assert intervals
    assert all(item["start"] < item["end"] for item in intervals)
    assert not any(
        item["start"] <= busy_start < item["end"] or item["start"] < busy_end <= item["end"]
        for item in intervals
    )


def test_build_booking_suggestions_lists_free_intervals_and_rooms(db_session):
    user = create_user(db_session, "suggest_user2", "pass123")
    room_a = Room(name="Busy A", capacity=10, equipment="[]")
    room_b = Room(name="Free B", capacity=10, equipment="[]")
    db_session.add_all([room_a, room_b])
    db_session.commit()

    start = datetime(2026, 8, 21, 14, 0)
    end = datetime(2026, 8, 21, 15, 0)
    db_session.add(
        Booking(
            room_id=room_a.id,
            user_id=user.id,
            code="SR-20260821-BUSY",
            start_time=start,
            end_time=end,
            status=BookingStatus.active,
        )
    )
    db_session.commit()

    data = build_booking_suggestions(room_a, start, end, db_session)
    assert data["room_id"] == room_a.id
    assert data["time_slots"]
    assert any(room["id"] == room_b.id for room in data["rooms"])
