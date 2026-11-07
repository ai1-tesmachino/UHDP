from datetime import UTC, datetime

from app.hal.diagnostic_evaluation import DiagnosticEvaluation
from app.hal.diagnostic_result import DiagnosticResult
from app.hal.diagnostic_status import DiagnosticStatus
from app.hal.evaluation_status import EvaluationStatus
from app.reports.json_report_generator import JsonReportGenerator
from app.reports.report_models import DiagnosticReport


class MockResult:

    def __init__(
        self,
        status,
        details,
    ):
        self.status = status
        self.details = details


def test_generate_json_report():

    report = DiagnosticReport(
        report_id="report-1",
        session_id="session-1",
        device_id="device-1",
        started_at=datetime.now(UTC),
        completed_at=datetime.now(UTC),
        overall_status="PASS",
        total_diagnostics=2,
        passed_diagnostics=2,
        failed_diagnostics=0,
        results={
            "cpu": MockResult(
                "PASS",
                "CPU OK",
            ),
            "memory": MockResult(
                "PASS",
                "Memory OK",
            ),
        },
    )

    generator = JsonReportGenerator()

    data = generator.generate(
        report
    )

    assert data["report_id"] == "report-1"
    assert data["session_id"] == "session-1"
    assert data["device_id"] == "device-1"

    assert data["overall_status"] == "PASS"

    assert data["total_diagnostics"] == 2
    assert data["passed_diagnostics"] == 2
    assert data["failed_diagnostics"] == 0

    assert "cpu" in data["results"]
    assert "memory" in data["results"]

    assert data["results"]["cpu"]["status"] == "PASS"


def test_generate_json_report_with_empty_results():

    report = DiagnosticReport(
        report_id="report-2",
        session_id="session-2",
        device_id="device-2",
    )

    generator = JsonReportGenerator()

    data = generator.generate(
        report
    )

    assert data["results"] == {}


def test_slotted_diagnostic_result_is_preserved_as_structured_json():
    report = DiagnosticReport(
        report_id="report-3",
        session_id="session-3",
        device_id="device-3",
        results={
            "cpu": DiagnosticResult(
                diagnostic_id="cpu",
                diagnostic_type="cpu",
                device_id="device-3",
                status=DiagnosticStatus.PASSED,
                evaluation=DiagnosticEvaluation(
                    status=EvaluationStatus.INCONCLUSIVE,
                    warnings=["Inventory is not a functional check"],
                ),
                details={"logical_cores": 8},
            )
        },
    )

    result = JsonReportGenerator().generate(report)["results"]["cpu"]

    assert result["diagnostic_type"] == "cpu"
    assert result["status"] == "passed"
    assert result["evaluation"]["status"] == "inconclusive"
    assert result["details"]["logical_cores"] == 8