from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.api import reports as reports_api
from app.main import app


client = TestClient(app)


def test_list_reports_endpoint():

    response = client.get(
        "/reports/"
    )

    assert response.status_code == 200


def test_report_not_found():

    response = client.get(
        "/reports/does-not-exist"
    )

    assert response.status_code == 404


def test_report_revision_history_route_exposes_all_revisions(monkeypatch):
    class SessionRepository:
        def get(self, session_id):
            return {"session_id": session_id}

    class ReportRepository:
        def list_revisions(self, report_name):
            assert report_name == "diagnostic_session-1"
            return [
                {"report_id": "report-1", "revision_id": "rev-1"},
                {"report_id": "report-1", "revision_id": "rev-2"},
            ]

    monkeypatch.setattr(reports_api, "session_repository", SessionRepository())
    monkeypatch.setattr(reports_api, "report_repository", ReportRepository())
    api = FastAPI()
    api.include_router(reports_api.router)

    response = TestClient(api).get("/reports/session-1/revisions")

    assert response.status_code == 200
    assert [item["revision_id"] for item in response.json()] == ["rev-1", "rev-2"]