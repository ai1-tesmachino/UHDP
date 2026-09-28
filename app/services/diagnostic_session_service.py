from datetime import UTC, datetime

from app.hal.models.diagnostic_result_collection import (
    DiagnosticResultCollection,
)
from app.services.session_service import session_service
from app.workflows.reporting.file_report_repository import (
    FileReportRepository,
)
from app.workflows.reporting.report_builder import (
    ReportBuilder,
)
from app.workflows.workflow_context import (
    WorkflowContext,
)
from app.workflows.workflow_engine import (
    WorkflowEngine,
)


class DiagnosticSessionService:

    def __init__(self) -> None:
        self._sessions = {}

    def create_session(self):
        session = session_service.create()

        self._sessions[session.id] = {
            "session_id": session.id,
            "status": "created",
            "created_at": datetime.now(UTC),
            "device_id": None,
            "workflow_name": None,
            "workflow_result": None,
            "diagnostic_results": DiagnosticResultCollection(),
            "diagnostic_summary": None,
            "report": None,
        }

        return self._sessions[session.id]

    def get_session(
        self,
        session_id: str,
    ):
        return self._sessions.get(session_id)

    def execute_workflow(
        self,
        session_id: str,
        workflow,
        device_id: str,
    ):
        session = self.get_session(session_id)

        if session is None:
            raise ValueError(
                f"Session not found: {session_id}"
            )

        context = WorkflowContext()

        context.set(
            "session_id",
            session_id,
        )

        context.set(
            "device_id",
            device_id,
        )

        session["status"] = "running"
        session["device_id"] = device_id
        session["workflow_name"] = workflow.name

        engine = WorkflowEngine()

        result = engine.execute(
            workflow,
            context,
        )

        session["workflow_result"] = result

        if result.success:
            session["status"] = "completed"
        else:
            session["status"] = "failed"

        diagnostic_results = (
            self._collect_diagnostic_results(
                context
            )
        )

        session["diagnostic_results"] = (
            diagnostic_results
        )

        session["diagnostic_summary"] = (
            diagnostic_results.summary()
        )

        report = ReportBuilder().build(
            context
        )

        session["report"] = report

        report_name = (
            f"diagnostic_{session_id}"
        )

        FileReportRepository().save(
            report_name,
            report,
        )

        return {
            "session": session,
            "workflow_result": result,
            "diagnostic_results": diagnostic_results,
            "diagnostic_summary": (
                session["diagnostic_summary"]
            ),
            "report": report,
        }

    def _collect_diagnostic_results(
        self,
        context: WorkflowContext,
    ) -> DiagnosticResultCollection:

        collection = DiagnosticResultCollection()

        for key in (
            "cpu_result",
            "memory_result",
            "storage_result",
            "network_result",
        ):
            result = context.get(key)

            if result is not None:
                collection.add(result)

        return collection


diagnostic_session_service = (
    DiagnosticSessionService()
)