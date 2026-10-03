import json
import platform
import shutil
import subprocess

import psutil

from app.discovery.discovery_provider import DiscoveryProvider
from app.discovery.discovery_result import DiscoveryResult
from app.discovery.models.device import Device


class MemoryProvider(DiscoveryProvider):

    def discover(self) -> DiscoveryResult:
        result = DiscoveryResult()

        memory = psutil.virtual_memory()

        modules = []
        inventory_warning = None
        if platform.system() == "Windows":
            powershell = shutil.which("powershell.exe") or shutil.which("powershell")
        else:
            powershell = None

        if powershell:
            command = """
            Get-CimInstance Win32_PhysicalMemory |
            Select-Object Manufacturer,
                        PartNumber,
                        SerialNumber,
                        Capacity,
                        Speed,
                        ConfiguredClockSpeed,
                        MemoryType,
                        SMBIOSMemoryType,
                        BankLabel |
            ConvertTo-Json -Compress
            """
            try:
                result_json = subprocess.run(
                    [
                        powershell,
                        "-NoProfile",
                        "-NonInteractive",
                        "-Command",
                        command,
                    ],
                    capture_output=True,
                    text=True,
                    timeout=10,
                    check=False,
                )
            except (OSError, subprocess.SubprocessError) as exc:
                inventory_warning = str(exc)
            else:
                if result_json.returncode == 0:
                    try:
                        data = json.loads(result_json.stdout) if result_json.stdout.strip() else []
                    except json.JSONDecodeError as exc:
                        inventory_warning = f"Physical memory query returned invalid JSON: {exc}"
                    else:
                        modules = data if isinstance(data, list) else [data]
                else:
                    inventory_warning = result_json.stderr.strip() or "Physical memory query failed"
        elif platform.system() == "Linux" and shutil.which("lshw"):
            try:
                result_json = subprocess.run(
                    ["lshw", "-class", "memory", "-json"],
                    capture_output=True,
                    text=True,
                    timeout=10,
                    check=False,
                )
            except (OSError, subprocess.SubprocessError) as exc:
                inventory_warning = str(exc)
            else:
                if result_json.returncode == 0:
                    try:
                        data = json.loads(result_json.stdout) if result_json.stdout.strip() else []
                    except json.JSONDecodeError as exc:
                        inventory_warning = f"lshw returned invalid JSON: {exc}"
                    else:
                        data = data if isinstance(data, list) else [data]
                        modules = [
                            item
                            for item in data
                            if isinstance(item, dict)
                            and (
                                item.get("id", "").startswith("bank:")
                                or "bank" in item.get("description", "").lower()
                            )
                        ]
                else:
                    inventory_warning = result_json.stderr.strip() or "lshw memory query failed"
        else:
            inventory_warning = "Memory module detail requires Windows CIM or Linux lshw; capacity is still available from psutil."

        for module in modules:
            if (
                isinstance(module, dict)
                and "size" not in module
                and module.get("Capacity") is not None
            ):
                module["capacity_bytes"] = int(module["Capacity"])
                module["capacity_gb"] = round(module["capacity_bytes"] / (1024**3), 2)

        device = Device(
            device_id="memory",
            device_type="memory",
            name="System Memory",
            properties={
                "total_bytes": memory.total,
                "available_bytes": memory.available,
                "used_bytes": memory.used,
                "free_bytes": memory.free,
                "percent_used": memory.percent,
                "total_gb": round(
                    memory.total / (1024**3),
                    2,
                ),
                "memory_modules": modules,
                "installed_slots": len(modules),
                "module_inventory_warning": inventory_warning,
                "memory_type": (
                    modules[0].get("SMBIOSMemoryType")
                    if modules and isinstance(modules[0], dict)
                    else None
                ),
                "platform": platform.platform(),
            },
        )

        result.add_device(device)

        return result