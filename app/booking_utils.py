from datetime import datetime

from sqlalchemy.orm import Session

from app.datetime_utils import local_now
from app.models import Booking, BookingStatus


def effective_booking_status(
    booking: Booking,
    now: datetime | None = None,
) -> BookingStatus:
    now = now or local_now()
    if booking.status == BookingStatus.active and booking.end_time <= now:
        return BookingStatus.completed
    return booking.status


def expire_finished_bookings(db: Session, now: datetime | None = None, *, commit: bool = True) -> int:
    now = now or local_now()
    updated = (
        db.query(Booking)
        .filter(Booking.status == BookingStatus.active, Booking.end_time <= now)
        .update({Booking.status: BookingStatus.completed}, synchronize_session=False)
    )
    if updated:
        if commit:
            db.commit()
        else:
            db.flush()
    return updated


def booking_blocks_interval(
    booking: Booking,
    start_time: datetime,
    end_time: datetime,
    now: datetime | None = None,
) -> bool:
    now = now or local_now()
    if booking.status != BookingStatus.active:
        return False
    if booking.end_time <= now:
        return False
    return booking.start_time < end_time and booking.end_time > start_time


def booking_occupies_slot(
    booking: Booking,
    slot_start: datetime,
    slot_end: datetime,
) -> bool:
    if booking.status not in (BookingStatus.active, BookingStatus.completed):
        return False
    return booking.start_time < slot_end and booking.end_time > slot_start


def booking_blocks_slot(
    booking: Booking,
    slot_start: datetime,
    slot_end: datetime,
    now: datetime | None = None,
) -> bool:
    if not booking_occupies_slot(booking, slot_start, slot_end):
        return False
    now = now or local_now()
    if booking.status == BookingStatus.completed:
        return True
    return booking.end_time > now
