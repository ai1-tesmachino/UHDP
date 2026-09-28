from app.hal.diagnostic_result import DiagnosticResult
from app.hal.diagnostic_status import DiagnosticStatus
from app.services.diagnostic_session_service import (
    DiagnosticSessionService,
)
from app.workflows.workflow import Workflow
from app.workflows.workflow_context import WorkflowContext
from app.workflows.actions.base import Action


class SetDiagnosticResultsAction(Action):

    def execute(
        self,
        context: WorkflowContext,
    ) -> None:
        context.set(
            "cpu_result",
            DiagnosticResult(
                diagnostic_id="cpu-1",
                diagnostic_type="cpu",
                device_id="device-1",
                status=DiagnosticStatus.PASSED,
                message="CPU passed",
            ),
        )

        context.set(
            "memory_result",
            DiagnosticResult(
                diagnostic_id="memory-1",
                diagnostic_type="memory",
                device_id="device-1",
                status=DiagnosticStatus.FAILED,
                message="Memory failed",
            ),
        )


def test_session_collects_diagnostic_results(
    tmp_path,
    monkeypatch,
):
    monkeypatch.chdir(tmp_path)

    service = DiagnosticSessionService()

    session = service.create_session()

    workflow = Workflow(
        name="result_collection_test",
        actions=[
            SetDiagnosticResultsAction()
        ],
    )

    result = service.execute_workflow(
        session["session_id"],
        workflow,
        "device-1",
    )

    collection = result["diagnostic_results"]
    summary = result["diagnostic_summary"]

    assert len(collection) == 2
    assert summary.total == 2
    assert summary.passed == 1
    assert summary.failed == 1
    assert summary.errors == 0


def test_session_stores_diagnostic_summary(
    tmp_path,
    monkeypatch,
):
    monkeypatch.chdir(tmp_path)

    service = DiagnosticSessionService()

    session = service.create_session()

    workflow = Workflow(
        name="summary_test",
        actions=[
            SetDiagnosticResultsAction()
        ],
    )

    service.execute_workflow(
        session["session_id"],
        workflow,
        "device-1",
    )

    stored_session = service.get_session(
        session["session_id"]
    )

    assert stored_session[
        "diagnostic_summary"
    ].total == 2

    assert stored_session[
        "diagnostic_summary"
    ].passed == 1

    assert stored_session[
        "diagnostic_summary"
    ].failed == 1