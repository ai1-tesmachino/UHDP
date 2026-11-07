import math
import platform
from numbers import Real

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


def _valid_battery_percent(value: object) -> bool:
    if isinstance(value, bool) or not isinstance(value, Real):
        return False
    try:
        return math.isfinite(value) and 0 <= value <= 100
    except OverflowError:
        return False


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
                battery_present = details.get("battery_present")
                if battery_present is False:
                    status = DiagnosticStatus.NOT_APPLICABLE
                elif battery_present is not True:
                    status = DiagnosticStatus.INCONCLUSIVE
                else:
                    batteries = details.get("batteries")
                    if isinstance(batteries, list) and batteries:
                        capacities = [
                            battery.get("capacity_percent")
                            for battery in batteries
                            if isinstance(battery, dict)
                        ]
                        if len(capacities) == len(batteries) and all(
                            isinstance(capacity, int)
                            and not isinstance(capacity, bool)
                            and 0 <= capacity <= 100
                            for capacity in capacities
                        ):
                            details["percent"] = min(capacities)
                    status = (
                        DiagnosticStatus.PASSED
                        if _valid_battery_percent(details.get("percent"))
                        else DiagnosticStatus.INCONCLUSIVE
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
                if battery is None:
                    status = DiagnosticStatus.NOT_APPLICABLE
                else:
                    status = (
                        DiagnosticStatus.PASSED
                        if _valid_battery_percent(battery.percent)
                        else DiagnosticStatus.INCONCLUSIVE
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