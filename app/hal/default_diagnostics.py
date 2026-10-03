from app.hal.diagnostic_registry import (
    DiagnosticRegistry,
)
from app.hal.diagnostics.battery_diagnostic import (
    BatteryDiagnostic,
)
from app.hal.diagnostics.bluetooth_diagnostic import (
    BluetoothDiagnostic,
)
from app.hal.diagnostics.cpu_diagnostic import (
    CpuDiagnostic,
)
from app.hal.diagnostics.display_diagnostic import (
    DisplayDiagnostic,
)
from app.hal.diagnostics.hdmi_diagnostic import (
    HdmiDiagnostic,
)
from app.hal.diagnostics.keyboard_diagnostic import (
    KeyboardDiagnostic,
)
from app.hal.diagnostics.memory_diagnostic import (
    MemoryDiagnostic,
)
from app.hal.diagnostics.network_diagnostic import (
    NetworkDiagnostic,
)
from app.hal.diagnostics.speaker_diagnostic import (
    SpeakerDiagnostic,
)
from app.hal.diagnostics.storage_diagnostic import (
    StorageDiagnostic,
)
from app.hal.diagnostics.system_diagnostic import (
    SystemDiagnostic,
)
from app.hal.diagnostics.usb_c_diagnostic import (
    UsbCDiagnostic,
)
from app.hal.diagnostics.usb_diagnostic import (
    UsbDiagnostic,
)
from app.hal.diagnostics.vga_diagnostic import (
    VgaDiagnostic,
)
from app.hal.diagnostics.webcam_diagnostic import (
    WebcamDiagnostic,
)
from app.hal.diagnostics.wifi_diagnostic import (
    WifiDiagnostic,
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
        "display",
        DisplayDiagnostic(),
    )

    registry.register(
        "battery",
        BatteryDiagnostic(),
    )

    registry.register(
        "webcam",
        WebcamDiagnostic(),
    )

    registry.register(
        "keyboard",
        KeyboardDiagnostic(),
    )

    registry.register(
        "speaker",
        SpeakerDiagnostic(),
    )

    registry.register(
        "usb",
        UsbDiagnostic(),
    )

    registry.register(
        "usb_c",
        UsbCDiagnostic(),
    )

    registry.register(
        "hdmi",
        HdmiDiagnostic(),
    )

    registry.register(
        "vga",
        VgaDiagnostic(),
    )

    registry.register(
        "wifi",
        WifiDiagnostic(),
    )

    registry.register(
        "bluetooth",
        BluetoothDiagnostic(),
    )

    registry.register(
        "system",
        SystemDiagnostic(),
    )

    return registry