from fastapi import APIRouter
from fastapi import HTTPException
from fastapi.responses import HTMLResponse

from app.services.report_service import ReportService

router = APIRouter(
    prefix="/reports/export",
    tags=["reports"],
)

_report_service = ReportService()


@router.get(
    "/{session_id}"
)
def get_report(
    session_id: str,
):

    report = _report_service.get_report_json(
        session_id
    )

    if report is None:
        raise HTTPException(
            status_code=404,
            detail="Report not found",
        )

    return report


@router.get(
    "/{session_id}/json"
)
def get_report_json(
    session_id: str,
):

    report = _report_service.get_report_json(
        session_id
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

    report = _report_service.get_report_html(
        session_id
    )

    if report is None:
        raise HTTPException(
            status_code=404,
            detail="Report not found",
        )

    return report