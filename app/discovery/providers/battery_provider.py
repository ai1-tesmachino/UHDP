import json
import platform
import shutil
import subprocess

from app.core.linux_hardware import linux_battery_inventory
from app.discovery.discovery_provider import DiscoveryProvider
from app.discovery.discovery_result import DiscoveryResult
from app.discovery.models.device import Device

class BatteryProvider(DiscoveryProvider):

    def discover(self) -> DiscoveryResult:
        result = DiscoveryResult()

        warning = None
        if platform.system() == "Linux":
            battery, warning = linux_battery_inventory()
        elif platform.system() == "Windows":
            powershell = shutil.which("powershell.exe") or shutil.which("powershell")
            if not powershell:
                battery, warning = {}, "PowerShell is unavailable"
            else:
                command = """
                Get-CimInstance Win32_Battery |
                Select Name,Status,EstimatedChargeRemaining,DesignVoltage |
                ConvertTo-Json -Compress
                """
                try:
                    response = subprocess.run(
                        [powershell, "-NoProfile", "-NonInteractive", "-Command", command],
                        capture_output=True,
                        text=True,
                        timeout=10,
                        check=False,
                    )
                    if response.returncode == 0:
                        parsed = json.loads(response.stdout) if response.stdout.strip() else []
                        batteries = parsed if isinstance(parsed, list) else [parsed]
                        battery = {
                            "battery_present": bool(batteries),
                            "batteries": batteries,
                            "battery_count": len(batteries),
                        }
                    else:
                        battery, warning = {}, response.stderr.strip() or "Windows battery query failed"
                except (OSError, subprocess.SubprocessError, json.JSONDecodeError) as exc:
                    battery, warning = {}, str(exc)
        else:
            battery, warning = {}, f"Battery inventory is not implemented for {platform.system()}"

        if warning:
            battery["inventory_warning"] = warning

        result.add_device(
            Device(
                device_id="battery",
                device_type="battery",
                name="Battery",
                properties=battery,
            )
        )

        return result