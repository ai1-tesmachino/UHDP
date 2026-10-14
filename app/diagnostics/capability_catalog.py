import importlib.util
import platform
import shutil


CAPABILITY_DEFINITIONS = [
    ("device_inventory", "Device discovery and inventory", "Core", ["psutil", "pyudev", "pciutils"]),
    ("cpu", "CPU diagnostics", "Tier 1", ["psutil", "stress-ng"]),
    ("ram", "RAM diagnostics", "Tier 1", ["psutil", "lshw", "memtester", "MemTest86+"]),
    ("gpu", "GPU diagnostics", "Tier 2", ["glmark2", "vulkan-tools", "intel-gpu-tools", "nvtop"]),
    ("storage", "Storage diagnostics", "Tier 1", ["smartmontools", "nvme-cli", "fio"]),
    ("battery", "Battery diagnostics", "Core", ["psutil", "upower", "acpi"]),
    ("thermal", "Thermal monitoring", "Tier 1", ["psutil", "lm-sensors"]),
    ("fan", "Fan diagnostics", "Tier 1", ["lm-sensors"]),
    ("usb", "USB diagnostics", "Tier 1", ["pyusb", "usbutils", "pyudev"]),
    ("usb_c_thunderbolt", "USB-C and Thunderbolt diagnostics", "Core", ["pyusb", "usbutils", "pyudev"]),
    ("keyboard", "Keyboard diagnostics", "Tier 1", ["evdev", "evtest"]),
    ("mouse", "Mouse diagnostics", "Tier 1", ["evdev", "libinput-tools"]),
    ("touchpad", "Touchpad diagnostics", "Tier 1", ["evdev", "libinput-tools"]),
    ("touchscreen", "Touchscreen diagnostics", "Core", ["browser_pointer_events"]),
    ("display", "Display diagnostics", "Core", ["browser_test_patterns", "xrandr", "edid-decode"]),
    ("webcam", "Webcam diagnostics", "Tier 1", ["v4l-utils"]),
    ("audio", "Audio diagnostics", "Tier 1", ["alsa-utils", "pipewire", "wireplumber"]),
    ("network", "Network diagnostics", "Tier 1", ["iperf3", "iw", "rfkill", "iproute2", "ethtool"]),
    ("bluetooth", "Bluetooth diagnostics", "Tier 1", ["bluez", "rfkill", "pyudev"]),
    ("power_adapter", "Power adapter diagnostics", "Tier 1", ["upower", "acpi"]),
    ("sensor_analytics", "Sensor analytics", "Tier 1", ["lm-sensors", "psutil"]),
    ("firmware_tpm", "Firmware and TPM inventory", "Tier 1", ["dmidecode", "fwupd", "tpm2-tools"]),
    ("burn_in", "Burn-in testing", "Tier 2", ["stress-ng", "intel-gpu-tools", "fio"]),
]

MODULE_NAMES = {
    "psutil": "psutil",
    "pyusb": "usb",
    "pyudev": "pyudev",
    "evdev": "evdev",
}

EXECUTABLE_NAMES = {
    "stress-ng": "stress-ng",
    "MemTest86+": "memtest86",
    "glmark2": "glmark2",
    "fio": "fio",
    "smartmontools": "smartctl",
    "nvme-cli": "nvme",
    "memtester": "memtester",
    "lm-sensors": "sensors",
    "upower": "upower",
    "acpi": "acpi",
    "pciutils": "lspci",
    "util-linux": "lsblk",
    "sysstat": "iostat",
    "usbutils": "lsusb",
    "evtest": "evtest",
    "libinput-tools": "libinput",
    "v4l-utils": "v4l2-ctl",
    "alsa-utils": "arecord",
    "pipewire": "pw-cli",
    "wireplumber": "wpctl",
    "iperf3": "iperf3",
    "iw": "iw",
    "rfkill": "rfkill",
    "iproute2": "ip",
    "ethtool": "ethtool",
    "xrandr": "xrandr",
    "edid-decode": "edid-decode",
    "vulkan-tools": "vulkaninfo",
    "mesa-utils": "glxinfo",
    "intel-gpu-tools": "intel_gpu_top",
    "nvtop": "nvtop",
    "dmidecode": "dmidecode",
    "fwupd": "fwupdmgr",
    "tpm2-tools": "tpm2_getcap",
    "bluez": "bluetoothctl",
}

UI_ENGINES = {"browser_pointer_events", "browser_test_patterns"}


def _engine_state(name: str) -> dict:
    if name in UI_ENGINES:
        return {
            "name": name,
            "kind": "built_in",
            "available": True,
            "status": "available",
        }

    if name == "MemTest86+":
        return {
            "name": name,
            "kind": "bootable_external",
            "available": False,
            "status": "operator_run_required",
        }

    executable = EXECUTABLE_NAMES.get(name)
    if executable:
        path = shutil.which(executable)
        return {
            "name": name,
            "kind": "external",
            "available": path is not None,
            "status": "available" if path else "not_installed",
            "path": path,
        }

    module_name = MODULE_NAMES.get(name)
    if module_name:
        available = importlib.util.find_spec(module_name) is not None
        return {
            "name": name,
            "kind": "python_package",
            "available": available,
            "status": "available" if available else "not_installed",
        }

    return {
        "name": name,
        "kind": "optional_external",
        "available": False,
        "status": "not_detected",
    }


def get_capabilities() -> dict:
    components = []
    for component_id, name, tier, engines in CAPABILITY_DEFINITIONS:
        engine_states = [_engine_state(engine) for engine in engines]
        components.append({
            "id": component_id,
            "name": name,
            "tier": tier,
            "engines": engine_states,
            "available_engines": sum(
                engine["available"]
                for engine in engine_states
            ),
            "engine_count": len(engine_states),
        })
    return {
        "platform": platform.system(),
        "components": components,
        "oem_extension_points": ["Dell", "Lenovo", "HP", "ASUS"],
    }
