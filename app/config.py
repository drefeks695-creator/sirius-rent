from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

_PROJECT_ROOT = Path(__file__).resolve().parent.parent


def _default_sqlite_url() -> str:
    """Always create/open DB in the project root (not the current working directory)."""
    db_path = (_PROJECT_ROOT / "sirius_rent.db").resolve()
    return f"sqlite:///{db_path.as_posix()}"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    app_name: str = "Сириус.Аренда"
    database_url: str = _default_sqlite_url()
    secret_key: str = "dev-only-set-SECRET_KEY-in-env"
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 60 * 24


settings = Settings()
