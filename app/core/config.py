from functools import lru_cache

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

    REPORTS_DIRECTORY: str = "data/reports"

    SESSIONS_DIRECTORY: str = "data/sessions"

    CORS_ORIGINS: str = (
        "http://localhost:3000"
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