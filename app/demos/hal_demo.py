from pprint import pprint

from app.hal.diagnostic_request import (
    DiagnosticRequest,
)
from app.hal.diagnostic_service import (
    DiagnosticService,
)


def run_demo() -> None:
    service = DiagnosticService()

    device = service.get_device()

    print("\n=== DEVICE ===")
    pprint(device)

    diagnostics = [
        "cpu",
        "memory",
        "storage",
        "network",
        "usb",
        "battery",
        "system",
    ]

    for diagnostic_type in diagnostics:
        print(
            f"\n=== {diagnostic_type.upper()} ==="
        )

        request = DiagnosticRequest(
            diagnostic_type=diagnostic_type,
            device_id=device.device_id,
        )

        result = service.execute(
            request,
        )

        print(
            f"Status: {result.status.value}"
        )

        print(
            f"Message: {result.message}"
        )

        pprint(
            result.details,
        )


if __name__ == "__main__":
    run_demo()