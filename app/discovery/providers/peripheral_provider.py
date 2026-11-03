import re
from datetime import datetime, timezone
from pathlib import Path

from app.discovery.discovery_provider import DiscoveryProvider
from app.discovery.discovery_result import DiscoveryResult
from app.discovery.models.device import Device


LINUX_USB_ROOT = Path("/sys/bus/usb/devices")
LINUX_USB_HOST_ROOT = Path("/sys/class/usb_host")
LINUX_INPUT_ROOT = Path("/sys/class/input")
LINUX_VIDEO_ROOT = Path("/sys/class/video4linux")
LINUX_AUDIO_ROOT = Path("/proc/asound")
LINUX_HWMON_ROOT = Path("/sys/class/hwmon")


def _read(path: Path) -> str | None:
    try:
        value = path.read_text(encoding="utf-8", errors="replace").strip()
    except OSError:
        return None
    return value or None


def _usb_devices() -> list[dict[str, str | None]]:
    devices = []
    try:
        entries = sorted(LINUX_USB_ROOT.iterdir())
    except OSError:
        return devices
    for entry in entries:
        if ":" in entry.name:
            continue
        vendor_id = _read(entry / "idVendor")
        product_id = _read(entry / "idProduct")
        if not vendor_id and not product_id:
            continue
        devices.append({
            "sysfs_device": entry.name,
            "vendor_id": vendor_id,
            "product_id": product_id,
            "manufacturer": _read(entry / "manufacturer"),
            "product": _read(entry / "product"),
            "serial_number": _read(entry / "serial"),
            "source": "sysfs",
        })
    return devices


def _input_devices() -> dict[str, list[dict[str, str | None]]]:
    categories: dict[str, list[dict[str, str | None]]] = {
        "keyboards": [],
        "pointing_devices": [],
        "touchscreens": [],
    }
    try:
        entries = sorted(LINUX_INPUT_ROOT.glob("event*"))
    except OSError:
        return categories
    for entry in entries:
        name = _read(entry / "device" / "name")
        if not name:
            continue
        record = {
            "name": name,
            "device_node": f"/dev/input/{entry.name}",
            "phys": _read(entry / "device" / "phys"),
            "source": "sysfs input",
        }
        lowered = name.lower()
        if re.search(r"keyboard|keypad", lowered):
            categories["keyboards"].append(record)
        if re.search(r"mouse|touchpad|trackpad", lowered):
            categories["pointing_devices"].append(record)
        if re.search(r"touchscreen", lowered):
            categories["touchscreens"].append(record)
    return categories


def _video_devices() -> list[dict[str, str | None]]:
    devices = []
    try:
        entries = sorted(LINUX_VIDEO_ROOT.glob("video*"))
    except OSError:
        return devices
    for entry in entries:
        devices.append({
            "name": _read(entry / "name"),
            "device_node": f"/dev/{entry.name}",
            "source": "sysfs video4linux",
        })
    return devices


def _audio_devices() -> list[str]:
    cards = LINUX_AUDIO_ROOT / "cards"
    try:
        lines = cards.read_text(
            encoding="utf-8",
            errors="replace",
        ).splitlines()
    except OSError:
        return []
    return [
        line.strip()
        for line in lines
        if line.strip() and not line.lstrip().startswith("--")
    ]


def _audio_endpoints() -> dict[str, list[str]]:
    pcm_path = LINUX_AUDIO_ROOT / "pcm"
    try:
        lines = pcm_path.read_text(
            encoding="utf-8",
            errors="replace",
        ).splitlines()
    except OSError:
        return {"playback": [], "capture": []}
    return {
        direction: [
            line.strip()
            for line in lines
            if re.search(rf"\b{direction}\s+[1-9]\d*\b", line)
        ]
        for direction in ("playback", "capture")
    }


def _audio_status(
    devices: list[str],
    endpoints: dict[str, list[str]],
) -> str:
    if devices or any(endpoints.values()):
        return "detected"
    available_file = False
    for path in (LINUX_AUDIO_ROOT / "cards", LINUX_AUDIO_ROOT / "pcm"):
        try:
            path.read_text(encoding="utf-8", errors="replace")
        except FileNotFoundError:
            continue
        except PermissionError:
            return "inaccessible"
        except OSError:
            return "unavailable"
        available_file = True
    return "not_detected" if available_file else "unsupported"


def _availability(root: Path, detected: bool) -> str:
    if detected:
        return "detected"
    if not root.exists():
        return "unsupported"
    try:
        next(root.iterdir(), None)
    except PermissionError:
        return "inaccessible"
    except OSError:
        return "unavailable"
    return "not_detected"


def _sensor_inventory() -> tuple[list[dict[str, str | int | float]], list[dict[str, str | int | float]]]:
    temperatures = []
    fans = []
    try:
        devices = sorted(LINUX_HWMON_ROOT.glob("hwmon*"))
    except OSError:
        return temperatures, fans
    for device in devices:
        for path in sorted(device.glob("temp*_input")):
            raw = _read(path)
            try:
                millidegrees = int(raw) if raw is not None else None
            except ValueError:
                continue
            if millidegrees is None or not -100000 <= millidegrees <= 250000:
                continue
            label = _read(path.with_name(path.name.removesuffix("_input") + "_label"))
            temperatures.append({
                "name": label or path.parent.name,
                "temperature_c": millidegrees / 1000,
                "source": str(path),
            })
        for path in sorted(device.glob("fan*_input")):
            raw = _read(path)
            try:
                rpm = int(raw) if raw is not None else None
            except ValueError:
                continue
            if rpm is None or rpm < 0:
                continue
            label = _read(path.with_name(path.name.removesuffix("_input") + "_label"))
            fans.append({
                "name": label or path.parent.name,
                "rpm": rpm,
                "source": str(path),
            })
    return temperatures, fans


class PeripheralProvider(DiscoveryProvider):
    def discover(self) -> DiscoveryResult:
        usb_devices = _usb_devices()
        input_devices = _input_devices()
        cameras = _video_devices()
        audio_devices = _audio_devices()
        audio_endpoints = _audio_endpoints()
        temperatures, fans = _sensor_inventory()
        try:
            usb_controllers = sorted(
                path.name for path in LINUX_USB_HOST_ROOT.iterdir()
            )
        except OSError:
            usb_controllers = []

        usb_status = _availability(
            LINUX_USB_ROOT,
            bool(usb_devices or usb_controllers),
        )
        input_status = _availability(
            LINUX_INPUT_ROOT,
            any(input_devices.values()),
        )
        video_status = _availability(LINUX_VIDEO_ROOT, bool(cameras))
        audio_status = _audio_status(audio_devices, audio_endpoints)
        sensor_status = _availability(
            LINUX_HWMON_ROOT,
            bool(fans or temperatures),
        )
        inventory_status = "detected" if (
            usb_devices or usb_controllers or cameras or audio_devices
            or any(input_devices.values()) or fans or temperatures
            or any(audio_endpoints.values())
        ) else "partial" if "unsupported" in {
            usb_status, input_status, video_status, audio_status, sensor_status,
        } else "not_detected"

        result = DiscoveryResult()
        result.add_device(
            Device(
                device_id="peripherals",
                device_type="peripherals",
                name="Peripheral inventory",
                properties={
                    "usb_controllers": usb_controllers,
                    "usb_devices": usb_devices,
                    "usb_inventory_status": usb_status,
                    "input_devices": input_devices,
                    "input_inventory_status": input_status,
                    "cameras": cameras,
                    "camera_inventory_status": video_status,
                    "audio_devices": audio_devices,
                    "audio_endpoints": audio_endpoints,
                    "audio_inventory_status": audio_status,
                    "temperature_sensors": temperatures,
                    "fans": fans,
                    "sensor_inventory_status": sensor_status,
                    "inventory_status": inventory_status,
                    "collected_at": datetime.now(timezone.utc).isoformat(),
                    "inventory_source": [
                        "/sys/bus/usb/devices",
                        "/sys/class/input",
                        "/sys/class/video4linux",
                        "/proc/asound",
                        "/sys/class/hwmon",
                    ],
                    "functional_test_performed": False,
                },
            )
        )
        return result
