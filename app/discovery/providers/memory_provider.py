import json
import math
import platform
import re
import shutil
import subprocess
from datetime import datetime, timezone

import psutil

from app.discovery.discovery_provider import DiscoveryProvider
from app.discovery.discovery_result import DiscoveryResult
from app.discovery.models.device import Device


def _capacity_bytes(value: object) -> int | None:
    if (
        not isinstance(value, bool)
        and isinstance(value, (int, float))
        and math.isfinite(value)
        and value >= 0
    ):
        return int(value)
    if not isinstance(value, str):
        return None
    match = re.fullmatch(
        r"\s*(\d+(?:\.\d+)?)\s*(B|KB|MB|GB|TB|KiB|MiB|GiB|TiB)?\s*",
        value,
        re.IGNORECASE,
    )
    if not match:
        return None
    units = {
        "B": 1,
        "KB": 1000,
        "MB": 1000**2,
        "GB": 1000**3,
        "TB": 1000**4,
        "KIB": 1024,
        "MIB": 1024**2,
        "GIB": 1024**3,
        "TIB": 1024**4,
    }
    unit = (match.group(2) or "B").upper()
    return round(float(match.group(1)) * units[unit])


def _speed_mts(value: object) -> int | float | None:
    if isinstance(value, bool):
        return None
    if isinstance(value, (int, float)):
        if not math.isfinite(value) or value <= 0:
            return None
        return round(value / 1_000_000) if value > 1_000_000 else value
    if isinstance(value, str):
        match = re.fullmatch(r"\s*(\d+(?:\.\d+)?)\s*(MT/s|MHz|GHz)?\s*", value, re.I)
        if not match:
            return None
        speed = float(match.group(1))
        unit = (match.group(2) or "MT/s").lower()
        if unit == "ghz":
            speed *= 1000
        return round(speed) if speed > 0 else None
    return None


def _normalize_linux_modules(items: list[dict]) -> list[dict]:
    modules = []
    for item in items:
        capacity = _capacity_bytes(
            item.get("size", item.get("capacity_bytes", item.get("Capacity")))
        )
        speed = _speed_mts(item.get("clock", item.get("Speed")))
        module = {
            "source": "lshw",
            "manufacturer": item.get("vendor", item.get("Manufacturer")),
            "model": item.get("product", item.get("PartNumber")),
            "part_number": item.get("product", item.get("PartNumber")),
            "serial_number": item.get("serial", item.get("SerialNumber")),
            "bank": item.get("slot", item.get("id", item.get("BankLabel"))),
            "capacity_bytes": capacity,
            "speed_mts": speed,
        }
        module["capacity_gb"] = (
            round(capacity / (1024**3), 2) if capacity is not None else None
        )
        modules.append(module)
    return modules


def _lshw_memory_modules(data: object) -> list[dict]:
    found = []
    stack = [data]
    while stack:
        item = stack.pop()
        if isinstance(item, list):
            stack.extend(reversed(item))
        elif isinstance(item, dict):
            identifier = item.get("id")
            description = item.get("description", "")
            if (
                isinstance(identifier, str)
                and identifier.startswith("bank:")
            ) or (
                isinstance(description, str)
                and "bank" in description.lower()
            ):
                found.append(item)
            children = item.get("children")
            if isinstance(children, list):
                stack.extend(reversed(children))
    return found


class MemoryProvider(DiscoveryProvider):

    def discover(self) -> DiscoveryResult:
        result = DiscoveryResult()

        memory = psutil.virtual_memory()

        modules = []
        inventory_warning = None
        module_source = None
        if platform.system() == "Windows":
            powershell = shutil.which("powershell.exe") or shutil.which("powershell")
        else:
            powershell = None
        lshw = shutil.which("lshw") if platform.system() == "Linux" else None

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
        elif lshw:
            try:
                result_json = subprocess.run(
                    [lshw, "-class", "memory", "-json"],
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
                        modules = _lshw_memory_modules(data)
                        modules = _normalize_linux_modules(modules)
                        module_source = "lshw"
                        if not modules:
                            inventory_warning = (
                                "lshw did not expose individual memory-module records"
                            )
                else:
                    inventory_warning = result_json.stderr.strip() or "lshw memory query failed"
        else:
            inventory_warning = "Memory module detail requires Windows CIM or Linux lshw; capacity is still available from psutil."

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
                "physical_module_count": len(modules) if module_source else None,
                "installed_slots": (
                    len(modules) if module_source else None
                ),
                "module_inventory_warning": inventory_warning,
                "module_inventory_status": (
                    "detected" if modules
                    else "unavailable" if inventory_warning
                    else "unknown"
                ),
                "module_inventory_source": module_source,
                "collected_at": datetime.now(timezone.utc).isoformat(),
                "inventory_source": "psutil",
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