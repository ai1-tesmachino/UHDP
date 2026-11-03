import uuid
from datetime import UTC
from datetime import datetime
from uuid import UUID

from app.runtime.models.session import Session


class SessionService:

    def __init__(self):
        self.sessions = {}

    def create(self, session_id: str | None = None):
        resolved_id = str(UUID(session_id)) if session_id else str(uuid.uuid4())
        s = Session(
            id=resolved_id,
            created_at=datetime.now(UTC),
        )

        self.sessions[s.id] = s

        return s

    def get(
        self,
        session_id,
    ):
        return self.sessions.get(
            session_id,
        )

    def list(self):
        return list(self.sessions.values())

    def delete(
        self,
        session_id,
    ):
        return self.sessions.pop(
            session_id,
            None,
        )


session_service = SessionService()