from datetime import datetime, timezone

from jose import jwt

from app.auth import (
    authenticate_user,
    create_access_token,
    create_user,
    decode_token,
    hash_password,
    verify_password,
)
from app.config import settings
from app.models import UserRole


def test_hash_and_verify_password():
    hashed = hash_password("secret123")
    assert hashed != "secret123"
    assert verify_password("secret123", hashed)
    assert not verify_password("wrong", hashed)


def test_create_access_token_and_decode(db_session):
    user = create_user(db_session, "token_user", "pass123")
    token = create_access_token(user.id, user.username, user.role)

    payload = decode_token(token)
    assert payload is not None
    assert payload["sub"] == str(user.id)
    assert payload["username"] == "token_user"
    assert payload["role"] == UserRole.user.value

    decoded = jwt.decode(token, settings.secret_key, algorithms=[settings.algorithm])
    assert decoded["exp"] > int(datetime.now(timezone.utc).timestamp())


def test_decode_invalid_token_returns_none():
    assert decode_token("not-a-jwt") is None
    assert decode_token("") is None


def test_authenticate_user(db_session):
    create_user(db_session, "auth_user", "correct")

    ok = authenticate_user(db_session, "auth_user", "correct")
    assert ok is not None
    assert ok.username == "auth_user"

    assert authenticate_user(db_session, "auth_user", "wrong") is None
    assert authenticate_user(db_session, "missing", "correct") is None
