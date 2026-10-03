from datetime import datetime

from app.reports.html_report_generator import HtmlReportGenerator
from app.reports.report_models import DiagnosticReport


class MockResult:

    def __init__(
        self,
        status,
        details,
    ):
        self.status = status
        self.details = details


def test_generate_html_report():

    report = DiagnosticReport(
        report_id="report-1",
        session_id="session-1",
        device_id="device-1",
        started_at=datetime.utcnow(),
        completed_at=datetime.utcnow(),
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

    generator = HtmlReportGenerator()

    html = generator.generate(
        report
    )

    assert "UHDP Diagnostic Report" in html
    assert "session-1" in html
    assert "device-1" in html

    assert "cpu" in html
    assert "memory" in html

    assert "CPU OK" in html
    assert "Memory OK" in html

    assert "PASS" in html


def test_generate_html_report_empty_results():

    report = DiagnosticReport(
        report_id="report-2",
        session_id="session-2",
        device_id="device-2",
    )

    generator = HtmlReportGenerator()

    html = generator.generate(
        report
    )

    assert "<html>" in html
    assert "session-2" in html