import pytest
from fastapi.testclient import TestClient

from tests.helpers import auth_header, fill_booking_profile


def test_public_rooms_without_auth(client: TestClient):
    response = client.get("/rooms")
    assert response.status_code == 200
    assert isinstance(response.json(), list)


def test_booking_without_profile_returns_400(client: TestClient):
    admin_headers = auth_header(client, "admin", "admin123")
    room = client.post(
        "/rooms",
        json={"name": "Без профиля", "capacity": 5, "equipment": []},
        headers=admin_headers,
    ).json()

    user_headers = auth_header(client, "student", "student123")
    response = client.post(
        "/bookings",
        json={
            "room_id": room["id"],
            "start_time": "2026-07-15T12:00:00",
            "end_time": "2026-07-15T13:00:00",
        },
        headers=user_headers,
    )
    assert response.status_code == 400
    assert "почту" in response.json()["detail"].lower()


def test_booking_with_inline_contact_succeeds(client: TestClient):
    admin_headers = auth_header(client, "admin", "admin123")
    room = client.post(
        "/rooms",
        json={"name": "Контакт в брони", "capacity": 5, "equipment": []},
        headers=admin_headers,
    ).json()

    user_headers = auth_header(client, "student", "student123")
    response = client.post(
        "/bookings",
        json={
            "room_id": room["id"],
            "start_time": "2026-07-15T16:00:00",
            "end_time": "2026-07-15T17:00:00",
            "full_name": "Петров Пётр",
            "phone": "+7 999 111-22-33",
            "email": "petrov@example.com",
        },
        headers=user_headers,
    )
    assert response.status_code == 201
    data = response.json()
    assert data["full_name"] == "Петров Пётр"
    assert data["phone"] == "+7 999 111-22-33"
    assert data["email"] == "petrov@example.com"


def test_booking_with_profile_succeeds(client: TestClient):
    admin_headers = auth_header(client, "admin", "admin123")
    room = client.post(
        "/rooms",
        json={"name": "С профилем", "capacity": 5, "equipment": []},
        headers=admin_headers,
    ).json()

    user_headers = auth_header(client, "student", "student123")
    fill_booking_profile(client, user_headers)
    response = client.post(
        "/bookings",
        json={
            "room_id": room["id"],
            "start_time": "2026-07-15T14:00:00",
            "end_time": "2026-07-15T15:00:00",
        },
        headers=user_headers,
    )
    assert response.status_code == 201
    data = response.json()
    assert data["code"].startswith("SR-")
    assert len(data["code"]) >= 12


def test_profile_username_update(client: TestClient):
    headers = auth_header(client, "student", "student123")
    response = client.patch(
        "/profile/me",
        json={"username": "renamed_user", "avatar_url": "/ui/avatars/2.svg"},
        headers=headers,
    )
    assert response.status_code == 200
    data = response.json()
    assert data["username"] == "renamed_user"
    assert data["avatar_url"] == "/ui/avatars/2.svg"
    assert data["access_token"]

    refreshed = client.get(
        "/profile/me",
        headers={"Authorization": f"Bearer {data['access_token']}"},
    )
    assert refreshed.json()["username"] == "renamed_user"


def test_upload_custom_avatar(client: TestClient):
    headers = auth_header(client, "student", "student123")
    png_bytes = (
        b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01"
        b"\x00\x00\x00\x01\x08\x06\x00\x00\x00\x1f\x15\xc4\x89"
        b"\x00\x00\x00\nIDATx\x9cc\x00\x01\x00\x00\x05\x00\x01"
        b"\r\n-\xb4\x00\x00\x00\x00IEND\xaeB`\x82"
    )

    response = client.post(
        "/profile/me/avatar",
        headers=headers,
        files={"file": ("avatar.png", png_bytes, "image/png")},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["avatar_url"].startswith("/ui/uploads/avatars/")
    assert data["avatar_url"].endswith(".png")

    profile = client.get("/profile/me", headers=headers).json()
    assert profile["avatar_url"] == data["avatar_url"]
    assert profile["custom_avatar_url"] == data["avatar_url"]


def test_delete_custom_avatar(client: TestClient):
    headers = auth_header(client, "student", "student123")
    png_bytes = (
        b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01"
        b"\x00\x00\x00\x01\x08\x06\x00\x00\x00\x1f\x15\xc4\x89"
        b"\x00\x00\x00\nIDATx\x9cc\x00\x01\x00\x00\x05\x00\x01"
        b"\r\n-\xb4\x00\x00\x00\x00IEND\xaeB`\x82"
    )

    uploaded = client.post(
        "/profile/me/avatar",
        headers=headers,
        files={"file": ("avatar.png", png_bytes, "image/png")},
    )
    assert uploaded.status_code == 200
    assert uploaded.json()["custom_avatar_url"]

    deleted = client.delete("/profile/me/avatar", headers=headers)
    assert deleted.status_code == 200
    data = deleted.json()
    assert data["avatar_url"] == "/ui/avatars/1.svg"
    assert data["custom_avatar_url"] is None

    missing = client.delete("/profile/me/avatar", headers=headers)
    assert missing.status_code == 404


def test_register_new_user(client: TestClient):
    response = client.post(
        "/auth/register",
        json={"username": "newbie", "password": "secret123"},
    )
    assert response.status_code == 201
    data = response.json()
    assert data["username"] == "newbie"
    assert data["avatar_url"] == "/ui/avatars/1.svg"
    assert data["role"] == "user"

    login = client.post(
        "/auth/login",
        data={"username": "newbie", "password": "secret123"},
    )
    assert login.status_code == 200
    assert "access_token" in login.json()

    duplicate = client.post(
        "/auth/register",
        json={"username": "newbie", "password": "other456"},
    )
    assert duplicate.status_code == 400


def test_create_room_as_admin(client: TestClient):
    headers = auth_header(client, "admin", "admin123")
    response = client.post(
        "/rooms",
        json={"name": "Тестовая комната", "capacity": 10, "equipment": ["проектор"]},
        headers=headers,
    )
    assert response.status_code == 201
    data = response.json()
    assert data["name"] == "Тестовая комната"
    assert data["capacity"] == 10


def test_booking_conflict_returns_409(client: TestClient):
    admin_headers = auth_header(client, "admin", "admin123")
    room = client.post(
        "/rooms",
        json={"name": "Конфликт", "capacity": 5, "equipment": []},
        headers=admin_headers,
    ).json()

    user_headers = auth_header(client, "student", "student123")
    fill_booking_profile(client, user_headers)
    payload = {
        "room_id": room["id"],
        "start_time": "2026-07-15T10:00:00",
        "end_time": "2026-07-15T11:00:00",
    }
    first = client.post("/bookings", json=payload, headers=user_headers)
    assert first.status_code == 201

    second = client.post("/bookings", json=payload, headers=user_headers)
    assert second.status_code == 409
    assert "занято" in second.json()["detail"].lower()


def test_available_rooms_excludes_booked(client: TestClient):
    admin_headers = auth_header(client, "admin", "admin123")
    room = client.post(
        "/rooms",
        json={"name": "Свободная", "capacity": 20, "equipment": ["доска"]},
        headers=admin_headers,
    ).json()

    user_headers = auth_header(client, "student", "student123")
    fill_booking_profile(client, user_headers)
    client.post(
        "/bookings",
        json={
            "room_id": room["id"],
            "start_time": "2026-07-20T14:00:00",
            "end_time": "2026-07-20T15:00:00",
        },
        headers=user_headers,
    )

    response = client.get(
        "/rooms/available",
        params={
            "start": "2026-07-20T14:00:00",
            "end": "2026-07-20T15:00:00",
        },
    )
    assert response.status_code == 200
    ids = [item["id"] for item in response.json()]
    assert room["id"] not in ids


def test_user_cannot_cancel_foreign_booking(client: TestClient):
    admin_headers = auth_header(client, "admin", "admin123")
    room = client.post(
        "/rooms",
        json={"name": "Чужая", "capacity": 4, "equipment": []},
        headers=admin_headers,
    ).json()

    student_headers = auth_header(client, "student", "student123")
    fill_booking_profile(client, student_headers)
    booking = client.post(
        "/bookings",
        json={
            "room_id": room["id"],
            "start_time": "2026-07-21T09:00:00",
            "end_time": "2026-07-21T10:00:00",
        },
        headers=student_headers,
    ).json()

    client.post("/auth/register", json={"username": "other", "password": "other123"})
    other_headers = auth_header(client, "other", "other123")
    response = client.delete(f"/bookings/{booking['id']}", headers=other_headers)
    assert response.status_code == 403


def test_room_schedule_returns_slots(client: TestClient):
    admin_headers = auth_header(client, "admin", "admin123")
    room = client.post(
        "/rooms",
        json={"name": "Расписание тест", "capacity": 10, "equipment": []},
        headers=admin_headers,
    ).json()

    response = client.get(f"/rooms/{room['id']}/schedule", params={"date": "2026-08-01"})
    assert response.status_code == 200
    data = response.json()
    assert data["open_time"] == "08:00"
    assert data["close_time"] == "22:00"
    assert len(data["slots"]) > 0
    assert all(slot["status"] in {"free", "busy"} for slot in data["slots"])


def test_room_month_schedule(client: TestClient):
    admin_headers = auth_header(client, "admin", "admin123")
    room = client.post(
        "/rooms",
        json={"name": "Календарь тест", "capacity": 10, "equipment": []},
        headers=admin_headers,
    ).json()

    response = client.get(
        f"/rooms/{room['id']}/schedule/month",
        params={"year": 2026, "month": 8},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["month"] == 8
    assert len(data["days"]) == 31
    assert data["days"][0]["status"] in {"free", "partial", "busy", "closed"}
    assert "bookings_count" in data["days"][0]


def test_schedule_shows_active_booking(client: TestClient):
    from datetime import datetime, time, timedelta

    admin_headers = auth_header(client, "admin", "admin123")
    room = client.post(
        "/rooms",
        json={"name": "Отображение брони", "capacity": 8, "equipment": []},
        headers=admin_headers,
    ).json()

    student_headers = auth_header(client, "student", "student123")
    fill_booking_profile(client, student_headers)

    tomorrow = (datetime.now() + timedelta(days=1)).date()
    start = datetime.combine(tomorrow, time(10, 0))
    end = start + timedelta(hours=1)
    booking_date = tomorrow.isoformat()

    response = client.post(
        "/bookings",
        json={
            "room_id": room["id"],
            "start_time": start.isoformat(),
            "end_time": end.isoformat(),
        },
        headers=student_headers,
    )
    assert response.status_code == 201

    schedule = client.get(
        f"/rooms/{room['id']}/schedule",
        params={"date": booking_date},
    ).json()

    assert schedule["busy_slots"] > 0
    assert len(schedule["bookings"]) == 1
    assert schedule["bookings"][0]["user_name"] == "Занято"
    assert schedule["bookings"][0]["code"].startswith("SR-")


def test_availability_outside_working_hours_rejected(client: TestClient):
    admin_headers = auth_header(client, "admin", "admin123")
    room = client.post(
        "/rooms",
        json={"name": "Доступность вне часов", "capacity": 8, "equipment": []},
        headers=admin_headers,
    ).json()

    response = client.get(
        f"/rooms/{room['id']}/availability",
        params={
            "start": "2026-07-15T22:30:00",
            "end": "2026-07-15T23:30:00",
        },
    )
    assert response.status_code == 400
    assert "08:00" in response.json()["detail"]


def test_booking_outside_working_hours_rejected(client: TestClient):
    admin_headers = auth_header(client, "admin", "admin123")
    room = client.post(
        "/rooms",
        json={"name": "Часы работы", "capacity": 8, "equipment": []},
        headers=admin_headers,
    ).json()

    student_headers = auth_header(client, "student", "student123")
    fill_booking_profile(client, student_headers)

    response = client.post(
        "/bookings",
        json={
            "room_id": room["id"],
            "start_time": "2026-07-15T22:30:00",
            "end_time": "2026-07-15T23:30:00",
        },
        headers=student_headers,
    )
    assert response.status_code == 400
    assert "08:00" in response.json()["detail"]


def test_expired_booking_does_not_block(client: TestClient):
    from datetime import datetime, time, timedelta

    from app.auth import get_user_by_username
    from app.booking_codes import assign_booking_code
    from app.database import SessionLocal
    from app.models import Booking, BookingStatus

    admin_headers = auth_header(client, "admin", "admin123")
    room = client.post(
        "/rooms",
        json={"name": "Истекшая", "capacity": 5, "equipment": []},
        headers=admin_headers,
    ).json()

    student_headers = auth_header(client, "student", "student123")
    fill_booking_profile(client, student_headers)

    now = datetime.now()
    past_start = now.replace(hour=15, minute=0, second=0, microsecond=0)
    if past_start >= now:
        past_start = (now - timedelta(days=1)).replace(hour=15, minute=0, second=0, microsecond=0)
    past_end = past_start + timedelta(hours=1)

    with SessionLocal() as db:
        student = get_user_by_username(db, "student")
        db.add(
            Booking(
                room_id=room["id"],
                user_id=student.id,
                code=assign_booking_code(db, past_start),
                start_time=past_start,
                end_time=past_end,
                status=BookingStatus.completed,
            )
        )
        db.commit()

    client.post("/auth/register", json={"username": "other2", "password": "other456"})
    other_headers = auth_header(client, "other2", "other456")
    fill_booking_profile(client, other_headers)

    future_day = (now + timedelta(days=1)).date()
    future_start = datetime.combine(future_day, time(10, 0))
    future_end = datetime.combine(future_day, time(11, 0))
    response = client.post(
        "/bookings",
        json={
            "room_id": room["id"],
            "start_time": future_start.isoformat(),
            "end_time": future_end.isoformat(),
        },
        headers=other_headers,
    )
    assert response.status_code == 201

    student_profile = client.get("/profile/me", headers=student_headers).json()
    assert len(student_profile["bookings"]) == 0


def test_booking_suggestions_when_busy(client: TestClient):
    admin_headers = auth_header(client, "admin", "admin123")
    room_a = client.post(
        "/rooms",
        json={"name": "Занятая", "capacity": 10, "equipment": []},
        headers=admin_headers,
    ).json()
    room_b = client.post(
        "/rooms",
        json={"name": "Свободная", "capacity": 10, "equipment": []},
        headers=admin_headers,
    ).json()

    student_headers = auth_header(client, "student", "student123")
    fill_booking_profile(client, student_headers)
    client.post(
        "/bookings",
        json={
            "room_id": room_a["id"],
            "start_time": "2026-08-10T10:00:00",
            "end_time": "2026-08-10T11:00:00",
        },
        headers=student_headers,
    )

    response = client.get(
        f"/rooms/{room_a['id']}/suggestions",
        params={
            "start": "2026-08-10T10:00:00",
            "end": "2026-08-10T11:00:00",
        },
    )
    assert response.status_code == 200
    data = response.json()
    assert data["time_slots"]
    assert any(room["id"] == room_b["id"] for room in data["rooms"])


def test_admin_block_room_prevents_booking(client: TestClient):
    admin_headers = auth_header(client, "admin", "admin123")
    room = client.post(
        "/rooms",
        json={"name": "Закрытая", "capacity": 6, "equipment": []},
        headers=admin_headers,
    ).json()

    client.put(
        f"/rooms/{room['id']}",
        json={"bookings_blocked": True},
        headers=admin_headers,
    )

    student_headers = auth_header(client, "student", "student123")
    fill_booking_profile(client, student_headers)
    response = client.post(
        "/bookings",
        json={
            "room_id": room["id"],
            "start_time": "2026-09-01T10:00:00",
            "end_time": "2026-09-01T11:00:00",
        },
        headers=student_headers,
    )
    assert response.status_code == 403

    availability = client.get(
        f"/rooms/{room['id']}/availability",
        params={"start": "2026-09-01T10:00:00", "end": "2026-09-01T11:00:00"},
    )
    assert availability.status_code == 200
    assert availability.json()["available"] is False


def test_admin_list_bookings(client: TestClient):
    admin_headers = auth_header(client, "admin", "admin123")
    room = client.post(
        "/rooms",
        json={"name": "Для админа", "capacity": 8, "equipment": []},
        headers=admin_headers,
    ).json()

    student_headers = auth_header(client, "student", "student123")
    fill_booking_profile(client, student_headers)
    client.post(
        "/bookings",
        json={
            "room_id": room["id"],
            "start_time": "2026-10-01T10:00:00",
            "end_time": "2026-10-01T11:00:00",
        },
        headers=student_headers,
    )

    response = client.get("/admin/bookings", headers=admin_headers)
    assert response.status_code == 200
    data = response.json()
    assert any(item["room_name"] == "Для админа" for item in data)

    forbidden = client.get("/admin/bookings", headers=student_headers)
    assert forbidden.status_code == 403


def test_admin_delete_room(client: TestClient):
    admin_headers = auth_header(client, "admin", "admin123")
    room = client.post(
        "/rooms",
        json={"name": "На удаление", "capacity": 4, "equipment": []},
        headers=admin_headers,
    ).json()

    response = client.delete(f"/rooms/{room['id']}", headers=admin_headers)
    assert response.status_code == 200
    assert client.get(f"/rooms/{room['id']}").status_code == 404


def test_admin_manage_users(client: TestClient):
    admin_headers = auth_header(client, "admin", "admin123")
    student_headers = auth_header(client, "student", "student123")
    fill_booking_profile(client, student_headers)

    users = client.get("/admin/users", headers=admin_headers).json()
    student = next(user for user in users if user["username"] == "student")

    updated = client.patch(
        f"/admin/users/{student['id']}",
        json={
            "full_name": "Студент Тестовый",
            "phone": "+79991112233",
            "email": "student@test.ru",
            "password": "newpass123",
        },
        headers=admin_headers,
    )
    assert updated.status_code == 200
    data = updated.json()
    assert data["full_name"] == "Студент Тестовый"
    assert data["email"] == "student@test.ru"
    assert data["booking_profile_complete"] is True

    login_ok = client.post(
        "/auth/login",
        data={"username": "student", "password": "newpass123"},
    )
    assert login_ok.status_code == 200

    forbidden = client.get("/admin/users", headers=student_headers)
    assert forbidden.status_code == 403


def test_admin_cannot_delete_self(client: TestClient):
    admin_headers = auth_header(client, "admin", "admin123")
    admin_user = next(
        user for user in client.get("/admin/users", headers=admin_headers).json()
        if user["username"] == "admin"
    )

    response = client.delete(f"/admin/users/{admin_user['id']}", headers=admin_headers)
    assert response.status_code == 400


def test_admin_rooms_report(client: TestClient):
    admin_headers = auth_header(client, "admin", "admin123")
    student_headers = auth_header(client, "student", "student123")
    fill_booking_profile(client, student_headers)

    room = client.post(
        "/rooms",
        json={"name": "Отчётная аудитория", "capacity": 20, "equipment": []},
        headers=admin_headers,
    ).json()

    active = client.post(
        "/bookings",
        json={
            "room_id": room["id"],
            "start_time": "2026-11-01T10:00:00",
            "end_time": "2026-11-01T11:00:00",
        },
        headers=student_headers,
    ).json()

    cancelled = client.post(
        "/bookings",
        json={
            "room_id": room["id"],
            "start_time": "2026-11-02T12:00:00",
            "end_time": "2026-11-02T13:00:00",
        },
        headers=student_headers,
    ).json()
    client.delete(f"/bookings/{cancelled['id']}", headers=student_headers)

    report = client.get("/admin/reports/rooms", headers=admin_headers)
    assert report.status_code == 200
    data = report.json()

    assert data["summary"]["total_booked"] >= 1
    assert data["summary"]["total_cancelled"] >= 1

    room_report = next(item for item in data["rooms"] if item["room_id"] == room["id"])
    assert room_report["room_name"] == "Отчётная аудитория"
    assert room_report["active_count"] >= 1
    assert room_report["cancelled_count"] >= 1
    assert any(item["id"] == active["id"] for item in room_report["booked"])
    assert any(item["id"] == cancelled["id"] for item in room_report["cancelled"])

    forbidden = client.get("/admin/reports/rooms", headers=student_headers)
    assert forbidden.status_code == 403


def test_upload_room_image(client: TestClient):
    admin_headers = auth_header(client, "admin", "admin123")
    room = client.post(
        "/rooms",
        json={"name": "С фото", "capacity": 12, "equipment": []},
        headers=admin_headers,
    ).json()

    png_bytes = (
        b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01"
        b"\x00\x00\x00\x01\x08\x06\x00\x00\x00\x1f\x15\xc4\x89"
        b"\x00\x00\x00\nIDATx\x9cc\x00\x01\x00\x00\x05\x00\x01"
        b"\r\n-\xb4\x00\x00\x00\x00IEND\xaeB`\x82"
    )

    uploaded = client.post(
        f"/rooms/{room['id']}/image",
        headers=admin_headers,
        files={"file": ("room.png", png_bytes, "image/png")},
    )
    assert uploaded.status_code == 200
    data = uploaded.json()
    assert data["image_url"] == f"/ui/uploads/rooms/{room['id']}.png"

    room_data = client.get(f"/rooms/{room['id']}").json()
    assert room_data["image_url"] == data["image_url"]

    student_headers = auth_header(client, "student", "student123")
    forbidden = client.post(
        f"/rooms/{room['id']}/image",
        headers=student_headers,
        files={"file": ("room.png", png_bytes, "image/png")},
    )
    assert forbidden.status_code == 403
