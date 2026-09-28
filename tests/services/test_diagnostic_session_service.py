from app.services.diagnostic_session_service import (
    DiagnosticSessionService,
)


def test_create_diagnostic_session():

    service = DiagnosticSessionService()

    session = service.create_session()

    assert session["session_id"]
    assert session["status"] == "created"
    assert session["device_id"] is None
    assert session["workflow_result"] is None
    assert session["report"] is None


def test_get_diagnostic_session():

    service = DiagnosticSessionService()

    session = service.create_session()

    loaded = service.get_session(
        session["session_id"]
    )

    assert loaded is session