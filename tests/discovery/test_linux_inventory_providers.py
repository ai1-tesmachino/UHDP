from pathlib import Path

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
    assert inventory["battery_present"] is False
    assert inventory["batteries"] == []
    assert inventory["battery_count"] == 0
    assert inventory["inventory_status"] == "not_detected"


def test_linux_storage_reads_physical_disk_identity_and_capacity(tmp_path, monkeypatch):
    disk = tmp_path / "nvme0n1"
    _write(disk / "size", "2000\n")
    _write(disk / "device/model", "Test NVMe\n")
    _write(disk / "device/serial", "NVME-SERIAL-1\n")
    _write(disk / "device/rev", "1.2.3\n")
    _write(disk / "queue/rotational", "0\n")
    loop = tmp_path / "loop0"
    _write(loop / "size", "500\n")
    device_mapper = tmp_path / "dm-0"
    _write(device_mapper / "size", "9000\n")
    raid_array = tmp_path / "md127"
    _write(raid_array / "size", "12000\n")

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


def test_smartctl_timeout_and_invalid_measurements_are_not_health_failures(monkeypatch):
    import subprocess

    from app.discovery.providers import storage_provider

    monkeypatch.setattr(
        storage_provider.shutil,
        "which",
        lambda name: "/usr/sbin/smartctl",
    )

    def timeout(*args, **kwargs):
        raise subprocess.TimeoutExpired(args[0], kwargs["timeout"])

    monkeypatch.setattr(storage_provider.subprocess, "run", timeout)
    timed_out = storage_provider._linux_smart_health("/dev/nvme0n1")
    assert timed_out["status"] == "blocked"
    assert "timed out" in timed_out["message"]

    class Completed:
        returncode = 0
        stdout = (
            '{"smart_status":{"passed":"yes"},'
            '"temperature":{"current":"hot"},'
            '"nvme_smart_health_information_log":{"media_errors":-1}}'
        )
        stderr = ""

    monkeypatch.setattr(
        storage_provider.subprocess,
        "run",
        lambda *args, **kwargs: Completed(),
    )
    malformed = storage_provider._linux_smart_health("/dev/nvme0n1")

    assert malformed["status"] == "unknown"
    assert malformed["health_passed"] is None
    assert malformed["temperature_c"] is None
    assert malformed["media_errors"] is None


def test_linux_system_reports_dmi_secure_boot_and_tpm_sources(
    tmp_path,
    monkeypatch,
):
    from app.discovery.providers import system_provider

    dmi = tmp_path / "dmi"
    _write(dmi / "sys_vendor", "Fixture Maker\n")
    _write(dmi / "product_name", "Fixture Model\n")
    _write(dmi / "product_serial", "SERIAL-1\n")
    _write(dmi / "product_uuid", "UUID-1\n")
    _write(dmi / "bios_version", "1.2\n")
    efivars = tmp_path / "efivars"
    secure_boot = efivars / "SecureBoot-00000000-0000-0000-0000-000000000000"
    secure_boot.parent.mkdir(parents=True, exist_ok=True)
    secure_boot.write_bytes(bytes([0, 0, 0, 0, 1]))
    tpm = tmp_path / "tpm"
    (tpm / "tpm0").mkdir(parents=True)
    monkeypatch.setattr(system_provider, "LINUX_DMI_ROOT", dmi)
    monkeypatch.setattr(system_provider, "LINUX_EFIVARS_ROOT", efivars)
    monkeypatch.setattr(system_provider, "LINUX_TPM_ROOT", tpm)
    monkeypatch.setattr(system_provider.platform, "system", lambda: "Linux")

    properties = system_provider.SystemProvider().discover().devices[0].properties

    assert properties["manufacturer"] == "Fixture Maker"
    assert properties["model"] == "Fixture Model"
    assert properties["serial_number"] == "SERIAL-1"
    assert properties["uuid"] == "UUID-1"
    assert properties["secure_boot"]["enabled"] is True
    assert properties["tpm_inventory"]["devices"] == ["tpm0"]
    assert properties["collected_at"]


def test_secure_boot_unknown_when_efi_value_is_malformed(tmp_path, monkeypatch):
    from app.discovery.providers import system_provider

    secure_boot = tmp_path / "SecureBoot-test"
    secure_boot.write_bytes(b"\x00")
    monkeypatch.setattr(system_provider, "LINUX_EFIVARS_ROOT", tmp_path)

    result = system_provider._linux_secure_boot()

    assert result["status"] == "unknown"
    assert "invalid" in result["message"]


def test_linux_gpu_reports_pci_identity_driver_vram_and_exposed_temperature(
    tmp_path,
    monkeypatch,
):
    from app.discovery.providers import gpu_provider

    device = tmp_path / "card0/device"
    _write(device / "vendor", "0x1234\n")
    _write(device / "device", "0xabcd\n")
    _write(device / "product_name", "Fixture GPU\n")
    _write(device / "mem_info_vram_total", str(4 * 1024**3))
    _write(device / "hwmon/hwmon0/name", "fixture-gpu\n")
    _write(device / "hwmon/hwmon0/temp1_input", "61250\n")
    _write(device / "hwmon/hwmon0/temp1_label", "GPU Core\n")
    monkeypatch.setattr(gpu_provider, "LINUX_DRM_ROOT", tmp_path)
    monkeypatch.setattr(gpu_provider.platform, "system", lambda: "Linux")

    result = gpu_provider.GPUProvider().discover().devices[0]

    assert result.name == "Fixture GPU"
    assert result.properties["vendor_id"] == "0x1234"
    assert result.properties["device_id"] == "0xabcd"
    assert result.properties["vram_bytes"] == 4 * 1024**3
    assert result.properties["temperature_sensors"][0]["temperature_c"] == 61.25
    assert result.properties["temperature_status"] == "detected"


def test_linux_display_reports_connected_modes(tmp_path, monkeypatch):
    connector = tmp_path / "card0-eDP-1"
    _write(connector / "status", "connected\n")
    _write(connector / "modes", "1920x1080\n1280x720\n")
    monkeypatch.setattr(display_provider, "LINUX_DRM_ROOT", tmp_path)
    monkeypatch.setattr(display_provider.platform, "system", lambda: "Linux")

    device = display_provider.DisplayProvider().discover().devices[0]

    assert device.properties["resolution"] == "Unknown"
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
    assert device.properties["batteries"][0]["capacity_percent"] == 75


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
        "name": "nvme0n1",
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


def test_linux_storage_keeps_physical_disks_and_mounted_volumes_distinct(
    tmp_path,
    monkeypatch,
):
    from types import SimpleNamespace
    from app.discovery.providers import storage_provider

    block_root = tmp_path / "sys/block"
    class_block = tmp_path / "sys/class/block"
    for name in ("sda", "nvme0n1"):
        (block_root / name).mkdir(parents=True)
    class_block.mkdir(parents=True)
    for partition, parent in (("sda1", "sda"), ("nvme0n1p1", "nvme0n1")):
        target = block_root / parent / partition
        target.mkdir()
        (class_block / partition).symlink_to(target, target_is_directory=True)

    monkeypatch.setattr(storage_provider.platform, "system", lambda: "Linux")
    monkeypatch.setattr(storage_provider, "LINUX_BLOCK_ROOT", block_root)
    monkeypatch.setattr(
        storage_provider,
        "_linux_physical_disks",
        lambda: [
            {"device": "/dev/sda", "name": "sda", "model": "Drive A", "partitions": []},
            {"device": "/dev/nvme0n1", "name": "nvme0n1", "partitions": []},
        ],
    )
    monkeypatch.setattr(
        storage_provider.psutil,
        "disk_partitions",
        lambda all=False: [
            SimpleNamespace(device="/dev/sda1", mountpoint="/mnt/a", fstype="ext4"),
            SimpleNamespace(device="/dev/nvme0n1p1", mountpoint="/mnt/b", fstype="xfs"),
        ],
    )
    monkeypatch.setattr(
        storage_provider.psutil,
        "disk_usage",
        lambda mountpoint: SimpleNamespace(
            total=1000, used=400, free=600, percent=40
        ),
    )

    devices = storage_provider.StorageProvider().discover().devices
    physical = [device for device in devices if device.properties.get("physical_drive")]
    volumes = [
        device
        for device in devices
        if device.properties.get("inventory_kind") == "logical_volume"
    ]

    assert len(physical) == 2
    assert len(volumes) == 2
    assert {volume.properties["physical_device"] for volume in volumes} == {
        "/dev/sda",
        "/dev/nvme0n1",
    }
    assert all("physical_disks" not in volume.properties for volume in volumes)
    assert {
        partition["device"]
        for drive in physical
        for partition in drive.properties["partitions"]
    } == {"/dev/sda1", "/dev/nvme0n1p1"}


def test_linux_storage_does_not_invent_missing_drive_identifiers(
    tmp_path,
    monkeypatch,
):
    from app.discovery.providers import storage_provider

    block_root = tmp_path / "sys/block"
    block_root.mkdir(parents=True)
    monkeypatch.setattr(storage_provider.platform, "system", lambda: "Linux")
    monkeypatch.setattr(storage_provider, "LINUX_BLOCK_ROOT", block_root)
    monkeypatch.setattr(
        storage_provider,
        "_linux_physical_disks",
        lambda: [{"device": "/dev/sda", "name": "sda", "partitions": []}],
    )
    monkeypatch.setattr(
        storage_provider.psutil,
        "disk_partitions",
        lambda all=False: [],
    )

    devices = storage_provider.StorageProvider().discover().devices

    assert len(devices) == 1
    assert devices[0].properties["device"] == "/dev/sda"
    assert "serial_number" not in devices[0].properties
    assert "model" not in devices[0].properties


def test_linux_storage_reports_unavailable_usage_without_calling_it_a_failure(
    monkeypatch,
):
    from types import SimpleNamespace
    from app.discovery.providers import storage_provider

    monkeypatch.setattr(storage_provider.platform, "system", lambda: "Linux")
    monkeypatch.setattr(storage_provider, "_linux_physical_disks", lambda: [])
    monkeypatch.setattr(
        storage_provider,
        "LINUX_BLOCK_ROOT",
        Path("/missing/sys/block"),
    )
    monkeypatch.setattr(
        storage_provider.psutil,
        "disk_partitions",
        lambda all=False: [
            SimpleNamespace(device="/dev/mapper/volume", mountpoint="/mnt/data", fstype="ext4")
        ],
    )

    def denied(_):
        raise PermissionError("permission denied")

    monkeypatch.setattr(storage_provider.psutil, "disk_usage", denied)
    devices = storage_provider.StorageProvider().discover().devices
    volume = next(device for device in devices if device.properties.get("inventory_kind"))

    assert volume.properties["usage_status"] == "inaccessible"
    assert volume.properties["usage_warning"] == "permission denied"
    assert volume.properties["physical_device"] is None


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


def test_linux_cpu_reads_model_flags_and_only_exposed_temperatures(
    tmp_path,
    monkeypatch,
):
    from app.discovery.providers import cpu_provider

    cpuinfo = tmp_path / "cpuinfo"
    _write(
        cpuinfo,
        "processor : 0\nmodel name : Fixture CPU\nvendor_id : FixtureVendor\nflags : sse avx\n",
    )
    hwmon = tmp_path / "hwmon/hwmon0"
    _write(hwmon / "name", "coretemp\n")
    _write(hwmon / "temp1_input", "44500\n")
    _write(hwmon / "temp1_label", "Package id 0\n")
    _write(hwmon / "temp2_input", "not-a-temperature\n")
    monkeypatch.setattr(cpu_provider, "LINUX_CPUINFO", cpuinfo)
    monkeypatch.setattr(cpu_provider, "LINUX_HWMON_ROOT", tmp_path / "hwmon")
    monkeypatch.setattr(cpu_provider.platform, "system", lambda: "Linux")

    device = cpu_provider.CPUProvider().discover().devices[0]

    assert device.name == "Fixture CPU"
    assert device.properties["vendor"] == "FixtureVendor"
    assert device.properties["instruction_sets"] == ["sse", "avx"]
    assert device.properties["temperature_sensors"] == [{
        "name": "Package id 0",
        "temperature_c": 44.5,
        "source": str(hwmon / "temp1_input"),
    }]
    assert device.properties["temperature_available"] is True


def test_linux_cpu_reports_missing_temperature_data_as_unavailable(
    tmp_path,
    monkeypatch,
):
    from app.discovery.providers import cpu_provider

    monkeypatch.setattr(
        cpu_provider,
        "LINUX_CPUINFO",
        tmp_path / "missing-cpuinfo",
    )
    monkeypatch.setattr(
        cpu_provider,
        "LINUX_HWMON_ROOT",
        tmp_path / "missing-hwmon",
    )
    monkeypatch.setattr(cpu_provider.platform, "system", lambda: "Linux")
    device = cpu_provider.CPUProvider().discover().devices[0]

    assert device.properties["temperature_sensors"] == []
    assert device.properties["temperature_available"] is False


def test_linux_memory_normalizes_multiple_lshw_modules(monkeypatch):
    from types import SimpleNamespace
    from app.discovery.providers import memory_provider

    class Completed:
        returncode = 0
        stderr = ""
        stdout = (
            '{"id":"memory","children":['
            '{"id":"bank:0","description":"DIMM","vendor":"Maker",'
            '"product":"Part-A","serial":"RAM-1","size":8589934592,"clock":3200000000},'
            '{"id":"bank:1","description":"DIMM","size":"16GiB","clock":2666000000}'
            ']}'
        )

    monkeypatch.setattr(memory_provider.platform, "system", lambda: "Linux")
    monkeypatch.setattr(memory_provider.shutil, "which", lambda name: "/usr/bin/lshw")
    monkeypatch.setattr(
        memory_provider.subprocess,
        "run",
        lambda *args, **kwargs: Completed(),
    )
    monkeypatch.setattr(
        memory_provider.psutil,
        "virtual_memory",
        lambda: SimpleNamespace(
            total=24 * 1024**3,
            available=8 * 1024**3,
            used=16 * 1024**3,
            free=7 * 1024**3,
            percent=66.7,
        ),
    )

    properties = memory_provider.MemoryProvider().discover().devices[0].properties

    assert properties["total_bytes"] == 24 * 1024**3
    assert properties["physical_module_count"] == 2
    assert properties["memory_modules"][0]["capacity_bytes"] == 8 * 1024**3
    assert properties["memory_modules"][0]["speed_mts"] == 3200
    assert properties["memory_modules"][0]["serial_number"] == "RAM-1"
    assert properties["memory_modules"][1]["capacity_bytes"] == 16 * 1024**3
    assert properties["module_inventory_source"] == "lshw"


def test_linux_memory_marks_modules_unavailable_when_lshw_is_missing(monkeypatch):
    from app.discovery.providers import memory_provider

    monkeypatch.setattr(memory_provider.platform, "system", lambda: "Linux")
    monkeypatch.setattr(memory_provider.shutil, "which", lambda name: None)

    properties = memory_provider.MemoryProvider().discover().devices[0].properties

    assert properties["memory_modules"] == []
    assert properties["physical_module_count"] is None
    assert properties["module_inventory_status"] == "unavailable"
    assert "lshw" in properties["module_inventory_warning"]


def test_linux_memory_reports_lshw_timeout_as_unavailable(monkeypatch):
    import subprocess
    from app.discovery.providers import memory_provider

    monkeypatch.setattr(memory_provider.platform, "system", lambda: "Linux")
    monkeypatch.setattr(memory_provider.shutil, "which", lambda name: "/usr/bin/lshw")

    def timeout(*args, **kwargs):
        raise subprocess.TimeoutExpired(args[0], kwargs["timeout"])

    monkeypatch.setattr(memory_provider.subprocess, "run", timeout)
    properties = memory_provider.MemoryProvider().discover().devices[0].properties

    assert properties["module_inventory_status"] == "unavailable"
    assert "timed out" in properties["module_inventory_warning"]


def test_linux_network_reports_adapters_without_claiming_connectivity(
    tmp_path,
    monkeypatch,
):
    from types import SimpleNamespace
    from app.discovery.providers import network_provider

    interface = tmp_path / "net/wlan0"
    _write(interface / "type", "1\n")
    _write(interface / "address", "02:00:00:00:00:01\n")
    _write(interface / "operstate", "up\n")
    (interface / "wireless").mkdir()
    monkeypatch.setattr(network_provider, "LINUX_NET_ROOT", tmp_path / "net")
    monkeypatch.setattr(network_provider, "LINUX_BLUETOOTH_ROOT", tmp_path / "missing-bluetooth")
    monkeypatch.setattr(network_provider.platform, "system", lambda: "Linux")
    monkeypatch.setattr(
        network_provider.psutil,
        "net_if_addrs",
        lambda: {"wlan0": []},
    )
    monkeypatch.setattr(
        network_provider.psutil,
        "net_if_stats",
        lambda: {"wlan0": SimpleNamespace(isup=True, speed=300)},
    )

    properties = network_provider.NetworkProvider().discover().devices[0].properties

    assert properties["adapter_count"] == 1
    assert properties["adapters"][0]["name"] == "wlan0"
    assert properties["adapters"][0]["mac_address"] == "02:00:00:00:00:01"
    assert properties["adapters"][0]["type"] == "wifi"
    assert properties["adapters"][0]["speed_mbps"] == 300
    assert properties["connectivity_verified"] is False


def test_linux_network_missing_sysfs_is_unavailable_not_disconnected(
    tmp_path,
    monkeypatch,
):
    from app.discovery.providers import network_provider

    monkeypatch.setattr(
        network_provider,
        "LINUX_NET_ROOT",
        tmp_path / "missing-net",
    )
    monkeypatch.setattr(network_provider.platform, "system", lambda: "Linux")
    properties = network_provider.NetworkProvider().discover().devices[0].properties

    assert properties["adapter_count"] == 0
    assert properties["inventory_status"] == "unavailable"
    assert properties["inventory_warning"]


def test_linux_peripheral_inventory_reports_partial_ids_and_disconnected_devices(
    tmp_path,
    monkeypatch,
):
    from app.discovery.providers import peripheral_provider

    usb_root = tmp_path / "usb"
    _write(usb_root / "1-1/idVendor", "1234\n")
    _write(usb_root / "1-1/idProduct", "abcd\n")
    _write(usb_root / "1-1/product", "Partial device\n")
    video_root = tmp_path / "video4linux"
    (video_root / "video0").mkdir(parents=True)
    _write(video_root / "video0/name", "USB Camera\n")
    audio_root = tmp_path / "asound"
    _write(audio_root / "cards", "-- no soundcards --\n")
    monkeypatch.setattr(peripheral_provider, "LINUX_USB_ROOT", usb_root)
    monkeypatch.setattr(
        peripheral_provider,
        "LINUX_USB_HOST_ROOT",
        tmp_path / "missing-usb-host",
    )
    monkeypatch.setattr(
        peripheral_provider,
        "LINUX_INPUT_ROOT",
        tmp_path / "missing-input",
    )
    monkeypatch.setattr(peripheral_provider, "LINUX_VIDEO_ROOT", video_root)
    monkeypatch.setattr(peripheral_provider, "LINUX_AUDIO_ROOT", audio_root)
    monkeypatch.setattr(
        peripheral_provider,
        "LINUX_HWMON_ROOT",
        tmp_path / "missing-hwmon",
    )

    properties = peripheral_provider.PeripheralProvider().discover().devices[0].properties

    assert properties["usb_devices"] == [{
        "sysfs_device": "1-1",
        "vendor_id": "1234",
        "product_id": "abcd",
        "manufacturer": None,
        "product": "Partial device",
        "serial_number": None,
        "source": "sysfs",
    }]
    assert properties["cameras"][0]["device_node"] == "/dev/video0"
    assert properties["audio_devices"] == []
    assert properties["functional_test_performed"] is False


def test_linux_battery_distinguishes_inaccessible_from_absent(tmp_path, monkeypatch):
    missing_root = tmp_path / "absent"
    absent, absent_warning = linux_battery_inventory(missing_root)

    assert absent_warning is None
    assert absent["battery_present"] is False
    assert absent["inventory_status"] == "not_detected"

    inaccessible_root = tmp_path / "inaccessible"
    inaccessible_root.mkdir()
    path_class = type(inaccessible_root)
    original_iterdir = path_class.iterdir

    def denied(path):
        if path == inaccessible_root:
            raise PermissionError("permission denied")
        return original_iterdir(path)

    monkeypatch.setattr(path_class, "iterdir", denied)
    inaccessible, warning = linux_battery_inventory(inaccessible_root)

    assert warning == "permission denied"
    assert inaccessible["battery_present"] is None
    assert inaccessible["inventory_status"] == "inaccessible"


def test_devices_api_handles_empty_inventory(monkeypatch):
    from fastapi.testclient import TestClient
    from app.discovery.discovery_result import DiscoveryResult
    from app.main import app
    from app.api import devices as devices_api

    monkeypatch.setattr(
        devices_api.discovery_service,
        "discover",
        lambda: DiscoveryResult(),
    )
    with TestClient(app) as client:
        response = client.get("/devices/")

    assert response.status_code == 200
    assert response.json() == []


def test_devices_api_serializes_distinct_storage_inventory(monkeypatch):
    from fastapi.testclient import TestClient
    from app.discovery.discovery_result import DiscoveryResult
    from app.discovery.models.device import Device
    from app.main import app
    from app.api import devices as devices_api

    result = DiscoveryResult()
    result.add_device(Device(
        device_id="storage:/dev/sda",
        device_type="storage",
        name="Drive",
        properties={
            "device": "/dev/sda",
            "physical_drive": True,
            "inventory_kind": "physical_drive",
            "partitions": [{"device": "/dev/sda1"}],
        },
    ))
    result.add_device(Device(
        device_id="storage:/dev/sda1",
        device_type="storage",
        name="/dev/sda1",
        properties={
            "device": "/dev/sda1",
            "inventory_kind": "logical_volume",
            "physical_device": "/dev/sda",
            "mountpoint": "/mnt/data",
        },
    ))
    monkeypatch.setattr(
        devices_api.discovery_service,
        "discover",
        lambda: result,
    )

    with TestClient(app) as client:
        response = client.get("/devices/")

    assert response.status_code == 200
    payload = response.json()
    assert len(payload) == 2
    assert payload[0]["properties"]["physical_drive"] is True
    assert payload[1]["properties"]["inventory_kind"] == "logical_volume"
    assert "physical_disks" not in payload[1]["properties"]
