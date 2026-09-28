from app.hal.diagnostic_request import (
    DiagnosticRequest,
)
from app.hal.diagnostic_service import (
    DiagnosticService,
)
from app.hal.diagnostic_status import (
    DiagnosticStatus,
)


def test_execute_cpu():
    service = DiagnosticService()

    device = (
        service.get_device()
    )

    result = service.execute(
        DiagnosticRequest(
            diagnostic_type="cpu",
            device_id=device.device_id,
        )
    )

    assert (
        result.status
        == DiagnosticStatus.PASSED
    )