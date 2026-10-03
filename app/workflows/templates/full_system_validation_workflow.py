from app.workflows.actions.diagnostics.fail_if_diagnostic_failed_action import (
    FailIfDiagnosticFailedAction,
)
from app.workflows.actions.diagnostics.run_battery_diagnostic_action import (
    RunBatteryDiagnosticAction,
)
from app.workflows.actions.diagnostics.run_bluetooth_diagnostic_action import (
    RunBluetoothDiagnosticAction,
)
from app.workflows.actions.diagnostics.run_cpu_diagnostic_action import (
    RunCpuDiagnosticAction,
)
from app.workflows.actions.diagnostics.run_display_diagnostic_action import (
    RunDisplayDiagnosticAction,
)
from app.workflows.actions.diagnostics.run_hdmi_diagnostic_action import (
    RunHdmiDiagnosticAction,
)
from app.workflows.actions.diagnostics.run_keyboard_diagnostic_action import (
    RunKeyboardDiagnosticAction,
)
from app.workflows.actions.diagnostics.run_memory_diagnostic_action import (
    RunMemoryDiagnosticAction,
)
from app.workflows.actions.diagnostics.run_network_diagnostic_action import (
    RunNetworkDiagnosticAction,
)
from app.workflows.actions.diagnostics.run_speaker_diagnostic_action import (
    RunSpeakerDiagnosticAction,
)
from app.workflows.actions.diagnostics.run_storage_diagnostic_action import (
    RunStorageDiagnosticAction,
)
from app.workflows.actions.diagnostics.run_usb_c_diagnostic_action import (
    RunUsbCDiagnosticAction,
)
from app.workflows.actions.diagnostics.run_usb_diagnostic_action import (
    RunUsbDiagnosticAction,
)
from app.workflows.actions.diagnostics.run_vga_diagnostic_action import (
    RunVgaDiagnosticAction,
)
from app.workflows.actions.diagnostics.run_webcam_diagnostic_action import (
    RunWebcamDiagnosticAction,
)
from app.workflows.actions.diagnostics.run_wifi_diagnostic_action import (
    RunWifiDiagnosticAction,
)

from app.workflows.workflow import Workflow


DIAGNOSTIC_ACTIONS = {
    "cpu": (
        RunCpuDiagnosticAction,
        "cpu_result",
        "CPU diagnostic failed",
    ),
    "memory": (
        RunMemoryDiagnosticAction,
        "memory_result",
        "Memory diagnostic failed",
    ),
    "storage": (
        RunStorageDiagnosticAction,
        "storage_result",
        "Storage diagnostic failed",
    ),
    "network": (
        RunNetworkDiagnosticAction,
        "network_result",
        "Network diagnostic failed",
    ),
    "display": (
        RunDisplayDiagnosticAction,
        "display_result",
        "Display diagnostic failed",
    ),
    "battery": (
        RunBatteryDiagnosticAction,
        "battery_result",
        "Battery diagnostic failed",
    ),
    "webcam": (
        RunWebcamDiagnosticAction,
        "webcam_result",
        "Webcam diagnostic failed",
    ),
    "keyboard": (
        RunKeyboardDiagnosticAction,
        "keyboard_result",
        "Keyboard diagnostic failed",
    ),
    "speaker": (
        RunSpeakerDiagnosticAction,
        "speaker_result",
        "Speaker diagnostic failed",
    ),
    "usb": (
        RunUsbDiagnosticAction,
        "usb_result",
        "USB diagnostic failed",
    ),
    "usb_c": (
        RunUsbCDiagnosticAction,
        "usb_c_result",
        "USB-C diagnostic failed",
    ),
    "hdmi": (
        RunHdmiDiagnosticAction,
        "hdmi_result",
        "HDMI diagnostic failed",
    ),
    "vga": (
        RunVgaDiagnosticAction,
        "vga_result",
        "VGA diagnostic failed",
    ),
    "wifi": (
        RunWifiDiagnosticAction,
        "wifi_result",
        "Wi-Fi diagnostic failed",
    ),
    "bluetooth": (
        RunBluetoothDiagnosticAction,
        "bluetooth_result",
        "Bluetooth diagnostic failed",
    ),
}


DEFAULT_DIAGNOSTICS = [
    "cpu",
    "memory",
    "storage",
    "network",
    
]


def create_full_system_validation_workflow(
    selected_diagnostics: list[str] | None = None,
) -> Workflow:

    diagnostics = (
        selected_diagnostics
        if selected_diagnostics
        else DEFAULT_DIAGNOSTICS
    )

    actions = []

    for diagnostic in diagnostics:

        definition = DIAGNOSTIC_ACTIONS.get(
            diagnostic
        )

        if definition is None:
            continue

        action_class, result_key, message = definition

        actions.append(
            action_class(
                result_key=result_key,
            )
        )

        actions.append(
            FailIfDiagnosticFailedAction(
                result_key=result_key,
                message=message,
            )
        )

    return Workflow(
        name="full_system_validation_workflow",
        actions=actions,
    )