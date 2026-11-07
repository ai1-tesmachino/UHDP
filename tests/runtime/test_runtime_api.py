from uuid import uuid4

from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.api.runtime import router
from app.main import app


def test_runtime_monitoring_endpoints():
    with TestClient(app) as client:
        status_response = client.get("/api/runtime/status")
        health_response = client.get("/api/runtime/health")
        jobs_response = client.get("/api/runtime/jobs")

        assert status_response.status_code == 200
        assert status_response.json()["status"] == "running"
        assert health_response.status_code == 200
        assert health_response.json()["scheduler_status"] == "running"
        assert jobs_response.status_code == 200
        assert jobs_response.json() == []

        missing_id = str(uuid4())
        assert client.get(f"/api/runtime/jobs/{missing_id}").status_code == 404
        assert client.post(
            f"/api/runtime/jobs/{missing_id}/cancel"
        ).status_code == 404


def test_runtime_api_returns_service_unavailable_without_lifespan_runtime():
    isolated_app = FastAPI()
    isolated_app.include_router(router)
    with TestClient(isolated_app) as client:
        response = client.get("/api/runtime/health")
    assert response.status_code == 503


def test_existing_websocket_path_uses_runtime_manager():
    with TestClient(app) as client:
        with client.websocket_connect("/ws"):
            assert app.state.runtime.websocket_manager.connection_count() == 1
        assert app.state.runtime.websocket_manager.connection_count() == 0
