from functools import lru_cache
from typing import Literal

from pydantic_settings import BaseSettings
from pydantic_settings import SettingsConfigDict


class Settings(BaseSettings):

    APP_NAME: str = "UHDP"
    APP_VERSION: str = "1.0.0"

    HOST: str = "0.0.0.0"
    PORT: int = 8000

    LOG_LEVEL: str = "INFO"

    SESSION_TIMEOUT_MINUTES: int = 60

    DATA_DIR: str = "data"
    EVIDENCE_MAX_FILE_BYTES: int = 104857600

    REPORTS_DIRECTORY: str = "data/reports"

    SESSIONS_DIRECTORY: str = "data/sessions"
    STORAGE_BACKEND: Literal["file", "sqlite", "supabase"] = "file"
    SQLITE_DATABASE_PATH: str | None = None
    SUPABASE_URL: str | None = None
    SUPABASE_SERVICE_ROLE_KEY: str | None = None
    SUPABASE_RECORDS_TABLE: str = "uhdp_records"
    CLOUD_API_URL: str | None = None
    CLOUD_STATION_TOKEN: str | None = None
    SYNC_INTERVAL_SECONDS: int = 15
    SYNC_REQUEST_TIMEOUT_SECONDS: int = 20

    CORS_ORIGINS: str = (
        "http://localhost:3000,http://127.0.0.1:3000"
    )

    DEFAULT_REPORT_FORMAT: str = "json"

    DEVICE_SCAN_INTERVAL_SECONDS: int = 30

    WEBSOCKET_HEARTBEAT_SECONDS: int = 15

    model_config = SettingsConfigDict(
        env_file=".env",
        extra="ignore",
    )


@lru_cache
def get_settings() -> Settings:
    return Settings()