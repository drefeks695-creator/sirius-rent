import json
from datetime import datetime

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session

from app.auth import decode_token
from app.database import get_db
from app.datetime_utils import local_now
from app.models import Booking, BookingStatus, Room, User, UserRole
from app.schemas import ProfileUpdate

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")


def get_current_user(
    token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)
) -> User:
    payload = decode_token(token)
    if not payload or "sub" not in payload:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Недействительный токен")
    user = db.query(User).filter(User.id == int(payload["sub"])).first()
    if not user:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Пользователь не найден")
    return user


def user_has_booking_profile(user: User) -> bool:
    return (
        bool((user.full_name or "").strip())
        and bool((user.phone or "").strip())
        and bool((user.email or "").strip())
    )


def require_booking_profile(user: User) -> None:
    if not user_has_booking_profile(user):
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            "Укажите ФИО, телефон и почту перед бронированием",
        )


def apply_booking_contact_fields(
    user: User,
    *,
    full_name: str | None = None,
    phone: str | None = None,
    email: str | None = None,
) -> None:
    payload = {}
    if full_name is not None:
        payload["full_name"] = full_name
    if phone is not None:
        payload["phone"] = phone
    if email is not None:
        payload["email"] = email
    if not payload:
        return

    data = ProfileUpdate(**payload)
    if data.full_name is not None:
        user.full_name = data.full_name
    if data.phone is not None:
        user.phone = data.phone
    if data.email is not None:
        user.email = data.email


def require_admin(user: User = Depends(get_current_user)) -> User:
    if user.role != UserRole.admin:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Требуются права администратора")
    return user


def equipment_to_list(equipment: str) -> list[str]:
    if not equipment:
        return []
    try:
        data = json.loads(equipment)
        return data if isinstance(data, list) else []
    except json.JSONDecodeError:
        return [item.strip() for item in equipment.split(",") if item.strip()]


def equipment_to_str(equipment: list[str]) -> str:
    return json.dumps(equipment, ensure_ascii=False)


def room_to_response(room: Room) -> dict:
    image_url = room.image_url or f"/ui/images/room-{room.id}.webp"
    return {
        "id": room.id,
        "name": room.name,
        "capacity": room.capacity,
        "description": room.description or "",
        "image_url": image_url,
        "equipment": equipment_to_list(room.equipment),
        "bookings_blocked": bool(room.bookings_blocked),
        "open_time": room.open_time or "08:00",
        "close_time": room.close_time or "22:00",
    }


def booking_to_response(booking: Booking, *, public: bool = False) -> dict:
    user_name = "Занято" if public else booking.user.username
    full_name = "" if public else (booking.user.full_name or "")
    phone = "" if public else (booking.user.phone or "")
    email = "" if public else (booking.user.email or "")
    return {
        "id": booking.id,
        "code": booking.code,
        "room_id": booking.room_id,
        "user_name": user_name,
        "full_name": full_name,
        "phone": phone,
        "email": email,
        "start_time": booking.start_time,
        "end_time": booking.end_time,
        "status": booking.status,
    }


def has_booking_conflict(
    db: Session,
    room_id: int,
    start_time: datetime,
    end_time: datetime,
    exclude_booking_id: int | None = None,
) -> bool:
    now = local_now()
    query = db.query(Booking).filter(
        Booking.room_id == room_id,
        Booking.status == BookingStatus.active,
        Booking.end_time > now,
        Booking.start_time < end_time,
        Booking.end_time > start_time,
    )
    if exclude_booking_id is not None:
        query = query.filter(Booking.id != exclude_booking_id)
    return query.first() is not None
