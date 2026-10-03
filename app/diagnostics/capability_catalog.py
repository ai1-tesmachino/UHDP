import importlib.util
import platform
import shutil


CAPABILITY_DEFINITIONS = [
    ("device_inventory", "Device discovery and inventory", "Core", ["psutil"]),
    ("cpu", "CPU diagnostics", "Tier 1", ["stress-ng", "prime95", "y-cruncher"]),
    ("ram", "RAM diagnostics", "Tier 1", ["MemTest86+"]),
    ("gpu", "GPU diagnostics", "Tier 2", ["gpu-burn", "glmark2"]),
    ("storage", "Storage diagnostics", "Tier 1", ["fio", "smartctl", "openSeaChest"]),
    ("battery", "Battery diagnostics", "Core", ["psutil", "LibreHardwareMonitor"]),
    ("thermal", "Thermal monitoring", "Tier 1", ["LibreHardwareMonitor"]),
    ("fan", "Fan diagnostics", "Tier 1", ["LibreHardwareMonitor"]),
    ("usb", "USB diagnostics", "Tier 1", ["pyusb"]),
    ("usb_c_thunderbolt", "USB-C and Thunderbolt diagnostics", "Core", ["pyusb"]),
    ("keyboard", "Keyboard diagnostics", "Tier 1", ["pynput", "keyboard"]),
    ("mouse", "Mouse diagnostics", "Tier 1", ["pynput"]),
    ("touchpad", "Touchpad diagnostics", "Tier 1", ["hidapi", "pywin32"]),
    ("touchscreen", "Touchscreen diagnostics", "Core", ["browser_pointer_events"]),
    ("display", "Display diagnostics", "Core", ["browser_test_patterns"]),
    ("webcam", "Webcam diagnostics", "Tier 1", ["cv2"]),
    ("audio", "Audio diagnostics", "Tier 1", ["sounddevice", "pyaudio"]),
    ("network", "Network diagnostics", "Tier 1", ["iperf3"]),
    ("bluetooth", "Bluetooth diagnostics", "Tier 1", ["bleak", "bluetooth"]),
    ("power_adapter", "Power adapter diagnostics", "Tier 1", ["LibreHardwareMonitor"]),
    ("sensor_analytics", "Sensor analytics", "Tier 1", ["LibreHardwareMonitor"]),
    ("burn_in", "Burn-in testing", "Tier 2", ["stress-ng", "gpu-burn", "fio"]),
]

MODULE_NAMES = {
    "psutil": "psutil",
    "pyusb": "usb",
    "pynput": "pynput",
    "keyboard": "keyboard",
    "hidapi": "hid",
    "pywin32": "win32api",
    "cv2": "cv2",
    "sounddevice": "sounddevice",
    "pyaudio": "pyaudio",
    "bleak": "bleak",
    "bluetooth": "bluetooth",
}

EXECUTABLE_NAMES = {
    "stress-ng": "stress-ng",
    "prime95": "prime95",
    "y-cruncher": "y-cruncher",
    "MemTest86+": "memtest86",
    "gpu-burn": "gpu_burn",
    "glmark2": "glmark2",
    "fio": "fio",
    "smartctl": "smartctl",
    "openSeaChest": "openSeaChest",
    "iperf3": "iperf3",
    "LibreHardwareMonitor": "LibreHardwareMonitor",
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
