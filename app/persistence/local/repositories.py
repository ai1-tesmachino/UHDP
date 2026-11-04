from __future__ import annotations

from typing import Any

from app.persistence.local.database import SQLiteDatabase
from app.persistence.local.report_files import LocalReportFiles
from app.workflows.reporting.diagnostic_report import DiagnosticReport
from app.workflows.reporting.report_repository import ReportRepository
from app.services.session_repository import SessionRepository


class SQLiteSessionRepository(SessionRepository):
    def __init__(self, database: SQLiteDatabase | None = None) -> None:
        self._database = database or SQLiteDatabase()

    def save(self, session: dict) -> None:
        session_id = session.get("session_id")
        if not isinstance(session_id, str) or not session_id:
            raise ValueError("A session_id is required to persist a session.")
        self._database.save_session(session_id, session)

    def get(self, session_id: str) -> dict | None:
        return self._database.get_session(session_id)

    def list_all(self) -> list[dict]:
        return self._database.list_sessions()

    def find_asset(self, asset_id: str) -> dict | None:
        return self._database.get_asset(asset_id)

    def delete(self, session_id: str) -> None:
        self._database.delete_session(session_id)


class SQLiteReportRepository(ReportRepository):
    def __init__(self, database: SQLiteDatabase | None = None) -> None:
        self._database = database or SQLiteDatabase()
        self._files = LocalReportFiles()

    def _save_files(self, report_name: str) -> None:
        revision = self._database.latest_report_revision(report_name)
        if revision is not None:
            number, payload, html = revision
            self._files.save_revision(report_name, number, payload, html)

    def save(self, report_name: str, report: DiagnosticReport) -> None:
        payload = {
            "report_id": report.report_id,
            "revision_id": report.revision_id,
            "supersedes_revision_id": report.supersedes_revision_id,
            "supersession_reason": report.supersession_reason,
            "superseded_by": report.superseded_by,
            "session_id": report.session_id,
            "asset_id": report.asset_id,
            "device_id": report.device_id,
            "status": report.status,
            "created_at": report.created_at.isoformat(),
            "data": report.data,
        }
        html = _workflow_report_html(report)
        self._database.save_report(report_name, payload, html)
        self._save_files(report_name)

    def save_json(self, report_name: str, report: DiagnosticReport) -> None:
        payload = {
            "report_id": report.report_id,
            "revision_id": report.revision_id,
            "supersedes_revision_id": report.supersedes_revision_id,
            "supersession_reason": report.supersession_reason,
            "superseded_by": report.superseded_by,
            "session_id": report.session_id,
            "asset_id": report.asset_id,
            "device_id": report.device_id,
            "status": report.status,
            "created_at": report.created_at.isoformat(),
            "data": report.data,
        }
        self._database.save_report(report_name, payload, None)
        self._save_files(report_name)

    def save_html(self, report_name: str, report: DiagnosticReport) -> None:
        payload = self._database.get_report_json(report_name) or {
            "report_id": report.report_id,
            "revision_id": report.revision_id,
            "supersedes_revision_id": report.supersedes_revision_id,
            "supersession_reason": report.supersession_reason,
            "superseded_by": report.superseded_by,
            "session_id": report.session_id,
            "asset_id": report.asset_id,
            "device_id": report.device_id,
            "status": report.status,
            "created_at": report.created_at.isoformat(),
            "data": report.data,
        }
        self._database.save_report(
            report_name, payload, _workflow_report_html(report)
        )
        self._save_files(report_name)

    def get_json(self, report_name: str) -> dict | None:
        return self._database.get_report_json(report_name)

    def get_html(self, report_name: str) -> str | None:
        return self._database.get_report_html(report_name)

    def list_reports(self) -> list[str]:
        return self._database.list_reports()

    def list_revisions(self, report_name: str) -> list[dict]:
        return self._database.list_report_revisions(report_name)

    def finalize_revision(
        self,
        report_name: str,
        revision_id: str,
        finalized_by: str | None = None,
    ) -> dict:
        return self._database.finalize_report(
            report_name,
            revision_id,
            finalized_by,
        )


class SQLiteReportStorage:
    """SQLite-backed adapter for the legacy report-export endpoints."""

    def __init__(self, database: SQLiteDatabase | None = None) -> None:
        self._database = database or SQLiteDatabase()
        self._files = LocalReportFiles()

    def save(self, report: Any) -> None:
        from app.persistence.session_serialization import json_value
        from app.reports.html_report_generator import HtmlReportGenerator
        from app.reports.json_report_generator import JsonReportGenerator

        payload = json_value(JsonReportGenerator().generate(report))
        html = HtmlReportGenerator().generate(report)
        self._database.save_report(report.session_id, payload, html)
        revision = self._database.latest_report_revision(report.session_id)
        if revision is not None:
            number, revision_payload, revision_html = revision
            self._files.save_revision(
                report.session_id,
                number,
                revision_payload,
                revision_html,
            )

    def get_json(self, session_id: str) -> dict | None:
        return self._database.get_report_json(session_id)

    def get_html(self, session_id: str) -> str | None:
        return self._database.get_report_html(session_id)

    def list_reports(self) -> list[str]:
        return self._database.list_reports()


def _workflow_report_html(report: DiagnosticReport) -> str:
    import html
    import json
    from app.persistence.session_serialization import json_value

    data = json.dumps(json_value(report.data), indent=2, ensure_ascii=False)
    return (
        "<!DOCTYPE html><html><head><meta charset=\"utf-8\">"
        "<title>UHDP Diagnostic Report</title></head><body>"
        "<h1>UHDP Diagnostic Report</h1>"
        f"<p><strong>Report ID:</strong> {html.escape(report.report_id)}</p>"
        f"<p><strong>Device ID:</strong> {html.escape(report.device_id)}</p>"
        f"<p><strong>Status:</strong> {html.escape(report.status)}</p>"
        f"<p><strong>Created:</strong> {html.escape(report.created_at.isoformat())}</p>"
        f"<pre>{html.escape(data)}</pre></body></html>"
    )
