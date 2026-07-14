from fastapi.testclient import TestClient


def auth_header(client: TestClient, username: str, password: str) -> dict:
    response = client.post(
        "/auth/login",
        data={"username": username, "password": password},
    )
    token = response.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


def fill_booking_profile(client: TestClient, headers: dict) -> None:
    response = client.patch(
        "/profile/me",
        json={
            "full_name": "Иванов Иван",
            "phone": "+79991234567",
            "email": "ivanov@example.com",
        },
        headers=headers,
    )
    assert response.status_code == 200
    data = response.json()
    assert data["booking_profile_complete"] is True
