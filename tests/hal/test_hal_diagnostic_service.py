from app.hal.diagnostic_request import (
    DiagnosticRequest,
)
from app.hal.diagnostic_service import (
    DiagnosticService,
)
from app.hal.diagnostic_status import (
    DiagnosticStatus,
)


def test_diagnostic_service_registry():
    service = DiagnosticService()

    diagnostics = (
        service.registry.list_diagnostics()
    )

    assert diagnostics == [
    "battery",
    "bluetooth",
    "cpu",
    "display",
    "hdmi",
    "keyboard",
    "memory",
    "network",
    "speaker",
    "storage",
    "system",
    "usb",
    "usb_c",
    "vga",
    "webcam",
    "wifi",
]


def test_diagnostic_service_execute_cpu():
    service = DiagnosticService()

    request = DiagnosticRequest(
        diagnostic_type="cpu",
        device_id="cpu",
    )

    result = service.execute(
        request,
    )

    assert (
        result.diagnostic_id
        == request.diagnostic_id
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


def test_diagnostic_service_execute_memory():
    service = DiagnosticService()

    request = DiagnosticRequest(
        diagnostic_type="memory",
        device_id="memory",
    )

    result = service.execute(
        request,
    )

    assert (
        result.status
        == DiagnosticStatus.PASSED
    )

    assert (
        "total_ram_mb"
        in result.details
    )


def test_diagnostic_service_execute_storage():
    service = DiagnosticService()

    request = DiagnosticRequest(
        diagnostic_type="storage",
        device_id="storage:C:\\",
    )

    result = service.execute(
        request,
    )

    assert (
        result.status
        == DiagnosticStatus.PASSED
    )

    assert (
        "drives"
        in result.details
    )


def test_diagnostic_service_unknown_diagnostic():
    service = DiagnosticService()

    request = DiagnosticRequest(
        diagnostic_type="unknown",
        device_id="cpu",
    )

    result = service.execute(
        request,
    )

    assert (
        result.status
        == DiagnosticStatus.ERROR
    )
