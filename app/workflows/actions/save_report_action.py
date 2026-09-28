from app.workflows.actions.base import Action
from app.workflows.reporting.file_report_repository import (
    FileReportRepository,
)
from app.workflows.workflow_context import (
    WorkflowContext,
)


class SaveReportAction(Action):

    def __init__(
        self,
        report_name: str,
    ) -> None:
        self._report_name = report_name

    def execute(
        self,
        context: WorkflowContext,
    ) -> None:

        report = context.get(
            "diagnostic_report",
        )

        if report is None:
            raise ValueError(
                "diagnostic_report not found"
            )

        repository = FileReportRepository()

        repository.save(
            self._report_name,
            report,
        )

        context.set(
            "report_saved",
            True,
        )

        context.set(
            "report_path",
            f"data/reports/"
            f"{self._report_name}.json",
        )