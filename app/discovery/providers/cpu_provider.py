import platform
from datetime import datetime, timezone
from pathlib import Path

import psutil

from app.discovery.discovery_provider import DiscoveryProvider
from app.discovery.discovery_result import DiscoveryResult
from app.discovery.models.device import Device


LINUX_CPUINFO = Path("/proc/cpuinfo")
LINUX_HWMON_ROOT = Path("/sys/class/hwmon")


def _linux_cpuinfo() -> dict[str, str]:
    try:
        lines = LINUX_CPUINFO.read_text(
            encoding="utf-8",
            errors="replace",
        ).splitlines()
    except OSError:
        return {}

    values: dict[str, str] = {}
    for line in lines:
        key, separator, value = line.partition(":")
        key = key.strip().lower()
        value = value.strip()
        if separator and value and key in {
            "model name",
            "hardware",
            "vendor_id",
            "flags",
            "features",
        }:
            values.setdefault(key, value)
    return values


def _linux_cpu_temperature_sensors() -> list[dict[str, str | float]]:
    sensors = []
    try:
        hwmon_devices = sorted(LINUX_HWMON_ROOT.glob("hwmon*"))
    except OSError:
        return sensors

    for hwmon in hwmon_devices:
        for temperature_path in sorted(hwmon.glob("temp*_input")):
            raw_value = None
            try:
                raw_value = temperature_path.read_text(
                    encoding="utf-8",
                    errors="replace",
                ).strip()
                millidegrees = int(raw_value)
            except (OSError, ValueError):
                continue
            if not -100000 <= millidegrees <= 250000:
                continue
            label_path = temperature_path.with_name(
                temperature_path.name.removesuffix("_input") + "_label"
            )
            try:
                label = label_path.read_text(
                    encoding="utf-8",
                    errors="replace",
                ).strip()
            except OSError:
                label = ""
            try:
                sensor_name = (hwmon / "name").read_text(
                    encoding="utf-8",
                    errors="replace",
                ).strip()
            except OSError:
                sensor_name = ""
            identity = f"{sensor_name} {label}".lower()
            if not any(
                token in identity
                for token in ("coretemp", "k10temp", "zenpower", "cpu", "package")
            ):
                continue
            sensors.append({
                "name": label or sensor_name or temperature_path.parent.name,
                "temperature_c": millidegrees / 1000,
                "source": str(temperature_path),
            })
    return sensors


class CPUProvider(DiscoveryProvider):

    def discover(self) -> DiscoveryResult:
        result = DiscoveryResult()

        linux_info = _linux_cpuinfo() if platform.system() == "Linux" else {}
        cpu_name = (
            linux_info.get("model name")
            or linux_info.get("hardware")
            or platform.processor()
        )

        if not cpu_name:
            cpu_name = platform.machine()

        try:
            frequency = psutil.cpu_freq()
        except (OSError, AttributeError):
            frequency = None
        instruction_sets = (
            linux_info.get("flags", linux_info.get("features", "")).split()
        )
        try:
            logical_cores = psutil.cpu_count(logical=True)
        except (OSError, AttributeError):
            logical_cores = None
        try:
            physical_cores = psutil.cpu_count(logical=False)
        except (OSError, AttributeError):
            physical_cores = None
        temperature_sensors = (
            _linux_cpu_temperature_sensors()
            if platform.system() == "Linux"
            else []
        )
        if temperature_sensors:
            temperature_status = "detected"
        elif platform.system() == "Linux":
            temperature_status = (
                "not_detected" if LINUX_HWMON_ROOT.exists() else "unsupported"
            )
        else:
            temperature_status = "unsupported"
        cpuinfo_available = bool(linux_info)
        device = Device(
            device_id="cpu",
            device_type="cpu",
            name=cpu_name,
            properties={
                "physical_cores": physical_cores,
                "logical_cores": logical_cores,
                "architecture": platform.machine(),
                "instruction_sets": instruction_sets,
                "vendor": linux_info.get("vendor_id") or platform.processor() or None,
                "minimum_frequency_mhz": (
                    round(frequency.min, 2)
                    if frequency and frequency.min
                    else None
                ),
                "current_frequency_mhz": (
                    round(frequency.current, 2)
                    if frequency
                    else None
                ),
                "max_frequency_mhz": (
                    round(frequency.max, 2)
                    if frequency and frequency.max
                    else None
                ),
                "platform": platform.platform(),
                "collected_at": datetime.now(timezone.utc).isoformat(),
                "temperature_sensors": temperature_sensors,
                "temperature_available": bool(temperature_sensors),
                "temperature_status": temperature_status,
                "temperature_warning": (
                    None if temperature_sensors
                    else "No CPU temperature sensor was exposed through sysfs hwmon"
                ),
                "model_source": (
                    "/proc/cpuinfo"
                    if linux_info.get("model name") or linux_info.get("hardware")
                    else "platform.processor/architecture"
                ),
                "temperature_source": "sysfs hwmon" if temperature_sensors else None,
                "inventory_status": (
                    "detected"
                    if logical_cores is not None or cpuinfo_available
                    else "unknown"
                ),
                "inventory_source": (
                    ["/proc/cpuinfo", "psutil", "/sys/class/hwmon"]
                    if platform.system() == "Linux"
                    else ["platform", "psutil"]
                ),
            },
        )

        result.add_device(device)

        return result