from dataclasses import asdict
from typing import Any

from fastapi import APIRouter
from fastapi import HTTPException
from pydantic import BaseModel
from pydantic import Field
from typing import Literal

from app.services.diagnostic_session_service import (
    diagnostic_session_service,
)
from app.diagnostics.manual_checks import MANUAL_CHECKS


router = APIRouter(
    prefix="/diagnostic-sessions",
    tags=["diagnostic-sessions"],
)


class ExecuteSessionRequest(BaseModel):
    diagnostics: list[str] = Field(default_factory=list)


class DiagnosticExecutionRequest(BaseModel):
    parameters: dict[str, Any] = Field(default_factory=dict)


class ManualResultRequest(BaseModel):
    outcome: str
    notes: str = Field(default="", max_length=1000)


class CreateDiagnosticSessionRequest(BaseModel):
    device_id: str | None = None
    asset_tag: str | None = Field(default=None, max_length=100)
    technician: str | None = Field(default=None, max_length=150)
    customer_reference: str | None = Field(default=None, max_length=150)
    workflow_type: Literal[
        "service_center",
        "refurbishment",
        "manufacturing_qa",
        "rma_validation",
        "incoming_inspection",
        "outgoing_certification",
        "burn_in",
    ] = "service_center"


class TechnicianRecordRequest(BaseModel):
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


@router.post("/")
def create_diagnostic_session(
    request: CreateDiagnosticSessionRequest | None = None,
) -> dict[str, Any]:

    session = (
        diagnostic_session_service.create_session(
            request.device_id if request else None,
            request.model_dump(
                exclude={"device_id"},
                exclude_none=True,
            ) if request else None,
        )
    )

    return {
        "session_id": session["session_id"],
        "status": session["status"],
        "created_at": session["created_at"].isoformat(),
        "discovered_devices": session.get(
            "discovered_devices",
            [],
        ),
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
        "diagnostic_type": diagnostic_type,
        "diagnostic_id": diagnostic_result.diagnostic_id,
        "status": diagnostic_result.status.value,
        "message": diagnostic_result.message,
        "details": diagnostic_result.details,
        "evaluation": diagnostic_result.evaluation,
        "created_at": diagnostic_result.created_at,
        "summary": {
            "total": summary.total,
            "passed": summary.passed,
            "failed": summary.failed,
            "errors": summary.errors,
            "not_applicable": summary.not_applicable,
            "unsupported": summary.unsupported,
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
        )
    except ValueError as exc:
        status_code = 404 if str(exc).startswith("Session not found:") else 400
        raise HTTPException(status_code=status_code, detail=str(exc)) from exc

    return {"session_id": session_id, "result": result}


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
        "workflow_name": session["workflow_name"],
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
            "device_id": report.device_id,
            "status": report.status,
            "created_at": (
                report.created_at.isoformat()
            ),
            "data": {
                key: (
                    asdict(value)
                    if hasattr(
                        value,
                        "__dataclass_fields__",
                    )
                    else value
                )
                for key, value in report.data.items()
                if key != "diagnostic_summary"
            },
            "summary": (
                asdict(
                    report.data.get(
                        "diagnostic_summary"
                    )
                )
                if report.data.get(
                    "diagnostic_summary"
                ) is not None
                else None
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

        if hasattr(
            value,
            "__dataclass_fields__",
        ):
            response_data[key] = asdict(value)
        else:
            response_data[key] = value

    return {
        "report_id": report.report_id,
        "session_id": session_id,
        "device_id": report.device_id,
        "status": report.status,
        "created_at": (
            report.created_at.isoformat()
        ),
        "summary": (
            asdict(summary)
            if summary is not None
            else None
        ),
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