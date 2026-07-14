from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from sqlalchemy.orm import Session, joinedload

from app.auth import create_access_token, get_user_by_username
from app.avatars import (
    ALLOWED_CONTENT_TYPES,
    MAX_AVATAR_SIZE,
    custom_avatar_path,
    custom_avatar_url,
    ensure_uploads_dir,
    get_custom_avatar_url,
    has_custom_avatar,
    is_valid_avatar_url,
    remove_custom_avatar,
)
from app.database import get_db
from app.datetime_utils import local_now
from app.image_validation import validate_image_upload
from app.dependencies import get_current_user, user_has_booking_profile
from app.models import Booking, BookingStatus, User
from app.openapi_responses import AUTH, AUTH_BODY, combine, R400, R404
from app.schemas import ProfileResponse, ProfileSaveResponse, ProfileUpdate, Token

router = APIRouter(prefix="/profile", tags=["Профиль"])

def booking_with_room(booking: Booking) -> dict:
    return {
        "id": booking.id,
        "code": booking.code,
        "room_id": booking.room_id,
        "room_name": booking.room.name,
        "user_name": booking.user.username,
        "start_time": booking.start_time,
        "end_time": booking.end_time,
        "status": booking.status,
    }


def profile_response(user: User, db: Session) -> ProfileResponse:
    now = local_now()
    bookings = (
        db.query(Booking)
        .options(joinedload(Booking.room), joinedload(Booking.user))
        .filter(
            Booking.user_id == user.id,
            Booking.status == BookingStatus.active,
            Booking.end_time > now,
        )
        .order_by(Booking.start_time.desc())
        .all()
    )
    return ProfileResponse(
        id=user.id,
        username=user.username,
        avatar_url=user.avatar_url or "/ui/avatars/1.svg",
        full_name=user.full_name or "",
        phone=user.phone or "",
        email=user.email or "",
        booking_profile_complete=user_has_booking_profile(user),
        role=user.role,
        bookings=[booking_with_room(b) for b in bookings],
        custom_avatar_url=get_custom_avatar_url(user.id),
    )


@router.get("/me", response_model=ProfileResponse, responses=AUTH)
def get_profile(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return profile_response(current_user, db)


@router.patch(
    "/me",
    response_model=ProfileSaveResponse,
    responses=combine(AUTH_BODY, R400),
)
def update_profile(
    data: ProfileUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    username_changed = False

    if data.username is not None:
        username = data.username.strip()
        if len(username) < 2:
            raise HTTPException(status.HTTP_400_BAD_REQUEST, "Ник должен быть не короче 2 символов")
        if username != current_user.username:
            existing = get_user_by_username(db, username)
            if existing and existing.id != current_user.id:
                raise HTTPException(status.HTTP_400_BAD_REQUEST, "Этот ник уже занят")
            current_user.username = username
            username_changed = True

    if data.avatar_url is not None:
        if not is_valid_avatar_url(data.avatar_url, current_user.id):
            raise HTTPException(status.HTTP_400_BAD_REQUEST, "Недопустимая аватарка")
        current_user.avatar_url = data.avatar_url

    if data.full_name is not None:
        current_user.full_name = data.full_name

    if data.phone is not None:
        current_user.phone = data.phone

    if data.email is not None:
        current_user.email = data.email

    db.commit()
    db.refresh(current_user)

    profile = profile_response(current_user, db)
    if username_changed:
        token = create_access_token(current_user.id, current_user.username, current_user.role)
        return ProfileSaveResponse(**profile.model_dump(), access_token=token)
    return ProfileSaveResponse(**profile.model_dump())


@router.post(
    "/me/avatar",
    response_model=ProfileSaveResponse,
    responses=combine(AUTH, R400),
)
async def upload_avatar(
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    content_type = (file.content_type or "").split(";", 1)[0].strip().lower()
    if content_type not in ALLOWED_CONTENT_TYPES:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            "Допустимы только JPG, PNG, WEBP или GIF",
        )

    data = await file.read()
    if not data:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Пустой файл")
    if len(data) > MAX_AVATAR_SIZE:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Файл должен быть не больше 2 МБ")

    try:
        validate_image_upload(data, content_type)
    except ValueError as exc:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, str(exc)) from exc

    ensure_uploads_dir()
    ext = ALLOWED_CONTENT_TYPES[content_type]
    remove_custom_avatar(current_user.id)

    path = custom_avatar_path(current_user.id, ext)
    path.write_bytes(data)

    current_user.avatar_url = custom_avatar_url(current_user.id, ext)
    db.commit()
    db.refresh(current_user)

    profile = profile_response(current_user, db)
    return ProfileSaveResponse(**profile.model_dump())


@router.delete(
    "/me/avatar",
    response_model=ProfileSaveResponse,
    responses=combine(AUTH, R404),
)
def delete_avatar(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if not has_custom_avatar(current_user.id):
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Своё фото не найдено")

    remove_custom_avatar(current_user.id)

    custom_prefix = f"/ui/uploads/avatars/{current_user.id}."
    if (current_user.avatar_url or "").startswith(custom_prefix):
        current_user.avatar_url = "/ui/avatars/1.svg"

    db.commit()
    db.refresh(current_user)

    profile = profile_response(current_user, db)
    return ProfileSaveResponse(**profile.model_dump())


@router.post("/me/token", response_model=Token, responses=AUTH)
def refresh_token_after_profile_change(current_user: User = Depends(get_current_user)):
    token = create_access_token(current_user.id, current_user.username, current_user.role)
    return Token(access_token=token)
