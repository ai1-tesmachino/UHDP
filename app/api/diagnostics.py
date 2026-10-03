from fastapi import APIRouter
from pydantic import BaseModel

from app.hal.diagnostic_request import DiagnosticRequest
from app.hal.diagnostic_service import DiagnosticService

router = APIRouter(
    prefix="/diagnostics",
    tags=["diagnostics"],
)


service = DiagnosticService()


class ExecuteRequest(BaseModel):
    diagnostic_type: str
    device_id: str


@router.get("/")
def list_diagnostics():
    return service.registry.list_diagnostics()


@router.post("/execute")
def execute_diagnostic(
    request: ExecuteRequest,
):
    result = service.execute(
        DiagnosticRequest(
            diagnostic_type=request.diagnostic_type,
            device_id=request.device_id,
        )
    )

    return {
        "diagnostic_id": result.diagnostic_id,
        "device_id": result.device_id,
        "diagnostic_type": result.diagnostic_type,
        "status": result.status,
        "message": result.message,
    }