import pytest

from app.hal.diagnostic_evaluator import DiagnosticEvaluator
from app.hal.diagnostic_result import DiagnosticResult
from app.hal.diagnostic_status import DiagnosticStatus
from app.hal.evaluation_status import EvaluationStatus


@pytest.mark.parametrize(
    ("diagnostic_type", "details"),
    [
        ("cpu", {"physical_cores": 4}),
        ("memory", {"total_ram_mb": 8192}),
        ("storage", {"drives": [{"mountpoint": "/"}]}),
    ],
)
def test_valid_measurements_pass_without_changing_raw_evidence(
    diagnostic_type, details
):
    result = DiagnosticResult(
        diagnostic_id="test-1",
        diagnostic_type=diagnostic_type,
        device_id="device-1",
        status=DiagnosticStatus.PASSED,
        details=details,
    )

    evaluation = DiagnosticEvaluator().evaluate(result)

    assert evaluation.status is EvaluationStatus.PASSED
    assert result.details == details


def test_memory_measurement_normalizes_mib_to_bytes():
    result = DiagnosticResult(
        diagnostic_id="memory-1",
        diagnostic_type="memory",
        device_id="device-1",
        status=DiagnosticStatus.PASSED,
        details={"total_ram_mb": 8192},
    )

    normalized = DiagnosticEvaluator.normalize_measurements(result)

    assert normalized["total_memory_bytes"] == 8192 * 1024**2
    assert result.details["total_ram_mb"] == 8192


@pytest.mark.parametrize(
    ("diagnostic_type", "details"),
    [
        ("cpu", {}),
        ("cpu", {"physical_cores": "four"}),
        ("memory", {}),
        ("memory", {"total_ram_mb": "8192"}),
        ("memory", {"total_ram_mb": 0}),
        ("storage", {}),
        ("storage", {"drives": "not-a-list"}),
        ("storage", {"drives": [None]}),
        ("network", {}),
        ("network", {"adapter_count": -1}),
        ("network", {"adapter_count": "2"}),
    ],
)
def test_missing_or_malformed_measurements_are_inconclusive(
    diagnostic_type, details
):
    result = DiagnosticResult(
        diagnostic_id="test-1",
        diagnostic_type=diagnostic_type,
        device_id="device-1",
        status=DiagnosticStatus.PASSED,
        details=details,
    )

    assert (
        DiagnosticEvaluator().evaluate(result).status
        is EvaluationStatus.INCONCLUSIVE
    )


def test_storage_drive_normalization_uses_reported_drive_list():
    result = DiagnosticResult(
        diagnostic_id="storage-1",
        diagnostic_type="storage",
        device_id="device-1",
        status=DiagnosticStatus.PASSED,
        details={"drives": [{"mountpoint": "/"}, {"mountpoint": "/data"}]},
    )

    assert DiagnosticEvaluator.normalize_measurements(result)["drive_count"] == 2


@pytest.mark.parametrize(
    ("raw_status", "expected"),
    [
        (DiagnosticStatus.FAILED, EvaluationStatus.FAILED),
        (DiagnosticStatus.ERROR, EvaluationStatus.ERROR),
        (DiagnosticStatus.UNSUPPORTED, EvaluationStatus.UNSUPPORTED),
        (DiagnosticStatus.SKIPPED, EvaluationStatus.SKIPPED),
        (DiagnosticStatus.WARNING, EvaluationStatus.WARNING),
        (DiagnosticStatus.INCONCLUSIVE, EvaluationStatus.INCONCLUSIVE),
        (DiagnosticStatus.CANCELLED, EvaluationStatus.CANCELLED),
        (DiagnosticStatus.RUNNING, EvaluationStatus.INCONCLUSIVE),
        (DiagnosticStatus.PENDING, EvaluationStatus.INCONCLUSIVE),
    ],
)
def test_terminal_hal_status_is_not_collapsed(raw_status, expected):
    result = DiagnosticResult(
        diagnostic_id="test-1",
        diagnostic_type="cpu",
        device_id="device-1",
        status=raw_status,
        details={"physical_cores": 4},
    )

    assert DiagnosticEvaluator().evaluate(result).status is expected


def test_network_inventory_does_not_pass_without_connectivity_evidence():
    result = DiagnosticResult(
        diagnostic_id="network-1",
        diagnostic_type="network",
        device_id="device-1",
        status=DiagnosticStatus.PASSED,
        details={"adapter_count": 2, "adapters": [{"name": "eth0"}]},
    )

    evaluation = DiagnosticEvaluator().evaluate(result)

    assert evaluation.status is EvaluationStatus.INCONCLUSIVE
    assert result.details["adapter_count"] == 2


def test_network_diagnostic_pass_requires_explicit_connectivity_evidence():
    result = DiagnosticResult(
        diagnostic_id="network-2",
        diagnostic_type="network",
        device_id="device-1",
        status=DiagnosticStatus.PASSED,
        details={
            "adapter_count": 1,
            "adapters": [{"name": "eth0"}],
            "connectivity_verified": True,
        },
    )

    assert (
        DiagnosticEvaluator().evaluate(result).status
        is EvaluationStatus.PASSED
    )


def test_zero_reported_storage_and_network_are_inconclusive_not_failed():
    evaluator = DiagnosticEvaluator()
    storage = DiagnosticResult(
        "storage-1", "storage", "device-1", DiagnosticStatus.PASSED,
        details={"drives": []},
    )
    network = DiagnosticResult(
        "network-1", "network", "device-1", DiagnosticStatus.PASSED,
        details={"adapter_count": 0},
    )

    assert evaluator.evaluate(storage).status is EvaluationStatus.INCONCLUSIVE
    assert evaluator.evaluate(network).status is EvaluationStatus.INCONCLUSIVE
