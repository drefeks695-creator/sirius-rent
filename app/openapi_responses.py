"""Общие описания HTTP-ответов для OpenAPI / Swagger."""

from typing import Any

from app.schemas import ErrorResponse


def _error(status_code: int, description: str) -> dict[int, dict[str, Any]]:
    return {status_code: {"model": ErrorResponse, "description": description}}


R400 = _error(400, "Некорректный запрос")
R401 = _error(401, "Требуется авторизация")
R403 = _error(403, "Доступ запрещён")
R404 = _error(404, "Ресурс не найден")
R409 = _error(409, "Конфликт данных")
R422 = _error(422, "Ошибка валидации входных данных")
R429 = _error(429, "Слишком много запросов")


def combine(*parts: dict[int, dict[str, Any]]) -> dict[int, dict[str, Any]]:
    merged: dict[int, dict[str, Any]] = {}
    for part in parts:
        merged.update(part)
    return merged


AUTH = combine(R401)
AUTH_ADMIN = combine(R401, R403)
AUTH_BODY = combine(R401, R422)
AUTH_ADMIN_BODY = combine(R401, R403, R422)
