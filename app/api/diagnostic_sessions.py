from uuid import uuid4

from fastapi import APIRouter
from pydantic import BaseModel

from app.hal.diagnostic_request import DiagnosticRequest
from app.hal.diagnostic_service import DiagnosticService

router = APIRouter(
    prefix="/diagnostic-sessions",
    tags=["diagnostic-sessions"],
)

service = DiagnosticService()


class DiagnosticSessionRequest(BaseModel):
    device_id: str
    diagnostics: list[str]


@router.post("/")
def create_session(
    request: DiagnosticSessionRequest,
):
    session_id = str(uuid4())

    results = []

    for diagnostic in request.diagnostics:

        result = service.execute(
            DiagnosticRequest(
                device_id=request.device_id,
                diagnostic_type=diagnostic,
            )
        )

        results.append(
            {
                "diagnostic_id": result.diagnostic_id,
                "diagnostic_type": result.diagnostic_type,
                "status": result.status,
                "message": result.message,
            }
        )

    return {
        "session_id": session_id,
        "device_id": request.device_id,
        "results": results,
    }

@router.post("/run")
def run_session(
    request: DiagnosticSessionRequest,
):
    session_id = str(uuid4())

    results = []

    total = len(request.diagnostics)

    for index, diagnostic in enumerate(
        request.diagnostics,
        start=1,
    ):
        result = service.execute(
            DiagnosticRequest(
                device_id=request.device_id,
                diagnostic_type=diagnostic,
            )
        )

        results.append(
            {
                "diagnostic_id": result.diagnostic_id,
                "diagnostic_type": result.diagnostic_type,
                "status": result.status,
                "message": result.message,
                "progress": int(
                    index / total * 100
                ),
            }
        )

    return {
        "session_id": session_id,
        "device_id": request.device_id,
        "results": results,
    }