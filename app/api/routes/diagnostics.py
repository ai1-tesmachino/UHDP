from fastapi import APIRouter

from app.runtime.services.diagnostic_service import (
    DiagnosticService,
)

router = APIRouter(
    prefix="/diagnostics",
    tags=["diagnostics"],
)

service = DiagnosticService()


@router.get("/")
def list_diagnostics():
    return {
        "diagnostics": (
            service
            ._service
            .registry
            .list_diagnostics()
        )
    }


@router.post("/{diagnostic_type}")
def execute_diagnostic(
    diagnostic_type: str,
):
    result = service.execute(
        diagnostic_type,
    )

    return {
        "diagnostic_id": (
            result.diagnostic_id
        ),
        "diagnostic_type": (
            result.diagnostic_type
        ),
        "device_id": (
            result.device_id
        ),
        "status": (
            result.status.value
        ),
        "message": (
            result.message
        ),
        "details": (
            result.details
        ),
    }