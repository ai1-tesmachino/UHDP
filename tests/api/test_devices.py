from fastapi.testclient import TestClient

from app.main import app


def test_station_inventory_can_be_saved_and_loaded(monkeypatch):
    import app.api.devices as devices_api

    class FakeDatabase:
        payload = None

        def get_station_inventory(self, inventory_id):
            assert inventory_id == "local_station"
            return self.payload

        def save_station_inventory(self, inventory_id, payload):
            assert inventory_id == "local_station"
            self.payload = {**payload, "updated_at": "2026-01-01T00:00:00+00:00"}
            return self.payload

    database = FakeDatabase()
    monkeypatch.setattr(devices_api, "SQLiteDatabase", lambda: database)

    with TestClient(app) as client:
        saved = client.put(
            "/devices/inventory",
            json={
                "fields": {
                    "cpu.properties.vendor": {
                        "value": "Technician verified",
                        "source": "corrected",
                        "verified": True,
                    }
                },
                "notes": {"cpu": "Verified against device label"},
                "custom_components": [],
            },
        )
        loaded = client.get("/devices/inventory")

    assert saved.status_code == 200
    assert loaded.status_code == 200
    assert loaded.json()["fields"]["cpu.properties.vendor"]["verified"] is True
    assert loaded.json()["notes"]["cpu"] == "Verified against device label"


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
    assert "gpu" in device_types


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