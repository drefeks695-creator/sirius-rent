"""Incremental schema updates for SQLite (shared by app startup and Alembic)."""

from sqlalchemy import inspect, text
from sqlalchemy.engine import Engine


def _table_names(engine: Engine) -> set[str]:
    return set(inspect(engine).get_table_names())


def _has_column(engine: Engine, table: str, column: str) -> bool:
    inspector = inspect(engine)
    return column in {col["name"] for col in inspector.get_columns(table)}


def apply_pending_migrations(engine: Engine) -> None:
    """Add columns introduced after the first release."""
    tables = _table_names(engine)

    if "rooms" in tables:
        with engine.begin() as conn:
            if not _has_column(engine, "rooms", "description"):
                conn.execute(text("ALTER TABLE rooms ADD COLUMN description TEXT DEFAULT ''"))
            if not _has_column(engine, "rooms", "image_url"):
                conn.execute(text("ALTER TABLE rooms ADD COLUMN image_url VARCHAR(500) DEFAULT ''"))
            if not _has_column(engine, "rooms", "bookings_blocked"):
                conn.execute(text("ALTER TABLE rooms ADD COLUMN bookings_blocked BOOLEAN DEFAULT 0"))
            if not _has_column(engine, "rooms", "open_time"):
                conn.execute(text("ALTER TABLE rooms ADD COLUMN open_time VARCHAR(5) DEFAULT '08:00'"))
            if not _has_column(engine, "rooms", "close_time"):
                conn.execute(text("ALTER TABLE rooms ADD COLUMN close_time VARCHAR(5) DEFAULT '22:00'"))

    if "users" in tables:
        with engine.begin() as conn:
            if not _has_column(engine, "users", "avatar_url"):
                conn.execute(
                    text(
                        "ALTER TABLE users ADD COLUMN avatar_url VARCHAR(500) DEFAULT '/ui/avatars/1.svg'"
                    )
                )
            if not _has_column(engine, "users", "full_name"):
                conn.execute(text("ALTER TABLE users ADD COLUMN full_name VARCHAR(200) DEFAULT ''"))
            if not _has_column(engine, "users", "phone"):
                conn.execute(text("ALTER TABLE users ADD COLUMN phone VARCHAR(30) DEFAULT ''"))
            if not _has_column(engine, "users", "email"):
                conn.execute(text("ALTER TABLE users ADD COLUMN email VARCHAR(200) DEFAULT ''"))

    if "bookings" in tables:
        with engine.begin() as conn:
            if not _has_column(engine, "bookings", "code"):
                conn.execute(text("ALTER TABLE bookings ADD COLUMN code VARCHAR(20) DEFAULT ''"))

    if "reviews" in tables:
        with engine.begin() as conn:
            conn.execute(text("DROP TABLE reviews"))
