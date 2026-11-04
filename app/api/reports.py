from typing import Any

from fastapi import APIRouter
from fastapi import HTTPException
from fastapi.responses import HTMLResponse

from app.persistence.repository_factory import (
    create_report_repository,
    create_session_repository,
)

router = APIRouter(
    prefix="/reports",
    tags=["reports"],
)

session_repository = create_session_repository()
report_repository = create_report_repository()


@router.get("/")
def list_reports():

    sessions = (
        session_repository.list_all()
    )

    results = []
    for session in sessions:
        intake = session.get("intake_record")
        status = session.get("report_status")
        if not status:
            report = report_repository.get_json(
                f"diagnostic_{session['session_id']}"
            )
            if isinstance(report, dict):
                status = report.get("status")
        results.append({
            "session_id": session["session_id"],
            "device_id": session["device_id"],
            "asset_id": session.get("asset_id"),
            "report_id": session.get("report_id"),
            "status": status or session["status"],
            "created_at": session["created_at"],
            "station_id": intake.get("station_id") if isinstance(intake, dict) else None,
            "retest_of_session_id": (
                intake.get("retest_of_session_id") if isinstance(intake, dict) else None
            ),
        })
    return results


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

    return session


@router.get("/{session_id}/json")
def get_report_json(
    session_id: str,
):
    if session_repository.get(session_id) is None:
        raise HTTPException(
            status_code=404,
            detail="Report not found",
        )

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


@router.get("/{session_id}/revisions")
def get_report_revisions(session_id: str) -> list[dict[str, Any]]:
    if session_repository.get(session_id) is None:
        raise HTTPException(status_code=404, detail="Report not found")
    revisions = report_repository.list_revisions(
        f"diagnostic_{session_id}"
    )
    if not revisions:
        raise HTTPException(status_code=404, detail="Report revisions not found")
    return revisions


@router.get(
    "/{session_id}/html",
    response_class=HTMLResponse,
)
def get_report_html(
    session_id: str,
):
    if session_repository.get(session_id) is None:
        raise HTTPException(
            status_code=404,
            detail="Report not found",
        )

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