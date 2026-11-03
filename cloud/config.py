from __future__ import annotations

from dataclasses import dataclass
import os


@dataclass(frozen=True)
class CloudSettings:
    database_url: str
    jwt_secret: str
    jwt_lifetime_seconds: int

    @classmethod
    def from_env(cls) -> "CloudSettings":
        database_url = os.environ.get("CLOUD_DATABASE_URL", "")
        jwt_secret = os.environ.get("CLOUD_JWT_SECRET", "")
        if not database_url:
            raise RuntimeError("CLOUD_DATABASE_URL must be configured.")
        if len(jwt_secret.encode("utf-8")) < 32:
            raise RuntimeError("CLOUD_JWT_SECRET must contain at least 32 bytes.")
        if jwt_secret.lower().startswith("replace-with"):
            raise RuntimeError("Replace the example CLOUD_JWT_SECRET before startup.")
        lifetime = int(os.environ.get("CLOUD_JWT_LIFETIME_SECONDS", "900"))
        if not 60 <= lifetime <= 3600:
            raise RuntimeError("CLOUD_JWT_LIFETIME_SECONDS must be between 60 and 3600.")
        return cls(database_url, jwt_secret, lifetime)
