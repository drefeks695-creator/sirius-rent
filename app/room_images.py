from pathlib import Path

from app.avatars import ALLOWED_CONTENT_TYPES, ALLOWED_EXTENSIONS

BASE_DIR = Path(__file__).resolve().parent.parent
UPLOADS_DIR = BASE_DIR / "static" / "uploads" / "rooms"

MAX_ROOM_IMAGE_SIZE = 5 * 1024 * 1024


def ensure_room_uploads_dir() -> None:
    UPLOADS_DIR.mkdir(parents=True, exist_ok=True)


def room_image_path(room_id: int, ext: str) -> Path:
    return UPLOADS_DIR / f"{room_id}{ext}"


def room_image_url(room_id: int, ext: str) -> str:
    return f"/ui/uploads/rooms/{room_id}{ext}"


def is_uploaded_room_image(url: str) -> bool:
    return url.startswith("/ui/uploads/rooms/")


def is_valid_room_image_url(url: str, room_id: int) -> bool:
    prefix = f"/ui/uploads/rooms/{room_id}."
    if not url.startswith(prefix):
        return False
    ext = "." + url.rsplit(".", 1)[-1].lower()
    return ext in ALLOWED_EXTENSIONS


def remove_room_image(room_id: int) -> bool:
    removed = False
    for ext in ALLOWED_EXTENSIONS:
        path = UPLOADS_DIR / f"{room_id}{ext}"
        if path.exists():
            path.unlink()
            removed = True
    return removed


def get_room_image_url(room_id: int) -> str | None:
    for ext in ALLOWED_EXTENSIONS:
        if room_image_path(room_id, ext).exists():
            return room_image_url(room_id, ext)
    return None
