import uuid

from app.diagnostics.diagnostic_session_result import (
    DiagnosticSessionResult,
)


class DiagnosticSession:

    def __init__(self) -> None:
        self.session_id = str(
            uuid.uuid4(),
        )

        self.result = (
            DiagnosticSessionResult()
        )