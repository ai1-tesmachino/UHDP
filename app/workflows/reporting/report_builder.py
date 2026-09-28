from app.workflows.reporting.diagnostic_report import (
    DiagnosticReport,
)
from app.workflows.workflow_context import (
    WorkflowContext,
)


class ReportBuilder:

    def build(
        self,
        context: WorkflowContext,
    ) -> DiagnosticReport:

        return DiagnosticReport(
            data={
                "cpu_result": context.get(
                    "cpu_result",
                ),
                "memory_result": context.get(
                    "memory_result",
                ),
                "storage_result": context.get(
                    "storage_result",
                ),
                "network_result": context.get(
                    "network_result",
                ),
                "cpu_validation": context.get(
                    "cpu_validation",
                ),
                "memory_validation": context.get(
                    "memory_validation",
                ),
                "storage_validation": context.get(
                    "storage_validation",
                ),
                "network_validation": context.get(
                    "network_validation",
                ),
            }
        )