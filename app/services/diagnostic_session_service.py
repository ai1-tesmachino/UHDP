from datetime import UTC, datetime

from app.discovery.discovery_service import (
    discovery_service,
)
from app.hal.models.diagnostic_result_collection import (
    DiagnosticResultCollection,
)
from app.services.session_service import (
    session_service,
)
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

from app.services.file_session_repository import (
    FileSessionRepository,
)

from app.runtime.services.diagnostic_service import (
    DiagnosticService,
)

from app.hal.diagnostic_evaluator import (
    DiagnosticEvaluator,
)

from app.profiles.profile_service import (
    ProfileService,
)

from app.profiles.file_profile_repository import (
    FileProfileRepository,
)

class DiagnosticSessionService:

    def __init__(self) -> None:
        self._sessions = {}

        self._repository = (
            FileSessionRepository()
        )

    def create_session(self):

        session = session_service.create()

        discovery_result = (
            discovery_service.discover()
        )

        discovered_devices = [
            {
                "device_id": device.device_id,
                "device_type": device.device_type,
                "name": device.name,
                "properties": device.properties,
            }
            for device in discovery_result.devices
        ]

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
            "discovered_devices": discovered_devices,
        }

        self._repository.save(
            self._sessions[session.id]
        )

        return self._sessions[session.id]

    def get_session(
        self,
        session_id: str,
    ):

        session = self._sessions.get(
            session_id
        )

        if session is not None:
            return session

        session = self._repository.get(
            session_id
        )

        if session is not None:
            self._sessions[
                session_id
            ] = session

        return session
   
    def execute_diagnostic(
        self,
        session_id: str,
        device_id: str,
        diagnostic_type: str,
    ):

        session = self.get_session(
            session_id
        )

        if session is None:
            raise ValueError(
                f"Session not found: {session_id}"
            )

        discovery_service.discover()

        device = (
            discovery_service.get_device(
                device_id
            )
        )

        if device is None:
            raise ValueError(
                f"Device not found: {device_id}"
            )

        result = DiagnosticService().execute(
            diagnostic_type=diagnostic_type,
            device_id=device_id,
        )

        collection = session[
            "diagnostic_results"
        ]

        collection.add(
            result
        )

        session[
            "diagnostic_summary"
        ] = collection.summary()

        session["device_id"] = device_id

        self._repository.save(
            session
        )

        return {
            "session": session,
            "result": result,
            "summary": session[
                "diagnostic_summary"
            ],
        }

    def execute_workflow(
        self,
        session_id: str,
        workflow,
        device_id: str,
    ):
        session = self.get_session(
            session_id
        )

        if session is None:
            raise ValueError(
                f"Session not found: {session_id}"
            )

        discovery_service.discover()

        device = (
            discovery_service.get_device(
                device_id
            )
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

        if device is not None:
            context.set(
                "device",
                device,
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

        self._repository.save(
            session
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

    def execute_profile(
        self,
        session_id: str,
        profile_name: str,
        device_id: str,
    ):

        session = self.get_session(
            session_id
        )

        if session is None:
            raise ValueError(
                f"Session not found: {session_id}"
            )

        discovery_service.discover()

        device = (
            discovery_service.get_device(
                device_id
            )
        )

        if device is None:
            raise ValueError(
                f"Device not found: {device_id}"
            )

        profile_service = (
            ProfileService(
                FileProfileRepository(
                    "profiles"
                )
            )
        )

        collection = (
            DiagnosticResultCollection()
        )

        results = (
            profile_service.execute_profile(
                profile_name=profile_name,
                diagnostic_service=(
                    DiagnosticService()
                ),
                device_id=device_id,
            )
        )

        evaluator = (
            DiagnosticEvaluator()
        )

        for result in results:

            result.evaluation = (
                evaluator.evaluate(
                    result
                )
            )

            collection.add(
                result
            )

        session["device_id"] = (
            device_id
        )

        session[
            "diagnostic_results"
        ] = collection

        session[
            "diagnostic_summary"
        ] = collection.summary()

        self._repository.save(
            session
        )

        return {
            "session": session,
            "profile_name": profile_name,
            "diagnostic_results": collection,
            "diagnostic_summary": (
                session[
                    "diagnostic_summary"
                ]
            ),
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

            "battery_result",
            "display_result",
            "webcam_result",
            "keyboard_result",
            "speaker_result",

            "usb_result",
            "usb_c_result",

            "hdmi_result",
            "vga_result",

            "wifi_result",
            "bluetooth_result",

        ):

            result = context.get(key)

            if result is None:
                continue

            collection.add(result)

        return collection

diagnostic_session_service = (
    DiagnosticSessionService()
)