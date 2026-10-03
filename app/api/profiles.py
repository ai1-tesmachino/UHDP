from fastapi import APIRouter
from fastapi import HTTPException

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

    result = (
        diagnostic_session_service
        .execute_profile(
            session_id=session_id,
            profile_name=name,
            device_id=device_id,
        )
    )

    return {
        "profile_name": name,
        "summary": result[
            "diagnostic_summary"
        ],
    }