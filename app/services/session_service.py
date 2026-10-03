import uuid
from datetime import UTC
from datetime import datetime

from app.runtime.models.session import Session


class SessionService:

    def __init__(self):
        self.sessions = {}

    def create(self):
        s = Session(
            id=str(uuid.uuid4()),
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

    def delete(
        self,
        session_id,
    ):
        return self.sessions.pop(
            session_id,
            None,
        )


session_service = SessionService()