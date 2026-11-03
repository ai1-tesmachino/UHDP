from app.services.file_session_repository import (
    FileSessionRepository,
)
from app.hal.diagnostic_evaluation import DiagnosticEvaluation
from app.hal.diagnostic_result import DiagnosticResult
from app.hal.diagnostic_status import DiagnosticStatus
from app.hal.evaluation_status import EvaluationStatus
from app.hal.models.diagnostic_result_collection import DiagnosticResultCollection
from app.workflows.reporting.diagnostic_report import DiagnosticReport


def test_save_and_load_session(
    tmp_path,
):

    repository = (
        FileSessionRepository(
            str(tmp_path)
        )
    )

    session = {
        "session_id": "session-1",
        "status": "completed",
    }

    repository.save(
        session
    )

    loaded = repository.get(
        "session-1"
    )

    assert loaded is not None
    assert (
        loaded["session_id"]
        == "session-1"
    )


def test_list_sessions(
    tmp_path,
):

    repository = (
        FileSessionRepository(
            str(tmp_path)
        )
    )

    repository.save(
        {
            "session_id": "s1",
        }
    )

    repository.save(
        {
            "session_id": "s2",
        }
    )

    sessions = (
        repository.list_all()
    )

    assert len(sessions) == 2


def test_delete_session(
    tmp_path,
):

    repository = (
        FileSessionRepository(
            str(tmp_path)
        )
    )

    repository.save(
        {
            "session_id": "s1",
        }
    )

    repository.delete(
        "s1"
    )

    assert (
        repository.get("s1")
        is None
    )


def test_diagnostic_outcome_evidence_and_report_survive_reload(tmp_path):
    repository = FileSessionRepository(str(tmp_path))
    result = DiagnosticResult(
        diagnostic_id="memory-id",
        diagnostic_type="memory",
        device_id="device-1",
        status=DiagnosticStatus.PASSED,
        details={"total_ram_mb": 8192},
        evaluation=DiagnosticEvaluation(
            status=EvaluationStatus.INCONCLUSIVE,
            warnings=["Required integrity test unavailable"],
        ),
    )
    report = DiagnosticReport(
        report_id="report-1",
        device_id="device-1",
        status="inconclusive",
        data={"memory_result": result},
    )
    repository.save(
        {
            "session_id": "persisted-session",
            "created_at": result.created_at,
            "diagnostic_results": DiagnosticResultCollection([result]),
            "report": report,
        }
    )

    loaded = repository.get("persisted-session")

    assert loaded is not None
    loaded_result = loaded["diagnostic_results"].results[0]
    assert loaded_result.status is DiagnosticStatus.PASSED
    assert loaded_result.evaluation.status is EvaluationStatus.INCONCLUSIVE
    assert loaded_result.details == {"total_ram_mb": 8192}
    assert loaded["report"].status == "inconclusive"
    assert loaded["report"].data["memory_result"].evaluation.status is (
        EvaluationStatus.INCONCLUSIVE
    )