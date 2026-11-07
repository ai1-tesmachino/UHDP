from unittest.mock import patch

from app.hal.diagnostic_request import (
    DiagnosticRequest,
)
from app.hal.diagnostic_evaluator import DiagnosticEvaluator
from app.hal.diagnostic_status import (
    DiagnosticStatus,
)
from app.hal.evaluation_status import EvaluationStatus
from app.hal.diagnostics.battery_diagnostic import (
    BatteryDiagnostic,
)


def test_linux_battery_measurement_matches_evaluator_contract():
    inventory = {
        "battery_present": True,
        "batteries": [{"name": "BAT0", "capacity_percent": 80}],
        "battery_count": 1,
        "inventory_status": "detected",
    }
    with patch(
        "app.hal.diagnostics.battery_diagnostic.platform.system",
        return_value="Linux",
    ), patch(
        "app.hal.diagnostics.battery_diagnostic.linux_battery_inventory",
        return_value=(inventory, None),
    ):
        result = BatteryDiagnostic().execute(
            DiagnosticRequest(diagnostic_type="battery", device_id="local")
        )

    assert result.status is DiagnosticStatus.PASSED
    assert result.details["percent"] == 80
    assert (
        DiagnosticEvaluator().evaluate(result).status
        is EvaluationStatus.PASSED
    )


def test_linux_battery_without_charge_measurement_is_inconclusive():
    inventory = {
        "battery_present": True,
        "batteries": [{"name": "BAT0"}],
        "battery_count": 1,
        "inventory_status": "detected",
    }
    with patch(
        "app.hal.diagnostics.battery_diagnostic.platform.system",
        return_value="Linux",
    ), patch(
        "app.hal.diagnostics.battery_diagnostic.linux_battery_inventory",
        return_value=(inventory, None),
    ):
        result = BatteryDiagnostic().execute(
            DiagnosticRequest(diagnostic_type="battery", device_id="local")
        )

    assert result.status is DiagnosticStatus.INCONCLUSIVE


def test_linux_battery_inventory_access_error_is_not_absence():
    inventory = {
        "battery_present": None,
        "batteries": [],
        "battery_count": 0,
        "inventory_status": "inaccessible",
    }
    with patch(
        "app.hal.diagnostics.battery_diagnostic.platform.system",
        return_value="Linux",
    ), patch(
        "app.hal.diagnostics.battery_diagnostic.linux_battery_inventory",
        return_value=(inventory, "permission denied"),
    ):
        result = BatteryDiagnostic().execute(
            DiagnosticRequest(diagnostic_type="battery", device_id="local")
        )

    assert result.status is DiagnosticStatus.INCONCLUSIVE


def test_linux_multiple_batteries_use_lowest_valid_charge():
    inventory = {
        "battery_present": True,
        "batteries": [
            {"name": "BAT0", "capacity_percent": 80},
            {"name": "BAT1", "capacity_percent": 15},
        ],
        "battery_count": 2,
        "inventory_status": "detected",
    }
    with patch(
        "app.hal.diagnostics.battery_diagnostic.platform.system",
        return_value="Linux",
    ), patch(
        "app.hal.diagnostics.battery_diagnostic.linux_battery_inventory",
        return_value=(inventory, None),
    ):
        result = BatteryDiagnostic().execute(
            DiagnosticRequest(diagnostic_type="battery", device_id="local")
        )

    assert result.status is DiagnosticStatus.PASSED
    assert result.details["percent"] == 15


def test_nonlinux_battery_with_invalid_charge_is_inconclusive():
    battery = type(
        "Battery",
        (),
        {
            "percent": float("nan"),
            "power_plugged": False,
            "secsleft": 0,
        },
    )()
    with patch(
        "app.hal.diagnostics.battery_diagnostic.platform.system",
        return_value="Windows",
    ), patch(
        "app.hal.diagnostics.battery_diagnostic.psutil.sensors_battery",
        return_value=battery,
    ):
        result = BatteryDiagnostic().execute(
            DiagnosticRequest(diagnostic_type="battery", device_id="local")
        )

    assert result.status is DiagnosticStatus.INCONCLUSIVE