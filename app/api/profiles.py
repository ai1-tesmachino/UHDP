from fastapi import APIRouter
from fastapi import HTTPException
from pydantic import BaseModel, Field

from app.persistence.session_serialization import json_value
from app.profiles.file_profile_repository import (
    FileProfileRepository,
)
from app.profiles.profile_service import (
    ProfileService,
)
from app.services.diagnostic_session_service import (
    diagnostic_session_service,
)

router = APIRouter(
    prefix="/profiles",
    tags=["profiles"],
)

_repository = (
    FileProfileRepository(
        "profiles"
    )
)

_service = ProfileService(
    _repository
)

class ExecuteProfileRequest(BaseModel):
    diagnostics: list[str] | None = Field(default=None, max_length=100)
    parameters: dict[str, dict] = Field(default_factory=dict)


@router.get("/")
def list_profiles():

    profiles = (
        _service.list_profiles()
    )

    return [
        {
            "name": profile.name,
            "description": profile.description,
            "diagnostics": profile.diagnostics,
        }
        for profile in profiles
    ]


@router.get("/{name}")
def get_profile(
    name: str,
):
    profile = (
        _service.get_profile(
            name
        )
    )

    if profile is None:
        raise HTTPException(
            status_code=404,
            detail="Profile not found",
        )

    return {
        "name": profile.name,
        "description": profile.description,
        "diagnostics": profile.diagnostics,
    }


@router.post("/{name}/execute")
def execute_profile(
    name: str,
    session_id: str,
    device_id: str,
    request: ExecuteProfileRequest | None = None,
):

    profile = (
        _service.get_profile(
            name
        )
    )

    if profile is None:
        raise HTTPException(
            status_code=404,
            detail="Profile not found",
        )

    try:
        result = diagnostic_session_service.execute_profile(
            session_id=session_id,
            profile_name=name,
            device_id=device_id,
            diagnostics=request.diagnostics if request else None,
            parameters=request.parameters if request else None,
        )
    except ValueError as exc:
        if str(exc).startswith("Session not found:"):
            raise HTTPException(status_code=404, detail=str(exc)) from exc
        if str(exc).startswith("Device not found:"):
            raise HTTPException(status_code=404, detail=str(exc)) from exc
        if str(exc).startswith("Profile not found:"):
            raise HTTPException(status_code=404, detail=str(exc)) from exc
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    return {
        "profile_name": name,
        "session_id": session_id,
        "device_id": device_id,
        "results": [
            {
                **json_value(item),
                "raw_status": item.status.value,
                "status": (
                    item.evaluation.status.value
                    if item.evaluation is not None
                    else item.status.value
                ),
                "execution_status": result["session"]["test_results"][
                    item.diagnostic_type
                ]["execution_status"],
            }
            for item in result["executed_results"]
        ],
        "summary": json_value(result["diagnostic_summary"]),
    }