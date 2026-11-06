from app.persistence.session_serialization import json_value, restore_session
from app.workflows.workflow_result import WorkflowResult
from app.workflows.workflow_status import WorkflowStatus


def test_workflow_result_round_trips_through_session_serialization():
    result = WorkflowResult(
        status=WorkflowStatus.FAILED,
        message="A diagnostic action failed.",
    )

    serialized = json_value({"workflow_result": result})
    restored = restore_session(serialized)["workflow_result"]

    assert serialized["workflow_result"] == {
        "status": "failed",
        "message": "A diagnostic action failed.",
    }
    assert isinstance(restored, WorkflowResult)
    assert restored.status is WorkflowStatus.FAILED
    assert restored.message == "A diagnostic action failed."
