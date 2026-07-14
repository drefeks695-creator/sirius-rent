from datetime import date, datetime

from sqlalchemy.orm import Session

from app.dependencies import has_booking_conflict, room_to_response
from app.models import Room
from app.schedule import build_room_schedule, validate_booking_within_hours

MAX_FREE_INTERVALS = 12
MAX_ROOM_SUGGESTIONS = 8


def find_free_intervals(
    room: Room,
    target_date: date,
    db: Session,
    limit: int = MAX_FREE_INTERVALS,
) -> list[dict]:
    schedule = build_room_schedule(room, target_date, db)
    slots = schedule["slots"]
    if not slots:
        return []

    intervals: list[dict] = []
    current_start: datetime | None = None
    current_end: datetime | None = None

    for slot in slots:
        if slot["status"] == "free":
            if current_start is None:
                current_start = slot["start"]
            current_end = slot["end"]
            continue

        if current_start is not None and current_end is not None:
            intervals.append({"start": current_start, "end": current_end})
            current_start = None
            current_end = None

    if current_start is not None and current_end is not None:
        intervals.append({"start": current_start, "end": current_end})

    return intervals[:limit]


def find_available_rooms(
    room_id: int,
    start: datetime,
    end: datetime,
    db: Session,
    limit: int = MAX_ROOM_SUGGESTIONS,
) -> list[dict]:
    rooms = (
        db.query(Room)
        .filter(Room.id != room_id, Room.bookings_blocked.is_(False))
        .order_by(Room.name)
        .all()
    )
    suggestions: list[dict] = []
    for room in rooms:
        try:
            validate_booking_within_hours(room, start, end)
        except ValueError:
            continue
        if has_booking_conflict(db, room.id, start, end):
            continue
        suggestions.append(room_to_response(room))
        if len(suggestions) >= limit:
            break
    return suggestions


def build_booking_suggestions(
    room: Room,
    start: datetime,
    end: datetime,
    db: Session,
) -> dict:
    return {
        "room_id": room.id,
        "start": start,
        "end": end,
        "time_slots": find_free_intervals(room, start.date(), db),
        "rooms": find_available_rooms(room.id, start, end, db),
    }
