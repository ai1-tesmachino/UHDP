from typing import Any

from app.persistence.session_serialization import (
    json_value as _json_value,
    restore_session as _restore_session,
)
from app.persistence.supabase_store import SupabaseRestStore
from app.services.session_repository import SessionRepository
from app.workflows.reporting.report_repository import ReportRepository


class SupabaseSessionRepository(SessionRepository):
    def __init__(self, store: SupabaseRestStore | None = None) -> None:
        self._store = store or SupabaseRestStore.from_settings()

    def save(self, session: dict) -> None:
        session_id = session.get("session_id")
        if not isinstance(session_id, str) or not session_id:
            raise ValueError("A session_id is required to persist a session.")
        self._store.upsert("session", session_id, _json_value(session))

    def get(self, session_id: str) -> dict | None:
        payload = self._store.get("session", session_id)
        return _restore_session(payload) if isinstance(payload, dict) else None

    def list_all(self) -> list[dict]:
        return [
            _restore_session(row["payload"])
            for row in self._store.list("session")
            if isinstance(row.get("payload"), dict)
        ]

    def delete(self, session_id: str) -> None:
        self._store.delete("session", session_id)


class SupabaseReportRepository(ReportRepository):
    def __init__(self, store: SupabaseRestStore | None = None) -> None:
        self._store = store or SupabaseRestStore.from_settings()

    def save(self, report_name: str, report: DiagnosticReport) -> None:
        self.save_json(report_name, report)
        self.save_html(report_name, report)

    def save_json(self, report_name: str, report: DiagnosticReport) -> None:
        self._store.upsert(
            "report_json",
            report_name,
            self._create_report_payload(report),
        )

    def save_html(self, report_name: str, report: DiagnosticReport) -> None:
        self._store.upsert("report_html", report_name, self._build_html(report))

    def get_json(self, report_name: str) -> dict | None:
        payload = self._store.get("report_json", report_name)
        return payload if isinstance(payload, dict) else None

    def get_html(self, report_name: str) -> str | None:
        payload = self._store.get("report_html", report_name)
        return payload if isinstance(payload, str) else None

    def list_reports(self) -> list[str]:
        return sorted(
            row["id"]
            for row in self._store.list("report_json")
            if isinstance(row.get("id"), str)
        )

    @staticmethod
    def _create_report_payload(report: DiagnosticReport) -> dict[str, Any]:
        return {
            "report_id": report.report_id,
            "revision_id": report.revision_id,
            "session_id": report.session_id,
            "asset_id": report.asset_id,
            "device_id": report.device_id,
            "status": report.status,
            "created_at": report.created_at.isoformat(),
            "data": _json_value(report.data),
        }

    @classmethod
    def _build_html(cls, report: DiagnosticReport) -> str:
        import json

        return f"""<!DOCTYPE html>
<html>
<head><meta charset="utf-8"><title>UHDP Diagnostic Report</title></head>
<body>
<h1>UHDP Diagnostic Report</h1>
<p><strong>Report ID:</strong> {report.report_id}</p>
<p><strong>Device ID:</strong> {report.device_id}</p>
<p><strong>Status:</strong> {report.status}</p>
<p><strong>Created:</strong> {report.created_at.isoformat()}</p>
<pre>{json.dumps(_json_value(report.data), indent=2, ensure_ascii=False)}</pre>
</body>
</html>"""


class SupabaseReportStorage:
    """Supabase storage adapter for the legacy /reports/export endpoints."""

    def __init__(self, store: SupabaseRestStore | None = None) -> None:
        self._store = store or SupabaseRestStore.from_settings()

    def save(self, report: Any) -> None:
        from app.reports.html_report_generator import HtmlReportGenerator
        from app.reports.json_report_generator import JsonReportGenerator

        session_id = report.session_id
        self._store.upsert(
            "legacy_report_json",
            session_id,
            JsonReportGenerator().generate(report),
        )
        self._store.upsert(
            "legacy_report_html",
            session_id,
            HtmlReportGenerator().generate(report),
        )

    def get_json(self, session_id: str) -> dict | None:
        payload = self._store.get("legacy_report_json", session_id)
        return payload if isinstance(payload, dict) else None

    def get_html(self, session_id: str) -> str | None:
        payload = self._store.get("legacy_report_html", session_id)
        return payload if isinstance(payload, str) else None

    def list_reports(self) -> list[str]:
        return sorted(
            row["id"]
            for row in self._store.list("legacy_report_json")
            if isinstance(row.get("id"), str)
        )
