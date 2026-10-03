from fastapi import APIRouter
from fastapi import HTTPException
from fastapi.responses import HTMLResponse

from app.services.file_session_repository import (
    FileSessionRepository,
)

from app.workflows.reporting.file_report_repository import (
    FileReportRepository,
)

router = APIRouter(
    prefix="/reports",
    tags=["reports"],
)

session_repository = (
    FileSessionRepository()
)

report_repository = (
    FileReportRepository()
)


@router.get("/")
def list_reports():

    sessions = (
        session_repository.list_all()
    )

    return [
        {
            "session_id": session["session_id"],
            "device_id": session["device_id"],
            "status": session["status"],
            "created_at": session["created_at"],
        }
        for session in sessions
    ]


@router.get("/{session_id}")
def get_report(
    session_id: str,
):

    session = (
        session_repository.get(
            session_id,
        )
    )

    if session is None:
        raise HTTPException(
            status_code=404,
            detail="Report not found",
        )

    return session.to_dict()


@router.get("/{session_id}/json")
def get_report_json(
    session_id: str,
):

    report_name = (
        f"diagnostic_{session_id}"
    )

    report = (
        report_repository.get_json(
            report_name
        )
    )

    if report is None:
        raise HTTPException(
            status_code=404,
            detail="Report not found",
        )

    return report


@router.get(
    "/{session_id}/html",
    response_class=HTMLResponse,
)
def get_report_html(
    session_id: str,
):

    report_name = (
        f"diagnostic_{session_id}"
    )

    report = (
        report_repository.get_html(
            report_name
        )
    )

    if report is None:
        raise HTTPException(
            status_code=404,
            detail="Report not found",
        )

    return report