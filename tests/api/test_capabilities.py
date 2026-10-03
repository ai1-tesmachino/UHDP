from fastapi.testclient import TestClient

from app.main import app


def test_capability_api_lists_technician_hardware_areas_and_optional_engines():
    with TestClient(app) as client:
        response = client.get("/capabilities/")

    assert response.status_code == 200
    payload = response.json()
    component_ids = {component["id"] for component in payload["components"]}
    assert {
        "device_inventory",
        "cpu",
        "ram",
        "gpu",
        "storage",
        "battery",
        "thermal",
        "fan",
        "usb",
        "usb_c_thunderbolt",
        "keyboard",
        "mouse",
        "touchpad",
        "touchscreen",
        "display",
        "webcam",
        "audio",
        "network",
        "bluetooth",
        "power_adapter",
        "sensor_analytics",
        "burn_in",
    } <= component_ids
    memtest = next(
        engine
        for component in payload["components"]
        for engine in component["engines"]
        if engine["name"] == "MemTest86+"
    )
    assert memtest["status"] == "operator_run_required"
