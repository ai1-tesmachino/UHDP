from datetime import datetime

from app.reports.report_models import DiagnosticReport
from app.reports.report_storage import ReportStorage


class MockResult:

    def __init__(
        self,
        status,
        details,
    ):
        self.status = status
        self.details = details


def test_save_and_load_report(
    tmp_path,
):

    storage = ReportStorage(
        reports_directory=str(
            tmp_path
        )
    )

    report = DiagnosticReport(
        report_id="report-1",
        session_id="session-1",
        device_id="device-1",
        started_at=datetime.utcnow(),
        completed_at=datetime.utcnow(),
        overall_status="PASS",
        total_diagnostics=1,
        passed_diagnostics=1,
        failed_diagnostics=0,
        results={
            "cpu": MockResult(
                "PASS",
                "CPU OK",
            )
        },
    )

    storage.save(
        report
    )

    json_report = storage.get_json(
        "session-1"
    )

    html_report = storage.get_html(
        "session-1"
    )

    assert json_report is not None
    assert html_report is not None

    assert (
        json_report["session_id"]
        == "session-1"
    )

    assert (
        "UHDP Diagnostic Report"
        in html_report
    )


def test_list_reports(
    tmp_path,
):

    storage = ReportStorage(
        reports_directory=str(
            tmp_path
        )
    )

    for index in range(2):

        report = DiagnosticReport(
            report_id=f"report-{index}",
            session_id=f"session-{index}",
            device_id="device-1",
        )

        storage.save(
            report
        )

    reports = storage.list_reports()

    assert len(
        reports
    ) == 2

    assert "session-0" in reports
    assert "session-1" in reports


def test_missing_report_returns_none(
    tmp_path,
):

    storage = ReportStorage(
        reports_directory=str(
            tmp_path
        )
    )

    assert (
        storage.get_json(
            "missing"
        )
        is None
    )

    assert (
        storage.get_html(
            "missing"
        )
        is None
    )