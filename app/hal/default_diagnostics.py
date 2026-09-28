from app.hal.diagnostic_registry import (
    DiagnosticRegistry,
)
from app.hal.diagnostics.cpu_diagnostic import (
    CpuDiagnostic,
)
from app.hal.diagnostics.memory_diagnostic import (
    MemoryDiagnostic,
)
from app.hal.diagnostics.storage_diagnostic import (
    StorageDiagnostic,
)

from app.hal.diagnostics.network_diagnostic import (
    NetworkDiagnostic,
)

from app.hal.diagnostics.usb_diagnostic import (
    UsbDiagnostic,
)

from app.hal.diagnostics.battery_diagnostic import (
    BatteryDiagnostic,
)

from app.hal.diagnostics.system_diagnostic import (
    SystemDiagnostic,
)


def create_default_registry() -> DiagnosticRegistry:
    registry = DiagnosticRegistry()

    registry.register(
        "cpu",
        CpuDiagnostic(),
    )

    registry.register(
        "memory",
        MemoryDiagnostic(),
    )

    registry.register(
        "storage",
        StorageDiagnostic(),
    )

    registry.register(
    "network",
    NetworkDiagnostic(),
    )

    registry.register(
    "usb",
    UsbDiagnostic(),
)

    registry.register(
        "battery",
        BatteryDiagnostic(),
    )

    registry.register(
        "system",
        SystemDiagnostic(),
    )

    return registry