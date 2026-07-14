from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
UPLOADS_DIR = BASE_DIR / "static" / "uploads" / "avatars"

PRESET_AVATARS = {
    "/ui/avatars/1.svg",
    "/ui/avatars/2.svg",
    "/ui/avatars/3.svg",
    "/ui/avatars/4.svg",
    "/ui/avatars/5.svg",
    "/ui/avatars/6.svg",
}

ALLOWED_CONTENT_TYPES = {
    "image/jpeg": ".jpg",
    "image/png": ".png",
    "image/webp": ".webp",
    "image/gif": ".gif",
}

ALLOWED_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp", ".gif"}
MAX_AVATAR_SIZE = 2 * 1024 * 1024


def ensure_uploads_dir() -> None:
    UPLOADS_DIR.mkdir(parents=True, exist_ok=True)


def custom_avatar_path(user_id: int, ext: str) -> Path:
    return UPLOADS_DIR / f"{user_id}{ext}"


def custom_avatar_url(user_id: int, ext: str) -> str:
    return f"/ui/uploads/avatars/{user_id}{ext}"


def is_valid_avatar_url(url: str, user_id: int) -> bool:
    if url in PRESET_AVATARS:
        return True

    prefix = f"/ui/uploads/avatars/{user_id}."
    if not url.startswith(prefix):
        return False

    ext = "." + url.rsplit(".", 1)[-1].lower()
    return ext in ALLOWED_EXTENSIONS


def remove_custom_avatar(user_id: int) -> bool:
    removed = False
    for ext in ALLOWED_EXTENSIONS:
        path = UPLOADS_DIR / f"{user_id}{ext}"
        if path.exists():
            path.unlink()
            removed = True
    return removed


def get_custom_avatar_url(user_id: int) -> str | None:
    for ext in ALLOWED_EXTENSIONS:
        if custom_avatar_path(user_id, ext).exists():
            return custom_avatar_url(user_id, ext)
    return None


def has_custom_avatar(user_id: int) -> bool:
    return get_custom_avatar_url(user_id) is not None
