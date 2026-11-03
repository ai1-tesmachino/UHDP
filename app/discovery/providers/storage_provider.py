import platform
import json
import math
import shutil
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
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


def _linux_block_root_status() -> tuple[str, str | None]:
    try:
        list(LINUX_BLOCK_ROOT.iterdir())
    except FileNotFoundError:
        return "unsupported", "Linux block-device sysfs inventory is unavailable"
    except PermissionError as exc:
        return "inaccessible", str(exc) or "Linux block-device sysfs access is denied"
    except OSError as exc:
        return "unavailable", str(exc)
    return "available", None


def _linux_physical_disks() -> list[dict[str, Any]]:
    disks = []
    excluded_prefixes = ("loop", "ram", "zram", "fd", "dm-", "md", "nbd")
    try:
        devices = sorted(LINUX_BLOCK_ROOT.iterdir())
    except OSError:
        return disks

    for device in devices:
        if device.name.startswith(excluded_prefixes):
            continue
        sectors = _read_sysfs(device / "size")
        disk: dict[str, Any] = {
            "device": f"/dev/{device.name}",
            "name": device.name,
            "capacity_bytes": (
                int(sectors) * 512
                if sectors and sectors.isdigit()
                else None
            ),
            "source": "sysfs",
            "partitions": [],
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
        try:
            children = sorted(device.iterdir())
        except OSError:
            children = []
        disk["partitions"] = [
            {
                "name": child.name,
                "device": f"/dev/{child.name}",
                "source": "sysfs",
            }
            for child in children
            if _read_sysfs(child / "partition") is not None
        ]
        subsystem_path = device / "device" / "subsystem"
        try:
            disk["transport"] = subsystem_path.resolve().name
        except OSError:
            disk["transport"] = None
        disk["smart_health"] = _linux_smart_health(disk["device"])
        disks.append(disk)
    return disks


def _linux_smart_health(device: str) -> dict[str, Any]:
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
    if not isinstance(passed, bool):
        passed = None
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
    temperature_c = temperature.get("current")
    if temperature_c is None:
        temperature_c = nvme_log.get("temperature")
    if (
        isinstance(temperature_c, bool)
        or not isinstance(temperature_c, (int, float))
        or not math.isfinite(temperature_c)
        or not -50 <= temperature_c <= 150
    ):
        temperature_c = None
    power_on_hours = power_on_time.get("hours")
    if (
        isinstance(power_on_hours, bool)
        or not isinstance(power_on_hours, (int, float))
        or not math.isfinite(power_on_hours)
        or power_on_hours < 0
    ):
        power_on_hours = None
    media_errors = nvme_log.get("media_errors")
    if isinstance(media_errors, bool) or not isinstance(media_errors, int) or media_errors < 0:
        media_errors = None

    return {
        "status": status,
        "source": "smartctl --json --all",
        "health_passed": passed,
        "temperature_c": temperature_c,
        "power_on_hours": power_on_hours,
        "media_errors": media_errors,
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


def _linux_parent_disk(device: str, disk_names: set[str]) -> str | None:
    partition_name = Path(device).name
    class_block = LINUX_BLOCK_ROOT.parent / "class" / "block" / partition_name
    try:
        resolved = class_block.resolve(strict=True)
    except OSError:
        return None
    for parent in (resolved, *resolved.parents):
        if parent.name in disk_names:
            return parent.name
    return None


class StorageProvider(DiscoveryProvider):

    def discover(self) -> DiscoveryResult:
        result = DiscoveryResult()
        collected_at = datetime.now(timezone.utc).isoformat()

        seen_devices: set[str] = set()

        disk_details: dict[str, Any] = {}
        physical_disks: list[dict[str, Any]] = []
        inventory_warning = None
        inventory_status = "unknown"

        if platform.system() == "Linux":
            block_root_status, block_root_error = _linux_block_root_status()
            physical_disks = _linux_physical_disks()
            inventory_status = (
                "detected"
                if physical_disks
                else block_root_status
                if block_root_status != "available"
                else "not_detected"
            )
            disk_details = {
                disk["device"]: disk
                for disk in physical_disks
            }
            disk_by_name = {
                disk["name"]: disk
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
                            "inventory_kind": "physical_drive",
                            "inventory_status": "detected",
                            "collected_at": collected_at,
                            "platform": platform.platform(),
                        },
                    )
                )
            if block_root_error:
                inventory_warning = block_root_error
            elif not physical_disks:
                inventory_warning = "No physical block devices were detected"
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
            inventory_warning = (
                f"Physical drive inventory is not implemented for {platform.system()}"
            )

        for partition in psutil.disk_partitions(
            all=False,
        ):
            device_name = partition.device

            if device_name in seen_devices:
                continue

            seen_devices.add(device_name)

            physical_parent = (
                _linux_parent_disk(
                    device_name,
                    {disk["name"] for disk in physical_disks},
                )
                if platform.system() == "Linux"
                else None
            )
            volume_properties: dict[str, Any] = {
                "device": device_name,
                "mountpoint": partition.mountpoint,
                "filesystem": partition.fstype or None,
                "physical_device": (
                    f"/dev/{physical_parent}" if physical_parent else None
                ),
                "inventory_kind": "logical_volume",
                "inventory_source": "psutil",
                "physical_inventory_status": inventory_status,
                "collected_at": collected_at,
                "platform": platform.platform(),
            }
            if platform.system() == "Windows":
                volume_properties["physical_disks"] = list(disk_details.values())
            try:
                usage = psutil.disk_usage(
                    partition.mountpoint,
                )
            except (PermissionError, OSError) as exc:
                volume_properties.update({
                    "usage_status": "inaccessible",
                    "usage_warning": str(exc),
                })
            else:
                volume_properties.update({
                    "total_bytes": usage.total,
                    "used_bytes": usage.used,
                    "free_bytes": usage.free,
                    "percent_used": usage.percent,
                    "total_gb": round(usage.total / (1024 ** 3), 2),
                    "usage_status": "available",
                })

            if physical_parent and physical_parent in disk_by_name:
                partition_name = Path(device_name).name
                known_partitions = disk_by_name[physical_parent]["partitions"]
                partition_info = next(
                    (
                        item for item in known_partitions
                        if item.get("name") == partition_name
                    ),
                    None,
                )
                if partition_info is None:
                    partition_info = {"name": partition_name, "device": device_name}
                    known_partitions.append(partition_info)
                partition_info.update({
                    "mountpoint": partition.mountpoint,
                    "filesystem": partition.fstype,
                    "source": "sysfs/psutil",
                })
            device = Device(
                device_id=f"storage:{device_name}",
                device_type="storage",
                name=device_name,
                properties=volume_properties,
            )

            result.add_device(device)

        if platform.system() == "Linux" and inventory_warning and not physical_disks:
            result.add_device(
                Device(
                    device_id="storage:inventory",
                    device_type="storage_inventory",
                    name="Physical drive inventory",
                    properties={
                        "inventory_status": inventory_status,
                        "inventory_source": "sysfs",
                        "collected_at": collected_at,
                        "inventory_warning": inventory_warning,
                    },
                )
            )

        return result