from app.hal.diagnostic_request import (
    DiagnosticRequest,
)


def test_request_creation():
    request = DiagnosticRequest(
        diagnostic_type="cpu",
        device_id="device-1",
    )

    assert request.diagnostic_id
    assert request.diagnostic_type == "cpu"
    assert request.device_id == "device-1"
    assert request.parameters == {}