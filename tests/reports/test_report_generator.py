from datetime import datetime

from app.reports.report_generator import ReportGenerator


class MockResult:

    def __init__(
        self,
        status,
    ):
        self.status = status


class MockSession:

    def __init__(self):

        self.session_id = "session-1"
        self.device_id = "device-1"

        self.started_at = datetime.utcnow()
        self.completed_at = datetime.utcnow()

        self.results = {
            "cpu": MockResult("PASS"),
            "memory": MockResult("PASS"),
            "storage": MockResult("FAIL"),
        }


def test_generate_report():

    generator = ReportGenerator()

    report = generator.generate(
        MockSession()
    )

    assert report.session_id == "session-1"
    assert report.device_id == "device-1"

    assert report.total_diagnostics == 3
    assert report.passed_diagnostics == 2
    assert report.failed_diagnostics == 1

    assert report.overall_status == "FAIL"

    assert "cpu" in report.results
    assert "memory" in report.results
    assert "storage" in report.results


def test_generate_report_all_pass():

    session = MockSession()

    session.results = {
        "cpu": MockResult("PASS"),
        "memory": MockResult("PASS"),
    }

    generator = ReportGenerator()

    report = generator.generate(
        session
    )

    assert report.overall_status == "PASS"
    assert report.failed_diagnostics == 0