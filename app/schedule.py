from datetime import date, datetime, time, timedelta
from typing import Literal

from sqlalchemy.orm import Session, joinedload

from app.booking_utils import booking_occupies_slot
from app.datetime_utils import local_now
from app.models import Booking, BookingStatus, Room

SLOT_MINUTES = 30

DEFAULT_HOURS = {"open": "08:00", "close": "22:00"}

ROOM_HOURS: dict[str, dict[str, str]] = {
    "Переговорная А-101": {"open": "08:00", "close": "22:00"},
    "Аудитория Б-205": {"open": "08:00", "close": "21:00"},
    "Коворкинг С-12": {"open": "08:00", "close": "23:00"},
    "Актовый зал «Центральный»": {"open": "09:00", "close": "21:00"},
    "Учебный класс К-18": {"open": "08:00", "close": "20:00"},
}

Status = Literal["free", "busy", "closed"]


def parse_hm(value: str) -> time:
    hour, minute = value.split(":")
    return time(int(hour), int(minute))


def get_room_hours(room: Room) -> dict[str, str]:
    return {
        "open": room.open_time or DEFAULT_HOURS["open"],
        "close": room.close_time or DEFAULT_HOURS["close"],
    }


def day_bounds(target_date: date) -> tuple[datetime, datetime]:
    day_start = datetime.combine(target_date, time.min)
    day_end = datetime.combine(target_date, time.max)
    return day_start, day_end


def working_hours_bounds(room: Room, target_date: date) -> tuple[datetime, datetime]:
    hours = get_room_hours(room)
    return (
        datetime.combine(target_date, parse_hm(hours["open"])),
        datetime.combine(target_date, parse_hm(hours["close"])),
    )


def validate_booking_within_hours(room: Room, start_time: datetime, end_time: datetime) -> None:
    if start_time.date() != end_time.date():
        raise ValueError("Бронирование должно укладываться в один день")
    if start_time < local_now():
        raise ValueError("Нельзя бронировать время в прошлом")
    day_open, day_close = working_hours_bounds(room, start_time.date())
    hours = get_room_hours(room)
    if start_time < day_open or end_time > day_close:
        raise ValueError(
            f"Доступно с {hours['open']} до {hours['close']} в день бронирования"
        )


def booking_overlaps_day(booking: Booking, target_date: date) -> bool:
    day_start, day_end = day_bounds(target_date)
    return booking.start_time < day_end and booking.end_time > day_start


def get_current_status(room: Room, bookings: list[Booking], now: datetime) -> Status:
    hours = get_room_hours(room)
    today_open = datetime.combine(now.date(), parse_hm(hours["open"]))
    today_close = datetime.combine(now.date(), parse_hm(hours["close"]))
    if now < today_open or now >= today_close:
        return "closed"
    for booking in bookings:
        if booking.status == BookingStatus.active and booking.start_time <= now < booking.end_time:
            return "busy"
        if booking.status == BookingStatus.completed and booking.start_time <= now < booking.end_time:
            return "busy"
    return "free"


def build_room_schedule(room: Room, target_date: date, db: Session) -> dict:
    hours = get_room_hours(room)
    work_start, work_end = working_hours_bounds(room, target_date)
    day_start, day_end = day_bounds(target_date)

    bookings = (
        db.query(Booking)
        .options(joinedload(Booking.user))
        .filter(
            Booking.room_id == room.id,
            Booking.status.in_([BookingStatus.active, BookingStatus.completed]),
            Booking.start_time < day_end,
            Booking.end_time > day_start,
        )
        .order_by(Booking.start_time)
        .all()
    )

    slots = []
    current = work_start
    delta = timedelta(minutes=SLOT_MINUTES)
    while current + delta <= work_end:
        slot_end = current + delta
        status: Literal["free", "busy"] = "free"
        for booking in bookings:
            if booking_occupies_slot(booking, current, slot_end):
                status = "busy"
                break
        slots.append({"start": current, "end": slot_end, "status": status})
        current = slot_end

    now = local_now()
    if target_date < now.date():
        current_status: Status = "closed"
    elif target_date > now.date():
        current_status = "free"
    else:
        current_status = get_current_status(room, bookings, now)

    free_slots = sum(1 for slot in slots if slot["status"] == "free")
    busy_slots = sum(1 for slot in slots if slot["status"] == "busy")

    return {
        "room_id": room.id,
        "room_name": room.name,
        "date": target_date,
        "open_time": hours["open"],
        "close_time": hours["close"],
        "current_status": current_status,
        "free_slots": free_slots,
        "busy_slots": busy_slots,
        "slots": slots,
        "bookings": bookings,
    }


def day_calendar_status(
    target_date: date,
    free_slots: int,
    busy_slots: int,
    now: datetime | None = None,
) -> Literal["free", "partial", "busy", "closed"]:
    now = now or local_now()
    if target_date < now.date():
        return "closed"
    if busy_slots == 0:
        return "free"
    if free_slots == 0:
        return "busy"
    return "partial"


def _day_summary(
    room: Room,
    target_date: date,
    bookings: list[Booking],
    now: datetime,
) -> dict:
    work_start, work_end = working_hours_bounds(room, target_date)

    day_bookings = [
        booking for booking in bookings if booking_overlaps_day(booking, target_date)
    ]

    slots = []
    current = work_start
    delta = timedelta(minutes=SLOT_MINUTES)
    while current + delta <= work_end:
        slot_end = current + delta
        status: Literal["free", "busy"] = "free"
        for booking in day_bookings:
            if booking_occupies_slot(booking, current, slot_end):
                status = "busy"
                break
        slots.append({"start": current, "end": slot_end, "status": status})
        current = slot_end

    free_slots = sum(1 for slot in slots if slot["status"] == "free")
    busy_slots = sum(1 for slot in slots if slot["status"] == "busy")

    return {
        "date": target_date,
        "status": day_calendar_status(target_date, free_slots, busy_slots, now),
        "free_slots": free_slots,
        "busy_slots": busy_slots,
        "bookings_count": len(day_bookings),
    }


def build_month_schedule(room: Room, year: int, month: int, db: Session) -> dict:
    import calendar

    hours = get_room_hours(room)
    _, last_day = calendar.monthrange(year, month)
    month_start = date(year, month, 1)
    month_end = date(year, month, last_day)
    range_start, _ = day_bounds(month_start)
    _, range_end = day_bounds(month_end)

    bookings = (
        db.query(Booking)
        .options(joinedload(Booking.user))
        .filter(
            Booking.room_id == room.id,
            Booking.status.in_([BookingStatus.active, BookingStatus.completed]),
            Booking.start_time < range_end,
            Booking.end_time > range_start,
        )
        .all()
    )

    now = local_now()
    days = [
        _day_summary(room, date(year, month, day_num), bookings, now)
        for day_num in range(1, last_day + 1)
    ]

    return {
        "room_id": room.id,
        "room_name": room.name,
        "year": year,
        "month": month,
        "open_time": hours["open"],
        "close_time": hours["close"],
        "days": days,
    }
