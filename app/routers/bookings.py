from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session, joinedload

from app.booking_codes import assign_booking_code
from app.booking_utils import expire_finished_bookings
from app.database import get_db
from app.dependencies import (
    apply_booking_contact_fields,
    booking_to_response,
    get_current_user,
    has_booking_conflict,
    require_booking_profile,
)
from app.models import Booking, BookingStatus, Room, User, UserRole
from app.openapi_responses import AUTH_BODY, combine, R400, R403, R404, R409
from app.schedule import validate_booking_within_hours
from app.schemas import BookingCancelResponse, BookingCreate, BookingResponse

router = APIRouter(prefix="/bookings", tags=["Бронирования"])


@router.post(
    "",
    response_model=BookingResponse,
    status_code=status.HTTP_201_CREATED,
    responses=combine(AUTH_BODY, R400, R403, R404, R409),
)
def create_booking(
    data: BookingCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    expire_finished_bookings(db)

    room = db.query(Room).filter(Room.id == data.room_id).first()
    if not room:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Пространство не найдено")

    if room.bookings_blocked:
        raise HTTPException(
            status.HTTP_403_FORBIDDEN,
            "Бронирование этого пространства временно закрыто администратором",
        )

    apply_booking_contact_fields(
        current_user,
        full_name=data.full_name,
        phone=data.phone,
        email=data.email,
    )
    require_booking_profile(current_user)

    try:
        validate_booking_within_hours(room, data.start_time, data.end_time)
    except ValueError as exc:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, str(exc)) from exc

    db.query(Room).filter(Room.id == data.room_id).with_for_update().one()

    if has_booking_conflict(db, data.room_id, data.start_time, data.end_time):
        raise HTTPException(
            status.HTTP_409_CONFLICT,
            "Пространство уже занято на выбранное время",
        )

    booking = Booking(
        room_id=data.room_id,
        user_id=current_user.id,
        code=assign_booking_code(db, data.start_time),
        start_time=data.start_time,
        end_time=data.end_time,
        status=BookingStatus.active,
    )
    db.add(booking)
    db.commit()
    db.refresh(booking)
    booking.user = current_user
    return booking_to_response(booking)


@router.delete(
    "/{booking_id}",
    response_model=BookingCancelResponse,
    status_code=status.HTTP_200_OK,
    responses=combine(AUTH_BODY, R403, R404),
)
def cancel_booking(
    booking_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    expire_finished_bookings(db)
    booking = (
        db.query(Booking)
        .options(joinedload(Booking.user))
        .filter(Booking.id == booking_id)
        .first()
    )
    if not booking:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Бронирование не найдено")

    if booking.user_id != current_user.id and current_user.role != UserRole.admin:
        raise HTTPException(
            status.HTTP_403_FORBIDDEN,
            "Вы можете отменять только свои бронирования",
        )

    booking.status = BookingStatus.cancelled
    db.commit()
    db.refresh(booking)
    return {"detail": "Бронирование отменено", "booking": booking_to_response(booking)}
