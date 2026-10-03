from app.hal.diagnostic_evaluator import (
    DiagnosticEvaluator,
)
from app.hal.diagnostic_result import (
    DiagnosticResult,
)
from app.hal.diagnostic_status import (
    DiagnosticStatus,
)
from app.hal.evaluation_status import (
    EvaluationStatus,
)


def test_cpu_pass():

    result = DiagnosticResult(
        diagnostic_id="1",
        diagnostic_type="cpu",
        device_id="cpu",
        status=DiagnosticStatus.PASSED,
        details={
            "physical_cores": 4,
        },
    )

    evaluation = (
        DiagnosticEvaluator().evaluate(
            result
        )
    )

    assert (
        evaluation.status
        == EvaluationStatus.PASSED
    )


def test_memory_warning():

    result = DiagnosticResult(
        diagnostic_id="1",
        diagnostic_type="memory",
        device_id="memory",
        status=DiagnosticStatus.PASSED,
        details={
            "total_gb": 2,
        },
    )

    evaluation = (
        DiagnosticEvaluator().evaluate(
            result
        )
    )

    assert (
        evaluation.status
        == EvaluationStatus.WARNING
    )


def test_storage_failure():

    result = DiagnosticResult(
        diagnostic_id="1",
        diagnostic_type="storage",
        device_id="storage",
        status=DiagnosticStatus.PASSED,
        details={
            "drive_count": 0,
        },
    )

    evaluation = (
        DiagnosticEvaluator().evaluate(
            result
        )
    )

    assert (
        evaluation.status
        == EvaluationStatus.FAILED
    )


def test_network_failure():

    result = DiagnosticResult(
        diagnostic_id="1",
        diagnostic_type="network",
        device_id="network",
        status=DiagnosticStatus.PASSED,
        details={
            "adapter_count": 0,
        },
    )

    evaluation = (
        DiagnosticEvaluator().evaluate(
            result
        )
    )

    assert (
        evaluation.status
        == EvaluationStatus.FAILED
    )