from types import SimpleNamespace

from app.hal.diagnostic_request import DiagnosticRequest
from app.hal.diagnostic_status import DiagnosticStatus
from app.hal.diagnostics import platform_probes
from app.hal.diagnostics.cpu_stress_diagnostic import CpuStressDiagnostic
from app.hal.diagnostics.memory_stress_diagnostic import MemoryStressDiagnostic
from app.hal.diagnostics.stress_utils import stress_test_duration
import pytest


def test_linux_wifi_probe_finds_adapter_and_keeps_connection_manual(
    tmp_path,
    monkeypatch,
):
    net_root = tmp_path / "sys/class/net/wlan0"
    (net_root / "wireless").mkdir(parents=True)
    monkeypatch.setattr(platform_probes, "LINUX_ROOT", tmp_path)
    monkeypatch.setattr(platform_probes.platform, "system", lambda: "Linux")

    result = platform_probes.linux_inventory_probe(
        DiagnosticRequest(
            diagnostic_type="wifi",
            device_id="test",
        ),
        "wifi",
    )

    assert result is not None
    assert result.status == DiagnosticStatus.PASSED
    assert result.details["adapters"] == ["wlan0"]
    assert "operator-confirmed" in result.message


def test_linux_absent_bluetooth_is_not_applicable(tmp_path, monkeypatch):
    (tmp_path / "sys/class/bluetooth").mkdir(parents=True)
    monkeypatch.setattr(platform_probes, "LINUX_ROOT", tmp_path)
    monkeypatch.setattr(platform_probes.platform, "system", lambda: "Linux")

    result = platform_probes.linux_inventory_probe(
        DiagnosticRequest(
            diagnostic_type="bluetooth",
            device_id="test",
        ),
        "bluetooth",
    )

    assert result is not None
    assert result.status == DiagnosticStatus.NOT_APPLICABLE


def test_stress_duration_is_clamped_and_invalid_values_rejected():
    assert stress_test_duration(
        DiagnosticRequest(parameters={"duration_seconds": 99})
    ) == 30
    assert stress_test_duration(
        DiagnosticRequest(parameters={"duration_seconds": 0})
    ) == 1
    with pytest.raises(ValueError, match="duration_seconds"):
        stress_test_duration(
            DiagnosticRequest(parameters={"duration_seconds": "invalid"})
        )


def test_cpu_stress_never_runs_longer_than_30_seconds(monkeypatch):
    times = iter([0.0, 30.0])
    monkeypatch.setattr("app.hal.diagnostics.cpu_stress_diagnostic.time.monotonic", lambda: next(times))

    result = CpuStressDiagnostic().execute(
        DiagnosticRequest(
            diagnostic_type="cpu_stress",
            parameters={"duration_seconds": 120},
        )
    )

    assert result.details["duration_seconds"] == 30
    assert result.details["cpu_cores_used"] == 1


def test_memory_stress_stays_under_half_available_and_allocation_cap(monkeypatch):
    monkeypatch.setattr(
        "app.hal.diagnostics.memory_stress_diagnostic.psutil.virtual_memory",
        lambda: SimpleNamespace(available=64 * 1024 * 1024),
    )
    clock = iter([0.0, 0.0, 2.0])
    monkeypatch.setattr(
        "app.hal.diagnostics.memory_stress_diagnostic.time.monotonic",
        lambda: next(clock, 2.0),
    )
    monkeypatch.setattr("app.hal.diagnostics.memory_stress_diagnostic.time.sleep", lambda _: None)

    result = MemoryStressDiagnostic().execute(
        DiagnosticRequest(
            diagnostic_type="memory_stress",
            parameters={"duration_seconds": 1},
        )
    )

    assert result.details["allocation_bytes"] <= 32 * 1024 * 1024
    assert result.details["allocation_bytes"] <= result.details["allocation_limit_bytes"]
