from fastapi.testclient import TestClient

from app.main import app


def test_create_diagnostic_session():

    with TestClient(app) as client:

        response = client.post(
            "/diagnostic-sessions/"
        )

        assert response.status_code == 200

        data = response.json()

        assert data["session_id"]
        assert data["status"] == "created"


def test_get_diagnostic_session():

    with TestClient(app) as client:

        create_response = client.post(
            "/diagnostic-sessions/"
        )

        session_id = (
            create_response.json()[
                "session_id"
            ]
        )

        response = client.get(
            f"/diagnostic-sessions/{session_id}"
        )

        assert response.status_code == 200

        data = response.json()

        assert (
            data["session_id"]
            == session_id
        )


def test_get_missing_diagnostic_session():

    with TestClient(app) as client:

        response = client.get(
            "/diagnostic-sessions/missing"
        )

        assert response.status_code == 404