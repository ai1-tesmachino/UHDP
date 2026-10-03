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

def test_execute_single_diagnostic():

    service = DiagnosticSessionService()

    session = service.create_session()

    result = (
        service.execute_diagnostic(
            session_id=session[
                "session_id"
            ],
            device_id="cpu",
            diagnostic_type="cpu",
        )
    )

    assert (
        result["result"]
        .diagnostic_type
        == "cpu"
    )

    assert (
        result["result"]
        .device_id
        == "cpu"
    )

    assert (
        result["summary"]
        .total
        == 1
    )