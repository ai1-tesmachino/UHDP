from datetime import datetime

from app.reports.report_storage import ReportStorage
from app.services.report_service import ReportService


class MockResult:

    def __init__(
        self,
        status,
        details="",
    ):
        self.status = status
        self.details = details


class MockSession:

    def __init__(self):

        self.session_id = "session-1"
        self.device_id = "device-1"

        self.started_at = datetime.utcnow()
        self.completed_at = datetime.utcnow()

        self.results = {
            "cpu": MockResult(
                "PASS",
                "CPU OK",
            ),
            "memory": MockResult(
                "PASS",
                "Memory OK",
            ),
        }


def test_generate_report(
    tmp_path,
):

    storage = ReportStorage(
        reports_directory=str(
            tmp_path
        )
    )

    service = ReportService(
        report_storage=storage,
    )

    report = service.generate_report(
        MockSession()
    )

    assert report.session_id == "session-1"

    json_report = service.get_report_json(
        "session-1"
    )

    assert json_report is not None

    assert (
        json_report["session_id"]
        == "session-1"
    )


def test_get_html_report(
    tmp_path,
):

    storage = ReportStorage(
        reports_directory=str(
            tmp_path
        )
    )

    service = ReportService(
        report_storage=storage,
    )

    service.generate_report(
        MockSession()
    )

    html = service.get_report_html(
        "session-1"
    )

    assert html is not None

    assert (
        "UHDP Diagnostic Report"
        in html
    )


def test_list_reports(
    tmp_path,
):

    storage = ReportStorage(
        reports_directory=str(
            tmp_path
        )
    )

    service = ReportService(
        report_storage=storage,
    )

    service.generate_report(
        MockSession()
    )

    reports = service.list_reports()

    assert len(reports) == 1
    assert "session-1" in reports