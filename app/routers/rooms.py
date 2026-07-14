from datetime import date, datetime, time

from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile, status
from sqlalchemy.orm import Session, joinedload

from app.avatars import ALLOWED_CONTENT_TYPES
from app.database import get_db
from app.image_validation import validate_image_upload
from app.dependencies import (
    booking_to_response,
    equipment_to_str,
    has_booking_conflict,
    require_admin,
    room_to_response,
)
from app.models import Booking, BookingStatus, Room
from app.openapi_responses import AUTH_ADMIN, AUTH_ADMIN_BODY, combine, R400, R404, R422
from app.room_images import (
    MAX_ROOM_IMAGE_SIZE,
    ensure_room_uploads_dir,
    remove_room_image,
    room_image_path,
    room_image_url,
)
from app.schedule import build_month_schedule, build_room_schedule, validate_booking_within_hours
from app.suggestions import build_booking_suggestions
from app.schemas import (
    BookingResponse,
    BookingSuggestionsResponse,
    MessageResponse,
    RoomAvailabilityResponse,
    RoomCreate,
    RoomMonthScheduleResponse,
    RoomResponse,
    RoomScheduleResponse,
    RoomUpdate,
)

router = APIRouter(prefix="/rooms", tags=["Пространства"])


@router.post(
    "",
    response_model=RoomResponse,
    status_code=status.HTTP_201_CREATED,
    responses=combine(AUTH_ADMIN_BODY, R422),
)
def create_room(
    data: RoomCreate,
    db: Session = Depends(get_db),
    _: object = Depends(require_admin),
):
    room = Room(
        name=data.name,
        capacity=data.capacity,
        description=data.description,
        image_url=data.image_url,
        equipment=equipment_to_str(data.equipment),
        open_time=data.open_time,
        close_time=data.close_time,
    )
    db.add(room)
    db.commit()
    db.refresh(room)
    return room_to_response(room)


@router.post(
    "/{room_id}/image",
    response_model=RoomResponse,
    responses=combine(AUTH_ADMIN, R400, R404),
)
async def upload_room_image(
    room_id: int,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    _: object = Depends(require_admin),
):
    room = db.query(Room).filter(Room.id == room_id).first()
    if not room:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Пространство не найдено")

    content_type = (file.content_type or "").split(";", 1)[0].strip().lower()
    if content_type not in ALLOWED_CONTENT_TYPES:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            "Допустимы только JPG, PNG, WEBP или GIF",
        )

    data = await file.read()
    if not data:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Пустой файл")
    if len(data) > MAX_ROOM_IMAGE_SIZE:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Файл должен быть не больше 5 МБ")

    try:
        validate_image_upload(data, content_type)
    except ValueError as exc:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, str(exc)) from exc

    ensure_room_uploads_dir()
    ext = ALLOWED_CONTENT_TYPES[content_type]
    remove_room_image(room_id)

    path = room_image_path(room_id, ext)
    path.write_bytes(data)

    room.image_url = room_image_url(room_id, ext)
    db.commit()
    db.refresh(room)
    return room_to_response(room)


@router.get("", response_model=list[RoomResponse])
def list_rooms(
    capacity: int | None = Query(default=None, ge=1, alias="capacity_min"),
    capacity_max: int | None = Query(default=None, ge=1),
    equipment: str | None = Query(default=None, description="Фильтр по оборудованию"),
    db: Session = Depends(get_db),
):
    query = db.query(Room)
    if capacity is not None:
        query = query.filter(Room.capacity >= capacity)
    if capacity_max is not None:
        query = query.filter(Room.capacity <= capacity_max)
    rooms = query.all()
    if equipment:
        equipment_lower = equipment.lower()
        rooms = [
            room
            for room in rooms
            if any(
                equipment_lower in item.lower()
                for item in room_to_response(room)["equipment"]
            )
        ]
    return [room_to_response(room) for room in rooms]


@router.get(
    "/available",
    response_model=list[RoomResponse],
    responses=combine(R400, R422),
)
def available_rooms(
    start: datetime = Query(..., description="Начало интервала (ISO 8601)"),
    end: datetime = Query(..., description="Конец интервала (ISO 8601)"),
    capacity: int | None = Query(default=None, ge=1),
    db: Session = Depends(get_db),
):
    if end <= start:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Некорректный временной интервал")

    query = db.query(Room)
    if capacity is not None:
        query = query.filter(Room.capacity >= capacity)

    available = []
    for room in query.all():
        if room.bookings_blocked:
            continue
        if not has_booking_conflict(db, room.id, start, end):
            available.append(room_to_response(room))
    return available


@router.get(
    "/{room_id}/availability",
    response_model=RoomAvailabilityResponse,
    responses=combine(R400, R404, R422),
)
def check_room_availability(
    room_id: int,
    start: datetime = Query(..., description="Начало интервала (ISO 8601)"),
    end: datetime = Query(..., description="Конец интервала (ISO 8601)"),
    db: Session = Depends(get_db),
):
    if end <= start:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Некорректный временной интервал")

    room = db.query(Room).filter(Room.id == room_id).first()
    if not room:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Пространство не найдено")

    if room.bookings_blocked:
        return RoomAvailabilityResponse(room_id=room_id, available=False, start=start, end=end)

    try:
        validate_booking_within_hours(room, start, end)
    except ValueError as exc:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, str(exc)) from exc

    available = not has_booking_conflict(db, room_id, start, end)
    return RoomAvailabilityResponse(room_id=room_id, available=available, start=start, end=end)


@router.get(
    "/{room_id}/suggestions",
    response_model=BookingSuggestionsResponse,
    responses=combine(R400, R404, R422),
)
def room_booking_suggestions(
    room_id: int,
    start: datetime = Query(..., description="Начало интервала (ISO 8601)"),
    end: datetime = Query(..., description="Конец интервала (ISO 8601)"),
    db: Session = Depends(get_db),
):
    if end <= start:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Некорректный временной интервал")

    room = db.query(Room).filter(Room.id == room_id).first()
    if not room:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Пространство не найдено")

    return BookingSuggestionsResponse(**build_booking_suggestions(room, start, end, db))


@router.get("/{room_id}", response_model=RoomResponse, responses=R404)
def get_room(room_id: int, db: Session = Depends(get_db)):
    room = db.query(Room).filter(Room.id == room_id).first()
    if not room:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Пространство не найдено")
    return room_to_response(room)


@router.put(
    "/{room_id}",
    response_model=RoomResponse,
    responses=combine(AUTH_ADMIN_BODY, R404, R422),
)
def update_room(
    room_id: int,
    data: RoomUpdate,
    db: Session = Depends(get_db),
    _: object = Depends(require_admin),
):
    room = db.query(Room).filter(Room.id == room_id).first()
    if not room:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Пространство не найдено")

    if data.name is not None:
        room.name = data.name
    if data.capacity is not None:
        room.capacity = data.capacity
    if data.description is not None:
        room.description = data.description
    if data.image_url is not None:
        room.image_url = data.image_url
    if data.equipment is not None:
        room.equipment = equipment_to_str(data.equipment)
    if data.bookings_blocked is not None:
        room.bookings_blocked = data.bookings_blocked
    if data.open_time is not None:
        room.open_time = data.open_time
    if data.close_time is not None:
        room.close_time = data.close_time

    db.commit()
    db.refresh(room)
    return room_to_response(room)


@router.delete(
    "/{room_id}",
    response_model=MessageResponse,
    status_code=status.HTTP_200_OK,
    responses=combine(AUTH_ADMIN, R404),
)
def delete_room(
    room_id: int,
    db: Session = Depends(get_db),
    _: object = Depends(require_admin),
):
    room = db.query(Room).filter(Room.id == room_id).first()
    if not room:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Пространство не найдено")
    remove_room_image(room_id)
    db.delete(room)
    db.commit()
    return {"detail": "Пространство удалено"}


@router.get(
    "/{room_id}/bookings",
    response_model=list[BookingResponse],
    responses=combine(R404, R422),
)
def room_bookings(
    room_id: int,
    date: date = Query(..., description="Дата в формате YYYY-MM-DD"),
    db: Session = Depends(get_db),
):
    room = db.query(Room).filter(Room.id == room_id).first()
    if not room:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Пространство не найдено")

    day_start = datetime.combine(date, time.min)
    day_end = datetime.combine(date, time.max)

    bookings = (
        db.query(Booking)
        .options(joinedload(Booking.user))
        .filter(
            Booking.room_id == room_id,
            Booking.status == BookingStatus.active,
            Booking.start_time <= day_end,
            Booking.end_time >= day_start,
        )
        .order_by(Booking.start_time)
        .all()
    )
    return [booking_to_response(b, public=True) for b in bookings]


@router.get(
    "/{room_id}/schedule/month",
    response_model=RoomMonthScheduleResponse,
    responses=combine(R404, R422),
)
def room_month_schedule(
    room_id: int,
    year: int = Query(..., ge=2020, le=2100),
    month: int = Query(..., ge=1, le=12),
    db: Session = Depends(get_db),
):
    room = db.query(Room).filter(Room.id == room_id).first()
    if not room:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Пространство не найдено")
    schedule = build_month_schedule(room, year, month, db)
    return RoomMonthScheduleResponse(**schedule)


@router.get(
    "/{room_id}/schedule",
    response_model=RoomScheduleResponse,
    responses=combine(R404, R422),
)
def room_schedule(
    room_id: int,
    date: date = Query(..., description="Дата в формате YYYY-MM-DD"),
    db: Session = Depends(get_db),
):
    room = _get_room_or_404(db, room_id)
    schedule = build_room_schedule(room, date, db)
    return RoomScheduleResponse(
        room_id=schedule["room_id"],
        room_name=schedule["room_name"],
        date=schedule["date"],
        open_time=schedule["open_time"],
        close_time=schedule["close_time"],
        current_status=schedule["current_status"],
        free_slots=schedule["free_slots"],
        busy_slots=schedule["busy_slots"],
        slots=schedule["slots"],
        bookings=[booking_to_response(b, public=True) for b in schedule["bookings"]],
    )


def _get_room_or_404(db: Session, room_id: int) -> Room:
    room = db.query(Room).filter(Room.id == room_id).first()
    if not room:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Пространство не найдено")
    return room
