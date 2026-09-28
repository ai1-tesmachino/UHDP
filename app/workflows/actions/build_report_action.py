from app.workflows.actions.base import Action
from app.workflows.reporting.report_builder import (
    ReportBuilder,
)
from app.workflows.workflow_context import (
    WorkflowContext,
)


class BuildReportAction(Action):

    def execute(
        self,
        context: WorkflowContext,
    ) -> None:

        report = ReportBuilder().build(
            context,
        )

        context.set(
            "diagnostic_report",
            report,
        )