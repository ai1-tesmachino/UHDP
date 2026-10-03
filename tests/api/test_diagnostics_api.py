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

    assert "cpu" in body["diagnostics"]
    assert "memory" in body["diagnostics"]
    assert "storage" in body["diagnostics"]


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
        body["diagnostic_type"]
        == "cpu"
    )

    assert (
        body["status"]
        == "passed"
    )

    assert "diagnostic_id" in body
    assert "device_id" in body
    assert "message" in body


def test_execute_memory():
    client = TestClient(app)

    response = client.post(
        "/diagnostics/memory"
    )

    assert (
        response.status_code
        == 200
    )

    body = response.json()

    assert (
        body["diagnostic_type"]
        == "memory"
    )

    assert (
        body["status"]
        == "passed"
    )


def test_execute_storage():
    client = TestClient(app)

    response = client.post(
        "/diagnostics/storage"
    )

    assert (
        response.status_code
        == 200
    )

    body = response.json()

    assert (
        body["diagnostic_type"]
        == "storage"
    )

    assert (
        body["status"]
        == "passed"
    )


def test_execute_unknown_diagnostic():
    client = TestClient(app)

    response = client.post(
        "/diagnostics/unknown"
    )

    assert (
        response.status_code
        == 200
    )

    body = response.json()

    assert (
        body["status"]
        == "error"
    )