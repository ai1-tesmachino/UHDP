from pathlib import Path

from app.workflows.templates.full_hardware_test_template import (
    create_full_hardware_test_workflow,
)
from app.workflows.workflow_context import (
    WorkflowContext,
)
from app.workflows.workflow_engine import (
    WorkflowEngine,
)


def test_full_hardware_workflow(
    monkeypatch,
    tmp_path,
):

    from app.workflows.reporting.file_report_repository import (
        FileReportRepository,
    )

    original_init = (
        FileReportRepository.__init__
    )

    def fake_init(
        self,
        directory="data/reports",
    ):
        original_init(
            self,
            tmp_path,
        )

    monkeypatch.setattr(
        FileReportRepository,
        "__init__",
        fake_init,
    )

    workflow = (
        create_full_hardware_test_workflow()
    )

    context = WorkflowContext()

    result = WorkflowEngine().execute(
        workflow,
        context,
    )

    assert context.exists(
        "cpu_result",
    )

    assert context.exists(
        "memory_result",
    )

    assert context.exists(
        "storage_result",
    )

    assert context.exists(
        "network_result",
    )

    assert context.exists(
        "cpu_validation",
    )

    assert context.exists(
        "memory_validation",
    )

    assert context.exists(
        "storage_validation",
    )

    assert context.exists(
        "network_validation",
    )

    assert context.exists(
        "diagnostic_report",
    )

    assert (
        context.get(
            "report_saved",
        )
        is True
    )

    assert (
        Path(tmp_path)
        / "full_hardware_test.json"
    ).exists()

    assert (
        result.status.value
        == "success"
    )