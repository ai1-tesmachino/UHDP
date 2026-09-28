from datetime import UTC

from app.workflows.reporting.diagnostic_report import (
    DiagnosticReport,
)


def test_diagnostic_report_defaults():
    report = DiagnosticReport(
        report_id="report-001",
        device_id="device-001",
        status="passed",
    )

    assert report.report_id == "report-001"
    assert report.device_id == "device-001"
    assert report.status == "passed"
    assert report.data == {}
    assert report.created_at.tzinfo == UTC


def test_diagnostic_report_accepts_data():
    data = {
        "cpu_result": "passed",
        "memory_result": "passed",
    }

    report = DiagnosticReport(
        report_id="report-002",
        device_id="device-002",
        status="passed",
        data=data,
    )

    assert report.data == data