from app.runtime.services.diagnostic_service import (
    DiagnosticService,
)
from app.hal.diagnostic_status import (
    DiagnosticStatus,
)


def test_runtime_execute():
    service = DiagnosticService()

    result = service.execute(
        "cpu",
    )

    assert (
        result.status
        == DiagnosticStatus.PASSED
    )






