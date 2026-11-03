from pathlib import Path
import json
from app.core.config import get_settings
from app.persistence.session_serialization import (
    json_value,
    restore_session,
)
from app.services.session_repository import (
    SessionRepository,
)


class FileSessionRepository(
    SessionRepository
):

    def __init__(
        self,
            storage_path: str | None = None,
        ):

        settings = get_settings()

        self._storage_path = Path(
            storage_path
            or settings.SESSIONS_DIRECTORY
            )

        self._storage_path.mkdir(
            parents=True,
            exist_ok=True,
        )

    def save(
        self,
        session: dict,
    ) -> None:

        data = json_value(session)

        file_path = (
            self._storage_path /
            f"{session['session_id']}.json"
        )

        serialized = json.dumps(
            data,
            indent=4,
            default=str,
        )

        with open(
            file_path,
            "w",
            encoding="utf-8",
        ) as file:
            file.write(serialized)

    def get(
        self,
        session_id: str,
    ) -> dict | None:

        file_path = (
            self._storage_path /
            f"{session_id}.json"
        )

        if not file_path.exists():
            return None

        with open(
            file_path,
            "r",
            encoding="utf-8",
        ) as file:
            return restore_session(json.load(file))

    def list_all(
        self,
    ) -> list[dict]:

        sessions = []

        for file_path in (
            self._storage_path.glob(
                "*.json"
            )
        ):
            with open(
                file_path,
                "r",
                encoding="utf-8",
            ) as file:
                sessions.append(
                    restore_session(json.load(file))
                )

        return sessions

    def delete(
        self,
        session_id: str,
    ) -> None:

        file_path = (
            self._storage_path /
            f"{session_id}.json"
        )

        if file_path.exists():
            file_path.unlink()