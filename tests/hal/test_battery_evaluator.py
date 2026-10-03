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


def create_result(details):

    return DiagnosticResult(
        diagnostic_type="battery",
        diagnostic_id="1",
        device_id="device",
        status=DiagnosticStatus.PASSED,
        message="ok",
        details=details,
    )


def test_battery_pass():

    evaluation = (
        DiagnosticEvaluator()
        .evaluate(
            create_result(
                {
                    "battery_present": True,
                    "percent": 80,
                }
            )
        )
    )

    assert (
        evaluation.status
        == EvaluationStatus.PASSED
    )


def test_battery_low_warning():

    evaluation = (
        DiagnosticEvaluator()
        .evaluate(
            create_result(
                {
                    "battery_present": True,
                    "percent": 5,
                }
            )
        )
    )

    assert (
        evaluation.status
        == EvaluationStatus.WARNING
    )


def test_battery_missing_warning():

    evaluation = (
        DiagnosticEvaluator()
        .evaluate(
            create_result(
                {
                    "battery_present": False,
                }
            )
        )
    )

    assert (
        evaluation.status
        == EvaluationStatus.WARNING
    )