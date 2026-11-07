from datetime import UTC, datetime

from app.hal.diagnostic_evaluation import DiagnosticEvaluation
from app.hal.diagnostic_result import DiagnosticResult
from app.hal.diagnostic_status import DiagnosticStatus
from app.hal.evaluation_status import EvaluationStatus
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

        self.started_at = datetime.now(UTC)
        self.completed_at = datetime.now(UTC)

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


def test_inconclusive_and_empty_reports_are_not_reported_as_pass():
    generator = ReportGenerator()
    session = MockSession()
    session.results = {
        "cpu": DiagnosticResult(
            diagnostic_id="cpu",
            diagnostic_type="cpu",
            device_id="device-1",
            status=DiagnosticStatus.PASSED,
            evaluation=DiagnosticEvaluation(EvaluationStatus.INCONCLUSIVE),
        )
    }

    inconclusive = generator.generate(session)
    session.results = {}
    empty = generator.generate(session)

    assert inconclusive.overall_status == "INCOMPLETE"
    assert inconclusive.total_diagnostics == 1
    assert inconclusive.passed_diagnostics == 0
    assert empty.overall_status == "INCOMPLETE"
    assert empty.total_diagnostics == 0


def test_report_id_is_stable_for_the_same_session():
    generator = ReportGenerator()
    session = MockSession()

    first = generator.generate(session)
    second = generator.generate(session)

    assert first.report_id == second.report_id