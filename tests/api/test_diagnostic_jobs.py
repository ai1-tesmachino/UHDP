import time

import pytest
from fastapi.testclient import TestClient

from app.api.diagnostic_jobs import diagnostic_job_service
from app.main import app
from app.services.diagnostic_job_service import DiagnosticJobService


def wait_for_job(client: TestClient, job_id: str):
    deadline = time.monotonic() + 3
    while time.monotonic() < deadline:
        response = client.get(f"/diagnostic-jobs/{job_id}")
        assert response.status_code == 200
        job = response.json()
        if job["state"] in {"completed", "failed", "cancelled"}:
            return job
        time.sleep(0.01)
    pytest.fail("Diagnostic job did not reach a terminal state")


def test_diagnostic_job_api_evaluates_configured_criteria(monkeypatch):
    def fake_execute(job, cancellation, update):
        update(55, {"cpu_temperature_c": 95})
        return {
            "execution_status": "completed",
            "message": "load done",
            "measurements": {"max_cpu_temperature_c": 95},
            "criteria": job["criteria_profile"],
        }

    monkeypatch.setattr(
        diagnostic_job_service,
        "_execute_test",
        fake_execute,
    )
    with TestClient(app) as client:
        response = client.post(
            "/diagnostic-jobs/",
            json={
                "test_type": "cpu_stress",
                "device_id": "test-cpu",
                "parameters": {"duration_seconds": 1},
                "criteria": {"max_cpu_temp_c": 90},
            },
        )
        assert response.status_code == 202
        created = response.json()
        assert created["criteria_profile"]["version"] == "1.0"

        job = wait_for_job(client, created["job_id"])
        assert job["state"] == "completed"
        assert job["latest_measurement"]["cpu_temperature_c"] == 95
        assert job["result"]["evaluation_status"] == "failed"

        listed = client.get("/diagnostic-jobs/")
        assert listed.status_code == 200
        assert any(item["job_id"] == created["job_id"] for item in listed.json()["jobs"])


def test_diagnostic_job_rejects_invalid_duration_and_criteria():
    with TestClient(app) as client:
        invalid_duration = client.post(
            "/diagnostic-jobs/",
            json={
                "test_type": "cpu_stress",
                "device_id": "test-cpu",
                "parameters": {"duration_seconds": 3601},
            },
        )
        invalid_criterion = client.post(
            "/diagnostic-jobs/",
            json={
                "test_type": "battery_endurance",
                "device_id": "test-battery",
                "parameters": {"duration_minutes": 20},
                "criteria": {"unexpected": 1},
            },
        )
        assert invalid_duration.status_code == 422
        assert invalid_criterion.status_code == 422


@pytest.mark.parametrize("duration_seconds", [300, 900, 1800, 3600, 420])
def test_cpu_stress_accepts_presets_and_custom_duration(
    duration_seconds,
    tmp_path,
):
    service = DiagnosticJobService(tmp_path)
    service._validate(
        "cpu_stress",
        {"duration_seconds": duration_seconds},
        {},
    )


def test_cpu_stress_duration_is_capped_at_one_hour(tmp_path):
    service = DiagnosticJobService(tmp_path)
    with pytest.raises(ValueError, match="1 to 3600"):
        service._validate(
            "cpu_stress",
            {"duration_seconds": 3601},
            {},
        )


def test_non_cpu_stress_duration_remains_capped_at_30_seconds(tmp_path):
    service = DiagnosticJobService(tmp_path)
    with pytest.raises(ValueError, match="1 to 30"):
        service._validate(
            "gpu_stress",
            {"duration_seconds": 31},
            {},
        )


def test_diagnostic_job_missing_id_returns_not_found():
    with TestClient(app) as client:
        response = client.get("/diagnostic-jobs/not-a-job")
        assert response.status_code == 404


def test_internal_cpu_job_runs_and_exposes_explicit_evaluation():
    with TestClient(app) as client:
        response = client.post(
            "/diagnostic-jobs/",
            json={
                "test_type": "cpu_stress",
                "device_id": "system",
                "parameters": {"duration_seconds": 1},
            },
        )
        assert response.status_code == 202

        job = wait_for_job(client, response.json()["job_id"])
        assert job["state"] == "completed"
        assert job["result"]["engine"] == "uhdp-internal-single-core"
        assert job["result"]["evaluation_status"] == "inconclusive"


def test_diagnostic_job_cancel_endpoint():
    def fake_execute(job, cancellation, update):
        update(10, {"elapsed_seconds": 0.1})
        while not cancellation.wait(0.01):
            pass
        return {
            "execution_status": "completed",
            "message": "cancelled",
            "measurements": {},
            "criteria": job["criteria_profile"],
        }

    monkeypatch = pytest.MonkeyPatch()
    monkeypatch.setattr(diagnostic_job_service, "_execute_test", fake_execute)
    try:
        with TestClient(app) as client:
            created = client.post(
                "/diagnostic-jobs/",
                json={
                    "test_type": "cpu_stress",
                    "device_id": "cancel-me",
                    "parameters": {"duration_seconds": 1},
                },
            ).json()
            cancelled = client.post(
                f"/diagnostic-jobs/{created['job_id']}/cancel"
            )
            assert cancelled.status_code == 200
            job = wait_for_job(client, created["job_id"])
            assert job["state"] == "cancelled"
            assert job["result"]["evaluation_status"] == "inconclusive"
    finally:
        monkeypatch.undo()
