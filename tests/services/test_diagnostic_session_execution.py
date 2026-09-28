from app.services.diagnostic_session_service import (
    DiagnosticSessionService,
)
from app.workflows.templates.full_system_validation_workflow import (
    create_full_system_validation_workflow,
)


def test_diagnostic_session_executes_full_workflow(
    tmp_path,
    monkeypatch,
):
    from app.workflows.reporting.file_report_repository import (
        FileReportRepository,
    )

    def patched_init(
        self,
        directory="data/reports",
    ):
        self._directory = tmp_path
        self._directory.mkdir(
            parents=True,
            exist_ok=True,
        )

    monkeypatch.setattr(
        FileReportRepository,
        "__init__",
        patched_init,
    )

    service = DiagnosticSessionService()

    session = service.create_session()

    workflow = (
        create_full_system_validation_workflow()
    )

    result = service.execute_workflow(
        session_id=session["session_id"],
        workflow=workflow,
        device_id="test-device",
    )

    assert (
        result["session"]["session_id"]
        == session["session_id"]
    )

    assert (
        result["session"]["device_id"]
        == "test-device"
    )

    assert (
        result["session"]["workflow_name"]
        == workflow.name
    )

    assert result["workflow_result"] is not None

    assert result["report"] is not None

    assert result["report"].report_id

    assert (
        result["report"].device_id
        == "test-device"
    )

    assert result["report"].status in {
        "passed",
        "failed",
        "error",
        "pending",
    }