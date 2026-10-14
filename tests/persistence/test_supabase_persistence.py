import json
from datetime import UTC, datetime
from io import BytesIO
from types import SimpleNamespace
from urllib.error import HTTPError

import pytest

from app.hal.diagnostic_result import DiagnosticResult
from app.hal.diagnostic_evaluation import DiagnosticEvaluation
from app.hal.diagnostic_status import DiagnosticStatus
from app.hal.evaluation_status import EvaluationStatus
from app.hal.models.diagnostic_result_collection import DiagnosticResultCollection
from app.persistence.supabase_repositories import (
    SupabaseReportRepository,
    SupabaseReportStorage,
    SupabaseSessionRepository,
)
from app.persistence.supabase_store import SupabaseRestStore
from app.reports.report_models import DiagnosticReport as ExportDiagnosticReport
from app.workflows.reporting.diagnostic_report import DiagnosticReport


class MemoryStore:
    def __init__(self):
        self.records = {}

    def upsert(self, record_type, record_id, payload):
        self.records[(record_type, record_id)] = payload

    def get(self, record_type, record_id):
        return self.records.get((record_type, record_id))

    def list(self, record_type):
        return [
            {"id": record_id, "payload": payload}
            for (kind, record_id), payload in self.records.items()
            if kind == record_type
        ]

    def delete(self, record_type, record_id):
        self.records.pop((record_type, record_id), None)


def test_supabase_session_round_trip_restores_domain_types():
    store = MemoryStore()
    repository = SupabaseSessionRepository(store)
    created_at = datetime(2026, 1, 2, tzinfo=UTC)
    session = {
        "session_id": "session-1",
        "created_at": created_at,
        "diagnostic_results": DiagnosticResultCollection(results=[
            DiagnosticResult(
                diagnostic_id="cpu-1",
                diagnostic_type="cpu",
                device_id="cpu",
                status=DiagnosticStatus.PASSED,
                evaluation=DiagnosticEvaluation(
                    status=EvaluationStatus.PASSED,
                    recommendations=["Continue testing"],
                ),
                created_at=created_at,
            )
        ]),
    }

    repository.save(session)
    restored = repository.get("session-1")

    assert restored["created_at"] == created_at
    assert isinstance(restored["diagnostic_results"], DiagnosticResultCollection)
    assert restored["diagnostic_results"].results[0].status is DiagnosticStatus.PASSED
    assert restored["diagnostic_results"].results[0].created_at == created_at
    assert (
        restored["diagnostic_results"].results[0].evaluation.status
        is EvaluationStatus.PASSED
    )
    assert repository.list_all()[0]["session_id"] == "session-1"

    repository.delete("session-1")
    assert repository.get("session-1") is None


def test_supabase_report_repository_persists_json_html_and_lists():
    store = MemoryStore()
    repository = SupabaseReportRepository(store)
    report = DiagnosticReport(
        report_id="report-1",
        device_id="device-1",
        status="passed",
        data={"cpu": {"status": "passed"}},
    )

    repository.save("diagnostic_session-1", report)

    assert repository.get_json("diagnostic_session-1")["report_id"] == "report-1"
    assert "UHDP Diagnostic Report" in repository.get_html("diagnostic_session-1")
    assert repository.list_reports() == ["diagnostic_session-1"]


def test_supabase_legacy_report_storage_persists_generated_exports():
    store = MemoryStore()
    storage = SupabaseReportStorage(store)
    report = ExportDiagnosticReport(
        report_id="report-2",
        session_id="session-2",
        device_id="device-2",
    )

    storage.save(report)

    assert storage.get_json("session-2")["session_id"] == "session-2"
    assert "UHDP Diagnostic Report" in storage.get_html("session-2")
    assert storage.list_reports() == ["session-2"]


def test_supabase_store_uses_postgrest_service_auth_and_upsert(monkeypatch):
    captured = {}

    class Response:
        def __enter__(self):
            return self

        def __exit__(self, *args):
            return False

        def read(self):
            return b""

    def fake_urlopen(request, timeout):
        captured["request"] = request
        captured["timeout"] = timeout
        return Response()

    monkeypatch.setattr("app.persistence.supabase_store.urlopen", fake_urlopen)
    store = SupabaseRestStore(
        "https://project.supabase.co/",
        "server-secret",
    )
    store.upsert("session", "session-1", {"status": "created"})

    request = captured["request"]
    assert request.full_url == (
        "https://project.supabase.co/rest/v1/uhdp_records"
        "?on_conflict=record_type%2Cid"
    )
    assert request.get_method() == "POST"
    assert request.get_header("Authorization") == "Bearer server-secret"
    assert json.loads(request.data) == [{
        "record_type": "session",
        "id": "session-1",
        "payload": {"status": "created"},
    }]
    assert captured["timeout"] == 20


def test_supabase_store_surfaces_http_errors(monkeypatch):
    def fake_urlopen(*args, **kwargs):
        raise HTTPError(
            "https://project.supabase.co/rest/v1/uhdp_records",
            401,
            "Unauthorized",
            {},
            BytesIO(b'{"message":"invalid key"}'),
        )

    monkeypatch.setattr("app.persistence.supabase_store.urlopen", fake_urlopen)
    store = SupabaseRestStore("https://project.supabase.co", "secret")

    with pytest.raises(RuntimeError, match="HTTP 401"):
        store.get("session", "session-1")


def test_supabase_store_requires_backend_credentials(monkeypatch):
    monkeypatch.setattr(
        "app.persistence.supabase_store.get_settings",
        lambda: SimpleNamespace(
            SUPABASE_URL=None,
            SUPABASE_SERVICE_ROLE_KEY=None,
            SUPABASE_RECORDS_TABLE="uhdp_records",
        ),
    )

    with pytest.raises(RuntimeError, match="SUPABASE_URL"):
        SupabaseRestStore.from_settings()


def test_supabase_store_rejects_invalid_table_name():
    with pytest.raises(ValueError, match="simple table name"):
        SupabaseRestStore(
            "https://project.supabase.co",
            "secret",
            "uhdp_records?select=*",
        )
