from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session, joinedload

from app.auth import get_user_by_username, hash_password
from app.avatars import is_valid_avatar_url, remove_custom_avatar
from app.booking_utils import effective_booking_status, expire_finished_bookings
from app.database import get_db
from app.datetime_utils import local_now
from app.dependencies import booking_to_response, require_admin, user_has_booking_profile
from app.models import Booking, BookingStatus, Room, User, UserRole
from app.openapi_responses import AUTH_ADMIN, AUTH_ADMIN_BODY, combine, R400, R404
from app.schemas import (
    AdminBookingResponse,
    AdminReportBooking,
    AdminReportSummary,
    AdminRoomReport,
    AdminRoomsReportResponse,
    AdminUserResponse,
    AdminUserUpdate,
    MessageResponse,
)

router = APIRouter(prefix="/admin", tags=["Администрирование"])


def admin_user_response(user: User) -> dict:
    return {
        "id": user.id,
        "username": user.username,
        "avatar_url": user.avatar_url or "/ui/avatars/1.svg",
        "full_name": user.full_name or "",
        "phone": user.phone or "",
        "email": user.email or "",
        "booking_profile_complete": user_has_booking_profile(user),
        "role": user.role,
    }


def count_admins(db: Session) -> int:
    return db.query(User).filter(User.role == UserRole.admin).count()


def report_booking_entry(booking: Booking, now=None) -> dict:
    status = effective_booking_status(booking, now)
    return {
        "id": booking.id,
        "code": booking.code,
        "user_name": booking.user.username,
        "start_time": booking.start_time,
        "end_time": booking.end_time,
        "status": status,
    }


@router.get(
    "/reports/rooms",
    response_model=AdminRoomsReportResponse,
    responses=AUTH_ADMIN,
)
def rooms_booking_report(
    db: Session = Depends(get_db),
    _: User = Depends(require_admin),
):
    now = local_now()

    rooms = db.query(Room).order_by(Room.name).all()
    bookings = (
        db.query(Booking)
        .options(joinedload(Booking.room), joinedload(Booking.user))
        .order_by(Booking.start_time.desc())
        .all()
    )

    bookings_by_room: dict[int, list[Booking]] = {room.id: [] for room in rooms}
    for booking in bookings:
        if booking.room_id in bookings_by_room:
            bookings_by_room[booking.room_id].append(booking)

    room_reports: list[dict] = []
    total_booked = 0
    total_cancelled = 0
    total_active = 0
    total_completed = 0

    for room in rooms:
        room_bookings = bookings_by_room.get(room.id, [])
        booked_entries: list[dict] = []
        cancelled_entries: list[dict] = []
        active_count = 0
        completed_count = 0
        cancelled_count = 0

        for booking in room_bookings:
            entry = report_booking_entry(booking, now)
            status = entry["status"]
            if status == BookingStatus.cancelled:
                cancelled_count += 1
                cancelled_entries.append(entry)
            elif status in (BookingStatus.active, BookingStatus.completed):
                booked_entries.append(entry)
                if status == BookingStatus.active:
                    active_count += 1
                else:
                    completed_count += 1

        total_booked += len(booked_entries)
        total_cancelled += cancelled_count
        total_active += active_count
        total_completed += completed_count

        room_reports.append(
            {
                "room_id": room.id,
                "room_name": room.name,
                "capacity": room.capacity,
                "active_count": active_count,
                "completed_count": completed_count,
                "cancelled_count": cancelled_count,
                "booked": booked_entries,
                "cancelled": cancelled_entries,
            }
        )

    return {
        "generated_at": now,
        "summary": {
            "total_rooms": len(rooms),
            "total_booked": total_booked,
            "total_cancelled": total_cancelled,
            "total_active": total_active,
            "total_completed": total_completed,
        },
        "rooms": room_reports,
    }


@router.get(
    "/bookings",
    response_model=list[AdminBookingResponse],
    responses=AUTH_ADMIN,
)
def list_active_bookings(
    db: Session = Depends(get_db),
    _: User = Depends(require_admin),
):
    now = local_now()
    bookings = (
        db.query(Booking)
        .options(joinedload(Booking.room), joinedload(Booking.user))
        .filter(Booking.status == BookingStatus.active, Booking.end_time > now)
        .order_by(Booking.start_time)
        .all()
    )
    return [
        {
            **booking_to_response(booking),
            "room_name": booking.room.name,
        }
        for booking in bookings
    ]


@router.get(
    "/users",
    response_model=list[AdminUserResponse],
    responses=AUTH_ADMIN,
)
def list_users(
    db: Session = Depends(get_db),
    _: User = Depends(require_admin),
):
    users = db.query(User).order_by(User.username).all()
    return [admin_user_response(user) for user in users]


@router.patch(
    "/users/{user_id}",
    response_model=AdminUserResponse,
    responses=combine(AUTH_ADMIN_BODY, R400, R404),
)
def update_user(
    user_id: int,
    data: AdminUserUpdate,
    db: Session = Depends(get_db),
    admin: User = Depends(require_admin),
):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Пользователь не найден")

    if data.username is not None:
        username = data.username.strip()
        if len(username) < 2:
            raise HTTPException(status.HTTP_400_BAD_REQUEST, "Ник должен быть не короче 2 символов")
        if username != user.username:
            existing = get_user_by_username(db, username)
            if existing and existing.id != user.id:
                raise HTTPException(status.HTTP_400_BAD_REQUEST, "Этот ник уже занят")
            user.username = username

    if data.avatar_url is not None:
        if not is_valid_avatar_url(data.avatar_url, user.id):
            raise HTTPException(status.HTTP_400_BAD_REQUEST, "Недопустимая аватарка")
        user.avatar_url = data.avatar_url

    if data.full_name is not None:
        user.full_name = data.full_name

    if data.phone is not None:
        user.phone = data.phone

    if data.email is not None:
        user.email = data.email

    if data.role is not None and data.role != user.role:
        if user.role == UserRole.admin and data.role != UserRole.admin and count_admins(db) <= 1:
            raise HTTPException(
                status.HTTP_400_BAD_REQUEST,
                "Нельзя снять роль у последнего администратора",
            )
        user.role = data.role

    if data.password is not None:
        user.hashed_password = hash_password(data.password)

    if (
        data.username is None
        and data.avatar_url is None
        and data.full_name is None
        and data.phone is None
        and data.email is None
        and data.role is None
        and data.password is None
    ):
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Нечего обновлять")

    db.commit()
    db.refresh(user)
    return admin_user_response(user)


@router.delete(
    "/users/{user_id}",
    response_model=MessageResponse,
    status_code=status.HTTP_200_OK,
    responses=combine(AUTH_ADMIN, R400, R404),
)
def delete_user(
    user_id: int,
    db: Session = Depends(get_db),
    admin: User = Depends(require_admin),
):
    if user_id == admin.id:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Нельзя удалить свой аккаунт")

    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Пользователь не найден")

    if user.role == UserRole.admin and count_admins(db) <= 1:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            "Нельзя удалить последнего администратора",
        )

    db.query(Booking).filter(Booking.user_id == user_id).delete()
    remove_custom_avatar(user_id)
    db.delete(user)
    db.commit()
    return {"detail": "Пользователь удалён"}
