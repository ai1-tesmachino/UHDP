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
from app.diagnostics.manual_checks import MANUAL_CHECK_IDS

class DiagnosticSessionService:

    def __init__(self) -> None:
        self._sessions = {}

        self._repository = (
            FileSessionRepository()
        )

    def create_session(
        self,
        device_id: str | None = None,
        intake_record: dict | None = None,
    ):

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
            "device_id": device_id,
            "intake_record": intake_record or {},
            "workflow_name": None,
            "workflow_result": None,
            "diagnostic_results": DiagnosticResultCollection(),
            "diagnostic_summary": None,
            "manual_results": {},
            "technician_record": {
                "observed_issue": "",
                "repair_performed": "",
                "replacement_performed": "",
                "customer_notes": "",
                "refurbishment_grade": None,
            },
            "health_analytics": {},
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
        parameters: dict | None = None,
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
            parameters=parameters,
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
        session["status"] = "running"
        self._refresh_report(session)

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

    def complete_session(
        self,
        session_id: str,
    ):
        session = self.get_session(session_id)
        if session is None:
            raise ValueError(
                f"Session not found: {session_id}"
            )

        session["status"] = "completed"
        report = session.get("report")
        if report is not None:
            report.status = self._session_result_status(session, report)
            FileReportRepository().save(
                f"diagnostic_{session_id}",
                report,
            )
        self._repository.save(session)
        return session

    def record_manual_result(
        self,
        session_id: str,
        check_id: str,
        outcome: str,
        notes: str = "",
    ):
        session = self.get_session(session_id)
        if session is None:
            raise ValueError(
                f"Session not found: {session_id}"
            )
        if check_id not in MANUAL_CHECK_IDS:
            raise ValueError(
                f"Unknown manual check: {check_id}"
            )
        if outcome not in {"passed", "failed", "not_applicable"}:
            raise ValueError(
                f"Invalid manual outcome: {outcome}"
            )

        manual_results = session.setdefault("manual_results", {})
        manual_results[check_id] = {
            "check_id": check_id,
            "status": outcome,
            "notes": notes,
            "recorded_at": datetime.now(UTC).isoformat(),
        }
        self._refresh_report(session)
        self._repository.save(session)
        return manual_results[check_id]

    def _refresh_report(self, session: dict) -> None:
        context = WorkflowContext()
        context.set("device_id", session.get("device_id") or "system")

        collection = session.get("diagnostic_results")
        if collection is not None:
            for result in collection.results:
                context.set(f"{result.diagnostic_type}_result", result)

        report = ReportBuilder().build(context)
        report.data["manual_checks"] = session.get("manual_results", {})
        report.data["technician_record"] = session.get(
            "technician_record",
            {},
        )
        report.data["intake_record"] = session.get("intake_record", {})
        report.data["device_inventory"] = session.get(
            "discovered_devices",
            [],
        )
        report.data["health_analytics"] = self._calculate_health_analytics(
            session,
        )
        report.data["refurbishment_recommendation"] = self._recommend_grade(
            report.data["health_analytics"],
        )
        summary = report.data.get("diagnostic_summary")
        if summary is None:
            summary = DiagnosticResultCollection().summary()
            report.data["diagnostic_summary"] = summary
        manual_results = session.get("manual_results", {}).values()
        for result in manual_results:
            summary.total += 1
            if result["status"] == "passed":
                summary.passed += 1
            elif result["status"] == "failed":
                summary.failed += 1
            elif result["status"] == "not_applicable":
                summary.not_applicable += 1
        report.status = self._session_result_status(session, report)
        session["report"] = report
        FileReportRepository().save(
            f"diagnostic_{session['session_id']}",
            report,
        )

    def update_technician_record(
        self,
        session_id: str,
        record: dict,
    ):
        session = self.get_session(session_id)
        if session is None:
            raise ValueError(f"Session not found: {session_id}")

        technician_record = session.setdefault(
            "technician_record",
            {},
        )
        technician_record.update(record)
        self._refresh_report(session)
        self._repository.save(session)
        return technician_record

    def _calculate_health_analytics(self, session: dict) -> dict:
        result_collection = session.get("diagnostic_results")
        results = (
            result_collection.results
            if hasattr(result_collection, "results")
            else []
        )

        groups = {
            "cpu_health": {"cpu", "cpu_stress"},
            "ram_health": {"memory", "memory_stress"},
            "storage_health": {"storage"},
            "battery_health": {"battery"},
            "gpu_health": {"gpu", "gpu_stress"},
            "thermal_health": {"thermal"},
            "display_health": {"display", "display_pattern"},
        }
        manual_results = session.get("manual_results", {})
        status_lookup = {
            result.diagnostic_type: result.status.value
            if hasattr(result.status, "value")
            else str(result.status)
            for result in results
        }
        status_lookup.update({
            check_id: result.get("status", "unknown")
            for check_id, result in manual_results.items()
        })
        scores = {}
        for group, diagnostic_types in groups.items():
            observed = [
                status_lookup[name]
                for name in diagnostic_types
                if name in status_lookup
            ]
            scoreable = [
                status
                for status in observed
                if status in {"passed", "failed", "error"}
            ]
            scores[group] = {
                "score": (
                    round(
                        sum(status == "passed" for status in scoreable)
                        * 100
                        / len(scoreable),
                    )
                    if scoreable
                    else None
                ),
                "checks_observed": len(observed),
                "checks_scored": len(scoreable),
                "excluded_statuses": [
                    status
                    for status in observed
                    if status not in {"passed", "failed", "error"}
                ],
            }

        available_scores = [
            value["score"]
            for value in scores.values()
            if value["score"] is not None
        ]
        scores["overall_device_health"] = {
            "score": (
                round(sum(available_scores) / len(available_scores))
                if available_scores
                else None
            ),
            "scored_components": len(available_scores),
            "method": "unweighted average of observed passed/failed/error diagnostic checks",
        }
        return scores

    def _recommend_grade(self, analytics: dict) -> dict:
        required = (
            "battery_health",
            "storage_health",
            "thermal_health",
            "display_health",
            "overall_device_health",
        )
        scores = [
            analytics.get(component, {}).get("score")
            for component in required
        ]
        if any(score is None for score in scores):
            return {
                "grade": "insufficient_data",
                "reason": "Battery, storage, thermal, display, and overall diagnostic evidence are required.",
                "required_components": list(required),
            }

        lowest = min(scores)
        if lowest >= 90:
            grade = "A"
        elif lowest >= 75:
            grade = "B"
        elif lowest >= 60:
            grade = "C"
        else:
            grade = "needs_repair"
        return {
            "grade": grade,
            "reason": "Grade is based on the lowest required health component score; configure site policy before certification use.",
            "required_components": list(required),
        }

    def _session_result_status(
        self,
        session: dict,
        report=None,
    ) -> str:
        report = report or session.get("report")
        if report is not None and report.status in {"failed", "error"}:
            return report.status

        outcomes = [
            result.get("status")
            for result in session.get("manual_results", {}).values()
        ]
        if "failed" in outcomes:
            return "failed"
        if "error" in outcomes:
            return "error"
        if report is not None and report.status == "unsupported":
            return report.status
        if "passed" in outcomes:
            return "passed"
        if outcomes and all(outcome == "not_applicable" for outcome in outcomes):
            return "not_applicable"
        return report.status if report is not None else "pending"

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
            "system_result",

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