from app.core.linux_hardware import linux_battery_inventory
from app.discovery.providers import battery_provider, display_provider, motherboard_provider
from app.hal.diagnostic_request import DiagnosticRequest
from app.hal.diagnostics import platform_probes
from app.discovery.providers.storage_provider import (
    _linux_physical_disks,
    _linux_smart_health,
)


def _write(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(value, encoding="utf-8")


def test_linux_battery_inventory_reports_only_sysfs_values(tmp_path):
    battery = tmp_path / "BAT0"
    _write(battery / "type", "Battery\n")
    _write(battery / "manufacturer", "Test Maker\n")
    _write(battery / "model_name", "Test Battery\n")
    _write(battery / "serial_number", "BAT-SERIAL-1\n")
    _write(battery / "status", "Discharging\n")
    _write(battery / "capacity", "80\n")
    _write(battery / "energy_full_design", "50000000\n")
    _write(battery / "energy_full", "40000000\n")
    _write(battery / "cycle_count", "123\n")
    _write(battery / "voltage_now", "12000000\n")

    inventory, warning = linux_battery_inventory(tmp_path)

    assert warning is None
    assert inventory["battery_present"] is True
    assert inventory["batteries"][0]["serial_number"] == "BAT-SERIAL-1"
    assert inventory["batteries"][0]["wear_percent"] == 20
    assert inventory["batteries"][0]["cycle_count"] == 123


def test_linux_battery_inventory_marks_absent_battery_not_applicable(tmp_path):
    inventory, warning = linux_battery_inventory(tmp_path)

    assert warning is None
    assert inventory == {
        "battery_present": False,
        "batteries": [],
        "battery_count": 0,
    }


def test_linux_storage_reads_physical_disk_identity_and_capacity(tmp_path, monkeypatch):
    disk = tmp_path / "nvme0n1"
    _write(disk / "size", "2000\n")
    _write(disk / "device/model", "Test NVMe\n")
    _write(disk / "device/serial", "NVME-SERIAL-1\n")
    _write(disk / "device/rev", "1.2.3\n")
    _write(disk / "queue/rotational", "0\n")
    loop = tmp_path / "loop0"
    _write(loop / "size", "500\n")

    monkeypatch.setattr(
        "app.discovery.providers.storage_provider.LINUX_BLOCK_ROOT",
        tmp_path,
    )
    disks = _linux_physical_disks()

    assert len(disks) == 1
    assert disks[0]["device"] == "/dev/nvme0n1"
    assert disks[0]["capacity_bytes"] == 2000 * 512
    assert disks[0]["model"] == "Test NVMe"
    assert disks[0]["serial_number"] == "NVME-SERIAL-1"
    assert disks[0]["firmware"] == "1.2.3"
    assert disks[0]["drive_type"] == "SSD"
    assert disks[0]["smart_health"]["status"] in {"unavailable", "available"}


def test_smartctl_reads_health_without_marking_unknown_as_pass(monkeypatch):
    class Completed:
        returncode = 2
        stdout = (
            '{"smart_status":{"passed":false},'
            '"temperature":{"current":55},'
            '"power_on_time":{"hours":1234},'
            '"nvme_smart_health_information_log":{"media_errors":4}}'
        )
        stderr = ""

    monkeypatch.setattr(
        "app.discovery.providers.storage_provider.shutil.which",
        lambda name: "/usr/sbin/smartctl",
    )
    monkeypatch.setattr(
        "app.discovery.providers.storage_provider.subprocess.run",
        lambda *args, **kwargs: Completed(),
    )

    result = _linux_smart_health("/dev/nvme0n1")

    assert result["status"] == "failed"
    assert result["health_passed"] is False
    assert result["temperature_c"] == 55
    assert result["power_on_hours"] == 1234
    assert result["media_errors"] == 4


def test_smartctl_reports_unavailable_when_missing(monkeypatch):
    monkeypatch.setattr(
        "app.discovery.providers.storage_provider.shutil.which",
        lambda name: None,
    )

    result = _linux_smart_health("/dev/sda")

    assert result["status"] == "unavailable"
    assert "not installed" in result["message"]


def test_smartctl_does_not_turn_missing_health_data_into_pass(monkeypatch):
    class Completed:
        returncode = 0
        stdout = '{"model_name":"Drive without SMART data"}'
        stderr = ""

    monkeypatch.setattr(
        "app.discovery.providers.storage_provider.shutil.which",
        lambda name: "/usr/sbin/smartctl",
    )
    monkeypatch.setattr(
        "app.discovery.providers.storage_provider.subprocess.run",
        lambda *args, **kwargs: Completed(),
    )

    result = _linux_smart_health("/dev/sda")

    assert result["status"] == "unknown"
    assert result["health_passed"] is None
    assert result["temperature_c"] is None
    assert result["message"] == "SMART health status was not reported"


def test_linux_display_reports_connected_modes(tmp_path, monkeypatch):
    connector = tmp_path / "card0-eDP-1"
    _write(connector / "status", "connected\n")
    _write(connector / "modes", "1920x1080\n1280x720\n")
    monkeypatch.setattr(display_provider, "LINUX_DRM_ROOT", tmp_path)
    monkeypatch.setattr(display_provider.platform, "system", lambda: "Linux")

    device = display_provider.DisplayProvider().discover().devices[0]

    assert device.properties["resolution"] == "1920x1080"
    assert device.properties["supported_modes"] == ["1920x1080", "1280x720"]
    assert device.properties["connectors"][0]["status"] == "connected"


def test_linux_display_reads_active_refresh_from_xrandr(tmp_path, monkeypatch):
    class Completed:
        returncode = 0
        stdout = "eDP-1 connected primary 1920x1080+0+0\n   1920x1080  60.00*+ 59.94\n"

    monkeypatch.setattr(display_provider, "LINUX_DRM_ROOT", tmp_path)
    monkeypatch.setattr(display_provider.platform, "system", lambda: "Linux")
    monkeypatch.setattr(display_provider.shutil, "which", lambda name: "/usr/bin/xrandr")
    monkeypatch.setattr(
        display_provider.subprocess,
        "run",
        lambda *args, **kwargs: Completed(),
    )

    device = display_provider.DisplayProvider().discover().devices[0]

    assert device.properties["resolution"] == "1920x1080"
    assert device.properties["refresh_rate_hz"] == 60.0


def test_linux_motherboard_reads_dmi_identity(tmp_path, monkeypatch):
    _write(tmp_path / "board_vendor", "Test Vendor\n")
    _write(tmp_path / "board_name", "Test Board\n")
    _write(tmp_path / "board_serial", "BOARD-SERIAL-1\n")
    monkeypatch.setattr(motherboard_provider, "LINUX_DMI_ROOT", tmp_path)
    monkeypatch.setattr(motherboard_provider.platform, "system", lambda: "Linux")

    device = motherboard_provider.MotherboardProvider().discover().devices[0]

    assert device.properties["manufacturer"] == "Test Vendor"
    assert device.properties["product"] == "Test Board"
    assert device.properties["serial_number"] == "BOARD-SERIAL-1"


def test_linux_battery_provider_uses_sysfs(tmp_path, monkeypatch):
    battery = tmp_path / "BAT0"
    _write(battery / "type", "Battery\n")
    _write(battery / "capacity", "75\n")
    monkeypatch.setattr(
        "app.discovery.providers.battery_provider.linux_battery_inventory",
        lambda: linux_battery_inventory(tmp_path),
    )
    monkeypatch.setattr(battery_provider.platform, "system", lambda: "Linux")

    device = battery_provider.BatteryProvider().discover().devices[0]

    assert device.properties["battery_present"] is True
    assert device.properties["batteries"][0]["capacity_percent"] == "75"


def test_linux_webcam_probe_reports_v4l2_query(tmp_path, monkeypatch):
    video_root = tmp_path / "dev"
    video_root.mkdir()
    (video_root / "video0").touch()

    class Completed:
        returncode = 0
        stdout = "Driver name : uvcvideo\nCard type : Test Webcam\n"
        stderr = ""

    monkeypatch.setattr(
        "app.hal.diagnostics.platform_probes.LINUX_ROOT",
        tmp_path,
    )
    monkeypatch.setattr(
        "app.hal.diagnostics.platform_probes.platform.system",
        lambda: "Linux",
    )
    monkeypatch.setattr(
        "app.hal.diagnostics.platform_probes.shutil.which",
        lambda name: "/usr/bin/v4l2-ctl",
    )
    monkeypatch.setattr(
        "app.hal.diagnostics.platform_probes.subprocess.run",
        lambda *args, **kwargs: Completed(),
    )

    result = platform_probes.linux_inventory_probe(
        DiagnosticRequest(diagnostic_type="webcam", device_id="test"),
        "webcam",
    )

    assert result.details["webcam_present"] is True
    assert result.details["camera_details"][0]["status"] == "available"
    assert "Test Webcam" in result.details["camera_details"][0]["capabilities"]


def test_linux_storage_provider_emits_individual_physical_drives(monkeypatch):
    disk = {
        "device": "/dev/nvme0n1",
        "model": "Test drive",
        "capacity_bytes": 1024,
        "smart_health": {"status": "unknown"},
    }
    monkeypatch.setattr(
        "app.discovery.providers.storage_provider.platform.system",
        lambda: "Linux",
    )
    monkeypatch.setattr(
        "app.discovery.providers.storage_provider._linux_physical_disks",
        lambda: [disk],
    )
    monkeypatch.setattr(
        "app.discovery.providers.storage_provider.psutil.disk_partitions",
        lambda all=False: [],
    )

    from app.discovery.providers.storage_provider import StorageProvider

    result = StorageProvider().discover()

    assert len(result.devices) == 1
    assert result.devices[0].device_id == "storage:/dev/nvme0n1"
    assert result.devices[0].properties["physical_drive"] is True
    assert result.devices[0].properties["smart_health"]["status"] == "unknown"


def test_linux_usb_probe_uses_udev_descriptors(tmp_path, monkeypatch):
    import sys
    from types import SimpleNamespace

    usb_root = tmp_path / "sys/bus/usb/devices"
    usb_root.mkdir(parents=True)

    class UdevDevice(dict):
        sys_path = "/sys/devices/test-usb"
        device_node = None

    class UdevContext:
        def list_devices(self, **kwargs):
            assert kwargs == {"subsystem": "usb", "DEVTYPE": "usb_device"}
            return [
                UdevDevice({
                    "ID_VENDOR_ID": "1234",
                    "ID_MODEL_ID": "abcd",
                    "ID_VENDOR": "Test Vendor",
                    "ID_MODEL": "Test Device",
                    "ID_SERIAL_SHORT": "USB-SERIAL-1",
                })
            ]

    monkeypatch.setattr(platform_probes, "LINUX_ROOT", tmp_path)
    monkeypatch.setattr(platform_probes.platform, "system", lambda: "Linux")
    monkeypatch.setitem(
        sys.modules,
        "pyudev",
        SimpleNamespace(Context=UdevContext),
    )

    result = platform_probes.linux_inventory_probe(
        DiagnosticRequest(diagnostic_type="usb", device_id="test"),
        "usb",
    )

    assert result.details["device_count"] == 1
    assert result.details["devices"][0]["model"] == "Test Device"
    assert result.details["devices"][0]["serial_number"] == "USB-SERIAL-1"


def test_linux_usb_probe_falls_back_to_sysfs_when_pyudev_is_unavailable(
    tmp_path,
    monkeypatch,
):
    import sys

    usb_root = tmp_path / "sys/bus/usb/devices"
    (usb_root / "1-2").mkdir(parents=True)
    monkeypatch.setattr(platform_probes, "LINUX_ROOT", tmp_path)
    monkeypatch.setattr(platform_probes.platform, "system", lambda: "Linux")
    monkeypatch.setitem(sys.modules, "pyudev", None)

    result = platform_probes.linux_inventory_probe(
        DiagnosticRequest(diagnostic_type="usb", device_id="test"),
        "usb",
    )

    assert result.details["device_count"] == 1
    assert result.details["devices"] == [{"sysfs_device": "1-2"}]
    assert result.details["inventory_warning"]
