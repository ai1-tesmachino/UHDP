import platform
import json
import shutil
import subprocess
from pathlib import Path
import psutil

from app.discovery.discovery_provider import DiscoveryProvider
from app.discovery.discovery_result import DiscoveryResult
from app.discovery.models.device import Device

LINUX_BLOCK_ROOT = Path("/sys/block")


def _read_sysfs(path: Path) -> str | None:
    try:
        value = path.read_text(encoding="utf-8", errors="replace").strip()
    except OSError:
        return None
    return value or None


def _linux_physical_disks() -> list[dict]:
    disks = []
    excluded_prefixes = ("loop", "ram", "zram", "fd")
    try:
        devices = sorted(LINUX_BLOCK_ROOT.iterdir())
    except OSError:
        return disks

    for device in devices:
        if device.name.startswith(excluded_prefixes):
            continue
        sectors = _read_sysfs(device / "size")
        disk: dict = {
            "device": f"/dev/{device.name}",
            "name": device.name,
            "capacity_bytes": (
                int(sectors) * 512
                if sectors and sectors.isdigit()
                else None
            ),
        }
        for field, candidates in (
            ("model", (device / "device/model", device / "device/name")),
            ("manufacturer", (device / "device/vendor",)),
            ("serial_number", (device / "device/serial", device / "device/wwid")),
            ("firmware", (device / "device/rev",)),
            ("interface", (device / "device/protocol",)),
            ("rotational", (device / "queue/rotational",)),
        ):
            value = next(
                (
                    found
                    for path in candidates
                    if (found := _read_sysfs(path))
                ),
                None,
            )
            if value is not None:
                disk[field] = value
        disk["drive_type"] = (
            "HDD" if disk.get("rotational") == "1"
            else "SSD" if disk.get("rotational") == "0"
            else "unknown"
        )
        disk["smart_health"] = _linux_smart_health(disk["device"])
        disks.append(disk)
    return disks


def _linux_smart_health(device: str) -> dict:
    smartctl = shutil.which("smartctl")
    if not smartctl:
        return {
            "status": "unavailable",
            "message": "smartctl is not installed",
        }

    try:
        response = subprocess.run(
            [smartctl, "--json", "--all", device],
            capture_output=True,
            text=True,
            timeout=12,
            check=False,
        )
    except (OSError, subprocess.SubprocessError) as exc:
        return {"status": "blocked", "message": str(exc)}

    try:
        payload = json.loads(response.stdout) if response.stdout.strip() else {}
    except json.JSONDecodeError:
        return {
            "status": "blocked",
            "message": response.stderr.strip() or "smartctl returned invalid JSON",
        }

    if not isinstance(payload, dict) or not payload:
        return {
            "status": "blocked",
            "message": response.stderr.strip() or "smartctl returned no health data",
        }

    smart_status = payload.get("smart_status")
    passed = (
        smart_status.get("passed")
        if isinstance(smart_status, dict)
        else None
    )
    if passed is False:
        status = "failed"
    elif passed is True:
        status = "available"
    elif response.returncode != 0:
        status = "blocked"
    else:
        status = "unknown"
    nvme_log = payload.get("nvme_smart_health_information_log")
    nvme_log = nvme_log if isinstance(nvme_log, dict) else {}
    temperature = payload.get("temperature")
    temperature = temperature if isinstance(temperature, dict) else {}
    power_on_time = payload.get("power_on_time")
    power_on_time = power_on_time if isinstance(power_on_time, dict) else {}
    ata_error_log = payload.get("ata_smart_error_log")
    ata_error_log = ata_error_log if isinstance(ata_error_log, dict) else {}
    ata_summary = ata_error_log.get("summary")
    ata_summary = ata_summary if isinstance(ata_summary, dict) else {}

    return {
        "status": status,
        "health_passed": passed,
        "temperature_c": (
            temperature.get("current")
            or nvme_log.get("temperature")
        ),
        "power_on_hours": power_on_time.get("hours"),
        "media_errors": nvme_log.get("media_errors"),
        "reported_error_count": ata_summary.get("count"),
        "smartctl_exit_status": response.returncode,
        "message": (
            "Drive reports a SMART health failure"
            if passed is False
            else "SMART health status was not reported"
            if passed is None and status == "unknown"
            else response.stderr.strip() or None
        ),
    }


class StorageProvider(DiscoveryProvider):

    def discover(self) -> DiscoveryResult:
        result = DiscoveryResult()

        seen_devices: set[str] = set()

        disk_details = {}

        if platform.system() == "Linux":
            physical_disks = _linux_physical_disks()
            disk_details = {
                disk["device"]: disk
                for disk in physical_disks
            }
            for disk in physical_disks:
                result.add_device(
                    Device(
                        device_id=f"storage:{disk['device']}",
                        device_type="storage",
                        name=disk.get("model") or disk["device"],
                        properties={
                            **disk,
                            "physical_drive": True,
                            "platform": platform.platform(),
                        },
                    )
                )
        elif platform.system() == "Windows":
            try:
                command = """
                Get-PhysicalDisk |
                Select-Object FriendlyName,SerialNumber,Size,MediaType,FirmwareVersion |
                ConvertTo-Json -Compress
                """
                result_json = subprocess.run(
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
                if result_json.returncode == 0:
                    disks = json.loads(result_json.stdout) if result_json.stdout.strip() else []
                    if isinstance(disks, dict):
                        disks = [disks]
                    for disk in disks:
                        name = disk.get("FriendlyName") or disk.get("DeviceId")
                        if name:
                            disk_details[name] = disk
            except (OSError, subprocess.SubprocessError, json.JSONDecodeError) as exc:
                disk_details["inventory_warning"] = {"message": str(exc)}
        else:
            disk_details["inventory_warning"] = {
                "message": f"Physical drive inventory is not implemented for {platform.system()}"
            }

        for partition in psutil.disk_partitions(
            all=False,
        ):
            device_name = partition.device

            if device_name in seen_devices:
                continue

            seen_devices.add(device_name)

            try:
                usage = psutil.disk_usage(
                    partition.mountpoint,
                )
            except (
                PermissionError,
                OSError,
            ):
                continue

            device = Device(
                device_id=f"storage:{device_name}",
                device_type="storage",
                name=device_name,
                properties={
                    "device": device_name,
                    "mountpoint": partition.mountpoint,
                    "filesystem": partition.fstype,
                    "total_bytes": usage.total,
                    "used_bytes": usage.used,
                    "free_bytes": usage.free,
                    "percent_used": usage.percent,
                    "total_gb": round(
                        usage.total / (1024 ** 3),
                        2,
                    ),
                    "physical_disks": list(
                        disk_details.values()
                    ),
                    "platform": platform.platform(),
                },
            )

            result.add_device(device)

        return result