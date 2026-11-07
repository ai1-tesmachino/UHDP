import pytest

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


def test_battery_missing_is_not_applicable():

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
        == EvaluationStatus.NOT_APPLICABLE
    )


@pytest.mark.parametrize(
    "details",
    [
        {"battery_present": True},
        {"battery_present": True, "percent": True},
        {"battery_present": True, "percent": 101},
        {"battery_present": True, "percent": float("nan")},
        {"battery_present": True, "percent": 10**1000},
    ],
)
def test_battery_presence_without_valid_measurement_is_inconclusive(details):
    evaluation = DiagnosticEvaluator().evaluate(create_result(details))

    assert evaluation.status is EvaluationStatus.INCONCLUSIVE