from app.hal.diagnostic_request import (
    DiagnosticRequest,
)
from app.hal.diagnostic_service import (
    DiagnosticService as HalDiagnosticService,
)
from app.hal.diagnostic_status import (
    DiagnosticStatus,
)
from app.runtime.services.diagnostic_service import (
    DiagnosticService,
)


def test_execute_cpu():
    hal_service = HalDiagnosticService()

    device = (
        hal_service.get_device()
    )

    service = DiagnosticService(
        hal_service,
    )

    result = service.execute(
        "cpu",
        device_id=device.device_id,
    )

    assert (
        result.status
        == DiagnosticStatus.PASSED
    )


def test_execute_cpu_with_device_id():
    service = DiagnosticService()

    result = service.execute(
        "cpu",
        device_id="cpu",
    )

    assert (
        result.diagnostic_type
        == "cpu"
    )

    assert (
        result.device_id
        == "cpu"
    )

    assert (
        result.status
        == DiagnosticStatus.PASSED
    )

def test_execute_memory_with_device_id():
    service = DiagnosticService()

    result = service.execute(
        "memory",
        device_id="memory",
    )

    assert result.diagnostic_type == "memory"
    assert result.device_id == "memory"
    assert result.status == DiagnosticStatus.PASSED


def test_execute_storage_with_device_id():
    service = DiagnosticService()

    result = service.execute(
        "storage",
        device_id="storage:C:\\",
    )

    assert result.diagnostic_type == "storage"
    assert result.device_id == "storage:C:\\"
    assert result.status == DiagnosticStatus.PASSED


