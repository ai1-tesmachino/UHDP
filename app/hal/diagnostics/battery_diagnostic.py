import platform
import psutil

from app.core.linux_hardware import linux_battery_inventory
from app.hal.diagnostic_request import (
    DiagnosticRequest,
)
from app.hal.diagnostic_result import (
    DiagnosticResult,
)
from app.hal.diagnostic_status import (
    DiagnosticStatus,
)


class BatteryDiagnostic:

    def execute(
        self,
        request: DiagnosticRequest,
    ) -> DiagnosticResult:
        try:
            if platform.system() == "Linux":
                details, warning = linux_battery_inventory()
                if warning:
                    details["inventory_warning"] = warning
                battery_present = details["battery_present"]
                status = (
                    DiagnosticStatus.PASSED
                    if battery_present
                    else DiagnosticStatus.NOT_APPLICABLE
                )
            else:
                battery = psutil.sensors_battery()

                if battery is None:
                    details = {"battery_present": False}
                else:
                    details = {
                        "battery_present": True,
                        "percent": battery.percent,
                        "power_plugged": battery.power_plugged,
                        "seconds_left": battery.secsleft,
                    }
                status = (
                    DiagnosticStatus.PASSED
                    if battery is not None
                    else DiagnosticStatus.NOT_APPLICABLE
                )

            return DiagnosticResult(
                diagnostic_id=request.diagnostic_id,
                diagnostic_type=request.diagnostic_type,
                device_id=request.device_id,
                status=status,
                message="Battery diagnostic completed",
                details=details,
            )

        except Exception as ex:
            return DiagnosticResult(
                diagnostic_id=request.diagnostic_id,
                diagnostic_type=request.diagnostic_type,
                device_id=request.device_id,
                status=DiagnosticStatus.ERROR,
                message=str(ex),
            )