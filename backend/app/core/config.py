"""Application settings, read from environment variables prefixed ``LL_`` (and from ``.env``)."""

from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

MB = 1024 * 1024


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="LL_", env_file=".env", extra="ignore")

    env: Literal["dev", "test", "prod"] = "dev"
    version: str = "0.1.0"

    # Storage
    data_dir: Path = Path("./data")
    # Fernet key for blobs at rest (NFR-9). In dev/test one is generated into data_dir if unset.
    encryption_key: str | None = None

    # The single v1 user (FR-27), created or updated at startup.
    user_email: str = "dana@whitfieldlaw.com"
    user_password: str = "legallens"
    user_name: str = "Dana Whitfield"

    # Sessions
    session_cookie: str = "ll_session"
    session_idle_hours: int = 12
    session_max_days: int = 7
    cookie_secure: bool | None = None  # defaults to True only in prod

    # CORS — empty means same-origin only (the Vite dev proxy).
    cors_origins: list[str] = Field(default_factory=list)

    # Limits (FR-2, NFR-4)
    max_upload_bytes: int = 50 * MB
    max_pages: int = 500
    max_documents: int = 50
    max_request_bytes: int = 500 * MB

    # Rate limits, per session per minute
    rate_chat_per_minute: int = 20
    rate_upload_per_minute: int = 10
    rate_login_per_minute: int = 5

    # Ingestion
    worker_concurrency: int = 3  # NFR-5
    ingest_stage_delay_ms: int = 0  # >0 slows status transitions so the UI's progress is visible in demos

    # Chat turns
    orchestrator: Literal["stub"] = "stub"
    stub_token_delay_ms: int = 22
    turn_timeout_s: float = 120.0
    history_turns: int = 8

    @property
    def db_path(self) -> Path:
        return self.data_dir / "legallens.db"

    @property
    def blob_dir(self) -> Path:
        return self.data_dir / "blobs"

    @property
    def async_db_url(self) -> str:
        return f"sqlite+aiosqlite:///{self.db_path.as_posix()}"

    @property
    def sync_db_url(self) -> str:
        return f"sqlite:///{self.db_path.as_posix()}"

    @property
    def secure_cookies(self) -> bool:
        return self.cookie_secure if self.cookie_secure is not None else self.env == "prod"

    @property
    def is_dev(self) -> bool:
        return self.env in ("dev", "test")


@lru_cache
def get_settings() -> Settings:
    return Settings()
