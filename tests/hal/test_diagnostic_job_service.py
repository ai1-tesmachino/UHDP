import threading

from app.services.diagnostic_job_service import DiagnosticJobService


def test_cpu_threshold_without_sensor_is_inconclusive(tmp_path):
    service = DiagnosticJobService(tmp_path)
    job = {
        "test_type": "cpu_stress",
        "criteria_profile": {
            "version": "1.0",
            "criteria": {"max_cpu_temp_c": 90},
        },
    }
    result = {
        "execution_status": "completed",
        "measurements": {"max_cpu_temperature_c": None},
    }

    service._evaluate(job, result)

    assert result["evaluation_status"] == "inconclusive"
    assert "sensor was unavailable" in result["evaluation_message"]


def test_cpu_threshold_evaluates_measured_temperature(tmp_path):
    service = DiagnosticJobService(tmp_path)
    job = {
        "test_type": "cpu_stress",
        "criteria_profile": {
            "version": "1.0",
            "criteria": {"max_cpu_temp_c": 90},
        },
    }
    result = {
        "execution_status": "completed",
        "measurements": {"max_cpu_temperature_c": 86},
    }

    service._evaluate(job, result)

    assert result["evaluation_status"] == "passed"


def test_gpu_stress_is_explicitly_unsupported_without_tools(tmp_path, monkeypatch):
    service = DiagnosticJobService(tmp_path)
    monkeypatch.setattr(
        "app.services.diagnostic_job_service.shutil.which",
        lambda _: None,
    )
    job = {
        "test_type": "gpu_stress",
        "device_id": "test-gpu",
        "parameters": {"duration_seconds": 5},
        "criteria_profile": {"version": "1.0", "criteria": {}},
    }

    result = service._run_gpu_stress(job, threading.Event(), lambda *_: None)
    service._evaluate(job, result)

    assert result["execution_status"] == "unsupported"
    assert result["evaluation_status"] == "unsupported"


def test_battery_voltage_drop_criterion_is_evaluated(tmp_path):
    service = DiagnosticJobService(tmp_path)
    job = {
        "test_type": "battery_endurance",
        "criteria_profile": {
            "version": "1.0",
            "criteria": {"max_voltage_drop_percent": 10},
        },
        "parameters": {"duration_minutes": 30},
    }
    result = {
        "execution_status": "completed",
        "measurements": {"voltage_drop_percent": 12},
    }

    service._evaluate(job, result)

    assert result["evaluation_status"] == "failed"


def test_battery_job_skips_long_observation_without_telemetry(tmp_path, monkeypatch):
    service = DiagnosticJobService(tmp_path)
    monkeypatch.setattr(
        service,
        "_battery_measurement",
        lambda _: {
            "capacity_percent": None,
            "voltage_mv": None,
            "power_plugged": None,
        },
    )
    job = {
        "test_type": "battery_endurance",
        "parameters": {"duration_minutes": 60},
        "criteria_profile": {"version": "1.0", "criteria": {}},
    }

    result = service._run_battery_endurance(
        job,
        threading.Event(),
        lambda *_: None,
    )
    service._evaluate(job, result)

    assert result["execution_status"] == "unsupported"
    assert result["evaluation_status"] == "unsupported"
