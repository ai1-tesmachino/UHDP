import json

from app.hal.diagnostic_result import DiagnosticResult
from app.hal.diagnostic_status import DiagnosticStatus
from app.workflows.reporting.diagnostic_report import (
    DiagnosticReport,
)
from app.workflows.reporting.file_report_repository import (
    FileReportRepository,
)


def test_save_report(tmp_path):

    result = DiagnosticResult(
        diagnostic_id="cpu-001",
        diagnostic_type="cpu",
        device_id="device-001",
        status=DiagnosticStatus.PASSED,
        message="CPU passed",
        details={
            "cores": 8,
        },
    )

    report = DiagnosticReport(
        report_id="report-001",
        device_id="device-001",
        status="passed",
        data={
            "cpu_result": result,
        },
    )

    repository = FileReportRepository(
        tmp_path
    )

    repository.save(
        "test-report",
        report,
    )

    file_path = (
        tmp_path
        / "test-report.json"
    )

    assert file_path.exists()

    with open(
        file_path,
        "r",
        encoding="utf-8",
    ) as file:
        data = json.load(file)

    assert data["report_id"] == "report-001"
    assert data["device_id"] == "device-001"
    assert data["status"] == "passed"

    assert (
        data["data"]["cpu_result"]["diagnostic_id"]
        == "cpu-001"
    )

    assert (
        data["data"]["cpu_result"]["status"]
        == "passed"
    )

    assert (
        data["data"]["cpu_result"]["details"]["cores"]
        == 8
    )