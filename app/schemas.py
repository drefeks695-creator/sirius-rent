from datetime import date, datetime
import re
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from app.models import BookingStatus, UserRole


class UserCreate(BaseModel):
    username: str = Field(min_length=2, max_length=100)
    password: str = Field(min_length=8, max_length=100)


class UserResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    username: str
    avatar_url: str
    role: UserRole


class ProfileUpdate(BaseModel):
    username: str | None = Field(default=None, min_length=2, max_length=100)
    avatar_url: str | None = Field(default=None, max_length=500)
    full_name: str | None = Field(default=None, max_length=200)
    phone: str | None = Field(default=None, max_length=30)
    email: str | None = Field(default=None, max_length=200)

    @field_validator("full_name")
    @classmethod
    def validate_full_name(cls, value: str | None) -> str | None:
        if value is None:
            return None
        name = " ".join(value.split())
        if len(name) < 3:
            raise ValueError("ФИО должно быть не короче 3 символов")
        return name

    @field_validator("phone")
    @classmethod
    def validate_phone(cls, value: str | None) -> str | None:
        if value is None:
            return None
        phone = value.strip()
        digits = re.sub(r"\D", "", phone)
        if len(digits) < 10 or len(digits) > 15:
            raise ValueError("Введите корректный номер телефона")
        return phone

    @field_validator("email")
    @classmethod
    def validate_email(cls, value: str | None) -> str | None:
        if value is None:
            return None
        email = value.strip().lower()
        if not re.fullmatch(r"[^@\s]+@[^@\s]+\.[^@\s]+", email):
            raise ValueError("Введите корректный адрес почты")
        return email


class MyBookingResponse(BaseModel):
    id: int
    code: str
    room_id: int
    room_name: str
    user_name: str
    start_time: datetime
    end_time: datetime
    status: BookingStatus


class ProfileResponse(BaseModel):
    id: int
    username: str
    avatar_url: str
    full_name: str = ""
    phone: str = ""
    email: str = ""
    booking_profile_complete: bool = False
    role: UserRole
    bookings: list[MyBookingResponse]
    custom_avatar_url: str | None = None


class ProfileSaveResponse(ProfileResponse):
    access_token: str | None = None


class AdminUserResponse(BaseModel):
    id: int
    username: str
    avatar_url: str
    full_name: str = ""
    phone: str = ""
    email: str = ""
    booking_profile_complete: bool = False
    role: UserRole


class AdminUserUpdate(BaseModel):
    username: str | None = Field(default=None, min_length=2, max_length=100)
    role: UserRole | None = None
    avatar_url: str | None = Field(default=None, max_length=500)
    full_name: str | None = Field(default=None, max_length=200)
    phone: str | None = Field(default=None, max_length=30)
    email: str | None = Field(default=None, max_length=200)
    password: str | None = Field(default=None, min_length=8, max_length=100)

    @field_validator("full_name")
    @classmethod
    def validate_full_name(cls, value: str | None) -> str | None:
        if value is None:
            return None
        return " ".join(value.split())

    @field_validator("phone")
    @classmethod
    def validate_phone(cls, value: str | None) -> str | None:
        if value is None or not value.strip():
            return ""
        phone = value.strip()
        digits = re.sub(r"\D", "", phone)
        if len(digits) < 10 or len(digits) > 15:
            raise ValueError("Введите корректный номер телефона")
        return phone

    @field_validator("email")
    @classmethod
    def validate_email(cls, value: str | None) -> str | None:
        if value is None or not value.strip():
            return ""
        email = value.strip().lower()
        if not re.fullmatch(r"[^@\s]+@[^@\s]+\.[^@\s]+", email):
            raise ValueError("Введите корректный адрес почты")
        return email


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"


class RoomCreate(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    capacity: int = Field(gt=0, le=10000)
    description: str = Field(default="", max_length=2000)
    image_url: str = Field(default="", max_length=500)
    equipment: list[str] = Field(default_factory=list)
    open_time: str = Field(default="08:00", pattern=r"^\d{2}:\d{2}$")
    close_time: str = Field(default="22:00", pattern=r"^\d{2}:\d{2}$")


class RoomUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=200)
    capacity: int | None = Field(default=None, gt=0, le=10000)
    description: str | None = Field(default=None, max_length=2000)
    image_url: str | None = Field(default=None, max_length=500)
    equipment: list[str] | None = None
    bookings_blocked: bool | None = None
    open_time: str | None = Field(default=None, pattern=r"^\d{2}:\d{2}$")
    close_time: str | None = Field(default=None, pattern=r"^\d{2}:\d{2}$")


class RoomResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    capacity: int
    description: str
    image_url: str
    equipment: list[str]
    bookings_blocked: bool = False
    open_time: str = "08:00"
    close_time: str = "22:00"


class RoomAvailabilityResponse(BaseModel):
    room_id: int
    available: bool
    start: datetime
    end: datetime


class TimeSlotSuggestion(BaseModel):
    start: datetime
    end: datetime


class BookingSuggestionsResponse(BaseModel):
    room_id: int
    start: datetime
    end: datetime
    time_slots: list[TimeSlotSuggestion]
    rooms: list[RoomResponse]


class BookingCreate(BaseModel):
    room_id: int
    start_time: datetime
    end_time: datetime
    full_name: str | None = Field(
        default=None,
        max_length=200,
        description="ФИО для подтверждения брони",
    )
    phone: str | None = Field(
        default=None,
        max_length=30,
        description="Телефон для связи",
    )
    email: str | None = Field(
        default=None,
        max_length=200,
        description="Почта для уведомлений",
    )

    @field_validator("full_name")
    @classmethod
    def validate_full_name(cls, value: str | None) -> str | None:
        if value is None:
            return None
        name = " ".join(value.split())
        if len(name) < 3:
            raise ValueError("ФИО должно быть не короче 3 символов")
        return name

    @field_validator("phone")
    @classmethod
    def validate_phone(cls, value: str | None) -> str | None:
        if value is None:
            return None
        phone = value.strip()
        digits = re.sub(r"\D", "", phone)
        if len(digits) < 10 or len(digits) > 15:
            raise ValueError("Введите корректный номер телефона")
        return phone

    @field_validator("email")
    @classmethod
    def validate_email(cls, value: str | None) -> str | None:
        if value is None:
            return None
        email = value.strip().lower()
        if not re.fullmatch(r"[^@\s]+@[^@\s]+\.[^@\s]+", email):
            raise ValueError("Введите корректный адрес почты")
        return email

    @model_validator(mode="after")
    def validate_times(self):
        if self.end_time <= self.start_time:
            raise ValueError("Время окончания должно быть позже времени начала")
        return self


class BookingResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    code: str
    room_id: int
    user_name: str
    full_name: str = ""
    phone: str = ""
    email: str = ""
    start_time: datetime
    end_time: datetime
    status: BookingStatus


class AdminBookingResponse(BookingResponse):
    room_name: str


class AdminReportBooking(BaseModel):
    id: int
    code: str
    user_name: str
    start_time: datetime
    end_time: datetime
    status: BookingStatus


class AdminRoomReport(BaseModel):
    room_id: int
    room_name: str
    capacity: int
    active_count: int
    completed_count: int
    cancelled_count: int
    booked: list[AdminReportBooking]
    cancelled: list[AdminReportBooking]


class AdminReportSummary(BaseModel):
    total_rooms: int
    total_booked: int
    total_cancelled: int
    total_active: int
    total_completed: int


class AdminRoomsReportResponse(BaseModel):
    generated_at: datetime
    summary: AdminReportSummary
    rooms: list[AdminRoomReport]


class ErrorResponse(BaseModel):
    detail: str


class MessageResponse(BaseModel):
    detail: str


class BookingCancelResponse(BaseModel):
    detail: str
    booking: BookingResponse


class HealthResponse(BaseModel):
    status: str
    service: str


class ScheduleSlotResponse(BaseModel):
    start: datetime
    end: datetime
    status: Literal["free", "busy"]


class RoomScheduleResponse(BaseModel):
    room_id: int
    room_name: str
    date: date
    open_time: str
    close_time: str
    current_status: Literal["free", "busy", "closed"]
    free_slots: int
    busy_slots: int
    slots: list[ScheduleSlotResponse]
    bookings: list[BookingResponse]


class DayScheduleSummary(BaseModel):
    date: date
    status: Literal["free", "partial", "busy", "closed"]
    free_slots: int
    busy_slots: int
    bookings_count: int = 0


class RoomMonthScheduleResponse(BaseModel):
    room_id: int
    room_name: str
    year: int
    month: int
    open_time: str
    close_time: str
    days: list[DayScheduleSummary]
