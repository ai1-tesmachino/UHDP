from fastapi.testclient import TestClient

from app.main import app


def test_create_workflow():
    with TestClient(app) as client:
        response = client.post(
            "/workflows/",
            json={
                "name": "api_test",
                "actions": [
                    {
                        "type": "PrintAction",
                        "config": {
                            "message": "hello",
                        },
                    }
                ],
            },
        )

        assert response.status_code == 200


def test_list_workflows():
    with TestClient(app) as client:
        client.post(
            "/workflows/",
            json={
                "name": "list_test",
                "actions": [],
            },
        )

        response = client.get("/workflows/")

        assert response.status_code == 200
        assert "list_test" in response.json()["workflows"]


def test_get_workflow():
    with TestClient(app) as client:
        client.post(
            "/workflows/",
            json={
                "name": "get_test",
                "actions": [],
            },
        )

        response = client.get(
            "/workflows/get_test"
        )

        assert response.status_code == 200


def test_get_missing_workflow():
    with TestClient(app) as client:
        response = client.get(
            "/workflows/does_not_exist"
        )

        assert response.status_code == 404


def test_execute_workflow():
    with TestClient(app) as client:
        client.post(
            "/workflows/",
            json={
                "name": "execute_test",
                "actions": [],
            },
        )

        create_response = client.post(
            "/workflows/",
            json={
                "name": "execute_test",
                "actions": [],
            },
        )

        print(create_response.status_code)
        print(create_response.json())


        response = client.post(
            "/workflows/execute_test/execute"
        )

        assert response.status_code == 200


def test_execute_missing_workflow():
    with TestClient(app) as client:
        response = client.post(
            "/workflows/does_not_exist/execute"
        )

        assert response.status_code == 404


def test_delete_workflow():
    with TestClient(app) as client:
        client.post(
            "/workflows/",
            json={
                "name": "delete_test",
                "actions": [],
            },
        )

        response = client.delete(
            "/workflows/delete_test"
        )

        assert response.status_code == 200