from fastapi.testclient import TestClient

from app.main import app


def test_runtime_dependency_is_available():
    with TestClient(app) as client:
        response = client.get("/health/")

        assert response.status_code == 200

        runtime = app.state.runtime

        assert runtime.lifecycle_manager.get_status().value == "running"
