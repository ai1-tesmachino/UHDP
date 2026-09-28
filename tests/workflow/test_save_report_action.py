from pathlib import Path

from app.workflows.actions.save_report_action import (
    SaveReportAction,
)
from app.workflows.reporting.diagnostic_report import (
    DiagnosticReport,
)
from app.workflows.workflow_context import (
    WorkflowContext,
)


def test_save_report_action(
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

    context = WorkflowContext()

    context.set(
        "diagnostic_report",
        DiagnosticReport(
            data={
                "result": "ok",
            }
        ),
    )

    action = SaveReportAction(
        "hardware_test",
    )

    action.execute(
        context,
    )

    assert context.get(
        "report_saved",
    ) is True

    assert (
        Path(tmp_path)
        / "hardware_test.json"
    ).exists()