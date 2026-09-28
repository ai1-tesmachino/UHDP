from fastapi.testclient import (
    TestClient,
)

from app.main import app


def test_list_diagnostics():
    client = TestClient(app)

    response = client.get(
        "/diagnostics/"
    )

    assert (
        response.status_code
        == 200
    )

    body = response.json()

    assert (
        "diagnostics"
        in body
    )


def test_execute_cpu():
    client = TestClient(app)

    response = client.post(
        "/diagnostics/cpu"
    )

    assert (
        response.status_code
        == 200
    )

    body = response.json()

    assert (
        body["status"]
        == "passed"
    )