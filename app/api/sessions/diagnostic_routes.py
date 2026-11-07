import sqlite3
from typing import Any

from fastapi import APIRouter, HTTPException, Request
from fastapi import status
from pydantic import BaseModel, SecretStr
from pydantic import Field
from typing import Literal
from uuid import UUID

from app.core.config import get_settings
from app.core.local_reopen_auth import (
    load_local_supervisor_credential_hash,
    local_reopen_authorizer,
)
from app.persistence.local.database import SQLiteDatabase
from app.persistence.session_serialization import json_value
from app.services.diagnostic_session_service import (
    diagnostic_session_service,
)
from app.diagnostics.manual_checks import MANUAL_CHECKS

CosmeticArea = Literal["A", "B", "C", "D", "E"]


router = APIRouter(
    prefix="/diagnostic-sessions",
    tags=["diagnostic-sessions"],
)


class ExecuteSessionRequest(BaseModel):
    diagnostics: list[str] = Field(default_factory=list)


class DiagnosticExecutionRequest(BaseModel):
    parameters: dict[str, Any] = Field(default_factory=dict)
    component_id: str | None = Field(default=None, min_length=1, max_length=200)


class ManualResultRequest(BaseModel):
    outcome: str | None = None
    notes: str = Field(default="", max_length=1000)
    scan_status: Literal[
        "success",
        "no_results",
        "unsupported",
        "error",
        "not_attempted",
    ] = "not_attempted"
    detected_devices: list[Any] = Field(default_factory=list, max_length=100)
    technician_decision: Literal[
        "working",
        "not_working",
        "unable_to_verify",
    ] | None = None
    evidence: dict[str, Any] = Field(default_factory=dict)


class CosmeticInspectionItemRequest(BaseModel):
    name: str = Field(default="", max_length=150)
    areas: list[CosmeticArea] = Field(default_factory=list, max_length=2)
    condition: Literal[
        "Excellent",
        "Good",
        "Average",
        "Damaged",
        "Missing",
        "Not Applicable",
    ] | None = None
    severity: Literal["None", "Minor", "Moderate", "Severe"] | None = None
    damage_description: str = Field(default="", max_length=2000)
    damage_location: str = Field(default="", max_length=300)
    notes: str = Field(default="", max_length=2000)
    evidence_ids: list[str] = Field(default_factory=list, max_length=10)
    technician_confirmed: bool = False
    custom: bool = False
    model_dependent: bool = False


class CosmeticInspectionRequest(BaseModel):
    items: dict[str, CosmeticInspectionItemRequest] = Field(default_factory=dict)


class DisplayProgressRequest(BaseModel):
    current_test_id: str = Field(min_length=1, max_length=50)


class DisplayTestStartRequest(BaseModel):
    attempt_id: UUID


class DisplayDefectRequest(BaseModel):
    type: Literal[
        "DEAD_PIXEL",
        "STUCK_PIXEL",
        "COLOR_ABNORMALITY",
        "UNEVEN_BRIGHTNESS",
        "BACKLIGHT_BLEED",
        "FLICKERING",
        "DISPLAY_LINES",
        "DISTORTION",
        "OTHER",
    ]
    location: str = Field(default="", max_length=200)
    count: int | None = Field(default=None, ge=1, le=10000)


class DisplayTestResultRequest(BaseModel):
    attempt_id: UUID
    status: Literal["passed", "failed", "inconclusive", "skipped"]
    notes: str = Field(default="", max_length=2000)
    defects: list[DisplayDefectRequest] = Field(default_factory=list, max_length=20)


class CreateDiagnosticSessionRequest(BaseModel):
    session_id: UUID | None = None
    device_id: str | None = None
    asset_id: str | None = Field(default=None, min_length=1, max_length=200)
    create_asset: bool = False
    asset_tag: str | None = Field(default=None, max_length=100)
    technician: str | None = Field(default=None, max_length=150)
    station_id: str | None = Field(default=None, max_length=100)
    customer_reference: str | None = Field(default=None, max_length=150)
    profile_name: str | None = Field(default=None, max_length=100)
    retest_of_session_id: str | None = Field(default=None, max_length=100)
    planned_diagnostics: list[str] = Field(default_factory=list, max_length=100)
    planned_manual_checks: list[str] = Field(default_factory=list, max_length=100)
    workflow_type: Literal[
        "service_center",
        "refurbishment",
        "manufacturing_qa",
        "rma_validation",
        "incoming_inspection",
        "outgoing_certification",
        "burn_in",
    ] = "service_center"


class SessionIntakeRequest(BaseModel):
    device_id: str = Field(min_length=1, max_length=200)
    intake_record: dict[str, Any] = Field(default_factory=dict)
    device_inventory: list[dict[str, Any]] = Field(default_factory=list, max_length=300)


class TechnicianRecordRequest(BaseModel):
    fault_code: str | None = Field(default=None, max_length=100)
    observed_issue: str | None = Field(default=None, max_length=2000)
    repair_performed: str | None = Field(default=None, max_length=2000)
    replacement_performed: str | None = Field(default=None, max_length=2000)
    customer_notes: str | None = Field(default=None, max_length=2000)
    refurbishment_grade: Literal[
        "A",
        "B",
        "C",
        "needs_repair",
        "not_graded",
    ] | None = None
    final_disposition: Literal[
        "Ready for resale",
        "Resale with disclosed issues",
        "Repair required",
        "Reject / parts only",
        "Inspection incomplete / retest required",
    ] | None = None
    qa_approver: str | None = Field(default=None, max_length=150)
    final_disposition_reason: str | None = Field(default=None, max_length=2000)


class ReopenDiagnosticSessionRequest(BaseModel):
    actor_label: str | None = None
    credential: SecretStr | None = None


@router.post("/")
def create_diagnostic_session(
    request: CreateDiagnosticSessionRequest | None = None,
) -> dict[str, Any]:
    try:
        session = diagnostic_session_service.create_session(
            request.device_id if request else None,
            request.model_dump(
                exclude={"device_id", "session_id"},
                exclude_none=True,
                exclude_unset=True,
            ) if request else None,
            str(request.session_id) if request and request.session_id else None,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    return {
        "session_id": session["session_id"],
        "status": session["status"],
        "created_at": session["created_at"].isoformat(),
        "asset_id": session.get("asset_id"),
        "discovered_devices": session.get(
            "discovered_devices",
            [],
        ),
    }


@router.get("/")
def list_diagnostic_sessions() -> list[dict[str, Any]]:
    return [
        {
            "session_id": session["session_id"],
            "status": session["status"],
            "created_at": session["created_at"].isoformat(),
            "device_id": session.get("device_id"),
            "asset_id": session.get("asset_id"),
            "intake_record": session.get("intake_record", {}),
        }
        for session in diagnostic_session_service.list_sessions()
    ]


@router.delete("/{session_id}")
def delete_diagnostic_session(session_id: str) -> dict[str, Any]:
    if not diagnostic_session_service.delete_session(session_id):
        raise HTTPException(status_code=404, detail=f"Session not found: {session_id}")
    return {"session_id": session_id, "deleted": True}


@router.put("/{session_id}/intake")
def update_diagnostic_session_intake(
    session_id: str,
    request: SessionIntakeRequest,
) -> dict[str, Any]:
    try:
        session = diagnostic_session_service.update_session_intake(
            session_id=session_id,
            device_id=request.device_id,
            intake_record=request.intake_record,
            device_inventory=request.device_inventory,
        )
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return {
        "session_id": session["session_id"],
        "status": session["status"],
        "device_id": session["device_id"],
        "asset_id": session.get("asset_id"),
        "intake_record": session["intake_record"],
    }


@router.post(
    "/{session_id}/diagnostics/{device_id}/{diagnostic_type}"
)
def execute_diagnostic(
    session_id: str,
    device_id: str,
    diagnostic_type: str,
    request: DiagnosticExecutionRequest | None = None,
):

    try:

        result = (
            diagnostic_session_service.execute_diagnostic(
                session_id=session_id,
                device_id=device_id,
                diagnostic_type=diagnostic_type,
                parameters=request.parameters if request else None,
                component_id=request.component_id if request else None,
            )
        )

    except ValueError as exc:

        if str(exc).startswith(
            "Session not found:"
        ):
            raise HTTPException(
                status_code=404,
                detail=str(exc),
            ) from exc

        if str(exc).startswith(
            "Device not found:"
        ):
            raise HTTPException(
                status_code=404,
                detail=str(exc),
            ) from exc

        raise HTTPException(
            status_code=400,
            detail=str(exc),
        ) from exc

    diagnostic_result = result["result"]
    summary = result["summary"]

    return {
        "session_id": session_id,
        "device_id": device_id,
        "session_id": session_id,
        "asset_id": diagnostic_result.asset_id,
        "component_id": diagnostic_result.component_id,
        "diagnostic_type": diagnostic_type,
        "diagnostic_id": diagnostic_result.diagnostic_id,
        "run_id": diagnostic_result.run_id,
        "status": (
            diagnostic_result.evaluation.status.value
            if diagnostic_result.evaluation is not None
            else diagnostic_result.status.value
        ),
        "raw_status": diagnostic_result.status.value,
        "execution_status": result["test_result"]["execution_status"],
        "message": diagnostic_result.message,
        "details": diagnostic_result.details,
        "evaluation": diagnostic_result.evaluation,
        "created_at": diagnostic_result.created_at,
        "test_result": result["test_result"],
        "summary": {
            "total": summary.total,
            "passed": summary.passed,
            "failed": summary.failed,
            "warnings": summary.warnings,
            "errors": summary.errors,
            "not_applicable": summary.not_applicable,
            "unsupported": summary.unsupported,
            "blocked": summary.blocked,
            "not_run": summary.not_run,
            "inconclusive": summary.inconclusive,
            "cancelled": summary.cancelled,
        },
    }

@router.get("/manual-checks")
def list_manual_checks() -> dict[str, Any]:
    return {"manual_checks": MANUAL_CHECKS}


@router.post("/{session_id}/manual/{check_id}")
def record_manual_result(
    session_id: str,
    check_id: str,
    request: ManualResultRequest,
) -> dict[str, Any]:
    try:
        result = diagnostic_session_service.record_manual_result(
            session_id=session_id,
            check_id=check_id,
            outcome=request.outcome,
            notes=request.notes,
            scan_status=request.scan_status,
            detected_devices=request.detected_devices,
            technician_decision=request.technician_decision,
            evidence=request.evidence,
        )
    except ValueError as exc:
        status_code = 404 if str(exc).startswith("Session not found:") else 400
        raise HTTPException(status_code=status_code, detail=str(exc)) from exc

    return {
        "session_id": session_id,
        "result": result["result"],
        "test_result": result["test_result"],
    }


def _display_http_error(exc: ValueError) -> HTTPException:
    message = str(exc)
    if "Session not found:" in message or "Display diagnostic not started" in message:
        status_code = 404
    elif "read-only" in message or "must be associated" in message:
        status_code = 409
    elif "Complete or explicitly skip" in message:
        status_code = 409
    else:
        status_code = 422
    return HTTPException(status_code=status_code, detail=message)


@router.post("/{session_id}/display/start")
def start_display_diagnostic(session_id: str) -> dict[str, Any]:
    try:
        return diagnostic_session_service.start_display_diagnostic(session_id)
    except ValueError as exc:
        raise _display_http_error(exc) from exc


@router.get("/{session_id}/display")
def get_display_diagnostic(session_id: str) -> dict[str, Any]:
    try:
        return diagnostic_session_service.get_display_diagnostic(session_id)
    except ValueError as exc:
        raise _display_http_error(exc) from exc


@router.put("/{session_id}/display/progress")
def update_display_progress(
    session_id: str,
    request: DisplayProgressRequest,
) -> dict[str, Any]:
    try:
        return diagnostic_session_service.update_display_progress(
            session_id,
            request.current_test_id,
        )
    except ValueError as exc:
        raise _display_http_error(exc) from exc


@router.post("/{session_id}/display/tests/{test_id}/start")
def start_display_test(
    session_id: str,
    test_id: str,
    request: DisplayTestStartRequest,
) -> dict[str, Any]:
    try:
        return diagnostic_session_service.start_display_test(
            session_id,
            test_id,
            str(request.attempt_id),
        )
    except ValueError as exc:
        raise _display_http_error(exc) from exc


@router.post("/{session_id}/display/tests/{test_id}/result")
def record_display_test_result(
    session_id: str,
    test_id: str,
    request: DisplayTestResultRequest,
) -> dict[str, Any]:
    try:
        return diagnostic_session_service.record_display_test_result(
            session_id=session_id,
            test_id=test_id,
            attempt_id=str(request.attempt_id),
            status=request.status,
            notes=request.notes,
            defects=[item.model_dump() for item in request.defects],
        )
    except ValueError as exc:
        raise _display_http_error(exc) from exc


@router.post("/{session_id}/display/complete")
def complete_display_diagnostic(session_id: str) -> dict[str, Any]:
    try:
        return diagnostic_session_service.complete_display_diagnostic(session_id)
    except ValueError as exc:
        raise _display_http_error(exc) from exc


@router.post("/{session_id}/complete")
def complete_diagnostic_session(
    session_id: str,
) -> dict[str, Any]:
    try:
        session = diagnostic_session_service.complete_session(
            session_id
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=404,
            detail=str(exc),
        ) from exc

    return {
        "session_id": session_id,
        "status": session["status"],
    }


@router.post("/{session_id}/finalize")
def finalize_diagnostic_session(
    session_id: str,
) -> dict[str, Any]:
    try:
        session = diagnostic_session_service.finalize_session(session_id)
    except ValueError as exc:
        status_code = 400 if "disposition" in str(exc).lower() else 404
        raise HTTPException(status_code=status_code, detail=str(exc)) from exc
    return {
        "session_id": session_id,
        "status": session["status"],
    }


@router.post("/{session_id}/reopen")
def reopen_diagnostic_session(
    session_id: str,
    request: Request,
    body: ReopenDiagnosticSessionRequest,
) -> dict[str, Any]:
    actor_label = body.actor_label.strip() if body.actor_label else ""
    if not actor_label or len(actor_label) > 150:
        _record_reopen_audit(
            session_id,
            actor_label or None,
            authorization_basis=None,
            outcome="denied",
            reason="invalid_actor_label",
        )
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="A non-empty actor label of at most 150 characters is required.",
        )
    credential = (
        body.credential.get_secret_value()
        if body.credential is not None
        else None
    )
    peer_address = request.client.host if request.client is not None else None
    authorization = local_reopen_authorizer.authorize(
        peer_address,
        credential,
        load_local_supervisor_credential_hash(get_settings()),
    )
    if authorization != "authorized":
        _record_reopen_audit(
            session_id,
            actor_label,
            authorization_basis=None,
            outcome="denied",
            reason=authorization,
        )
        responses = {
            "remote_request": (
                status.HTTP_403_FORBIDDEN,
                "Session reopening is restricted to local requests.",
            ),
            "credential_not_configured": (
                status.HTTP_503_SERVICE_UNAVAILABLE,
                "Local supervisor authorization is not configured.",
            ),
            "credential_configuration_invalid": (
                status.HTTP_503_SERVICE_UNAVAILABLE,
                "Local supervisor authorization is unavailable.",
            ),
            "throttled": (
                status.HTTP_429_TOO_MANY_REQUESTS,
                "Too many failed local supervisor credential attempts.",
            ),
            "invalid_credential": (
                status.HTTP_401_UNAUTHORIZED,
                "The local supervisor credential is invalid.",
            ),
        }
        code, detail = responses[authorization]
        raise HTTPException(status_code=code, detail=detail)

    _record_reopen_audit(
        session_id,
        actor_label,
        authorization_basis="local_supervisor_credential",
        outcome="authorized",
    )
    try:
        session = diagnostic_session_service.reopen_session_for_retest(
            session_id,
            actor_label=actor_label,
            authorization_basis="local_supervisor_credential",
        )
    except ValueError as exc:
        _record_reopen_audit(
            session_id,
            actor_label,
            authorization_basis="local_supervisor_credential",
            outcome="failed",
            reason="session_reopen_failed",
        )
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except Exception:
        _record_reopen_audit(
            session_id,
            actor_label,
            authorization_basis="local_supervisor_credential",
            outcome="failed",
            reason="session_reopen_failed",
        )
        raise
    _record_reopen_audit(
        session_id,
        actor_label,
        authorization_basis="local_supervisor_credential",
        outcome="succeeded",
    )
    return {
        "session_id": session_id,
        "status": session["status"],
    }


def _record_reopen_audit(
    session_id: str,
    actor_label: str | None,
    *,
    authorization_basis: str | None,
    outcome: str,
    reason: str | None = None,
) -> None:
    payload: dict[str, Any] = {
        "action": "reopen",
        "outcome": outcome,
        "authorization_basis": authorization_basis,
    }
    if reason is not None:
        payload["reason"] = reason
    try:
        SQLiteDatabase.open_existing().record_audit_event(
            "qc_session",
            session_id,
            "session_reopen",
            {"actor_label": actor_label},
            payload,
        )
    except (OSError, sqlite3.Error, ValueError) as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Local audit persistence is unavailable.",
        ) from exc


@router.get("/{session_id}")
def get_diagnostic_session(
    session_id: str,
) -> dict[str, Any]:

    session = (
        diagnostic_session_service.get_session(
            session_id
        )
    )

    if session is None:
        raise HTTPException(
            status_code=404,
            detail=f"Session not found: {session_id}",
        )

    return {
        "session_id": session["session_id"],
        "status": session["status"],
        "created_at": (
            session["created_at"].isoformat()
        ),
        "device_id": session["device_id"],
        "asset_id": session.get("asset_id"),
        "report_id": session.get("report_id"),
        "components": session.get("components", []),
        "workflow_name": session["workflow_name"],
        "intake_record": session.get("intake_record", {}),
        "device_inventory": session.get("device_inventory", []),
        "technician_record": session.get("technician_record", {}),
        "manual_results": session.get("manual_results", {}),
        "cosmetic_inspections": session.get("cosmetic_inspections", {}),
        "performance_results": session.get("performance_results", {}),
        "display_diagnostic": session.get("display_diagnostic"),
        "test_results": session.get("test_results", {}),
    }


@router.put("/{session_id}/cosmetic-inspection/{phase}")
def save_cosmetic_inspection(
    session_id: str,
    phase: Literal["initial", "final"],
    request: CosmeticInspectionRequest,
) -> dict[str, Any]:
    if len(request.items) > 40:
        raise HTTPException(
            status_code=400,
            detail="A cosmetic inspection can contain at most 40 items.",
        )
    try:
        session = diagnostic_session_service.save_cosmetic_inspection(
            session_id,
            phase,
            {key: item.model_dump() for key, item in request.items.items()},
        )
    except ValueError as exc:
        status_code = 400 if str(exc).startswith("Completed QC sessions") else 404
        raise HTTPException(status_code=status_code, detail=str(exc)) from exc
    return {
        "session_id": session_id,
        "phase": phase,
        "inspection": session["cosmetic_inspections"][phase],
    }


@router.post("/{session_id}/execute")
def execute_diagnostic_session(
    session_id: str,
    device_id: str,
    request: ExecuteSessionRequest | None = None,
) -> dict[str, Any]:

    session = (
        diagnostic_session_service.get_session(
            session_id
        )
    )

    if session is None:
        raise HTTPException(
            status_code=404,
            detail=f"Session not found: {session_id}",
        )

    diagnostics = (
        request.diagnostics
        if request is not None
        and request.diagnostics
        else [
            "cpu",
            "memory",
            "storage",
            "network",
        ]
    )

    session["selected_diagnostics"] = diagnostics

    from app.workflows.templates.full_system_validation_workflow import (
        create_full_system_validation_workflow,
    )

    try:
        workflow = (
            create_full_system_validation_workflow(
                selected_diagnostics=diagnostics
            )
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=400,
            detail=str(exc),
        ) from exc

    try:

        result = (
            diagnostic_session_service.execute_workflow(
                session_id=session_id,
                workflow=workflow,
                device_id=device_id,
            )
        )

    except ValueError as exc:

        if str(exc).startswith(
            "Device not found:"
        ):
            raise HTTPException(
                status_code=404,
                detail=str(exc),
            ) from exc

        raise HTTPException(
            status_code=400,
            detail=str(exc),
        ) from exc

    workflow_result = result[
        "workflow_result"
    ]

    report = result["report"]

    summary = result[
        "diagnostic_summary"
    ]

    return {
        "session_id": session_id,
        "device_id": device_id,
        "asset_id": result["session"].get("asset_id"),
        "status": result[
            "session"
        ]["status"],
        "workflow_status": (
            workflow_result.status.value
            if hasattr(
                workflow_result.status,
                "value",
            )
            else str(
                workflow_result.status
            )
        ),
        "selected_diagnostics": diagnostics,
        "report": {
            "report_id": report.report_id,
            "revision_id": report.revision_id,
            "session_id": report.session_id,
            "asset_id": report.asset_id,
            "device_id": report.device_id,
            "status": report.status,
            "created_at": (
                report.created_at.isoformat()
            ),
            "data": {
                key: json_value(value)
                for key, value in report.data.items()
                if key != "diagnostic_summary"
            },
            "summary": json_value(
                report.data.get("diagnostic_summary")
            ),
        },
    }

@router.get("/{session_id}/report")
def get_diagnostic_session_report(
    session_id: str,
) -> dict[str, Any]:

    session = (
        diagnostic_session_service.get_session(
            session_id
        )
    )

    if session is None:
        raise HTTPException(
            status_code=404,
            detail=f"Session not found: {session_id}",
        )

    report = session.get("report")

    if report is None:
        raise HTTPException(
            status_code=404,
            detail=(
                f"Report not available for session: "
                f"{session_id}"
            ),
        )

    summary = report.data.get(
        "diagnostic_summary"
    )

    response_data = {}

    for key, value in report.data.items():

        if key == "diagnostic_summary":
            continue

        response_data[key] = json_value(value)

    return {
        "report_id": report.report_id,
        "revision_id": report.revision_id,
        "session_id": session_id,
        "asset_id": report.asset_id,
        "device_id": report.device_id,
        "status": report.status,
        "created_at": (
            report.created_at.isoformat()
        ),
        "summary": json_value(summary),
        "data": response_data,
    }


@router.put("/{session_id}/technician-record")
def update_technician_record(
    session_id: str,
    request: TechnicianRecordRequest,
) -> dict[str, Any]:
    try:
        record = diagnostic_session_service.update_technician_record(
            session_id,
            request.model_dump(exclude_unset=True),
        )
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc

    return {"session_id": session_id, "technician_record": record}