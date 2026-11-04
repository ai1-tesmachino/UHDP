import logging
from datetime import UTC, datetime
from threading import RLock
from uuid import uuid4

from app.domain.assets import (
    Asset,
    component_for_device,
    components_from_discovery,
)
from app.discovery.discovery_service import (
    discovery_service,
)
from app.discovery.providers.display_provider import DisplayProvider
from app.diagnostics.display_tests import (
    DISPLAY_NAVIGATION_IDS,
    DISPLAY_TESTS,
    DISPLAY_TEST_IDS,
)
from app.hal.diagnostic_result import DiagnosticResult
from app.hal.diagnostic_status import DiagnosticStatus
from app.hal.models.diagnostic_result_collection import (
    DiagnosticResultCollection,
)
from app.services.session_service import (
    session_service,
)
from app.persistence.repository_factory import (
    create_report_repository,
    create_session_repository,
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
from app.diagnostics.manual_checks import MANUAL_CHECKS
from app.diagnostics.models.test_result import (
    ScanStatus,
    TechnicianDecision,
    TestResultRecord,
    TestStatus,
)

logger = logging.getLogger(__name__)


class DiagnosticSessionService:

    def __init__(self) -> None:
        self._sessions = {}

        self._repository = create_session_repository()
        self._display_lock = RLock()

    def create_session(
        self,
        device_id: str | None = None,
        intake_record: dict | None = None,
        session_id: str | None = None,
    ):

        intake_record = intake_record or {}
        if session_id:
            existing_session = self.get_session(session_id)
            if existing_session is not None:
                return existing_session

        retest_of_session_id = intake_record.get("retest_of_session_id")
        prior_session = (
            self.get_session(retest_of_session_id)
            if retest_of_session_id
            else None
        )
        if retest_of_session_id and prior_session is None:
            raise ValueError(
                f"Retest source session not found: {retest_of_session_id}"
            )
        requested_asset_id = intake_record.get("asset_id")
        if requested_asset_id is not None and (
            not isinstance(requested_asset_id, str) or not requested_asset_id
        ):
            raise ValueError("A non-empty asset_id is required when supplied.")
        create_asset = intake_record.get("create_asset", False)
        if not isinstance(create_asset, bool):
            raise ValueError("create_asset must be a boolean.")
        if requested_asset_id is not None and create_asset:
            raise ValueError("Choose an existing asset_id or create_asset, not both.")
        prior_asset_id = (
            prior_session.get("asset_id") if prior_session is not None else None
        )
        if isinstance(prior_asset_id, str) and prior_asset_id:
            if create_asset:
                raise ValueError("A retest must inherit its source session's asset.")
            if requested_asset_id is not None and requested_asset_id != prior_asset_id:
                raise ValueError(
                    "A retest must use the asset_id assigned to its source session."
                )
            asset_id = prior_asset_id
        elif retest_of_session_id:
            if requested_asset_id is not None or create_asset:
                raise ValueError(
                    "A retest of a legacy session must preserve its unresolved asset identity."
                )
            asset_id = None
        elif requested_asset_id is not None:
            if self._repository.find_asset(requested_asset_id) is None:
                raise ValueError(
                    f"Asset not found: {requested_asset_id}. "
                    "Use create_asset=true to create a new asset."
                )
            asset_id = requested_asset_id
        elif create_asset:
            asset_id = str(uuid4())
        else:
            asset_id = None

        prior_asset = (
            prior_session.get("asset")
            if prior_session and isinstance(prior_session.get("asset"), dict)
            else {}
        )
        existing_asset = (
            self._repository.find_asset(asset_id)
            if isinstance(asset_id, str) and not prior_asset
            else None
        )
        prior_test_results = (
            prior_session.get("test_results", {})
            if prior_session
            else {}
        )
        prior_diagnostic_runs = []
        prior_collection = (
            prior_session.get("diagnostic_results")
            if prior_session
            else None
        )
        prior_results = (
            prior_collection.get("results", [])
            if isinstance(prior_collection, dict)
            else getattr(prior_collection, "results", [])
        )
        for prior_result in prior_results:
            if isinstance(prior_result, dict):
                prior_diagnostic_runs.append({
                    "diagnostic_id": prior_result.get("diagnostic_id"),
                    "run_id": prior_result.get("run_id"),
                    "diagnostic_type": prior_result.get("diagnostic_type"),
                    "device_id": prior_result.get("device_id"),
                })
            else:
                prior_diagnostic_runs.append({
                    "diagnostic_id": getattr(prior_result, "diagnostic_id", None),
                    "run_id": getattr(prior_result, "run_id", None),
                    "diagnostic_type": getattr(prior_result, "diagnostic_type", None),
                    "device_id": getattr(prior_result, "device_id", None),
                })
        session = session_service.create(session_id)
        asset = None
        if isinstance(asset_id, str):
            asset_payload = prior_asset or existing_asset or {}
            asset = Asset(
                asset_id=asset_id,
                asset_tag=(
                    intake_record.get("asset_tag")
                    if isinstance(intake_record.get("asset_tag"), str)
                    else asset_payload.get("asset_tag")
                ),
                manufacturer=asset_payload.get("manufacturer"),
                model=asset_payload.get("model"),
                serial_number=asset_payload.get("serial_number"),
            )

        self._sessions[session.id] = {
            "session_id": session.id,
            "status": "created",
            "created_at": datetime.now(UTC),
            "device_id": device_id,
            "asset_id": asset_id,
            "asset": asset.to_dict() if asset is not None else None,
            "components": [],
            "report_id": None,
            "intake_record": intake_record,
            "workflow_name": None,
            "workflow_result": None,
            "diagnostic_results": DiagnosticResultCollection(),
            "diagnostic_summary": None,
            "manual_results": {},
            "cosmetic_inspections": {},
            "test_results": {},
            "performance_results": {},
            "prior_test_results": prior_test_results,
            "prior_diagnostic_runs": prior_diagnostic_runs,
            "technician_record": {
                "fault_code": "",
                "observed_issue": "",
                "repair_performed": "",
                "replacement_performed": "",
                "customer_notes": "",
                "refurbishment_grade": None,
                "final_disposition": None,
                "qa_approver": None,
                "qa_approved_at": None,
                "final_disposition_reason": None,
            },
            "health_analytics": {},
            "report": None,
            "discovered_devices": [],
        }

        self._repository.save(
            self._sessions[session.id]
        )

        return self._sessions[session.id]

    def list_sessions(self) -> list[dict]:
        def created_at(session: dict) -> datetime:
            value = session.get("created_at")
            if isinstance(value, datetime):
                return value
            if isinstance(value, str):
                try:
                    return datetime.fromisoformat(value)
                except ValueError:
                    pass
            return datetime.min.replace(tzinfo=UTC)

        return sorted(
            self._repository.list_all(),
            key=created_at,
            reverse=True,
        )

    def delete_session(self, session_id: str) -> bool:
        session = self.get_session(session_id)
        if session is None:
            return False
        self._repository.delete(session_id)
        self._sessions.pop(session_id, None)
        return True

    def update_session_intake(
        self,
        session_id: str,
        device_id: str,
        intake_record: dict,
        device_inventory: list[dict],
    ) -> dict:
        session = self.get_session(session_id)
        if session is None:
            raise ValueError(f"Session not found: {session_id}")
        self._ensure_session_not_finalized(session)
        session["device_id"] = device_id
        session["intake_record"] = intake_record
        session["device_inventory"] = device_inventory
        self._refresh_report(session)
        self._repository.save(session)
        return session

    def refresh_report_for_session(self, session_id: str) -> dict:
        session = self.get_session(session_id)
        if session is None:
            raise ValueError(f"Session not found: {session_id}")
        self._refresh_report(session)
        self._repository.save(session)
        return session

    def record_performance_result(
        self,
        session_id: str,
        run_id: str,
        result: dict,
    ) -> dict:
        session = self.get_session(session_id)
        if session is None:
            raise ValueError(f"Session not found: {session_id}")
        self._ensure_session_not_finalized(session)
        session.setdefault("performance_results", {})[run_id] = result
        self._refresh_report(session)
        self._repository.save(session)
        return session

    def start_display_diagnostic(self, session_id: str) -> dict:
        with self._display_lock:
            session = self.get_session(session_id)
            if session is None:
                raise ValueError(f"Session not found: {session_id}")
            self._ensure_session_not_finalized(session)
            diagnostic = session.get("display_diagnostic")
            if diagnostic is None:
                self._ensure_display_session_is_editable(session)
                if not session.get("device_id"):
                    raise ValueError(
                        "A device must be associated with the QC session before display testing."
                    )
                discovered = DisplayProvider().discover()
                display = next(
                    (
                        item
                        for item in discovered.devices
                        if item.device_id == "display"
                    ),
                    None,
                )
                metadata = (
                    dict(display.properties)
                    if display is not None and isinstance(display.properties, dict)
                    else {"inventory_status": "not_available"}
                )
                now = datetime.now(UTC).isoformat()
                diagnostic = {
                    "diagnostic_id": str(uuid4()),
                    "session_id": session_id,
                    "device_id": session["device_id"],
                    "status": "in_progress",
                    "overall_status": None,
                    "created_at": now,
                    "updated_at": now,
                    "completed_at": None,
                    "current_test_id": DISPLAY_TESTS[0]["id"],
                    "display_metadata": metadata,
                    "tests": {
                        test["id"]: {
                            "status": "not_started",
                            "attempts": [],
                            "latest_result": None,
                        }
                        for test in DISPLAY_TESTS
                    },
                }
                session["display_diagnostic"] = diagnostic
                self._refresh_report(session)
                self._repository.save(session)
                logger.info(
                    "Display diagnostic initialized session_id=%s diagnostic_id=%s",
                    session_id,
                    diagnostic["diagnostic_id"],
                )
            else:
                self._ensure_display_test_entries(diagnostic)
            return diagnostic

    def get_display_diagnostic(self, session_id: str) -> dict:
        with self._display_lock:
            session = self.get_session(session_id)
            if session is None:
                raise ValueError(f"Session not found: {session_id}")
            diagnostic = session.get("display_diagnostic")
            if not isinstance(diagnostic, dict):
                raise ValueError(
                    f"Display diagnostic not started for session: {session_id}"
                )
            self._ensure_display_test_entries(diagnostic)
            return diagnostic

    def update_display_progress(
        self,
        session_id: str,
        current_test_id: str,
    ) -> dict:
        if current_test_id not in DISPLAY_NAVIGATION_IDS:
            raise ValueError(f"Unknown display test: {current_test_id}")
        with self._display_lock:
            session, diagnostic = self._require_display_diagnostic(session_id)
            self._ensure_display_session_is_editable(session)
            if diagnostic.get("status") == "completed":
                raise ValueError("Completed display diagnostics are read-only.")
            diagnostic["current_test_id"] = current_test_id
            diagnostic["updated_at"] = datetime.now(UTC).isoformat()
            self._repository.save(session)
            return diagnostic

    def start_display_test(
        self,
        session_id: str,
        test_id: str,
        attempt_id: str,
    ) -> dict:
        if test_id not in DISPLAY_TEST_IDS:
            raise ValueError(f"Unknown display test: {test_id}")
        with self._display_lock:
            session, diagnostic = self._require_display_diagnostic(session_id)
            self._ensure_display_session_is_editable(session)
            if diagnostic.get("status") == "completed":
                raise ValueError("Completed display diagnostics are read-only.")

            self._ensure_display_test_entries(diagnostic)
            test = diagnostic["tests"][test_id]
            existing = next(
                (item for item in test["attempts"] if item["attempt_id"] == attempt_id),
                None,
            )
            if existing is not None:
                return {"diagnostic": diagnostic, "attempt": existing}

            started_at = datetime.now(UTC).isoformat()
            attempt = {
                "attempt_id": attempt_id,
                "attempt_number": len(test["attempts"]) + 1,
                "status": "in_progress",
                "started_at": started_at,
                "completed_at": None,
                "duration_seconds": None,
                "result": None,
            }
            test["attempts"].append(attempt)
            test["status"] = "in_progress"
            diagnostic["current_test_id"] = test_id
            diagnostic["updated_at"] = started_at
            self._refresh_report(session)
            self._repository.save(session)
            logger.info(
                "Display test started session_id=%s diagnostic_id=%s test_id=%s attempt=%s",
                session_id,
                diagnostic["diagnostic_id"],
                test_id,
                attempt["attempt_number"],
            )
            return {"diagnostic": diagnostic, "attempt": attempt}

    def record_display_test_result(
        self,
        session_id: str,
        test_id: str,
        attempt_id: str,
        status: str,
        notes: str,
        defects: list[dict],
    ) -> dict:
        if test_id not in DISPLAY_TEST_IDS:
            raise ValueError(f"Unknown display test: {test_id}")
        if status not in {"passed", "failed", "inconclusive", "skipped"}:
            raise ValueError(f"Invalid display test status: {status}")
        if status == "failed" and not defects:
            raise ValueError("A defect category is required for a failed display test.")
        if any(
            defect.get("type") == "OTHER" and not notes.strip()
            for defect in defects
        ):
            raise ValueError("Add a technician note when the defect category is Other.")

        with self._display_lock:
            session, diagnostic = self._require_display_diagnostic(session_id)
            self._ensure_display_session_is_editable(session)
            if diagnostic.get("status") == "completed":
                raise ValueError("Completed display diagnostics are read-only.")
            self._ensure_display_test_entries(diagnostic)
            test = diagnostic["tests"][test_id]
            attempt = next(
                (item for item in test["attempts"] if item["attempt_id"] == attempt_id),
                None,
            )
            if attempt is None:
                raise ValueError("Start this display test before recording a result.")
            if attempt.get("result") is not None:
                return {"diagnostic": diagnostic, "result": attempt["result"]}
            if attempt.get("status") != "in_progress":
                raise ValueError("This display test attempt is no longer active.")

            completed_at = datetime.now(UTC)
            started_at = datetime.fromisoformat(attempt["started_at"])
            duration_seconds = max(
                0,
                round((completed_at - started_at).total_seconds(), 3),
            )
            test_definition = next(item for item in DISPLAY_TESTS if item["id"] == test_id)
            result = {
                "test_id": test_id,
                "test_name": test_definition["name"],
                "attempt_id": attempt_id,
                "attempt_number": attempt["attempt_number"],
                "status": status,
                "notes": notes.strip(),
                "defects": defects,
                "started_at": attempt["started_at"],
                "completed_at": completed_at.isoformat(),
                "duration_seconds": duration_seconds,
            }
            attempt.update({
                "status": status,
                "completed_at": result["completed_at"],
                "duration_seconds": duration_seconds,
                "result": result,
            })
            test["status"] = status
            test["latest_result"] = result
            diagnostic["updated_at"] = result["completed_at"]

            record_status = {
                "passed": TestStatus.PASS,
                "failed": TestStatus.FAIL,
                "inconclusive": TestStatus.INCONCLUSIVE,
                "skipped": TestStatus.SKIPPED,
            }[status]
            technician_decision = {
                "passed": TechnicianDecision.WORKING,
                "failed": TechnicianDecision.NOT_WORKING,
                "inconclusive": TechnicianDecision.UNABLE_TO_VERIFY,
                "skipped": TechnicianDecision.UNABLE_TO_VERIFY,
            }[status]
            record = self._store_test_result(
                session,
                test_id=(
                    "display_information"
                    if test_id == "display_information"
                    else f"display_{test_id}"
                ),
                test_status=record_status,
                scan_status=ScanStatus.NOT_ATTEMPTED,
                detected_devices=[],
                technician_decision=technician_decision,
                technician_notes=result["notes"],
                evidence={
                    "test_name": test_definition["name"],
                    "display_test_id": test_id,
                    "attempt_id": attempt_id,
                    "attempt_number": attempt["attempt_number"],
                    "defects": defects,
                    "display_metadata": diagnostic["display_metadata"],
                },
            )
            record["run_id"] = attempt_id
            record["started_at"] = result["started_at"]
            record["completed_at"] = result["completed_at"]
            record["duration_seconds"] = duration_seconds

            self._refresh_report(session)
            self._repository.save(session)
            logger.info(
                "Display test result persisted session_id=%s diagnostic_id=%s test_id=%s status=%s attempt=%s",
                session_id,
                diagnostic["diagnostic_id"],
                test_id,
                status,
                attempt["attempt_number"],
            )
            return {"diagnostic": diagnostic, "result": result}

    def complete_display_diagnostic(self, session_id: str) -> dict:
        with self._display_lock:
            session, diagnostic = self._require_display_diagnostic(session_id)
            if diagnostic.get("status") == "completed":
                return diagnostic
            self._ensure_display_session_is_editable(session)

            self._ensure_display_test_entries(diagnostic)
            missing = [
                test["id"]
                for test in DISPLAY_TESTS
                if (
                    not diagnostic["tests"][test["id"]].get("latest_result")
                    or any(
                        attempt.get("status") == "in_progress"
                        for attempt in diagnostic["tests"][test["id"]]["attempts"]
                    )
                )
            ]
            if missing:
                raise ValueError(
                    "Complete or explicitly skip every required display test before finishing: "
                    + ", ".join(missing)
                )

            outcomes = [
                diagnostic["tests"][test["id"]]["latest_result"]["status"]
                for test in DISPLAY_TESTS
            ]
            status = (
                DiagnosticStatus.FAILED
                if "failed" in outcomes
                else DiagnosticStatus.PASSED
                if all(outcome == "passed" for outcome in outcomes)
                else DiagnosticStatus.INCONCLUSIVE
            )
            result = DiagnosticResult(
                diagnostic_id="display_diagnostic",
                diagnostic_type="display_diagnostic",
                device_id=session["device_id"],
                status=status,
                message=(
                    "Technician completed all required display checks."
                    if status == DiagnosticStatus.PASSED
                    else "Technician reported one or more display defects."
                    if status == DiagnosticStatus.FAILED
                    else "Display assessment includes skipped or inconclusive checks."
                ),
                details={
                    "display_diagnostic_id": diagnostic["diagnostic_id"],
                    "test_outcomes": outcomes,
                    "display_metadata": diagnostic["display_metadata"],
                    "tests": diagnostic["tests"],
                },
            )
            result.evaluation = DiagnosticEvaluator().evaluate(result)

            collection = session.get("diagnostic_results")
            if not isinstance(collection, DiagnosticResultCollection):
                raise TypeError("Session diagnostic results are not restored correctly")
            collection.add(result)
            session["diagnostic_summary"] = collection.summary()
            self._record_automated_result(session, result)

            completed_at = datetime.now(UTC).isoformat()
            diagnostic["status"] = "completed"
            diagnostic["overall_status"] = result.evaluation.status.value
            diagnostic["evaluation"] = result.evaluation
            diagnostic["completed_at"] = completed_at
            diagnostic["updated_at"] = completed_at
            self._refresh_report(session)
            self._repository.save(session)
            logger.info(
                "Display diagnostic completed session_id=%s diagnostic_id=%s status=%s",
                session_id,
                diagnostic["diagnostic_id"],
                diagnostic["overall_status"],
            )
            return diagnostic

    @staticmethod
    def _ensure_display_session_is_editable(session: dict) -> None:
        if str(session.get("status", "")).lower() in {"complete", "completed"}:
            raise ValueError("Completed QC sessions are read-only.")

    def _require_display_diagnostic(self, session_id: str) -> tuple[dict, dict]:
        session = self.get_session(session_id)
        if session is None:
            raise ValueError(f"Session not found: {session_id}")
        diagnostic = session.get("display_diagnostic")
        if not isinstance(diagnostic, dict):
            raise ValueError(
                f"Display diagnostic not started for session: {session_id}"
            )
        return session, diagnostic

    @staticmethod
    def _ensure_display_test_entries(diagnostic: dict) -> None:
        tests = diagnostic.setdefault("tests", {})
        for test in DISPLAY_TESTS:
            tests.setdefault(
                test["id"],
                {
                    "status": "not_started",
                    "attempts": [],
                    "latest_result": None,
                },
            )

    def save_cosmetic_inspection(
        self,
        session_id: str,
        phase: str,
        items: dict,
    ) -> dict:
        session = self.get_session(session_id)
        if session is None:
            raise ValueError(f"Session not found: {session_id}")
        if str(session.get("status", "")).lower() in {"complete", "completed"}:
            raise ValueError("Completed QC sessions are read-only.")
        inspections = session.setdefault("cosmetic_inspections", {})
        inspections[phase] = {
            "items": items,
            "updated_at": datetime.now(UTC).isoformat(),
        }
        self._refresh_report(session)
        self._repository.save(session)
        return session

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
        component_id: str | None = None,
    ):

        session = self.get_session(
            session_id
        )

        if session is None:
            raise ValueError(
                f"Session not found: {session_id}"
            )

        discovered = discovery_service.discover()
        self._sync_discovered_components(session, discovered.devices)

        device = (
            discovery_service.get_device(
                device_id
            )
        )

        if device is None:
            raise ValueError(
                f"Device not found: {device_id}"
            )

        resolved_component_id = component_id or component_for_device(
            session.get("components", []),
            device_id,
        )
        if component_id is not None:
            component = next(
                (
                    item
                    for item in session.get("components", [])
                    if item.get("component_id") == component_id
                    and item.get("asset_id") == session.get("asset_id")
                    and item.get("legacy_device_id") == device_id
                ),
                None,
            )
            if component is None:
                raise ValueError(
                    "Component not found for the requested QC session and device."
                )

        result = DiagnosticService().execute(
            diagnostic_type=diagnostic_type,
            device_id=device_id,
            parameters=parameters,
        )
        result.session_id = session.get("session_id")
        result.asset_id = session.get("asset_id")
        result.component_id = resolved_component_id
        result.evaluation = DiagnosticEvaluator().evaluate(result)

        collection = session[
            "diagnostic_results"
        ]

        collection.add(
            result
        )
        test_record = self._record_automated_result(session, result)

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
            "test_result": test_record,
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
        self._ensure_session_not_finalized(session)

        session["status"] = "checks_complete"
        self._refresh_report(session)
        self._repository.save(session)
        return session

    def finalize_session(self, session_id: str):
        session = self.get_session(session_id)
        if session is None:
            raise ValueError(f"Session not found: {session_id}")
        report_name = f"diagnostic_{session_id}"
        report_repository = create_report_repository()
        report = session.get("report")
        if report is None:
            self._refresh_report(session)
            report = session.get("report")
        if report is None:
            raise ValueError("A report must exist before the QC session is finalized.")
        disposition = session.get("technician_record", {}).get("final_disposition")
        if disposition not in {
            "Ready for resale",
            "Resale with disclosed issues",
            "Repair required",
            "Reject / parts only",
            "Inspection incomplete / retest required",
        }:
            raise ValueError("A valid technician disposition is required before completing QC.")
        technician_record = session.get("technician_record", {})
        intake_record = session.get("intake_record", {})
        finalized_by = (
            technician_record.get("qa_approver")
            or technician_record.get("technician")
            or intake_record.get("technician")
        )
        report_repository.finalize_revision(
            report_name,
            report.revision_id,
            finalized_by,
        )
        session["status"] = "completed"
        self._repository.save(session)
        return session

    def reopen_session_for_retest(self, session_id: str):
        session = self.get_session(session_id)
        if session is None:
            raise ValueError(f"Session not found: {session_id}")
        revisions = create_report_repository().list_revisions(
            f"diagnostic_{session_id}"
        )
        latest_revision = revisions[-1] if revisions else None
        if latest_revision and latest_revision.get("finalized_at") is not None:
            technician_record = session.get("technician_record", {})
            intake_record = session.get("intake_record", {})
            superseded_by = (
                technician_record.get("qa_approver")
                or technician_record.get("technician")
                or intake_record.get("technician")
                or "operator"
            )
            session["_report_supersession"] = {
                "revision_id": latest_revision["revision_id"],
                "reason": "QC session explicitly reopened for retest",
                "actor": superseded_by,
            }
        technician_record = session.setdefault("technician_record", {})
        technician_record["final_disposition"] = None
        technician_record["qa_approver"] = None
        technician_record["qa_approved_at"] = None
        technician_record["final_disposition_reason"] = None
        session["status"] = "checks_complete"
        self._refresh_report(session)
        self._repository.save(session)
        return session

    def record_manual_result(
        self,
        session_id: str,
        check_id: str,
        outcome: str | None = None,
        notes: str = "",
        scan_status: str = ScanStatus.NOT_ATTEMPTED,
        detected_devices: list | None = None,
        technician_decision: str | None = None,
        evidence: dict | None = None,
    ):
        session = self.get_session(session_id)
        if session is None:
            raise ValueError(
                f"Session not found: {session_id}"
            )
        self._ensure_session_not_finalized(session)
        if check_id not in MANUAL_CHECK_IDS:
            raise ValueError(
                f"Unknown manual check: {check_id}"
            )
        valid_outcomes = {
            "passed",
            "failed",
            "warning",
            "not_applicable",
            "blocked",
            "not_run",
        }
        decision_outcomes = {
            TechnicianDecision.WORKING: "passed",
            TechnicianDecision.NOT_WORKING: "failed",
            TechnicianDecision.UNABLE_TO_VERIFY: "blocked",
        }
        if technician_decision is not None:
            if technician_decision not in decision_outcomes:
                raise ValueError(
                    f"Invalid technician decision: {technician_decision}"
                )
            decided_outcome = decision_outcomes[technician_decision]
            if outcome is not None and outcome != decided_outcome:
                raise ValueError(
                    "Outcome conflicts with technician decision"
                )
            outcome = decided_outcome
        if outcome not in valid_outcomes:
            raise ValueError(
                f"Invalid manual outcome: {outcome}"
            )
        if outcome == "passed" and technician_decision is None:
            technician_decision = TechnicianDecision.WORKING
        elif outcome == "failed" and technician_decision is None:
            technician_decision = TechnicianDecision.NOT_WORKING
        elif outcome == "blocked" and technician_decision is None:
            technician_decision = TechnicianDecision.UNABLE_TO_VERIFY
        if scan_status not in {
            ScanStatus.SUCCESS,
            ScanStatus.NO_RESULTS,
            ScanStatus.UNSUPPORTED,
            ScanStatus.ERROR,
            ScanStatus.NOT_ATTEMPTED,
        }:
            raise ValueError(f"Invalid scan status: {scan_status}")

        check = next(item for item in MANUAL_CHECKS if item["id"] == check_id)
        test_status = {
            "passed": TestStatus.PASS,
            "failed": TestStatus.FAIL,
            "warning": TestStatus.WARNING,
            "not_applicable": TestStatus.NOT_APPLICABLE,
            "blocked": TestStatus.BLOCKED,
            "not_run": TestStatus.NOT_RUN,
        }[outcome]
        record = self._store_test_result(
            session,
            test_id=check_id,
            test_status=test_status,
            scan_status=scan_status,
            detected_devices=detected_devices or [],
            technician_decision=technician_decision,
            technician_notes=notes,
            evidence=evidence or {},
            name=check["name"],
        )

        manual_results = session.setdefault("manual_results", {})
        manual_results[check_id] = {
            **record.copy(),
            "check_id": check_id,
            "status": outcome,
            "notes": notes,
        }
        self._refresh_report(session)
        self._repository.save(session)
        return {
            "result": manual_results[check_id],
            "test_result": record,
        }

    def _store_test_result(
        self,
        session: dict,
        *,
        test_id: str,
        test_status: str,
        scan_status: str,
        detected_devices: list,
        technician_decision: str | None,
        technician_notes: str,
        evidence: dict,
        execution_status: str = "completed",
        name: str | None = None,
        run_id: str | None = None,
        component_id: str | None = None,
    ) -> dict:
        records = session.setdefault("test_results", {})
        previous = records.get(test_id)
        history = list(previous.get("retest_history", [])) if previous else []
        prior_run_id = previous.get("run_id") if previous else None
        if previous:
            history.append({
                key: value
                for key, value in previous.items()
                if key != "retest_history"
            })
        elif test_id in session.get("prior_test_results", {}):
            prior_attempt = dict(session["prior_test_results"][test_id])
            prior_run_id = prior_attempt.get("run_id")
            prior_attempt["source_session_id"] = session["intake_record"].get(
                "retest_of_session_id"
            )
            history.append(prior_attempt)
        record = TestResultRecord(
            test_id=test_id,
            test_status=test_status,
            run_id=run_id or str(uuid4()),
            session_id=session.get("session_id"),
            asset_id=session.get("asset_id"),
            component_id=component_id,
            parent_run_id=prior_run_id,
            scan_status=scan_status,
            detected_devices=detected_devices,
            technician_decision=technician_decision,
            technician_notes=technician_notes,
            evidence={
                **({"test_name": name} if name else {}),
                **evidence,
            },
            execution_status=execution_status,
            retest_history=history,
        ).to_dict()
        records[test_id] = record
        return record

    def _record_automated_result(
        self,
        session: dict,
        result,
    ) -> dict:
        session_asset_id = session.get("asset_id")
        session_id = session.get("session_id")
        if result.session_id not in (None, session_id):
            raise ValueError(
                "A diagnostic run cannot be assigned to a different QC session."
            )
        result.session_id = session_id
        if result.asset_id not in (None, session_asset_id):
            raise ValueError(
                "A diagnostic run cannot be assigned to an asset outside its QC session."
            )
        result.asset_id = session_asset_id
        if result.component_id is None and isinstance(result.device_id, str):
            result.component_id = component_for_device(
                session.get("components", []),
                result.device_id,
            )
        if result.component_id is not None and not any(
            item.get("component_id") == result.component_id
            and item.get("asset_id") == session_asset_id
            for item in session.get("components", [])
        ):
            raise ValueError(
                "A diagnostic run component must belong to its QC session asset."
            )
        if isinstance(result.details, dict) and not result.details.get("parent_run_id"):
            prior_runs = session.get("prior_diagnostic_runs", [])
            collection = session.get("diagnostic_results")
            current_runs = (
                getattr(collection, "results", [])
                if collection is not None
                else []
            )
            parent = next(
                (
                    item
                    for item in reversed(current_runs)
                    if item is not result
                    and getattr(item, "diagnostic_type", None) == result.diagnostic_type
                    and getattr(item, "device_id", None) == result.device_id
                    and isinstance(getattr(item, "run_id", None), str)
                ),
                None,
            )
            if parent is not None:
                result.details = {
                    **result.details,
                    "parent_run_id": parent.run_id,
                }
            if isinstance(prior_runs, list):
                parent = parent or next(
                    (
                        item
                        for item in reversed(prior_runs)
                        if isinstance(item, dict)
                        and item.get("diagnostic_type") == result.diagnostic_type
                        and item.get("device_id") == result.device_id
                        and isinstance(item.get("run_id"), str)
                    ),
                    None,
                )
                if parent is not None and not result.details.get("parent_run_id"):
                    result.details = {
                        **result.details,
                        "parent_run_id": parent["run_id"],
                    }
        diagnostic_status = (
            result.evaluation.status.value
            if result.evaluation is not None
            and hasattr(result.evaluation.status, "value")
            else (
                result.evaluation.status
                if result.evaluation is not None
                else (
                    result.status.value
                    if hasattr(result.status, "value")
                    else str(result.status)
                )
            )
        )
        test_status = {
            "passed": TestStatus.PASS,
            "failed": TestStatus.FAIL,
            "warning": TestStatus.WARNING,
            "error": TestStatus.ERROR,
            "unsupported": TestStatus.UNSUPPORTED,
            "not_applicable": TestStatus.NOT_APPLICABLE,
            "skipped": TestStatus.SKIPPED,
            "inconclusive": TestStatus.INCONCLUSIVE,
            "cancelled": TestStatus.CANCELLED,
            "pending": TestStatus.INCONCLUSIVE,
            "running": TestStatus.INCONCLUSIVE,
        }.get(diagnostic_status, TestStatus.INCONCLUSIVE)
        details = result.details or {}
        scan_status = details.get("scan_status")
        if scan_status not in {
            ScanStatus.SUCCESS,
            ScanStatus.NO_RESULTS,
            ScanStatus.UNSUPPORTED,
            ScanStatus.ERROR,
            ScanStatus.NOT_ATTEMPTED,
        }:
            scan_status = {
                "passed": ScanStatus.SUCCESS,
                "failed": ScanStatus.SUCCESS,
                "error": ScanStatus.ERROR,
                "unsupported": ScanStatus.UNSUPPORTED,
                "not_applicable": ScanStatus.NO_RESULTS,
            }.get(diagnostic_status, ScanStatus.NOT_ATTEMPTED)
        detected_devices = details.get("detected_devices")
        if detected_devices is None:
            for key in (
                "devices",
                "adapters",
                "cameras",
                "controllers",
                "connectors",
                "audio_devices",
                "keyboards",
            ):
                if details.get(key):
                    detected_devices = details[key]
                    break
        if detected_devices is None:
            detected_devices = []
        if not isinstance(detected_devices, list):
            detected_devices = [detected_devices]
        return self._store_test_result(
            session,
            test_id=result.diagnostic_type,
            test_status=test_status,
            scan_status=scan_status,
            detected_devices=detected_devices,
            technician_decision=None,
            technician_notes="",
            evidence={
                "message": result.message,
                "measurements": details,
                "evaluation": result.evaluation,
                "diagnostic_id": result.diagnostic_id,
                "observed_at": result.created_at.isoformat(),
            },
            run_id=result.run_id,
            component_id=result.component_id,
            execution_status=(
                "cancelled"
                if diagnostic_status == "cancelled"
                else "completed"
            ),
        )

    def _refresh_report(self, session: dict) -> None:
        self._ensure_session_not_finalized(session)
        context = WorkflowContext()
        context.set("device_id", session.get("device_id") or "system")

        collection = session.get("diagnostic_results")
        if collection is not None:
            for result in collection.results:
                context.set(f"{result.diagnostic_type}_result", result)

        report = ReportBuilder().build(context)
        self._set_report_identity(session, report)
        supersession = session.get("_report_supersession")
        if isinstance(supersession, dict):
            report.supersedes_revision_id = supersession.get("revision_id")
            report.supersession_reason = supersession.get("reason")
            report.superseded_by = supersession.get("actor")
        report.data["manual_checks"] = session.get("manual_results", {})
        report.data["cosmetic_inspections"] = session.get(
            "cosmetic_inspections",
            {},
        )
        report.data["test_results"] = session.get("test_results", {})
        report.data["technician_record"] = session.get(
            "technician_record",
            {},
        )
        report.data["intake_record"] = session.get("intake_record", {})
        report.data["device_inventory"] = session.get(
            "device_inventory",
            session.get("discovered_devices", []),
        )
        report.data["performance_results"] = session.get("performance_results", {})
        if session.get("display_diagnostic") is not None:
            report.data["display_diagnostic"] = session["display_diagnostic"]
        from app.core.config import get_settings

        if get_settings().STORAGE_BACKEND == "sqlite":
            from app.persistence.local.database import SQLiteDatabase

            report.data["evidence"] = SQLiteDatabase().list_evidence(
                session["session_id"]
            )
        else:
            report.data["evidence"] = []
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
            elif result["status"] == "warning":
                summary.warnings += 1
            elif result["status"] == "not_applicable":
                summary.not_applicable += 1
            elif result["status"] == "blocked":
                summary.blocked += 1
            elif result["status"] == "not_run":
                summary.not_run += 1
        report.status = self._session_result_status(session, report)
        session["report_status"] = report.status
        session["report"] = report
        create_report_repository().save(
            f"diagnostic_{session['session_id']}",
            report,
        )
        session.pop("_report_supersession", None)

    @staticmethod
    def _ensure_session_not_finalized(session: dict) -> None:
        if str(session.get("status", "")).lower() in {"complete", "completed"}:
            raise ValueError(
                "Finalized QC sessions are read-only; explicitly reopen for retest."
            )

    @staticmethod
    def _sync_discovered_components(session: dict, devices: list) -> None:
        asset_id = session.get("asset_id")
        if not isinstance(asset_id, str) or not asset_id:
            return
        asset_payload = session.get("asset")
        asset_payload = asset_payload if isinstance(asset_payload, dict) else {}
        asset = Asset(
            asset_id=asset_id,
            asset_tag=asset_payload.get("asset_tag"),
            manufacturer=asset_payload.get("manufacturer"),
            model=asset_payload.get("model"),
            serial_number=asset_payload.get("serial_number"),
        )
        for device in devices:
            if getattr(device, "device_type", None) == "system":
                properties = getattr(device, "properties", None)
                if isinstance(properties, dict):
                    asset.add_discovered_identity(properties)
        session["asset"] = asset.to_dict()

        discovered_components = components_from_discovery(asset_id, devices)
        existing = {
            item.get("component_id"): item
            for item in session.get("components", [])
            if isinstance(item, dict) and isinstance(item.get("component_id"), str)
        }
        for component in discovered_components:
            existing[component.component_id] = component.to_dict()
        session["components"] = list(existing.values())

    @staticmethod
    def _set_report_identity(session: dict, report) -> None:
        report_id = session.get("report_id")
        if not isinstance(report_id, str) or not report_id:
            previous_report = session.get("report")
            previous_id = (
                previous_report.get("report_id")
                if isinstance(previous_report, dict)
                else getattr(previous_report, "report_id", None)
            )
            report_id = (
                previous_id
                if isinstance(previous_id, str) and previous_id
                else str(uuid4())
            )
        session["report_id"] = report_id
        report.report_id = report_id
        report.revision_id = str(uuid4())
        report.session_id = session.get("session_id")
        report.asset_id = session.get("asset_id")

    def update_technician_record(
        self,
        session_id: str,
        record: dict,
    ):
        session = self.get_session(session_id)
        if session is None:
            raise ValueError(f"Session not found: {session_id}")
        self._ensure_session_not_finalized(session)

        technician_record = session.setdefault(
            "technician_record",
            {},
        )
        technician_record.update(record)
        if record.get("final_disposition"):
            technician_record["qa_approved_at"] = datetime.now(UTC).isoformat()
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
        if "blocked" in outcomes or "not_run" in outcomes:
            return "incomplete"
        if report is not None:
            intake = report.data.get("intake_record", {})
            planned_count = (
                len(intake.get("planned_diagnostics", []))
                + len(intake.get("planned_manual_checks", []))
                if isinstance(intake, dict)
                else 0
            )
            summary = report.data.get("diagnostic_summary")
            if planned_count and summary is not None and summary.total < planned_count:
                return "incomplete"
        if report is not None and report.status == "unsupported":
            return report.status
        if "warning" in outcomes:
            return "warning"
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
        self._ensure_session_not_finalized(session)

        discovered = discovery_service.discover()
        self._sync_discovered_components(session, discovered.devices)

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
            session["status"] = "checks_complete"
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
        for diagnostic_result in diagnostic_results.results:
            self._record_automated_result(session, diagnostic_result)

        report = ReportBuilder().build(
            context
        )
        self._set_report_identity(session, report)
        report.data["test_results"] = session.get("test_results", {})

        session["report"] = report

        report_name = (
            f"diagnostic_{session_id}"
        )

        create_report_repository().save(
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
        diagnostics: list[str] | None = None,
        parameters: dict[str, dict] | None = None,
    ):

        session = self.get_session(
            session_id
        )

        if session is None:
            raise ValueError(
                f"Session not found: {session_id}"
            )
        self._ensure_session_not_finalized(session)

        discovered = discovery_service.discover()
        self._sync_discovered_components(session, discovered.devices)

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

        collection = session.get(
            "diagnostic_results",
            DiagnosticResultCollection(),
        )
        if not isinstance(collection, DiagnosticResultCollection):
            raise TypeError("Session diagnostic results are not restored correctly")

        results = (
            profile_service.execute_profile(
                profile_name=profile_name,
                diagnostic_service=(
                    DiagnosticService()
                ),
                device_id=device_id,
                diagnostics=diagnostics,
                parameters=parameters,
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
            self._record_automated_result(session, result)

        session["device_id"] = (
            device_id
        )

        session[
            "diagnostic_summary"
        ] = collection.summary()
        self._refresh_report(session)

        self._repository.save(
            session
        )

        return {
            "session": session,
            "profile_name": profile_name,
            "diagnostic_results": collection,
            "executed_results": results,
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