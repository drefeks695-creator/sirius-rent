from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session

from app.auth import authenticate_user, create_access_token, create_user, get_user_by_username
from app.database import get_db
from app.booking_utils import expire_finished_bookings
from app.models import User
from app.openapi_responses import R400, R401, R422, R429, combine
from app.rate_limit import check_login_allowed, clear_login_failures, record_login_failure
from app.schemas import Token, UserCreate, UserResponse

router = APIRouter(prefix="/auth", tags=["Аутентификация"])


@router.post(
    "/register",
    response_model=UserResponse,
    status_code=status.HTTP_201_CREATED,
    responses=combine(R400, R422),
)
def register(data: UserCreate, db: Session = Depends(get_db)):
    if get_user_by_username(db, data.username):
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Пользователь уже существует")
    user = create_user(db, data.username, data.password)
    return user


@router.post(
    "/login",
    response_model=Token,
    responses=combine(R401, R422, R429),
)
def login(form: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    key = form.username.strip().lower()
    check_login_allowed(key)

    user = authenticate_user(db, form.username, form.password)
    if not user:
        record_login_failure(key)
        raise HTTPException(
            status.HTTP_401_UNAUTHORIZED,
            "Неверное имя пользователя или пароль",
            headers={"WWW-Authenticate": "Bearer"},
        )

    clear_login_failures(key)
    expire_finished_bookings(db)
    token = create_access_token(user.id, user.username, user.role)
    return Token(access_token=token)
