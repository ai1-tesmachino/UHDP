from datetime import datetime

from app.reports.report_models import DiagnosticReport
from app.reports.report_models import ReportSummary


def test_create_diagnostic_report():

    report = DiagnosticReport(
        report_id="report-1",
        session_id="session-1",
        device_id="device-1",
    )

    assert report.report_id == "report-1"
    assert report.session_id == "session-1"
    assert report.device_id == "device-1"
    assert report.results == {}


def test_create_report_summary():

    summary = ReportSummary(
        report_id="report-1",
        session_id="session-1",
        device_id="device-1",
        overall_status="PASS",
        total_diagnostics=10,
        passed_diagnostics=10,
        failed_diagnostics=0,
        completed_at=datetime.utcnow(),
    )

    assert summary.overall_status == "PASS"
    assert summary.total_diagnostics == 10
    assert summary.failed_diagnostics == 0