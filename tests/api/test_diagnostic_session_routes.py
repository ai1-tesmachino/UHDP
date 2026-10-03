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

def test_execute_single_diagnostic():

    with TestClient(app) as client:

        create_response = client.post(
            "/diagnostic-sessions/"
        )

        session_id = (
            create_response.json()[
                "session_id"
            ]
        )

        response = client.post(
            f"/diagnostic-sessions/{session_id}/diagnostics/cpu/cpu"
        )

        assert (
            response.status_code
            == 200
        )

        data = response.json()

        assert (
            data["device_id"]
            == "cpu"
        )

        assert (
            data["diagnostic_type"]
            == "cpu"
        )

        assert data["diagnostic_id"]
        assert "logical_cores" in data["details"]
        assert "cpu_usage_percent" in data["details"]

        report_response = client.get(
            f"/reports/{session_id}/json"
        )

        assert report_response.status_code == 200
        report = report_response.json()
        assert report["data"]["cpu_result"]["details"] == data["details"]
        assert report["data"]["diagnostic_summary"]["total"] == 1

        complete_response = client.post(
            f"/diagnostic-sessions/{session_id}/complete"
        )

        assert complete_response.status_code == 200
        assert complete_response.json()["status"] == "completed"


def test_manual_results_are_persisted_in_session_report():
    with TestClient(app) as client:
        create_response = client.post(
            "/diagnostic-sessions/",
            json={"device_id": "manual-test-device"},
        )
        session_id = create_response.json()["session_id"]

        catalog = client.get("/diagnostic-sessions/manual-checks")
        assert catalog.status_code == 200
        assert any(
            item["id"] == "wifi_connection"
            for item in catalog.json()["manual_checks"]
        )

        response = client.post(
            f"/diagnostic-sessions/{session_id}/manual/wifi_connection",
            json={
                "outcome": "not_applicable",
                "notes": "No Wi-Fi adapter installed; confirmed by operator.",
            },
        )
        assert response.status_code == 200
        assert response.json()["result"]["status"] == "not_applicable"

        complete = client.post(
            f"/diagnostic-sessions/{session_id}/complete"
        )
        assert complete.status_code == 200

        report = client.get(
            f"/diagnostic-sessions/{session_id}/report"
        )
        assert report.status_code == 200
        payload = report.json()
        assert payload["device_id"] == "manual-test-device"
        assert payload["data"]["manual_checks"]["wifi_connection"]["notes"] == (
            "No Wi-Fi adapter installed; confirmed by operator."
        )
        assert payload["summary"]["total"] == 1
        assert payload["summary"]["not_applicable"] == 1
        assert payload["status"] == "not_applicable"


def test_manual_result_rejects_unknown_check_and_outcome():
    with TestClient(app) as client:
        session_id = client.post("/diagnostic-sessions/").json()["session_id"]
        unknown_check = client.post(
            f"/diagnostic-sessions/{session_id}/manual/unknown",
            json={"outcome": "passed"},
        )
        invalid_outcome = client.post(
            f"/diagnostic-sessions/{session_id}/manual/charger",
            json={"outcome": "maybe"},
        )
        assert unknown_check.status_code == 400
        assert invalid_outcome.status_code == 400


def test_stress_duration_is_forwarded_through_session_api():
    with TestClient(app) as client:
        session_id = client.post("/diagnostic-sessions/").json()["session_id"]
        response = client.post(
            f"/diagnostic-sessions/{session_id}/diagnostics/cpu/cpu_stress",
            json={"parameters": {"duration_seconds": 1}},
        )

        assert response.status_code == 200
        assert response.json()["details"]["duration_seconds"] == 1
        assert response.json()["details"]["cpu_cores_used"] == 1


def test_technician_record_is_in_report_with_evidence_limited_health_scores():
    with TestClient(app) as client:
        created = client.post(
            "/diagnostic-sessions/",
            json={
                "device_id": "tech-device",
                "asset_tag": "ASSET-123",
                "technician": "Alex",
                "customer_reference": "WO-55",
                "workflow_type": "refurbishment",
            },
        )
        assert created.status_code == 200
        session_id = created.json()["session_id"]

        cpu_result = client.post(
            f"/diagnostic-sessions/{session_id}/diagnostics/cpu/cpu"
        )
        assert cpu_result.status_code == 200

        updated = client.put(
            f"/diagnostic-sessions/{session_id}/technician-record",
            json={
                "observed_issue": "Intermittent thermal shutdown",
                "repair_performed": "Cleaned cooling assembly",
                "replacement_performed": "",
                "customer_notes": "Return for extended burn-in",
                "refurbishment_grade": "B",
            },
        )
        assert updated.status_code == 200

        report = client.get(
            f"/diagnostic-sessions/{session_id}/report"
        )
        payload = report.json()
        assert payload["data"]["intake_record"]["asset_tag"] == "ASSET-123"
        assert payload["data"]["technician_record"]["refurbishment_grade"] == "B"
        assert payload["data"]["health_analytics"]["cpu_health"]["score"] == 100
        assert payload["data"]["health_analytics"]["thermal_health"]["score"] is None
        assert (
            payload["data"]["refurbishment_recommendation"]["grade"]
            == "insufficient_data"
        )


def test_technician_record_rejects_invalid_grade_and_missing_session():
    with TestClient(app) as client:
        session_id = client.post("/diagnostic-sessions/").json()["session_id"]
        invalid_grade = client.put(
            f"/diagnostic-sessions/{session_id}/technician-record",
            json={"refurbishment_grade": "D"},
        )
        missing_session = client.put(
            "/diagnostic-sessions/missing/technician-record",
            json={"observed_issue": "Issue"},
        )
        assert invalid_grade.status_code == 422
        assert missing_session.status_code == 404