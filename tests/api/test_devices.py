from fastapi.testclient import TestClient

from app.main import app


def test_get_devices():

    with TestClient(app) as client:

        response = client.get(
            "/devices/",
        )

    assert response.status_code == 200

    devices = response.json()

    assert isinstance(devices, list)
    assert len(devices) >= 3

    device_types = {
        device["device_type"]
        for device in devices
    }

    assert "cpu" in device_types
    assert "memory" in device_types
    assert "storage" in device_types


def test_get_device():

    with TestClient(app) as client:

        response = client.get(
            "/devices/",
        )

        assert response.status_code == 200

        devices = response.json()

        device_id = devices[0]["device_id"]

        response = client.get(
            f"/devices/{device_id}",
        )

    assert response.status_code == 200

    device = response.json()

    assert device["device_id"] == device_id
    assert device["device_type"]
    assert device["name"]
    assert isinstance(
        device["properties"],
        dict,
    )


def test_get_unknown_device():

    with TestClient(app) as client:

        response = client.get(
            "/devices/does-not-exist",
        )

    assert response.status_code == 404