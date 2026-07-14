import secrets
from datetime import datetime

from sqlalchemy.orm import Session

from app.models import Booking


def generate_booking_code(start_time: datetime) -> str:
    date_part = start_time.strftime("%Y%m%d")
    suffix = secrets.token_hex(2).upper()
    return f"SR-{date_part}-{suffix}"


def assign_booking_code(db: Session, start_time: datetime) -> str:
    for _ in range(12):
        code = generate_booking_code(start_time)
        exists = db.query(Booking.id).filter(Booking.code == code).first()
        if not exists:
            return code
    raise RuntimeError("Не удалось сгенерировать уникальный код бронирования")


def backfill_booking_codes(db: Session) -> None:
    bookings = db.query(Booking).filter((Booking.code == "") | (Booking.code.is_(None))).all()
    if not bookings:
        return
    for booking in bookings:
        booking.code = assign_booking_code(db, booking.start_time)
    db.commit()
