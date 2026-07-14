from datetime import datetime

from app.booking_codes import assign_booking_code, generate_booking_code
from app.models import Booking, BookingStatus


def test_generate_booking_code_format():
    start = datetime(2026, 7, 15, 10, 0)
    code = generate_booking_code(start)

    assert code.startswith("SR-20260715-")
    assert len(code) == len("SR-20260715-") + 4


def test_assign_booking_code_is_unique(db_session):
    from app.auth import create_user
    from app.models import Room

    user = create_user(db_session, "code_user", "pass123")
    room = Room(name="Code room", capacity=5, equipment="[]")
    db_session.add(room)
    db_session.commit()

    start = datetime(2026, 8, 1, 12, 0)
    first = assign_booking_code(db_session, start)
    db_session.add(
        Booking(
            room_id=room.id,
            user_id=user.id,
            code=first,
            start_time=start,
            end_time=datetime(2026, 8, 1, 13, 0),
            status=BookingStatus.active,
        )
    )
    db_session.commit()

    second = assign_booking_code(db_session, start)
    assert second != first
    assert second.startswith("SR-20260801-")
