from fastapi.testclient import TestClient

from app.main import app


def test_diagnostic_session_end_to_end():

    with TestClient(app) as client:

        create_response = client.post(
            "/diagnostic-sessions/"
        )

        assert create_response.status_code == 200

        session_id = (
            create_response.json()[
                "session_id"
            ]
        )

        execute_response = client.post(
            f"/diagnostic-sessions/"
            f"{session_id}/execute",
            params={
                "device_id": "api-test-device"
            },
        )

        assert execute_response.status_code == 200

        data = execute_response.json()

        assert (
            data["session_id"]
            == session_id
        )

        assert data["workflow_status"] in {
            "success",
            "failed",
            "stopped",
        }

        assert data["report"] is not None

        assert data["report"]["report_id"]

        assert (
            data["report"]["device_id"]
            == "api-test-device"
        )