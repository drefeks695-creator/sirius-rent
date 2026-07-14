ALLOWED_CONTENT_TYPES = {
    "image/jpeg": ".jpg",
    "image/png": ".png",
    "image/webp": ".webp",
    "image/gif": ".gif",
}

_SIGNATURES: list[tuple[bytes, str]] = [
    (b"\xff\xd8\xff", "image/jpeg"),
    (b"\x89PNG\r\n\x1a\n", "image/png"),
    (b"GIF87a", "image/gif"),
    (b"GIF89a", "image/gif"),
]


def detect_image_content_type(data: bytes) -> str | None:
    if len(data) < 12:
        return None
    for prefix, content_type in _SIGNATURES:
        if data.startswith(prefix):
            return content_type
    if data[:4] == b"RIFF" and data[8:12] == b"WEBP":
        return "image/webp"
    return None


def validate_image_upload(data: bytes, content_type: str) -> None:
    normalized = (content_type or "").split(";", 1)[0].strip().lower()
    if normalized not in ALLOWED_CONTENT_TYPES:
        raise ValueError("Допустимы только JPG, PNG, WEBP или GIF")
    detected = detect_image_content_type(data)
    if detected != normalized:
        raise ValueError("Содержимое файла не совпадает с типом изображения")
