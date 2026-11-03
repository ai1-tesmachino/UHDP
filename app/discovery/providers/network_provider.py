import json
import platform
import subprocess
from datetime import datetime, timezone
from pathlib import Path

import psutil

from app.discovery.discovery_provider import DiscoveryProvider
from app.discovery.discovery_result import DiscoveryResult
from app.discovery.models.device import Device


LINUX_NET_ROOT = Path("/sys/class/net")
LINUX_BLUETOOTH_ROOT = Path("/sys/class/bluetooth")


def _read_sysfs(path: Path) -> str | None:
    try:
        value = path.read_text(encoding="utf-8", errors="replace").strip()
    except OSError:
        return None
    return value or None


def _linux_adapters() -> tuple[list[dict], list[str], str | None]:
    try:
        interface_paths = sorted(LINUX_NET_ROOT.iterdir())
    except OSError as exc:
        return [], [], str(exc)

    try:
        interface_addresses = psutil.net_if_addrs()
        interface_stats = psutil.net_if_stats()
    except (OSError, AttributeError) as exc:
        interface_addresses = {}
        interface_stats = {}
        warning = str(exc)
    else:
        warning = None

    adapters = []
    for interface in interface_paths:
        if interface.name == "lo" or _read_sysfs(interface / "type") == "772":
            continue
        addresses = interface_addresses.get(interface.name, [])
        ips = [
            address.address
            for address in addresses
            if address.family in {psutil.AF_INET, psutil.AF_INET6}
        ]
        mac = next(
            (
                address.address
                for address in addresses
                if getattr(address.family, "name", "") in {"AF_LINK", "AF_PACKET"}
            ),
            _read_sysfs(interface / "address"),
        )
        stats = interface_stats.get(interface.name)
        speed = getattr(stats, "speed", 0) if stats else 0
        adapters.append({
            "name": interface.name,
            "type": "wifi" if (interface / "wireless").exists() else "network",
            "mac_address": mac,
            "ip_addresses": ips,
            "operstate": _read_sysfs(interface / "operstate"),
            "link_up": getattr(stats, "isup", None) if stats else None,
            "speed_mbps": speed if speed and speed > 0 else None,
            "source": "sysfs/psutil",
        })

    try:
        bluetooth = sorted(path.name for path in LINUX_BLUETOOTH_ROOT.iterdir())
    except FileNotFoundError:
        bluetooth = []
    except OSError as exc:
        bluetooth = []
        warning = warning or str(exc)
    return adapters, bluetooth, warning


class NetworkProvider(DiscoveryProvider):

    def discover(self) -> DiscoveryResult:
        result = DiscoveryResult()

        current_platform = platform.system()
        adapters = []
        bluetooth = []
        warning = None

        if current_platform == "Linux":
            adapters, bluetooth, warning = _linux_adapters()
        elif current_platform == "Windows":
            command = """
            Get-NetAdapter |
            Select Name,
                   Status,
                   MacAddress,
                   LinkSpeed |
            ConvertTo-Json -Compress
            """

            try:
                response = subprocess.run(
                    [
                        "powershell.exe",
                        "-NoProfile",
                        "-ExecutionPolicy",
                        "Bypass",
                        "-Command",
                        command,
                    ],
                    capture_output=True,
                    text=True,
                    timeout=10,
                    check=False,
                )
            except (OSError, subprocess.SubprocessError) as exc:
                warning = str(exc)
                response = None

            if response is not None and response.returncode == 0:
                try:
                    payload = json.loads(response.stdout) if response.stdout.strip() else []
                except json.JSONDecodeError as exc:
                    warning = f"Network adapter inventory returned invalid JSON: {exc}"
                else:
                    if isinstance(payload, dict):
                        adapters = [payload]
                    elif isinstance(payload, list) and all(
                        isinstance(item, dict) for item in payload
                    ):
                        adapters = payload
                    else:
                        warning = "Network adapter inventory returned an unexpected shape"
            elif response is not None:
                warning = response.stderr.strip() or "Network adapter inventory failed"
        else:
            warning = f"Network inventory is not implemented for {current_platform}"

        result.add_device(
            Device(
                device_id="network",
                device_type="network",
                name="Network Adapters",
                properties={
                    "adapter_count": len(
                        adapters
                    ),
                    "adapters": adapters,
                    "bluetooth_controllers": bluetooth,
                    "bluetooth_controller_count": len(bluetooth),
                    "inventory_status": (
                        "detected" if adapters or bluetooth
                        else "unavailable" if warning
                        else "not_detected"
                    ),
                    "inventory_source": (
                        ["sysfs", "psutil"] if current_platform == "Linux"
                        else ["PowerShell"] if current_platform == "Windows"
                        else []
                    ),
                    "inventory_warning": warning,
                    "connectivity_verified": False,
                    "collected_at": datetime.now(timezone.utc).isoformat(),
                },
            )
        )

        return result