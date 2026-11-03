from __future__ import annotations

from contextlib import contextmanager
from pathlib import Path
from typing import Iterator, Any

from cloud.config import CloudSettings


class CloudDatabase:
    def __init__(self, settings: CloudSettings) -> None:
        try:
            import psycopg
            from psycopg.rows import dict_row
        except ImportError as exc:
            raise RuntimeError(
                "Install cloud/requirements.txt to run the cloud backend."
            ) from exc
        self._psycopg = psycopg
        self._dict_row = dict_row
        self._database_url = settings.database_url

    @contextmanager
    def connection(self) -> Iterator[Any]:
        connection = self._psycopg.connect(
            self._database_url,
            row_factory=self._dict_row,
        )
        try:
            yield connection
            connection.commit()
        except BaseException:
            connection.rollback()
            raise
        finally:
            connection.close()

    def migrate(self) -> None:
        with self.connection() as connection:
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS cloud_schema_migrations (
                    version TEXT PRIMARY KEY,
                    applied_at TIMESTAMPTZ NOT NULL DEFAULT now()
                )
                """
            )
            migration_dir = Path(__file__).parent / "migrations"
            for path in sorted(migration_dir.glob("[0-9]*.sql")):
                exists = connection.execute(
                    "SELECT 1 FROM cloud_schema_migrations WHERE version = %s",
                    (path.name,),
                ).fetchone()
                if exists:
                    continue
                connection.execute(
                    path.read_text(encoding="utf-8"),
                    prepare=False,
                )
                connection.execute(
                    "INSERT INTO cloud_schema_migrations (version) VALUES (%s)",
                    (path.name,),
                )

    def authenticate_station(self, token_sha256: str) -> dict[str, Any] | None:
        with self.connection() as connection:
            return connection.execute(
                """
                SELECT station_id, company_id, name
                FROM stations
                WHERE token_sha256 = %s AND status = 'active'
                """,
                (token_sha256,),
            ).fetchone()

    def get_user(self, company_id: str, username: str) -> dict[str, Any] | None:
        with self.connection() as connection:
            return connection.execute(
                """
                SELECT user_id, company_id, username, password_hash, role_id, active
                FROM users WHERE company_id = %s AND username = %s
                """,
                (company_id, username),
            ).fetchone()

    def get_active_user(self, user_id: str) -> dict[str, Any] | None:
        with self.connection() as connection:
            return connection.execute(
                """
                SELECT user_id, company_id, username, role_id, active
                FROM users WHERE user_id = %s AND active = TRUE
                """,
                (user_id,),
            ).fetchone()
