import json
import logging
import platform
import shutil
import subprocess
import threading
import time
import uuid
from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import psutil

from app.core.config import get_settings
from app.hal.diagnostics.memory_stress_diagnostic import MemoryStressDiagnostic
from app.hal.diagnostic_request import DiagnosticRequest


MAX_STRESS_SECONDS = 30
MAX_CPU_STRESS_SECONDS = 60 * 60
CPU_TELEMETRY_INTERVAL_SECONDS = 5
BATTERY_TEST_DURATIONS_MINUTES = {30, 60}
JOB_TYPES = {"cpu_stress", "memory_stress", "gpu_stress", "battery_endurance"}
CRITERIA_VERSION = "1.0"
MAX_CRITERIA = {
    "cpu_stress": {"max_cpu_temp_c": (40, 120)},
    "gpu_stress": {"max_gpu_temp_c": (40, 120)},
    "battery_endurance": {
        "max_voltage_drop_percent": (0, 100),
        "max_capacity_drop_percent": (0, 100),
    },
    "memory_stress": {},
}
logger = logging.getLogger(__name__)


def _utc_now() -> str:
    return datetime.now(UTC).isoformat()


def _stop_process(process: subprocess.Popen) -> None:
    if process.poll() is not None:
        return
    process.terminate()
    try:
        process.wait(timeout=3)
    except subprocess.TimeoutExpired:
        process.kill()
        process.wait(timeout=3)


class DiagnosticJobService:
    def __init__(self, directory: str | Path | None = None) -> None:
        data_dir = Path(directory or get_settings().DATA_DIR)
        self._directory = data_dir / "diagnostic_jobs"
        self._directory.mkdir(parents=True, exist_ok=True)
        self._lock = threading.RLock()
        self._executor = ThreadPoolExecutor(
            max_workers=2,
            thread_name_prefix="uhdp-diagnostic",
        )
        self._jobs: dict[str, dict[str, Any]] = {}
        self._cancellations: dict[str, threading.Event] = {}
        self._load_jobs()

    def create_job(
        self,
        test_type: str,
        device_id: str,
        parameters: dict[str, Any],
        criteria: dict[str, float],
        session_id: str | None = None,
    ) -> dict[str, Any]:
        self._validate(test_type, parameters, criteria)
        job_id = str(uuid.uuid4())
        job = {
            "job_id": job_id,
            "test_type": test_type,
            "device_id": device_id,
            "session_id": session_id,
            "state": "queued",
            "progress_percent": 0,
            "created_at": _utc_now(),
            "started_at": None,
            "completed_at": None,
            "criteria_profile": {
                "version": CRITERIA_VERSION,
                "criteria": criteria,
            },
            "parameters": parameters,
            "latest_measurement": None,
            "measurement_history": [],
            "result": None,
            "error": None,
        }
        cancellation = threading.Event()
        with self._lock:
            self._jobs[job_id] = job
            self._cancellations[job_id] = cancellation
            self._persist(job)
            self._executor.submit(self._run_job, job_id, cancellation)
        return self._snapshot(job)

    def get_job(self, job_id: str) -> dict[str, Any] | None:
        with self._lock:
            job = self._jobs.get(job_id)
            return self._snapshot(job) if job else None

    def list_jobs(self, limit: int = 50) -> list[dict[str, Any]]:
        with self._lock:
            jobs = sorted(
                self._jobs.values(),
                key=lambda job: job["created_at"],
                reverse=True,
            )
            return [self._snapshot(job) for job in jobs[:limit]]

    def cancel_job(self, job_id: str) -> dict[str, Any] | None:
        with self._lock:
            job = self._jobs.get(job_id)
            if job is None:
                return None
            if job["state"] in {"queued", "running"}:
                self._cancellations[job_id].set()
            return self._snapshot(job)

    def _validate(
        self,
        test_type: str,
        parameters: dict[str, Any],
        criteria: dict[str, float],
    ) -> None:
        if test_type not in JOB_TYPES:
            raise ValueError(f"Unsupported diagnostic job type: {test_type}")
        allowed_parameters = (
            {"duration_minutes", "process_id", "workload_label"}
            if test_type == "battery_endurance"
            else {"duration_seconds"}
        )
        extra_parameters = set(parameters) - allowed_parameters
        if extra_parameters:
            raise ValueError(
                f"Unsupported parameters for {test_type}: "
                f"{', '.join(sorted(extra_parameters))}"
            )
        for key, value in criteria.items():
            bounds = MAX_CRITERIA[test_type].get(key)
            if bounds is None:
                raise ValueError(
                    f"Unsupported criterion for {test_type}: {key}"
                )
            if not isinstance(value, (int, float)) or not bounds[0] <= value <= bounds[1]:
                raise ValueError(
                    f"Criterion {key} must be between {bounds[0]} and {bounds[1]}"
                )

        if test_type == "battery_endurance":
            duration = parameters.get("duration_minutes", 30)
            if duration not in BATTERY_TEST_DURATIONS_MINUTES:
                raise ValueError("Battery endurance duration must be 30 or 60 minutes")
            process_id = parameters.get("process_id")
            if process_id is not None and (
                isinstance(process_id, bool)
                or not isinstance(process_id, int)
                or process_id <= 0
            ):
                raise ValueError("process_id must be a positive process ID")
            workload_label = parameters.get("workload_label", "")
            if not isinstance(workload_label, str) or len(workload_label) > 100:
                raise ValueError("workload_label must be a string of at most 100 characters")
        else:
            duration = parameters.get("duration_seconds", 10)
            if isinstance(duration, bool) or not isinstance(duration, int):
                raise ValueError("duration_seconds must be an integer")
            maximum = (
                MAX_CPU_STRESS_SECONDS
                if test_type == "cpu_stress"
                else MAX_STRESS_SECONDS
            )
            if not 1 <= duration <= maximum:
                raise ValueError(
                    f"duration_seconds must be an integer from 1 to {maximum}"
                )

    def _run_job(self, job_id: str, cancellation: threading.Event) -> None:
        with self._lock:
            job = self._jobs[job_id]
            if cancellation.is_set():
                job["state"] = "cancelled"
                job["completed_at"] = _utc_now()
                self._persist(job)
                return
            job["state"] = "running"
            job["started_at"] = _utc_now()
            self._persist(job)

        try:
            result = self._execute_test(
                job,
                cancellation,
                lambda progress, measurement=None: self._update_progress(
                    job_id,
                    progress,
                    measurement,
                ),
            )
            with self._lock:
                job = self._jobs[job_id]
                if cancellation.is_set():
                    job["state"] = "cancelled"
                    result["evaluation_status"] = "inconclusive"
                    result["evaluation_message"] = "The operator cancelled this job before completion."
                else:
                    job["state"] = "completed"
                    self._evaluate(job, result)
                job["result"] = result
                job["progress_percent"] = 100 if job["state"] == "completed" else job["progress_percent"]
                job["completed_at"] = _utc_now()
                self._persist(job)
        except Exception as exc:
            with self._lock:
                job = self._jobs[job_id]
                job["state"] = "failed"
                job["error"] = str(exc)
                job["completed_at"] = _utc_now()
                self._persist(job)

    def _execute_test(
        self,
        job: dict[str, Any],
        cancellation: threading.Event,
        update,
    ) -> dict[str, Any]:
        test_type = job["test_type"]
        if test_type == "cpu_stress":
            return self._run_cpu_stress(job, cancellation, update)
        if test_type == "memory_stress":
            request = DiagnosticRequest(
                diagnostic_type=test_type,
                device_id=job["device_id"],
                parameters=job["parameters"],
            )
            result = MemoryStressDiagnostic().execute(
                request,
                cancellation=cancellation,
                progress_callback=lambda progress: update(progress, None),
            )
            return {
                "execution_status": result.status.value,
                "message": result.message,
                "details": result.details,
                "measurements": {"available_memory_bytes": result.details.get("available_bytes_before_test")},
                "criteria": job["criteria_profile"],
            }
        if test_type == "gpu_stress":
            return self._run_gpu_stress(job, cancellation, update)
        return self._run_battery_endurance(job, cancellation, update)

    def _run_cpu_stress(self, job, cancellation, update) -> dict[str, Any]:
        duration = job["parameters"]["duration_seconds"]
        stress_ng = shutil.which("stress-ng") if platform.system() == "Linux" else None
        start = time.monotonic()
        max_temp: float | None = None
        next_sample = start
        if stress_ng:
            process = subprocess.Popen(
                [stress_ng, "--cpu", "1", "--timeout", f"{duration}s", "--metrics-brief"],
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
            )
            while process.poll() is None:
                if cancellation.wait(0.25):
                    _stop_process(process)
                    break
                elapsed = time.monotonic() - start
                if time.monotonic() >= next_sample:
                    current_temp = self._sample_cpu_temperature()
                    if current_temp is not None:
                        max_temp = max(max_temp or current_temp, current_temp)
                    update(int(elapsed * 100 / duration), {
                        "elapsed_seconds": round(min(duration, elapsed), 1),
                        "cpu_temperature_c": current_temp,
                        "max_cpu_temperature_c": max_temp,
                    })
                    next_sample = time.monotonic() + CPU_TELEMETRY_INTERVAL_SECONDS
                if elapsed >= duration + 5:
                    _stop_process(process)
                    break
            try:
                output, _ = process.communicate(timeout=5)
            except subprocess.TimeoutExpired:
                _stop_process(process)
                output, _ = process.communicate(timeout=5)
            if process.returncode not in {0, -15} and not cancellation.is_set():
                raise RuntimeError(output.strip() or "stress-ng CPU stress failed")
            engine = "stress-ng"
        else:
            engine = "uhdp-internal-single-core"
            iterations = 0
            value = 1
            while time.monotonic() - start < duration and not cancellation.is_set():
                value = (value * 1_664_525 + 1_013_904_223) & 0xFFFFFFFF
                iterations += 1
                elapsed = time.monotonic() - start
                if time.monotonic() >= next_sample:
                    current_temp = self._sample_cpu_temperature()
                    if current_temp is not None:
                        max_temp = max(max_temp or current_temp, current_temp)
                    update(int(elapsed * 100 / duration), {
                        "elapsed_seconds": round(min(duration, elapsed), 1),
                        "cpu_temperature_c": current_temp,
                        "max_cpu_temperature_c": max_temp,
                    })
                    next_sample = time.monotonic() + CPU_TELEMETRY_INTERVAL_SECONDS
            result_details = {
                "iterations": iterations,
                "cpu_cores_used": 1,
                "stress_test": True,
            }
        return {
            "execution_status": "completed",
            "message": "CPU load test finished; thermal evaluation depends on sensor availability and configured criteria.",
            "engine": engine,
            "duration_seconds": duration,
            "measurements": {
                "max_cpu_temperature_c": max_temp,
            },
            "details": result_details if not stress_ng else {},
            "criteria": job["criteria_profile"],
        }

    def _run_gpu_stress(self, job, cancellation, update) -> dict[str, Any]:
        duration = job["parameters"]["duration_seconds"]
        tool = shutil.which("gpu_burn")
        if tool:
            command = [tool, str(duration)]
            method = "gpu-burn"
        else:
            stress_ng = shutil.which("stress-ng")
            if stress_ng:
                command = [stress_ng, "--gpu", "1", "--timeout", f"{duration}s", "--metrics-brief"]
                method = "stress-ng-gpu"
            else:
                glmark = shutil.which("glmark2")
                if glmark:
                    command = [glmark, "--run-forever"]
                    method = "glmark2-graphics-benchmark"
                else:
                    return {
                        "execution_status": "unsupported",
                        "message": "GPU load tool unavailable. Install gpu-burn, stress-ng with GPU workers, or glmark2 (benchmark-only).",
                        "engine": None,
                        "duration_seconds": duration,
                        "measurements": {"max_gpu_temperature_c": self._sample_gpu_temperature()},
                        "criteria": job["criteria_profile"],
                    }

        process = subprocess.Popen(
            command,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            text=True,
        )
        started = time.monotonic()
        max_temp = self._sample_gpu_temperature()
        while process.poll() is None:
            if cancellation.wait(1):
                _stop_process(process)
                break
            max_temp = self._sample_gpu_temperature(max_temp)
            elapsed = min(duration, time.monotonic() - started)
            update(int(elapsed * 100 / duration), {
                "elapsed_seconds": round(elapsed, 1),
                "gpu_temperature_c": max_temp,
            })
            if elapsed >= duration + 5:
                _stop_process(process)
                break
        try:
            process.communicate(timeout=5)
        except subprocess.TimeoutExpired:
            _stop_process(process)
            process.communicate(timeout=5)
        if process.returncode not in {0, -15} and not cancellation.is_set():
            raise RuntimeError(f"{method} GPU run failed with exit code {process.returncode}")
        return {
            "execution_status": "completed",
            "message": "GPU load run finished; review captured telemetry and thresholds.",
            "engine": method,
            "duration_seconds": duration,
            "measurements": {"max_gpu_temperature_c": max_temp},
            "tool_output": None,
            "criteria": job["criteria_profile"],
        }

    def _run_battery_endurance(self, job, cancellation, update) -> dict[str, Any]:
        duration = job["parameters"]["duration_minutes"] * 60
        started = time.monotonic()
        initial = self._battery_measurement(job["parameters"])
        if (
            initial.get("capacity_percent") is None
            and initial.get("voltage_mv") is None
        ):
            return {
                "execution_status": "unsupported",
                "message": "No battery capacity or voltage telemetry is available on this system.",
                "duration_minutes": job["parameters"]["duration_minutes"],
                "measurements": {"initial": initial, "samples": [initial]},
                "criteria": job["criteria_profile"],
            }
        samples = [initial]
        next_sample_at = started + 60
        while time.monotonic() - started < duration and not cancellation.is_set():
            elapsed = time.monotonic() - started
            update(min(99, int(elapsed * 100 / duration)), {
                "elapsed_seconds": round(elapsed, 1),
                **samples[-1],
            })
            cancellation.wait(min(5, max(0, next_sample_at - time.monotonic()), max(0, duration - elapsed)))
            if time.monotonic() - started >= duration:
                break
            if time.monotonic() >= next_sample_at:
                measurement = self._battery_measurement(job["parameters"])
                if measurement:
                    samples.append(measurement)
                next_sample_at += 60
        final = self._battery_measurement(job["parameters"])
        if final:
            samples.append(final)

        voltage_samples = [
            sample["voltage_mv"]
            for sample in samples
            if isinstance(sample.get("voltage_mv"), (int, float))
        ]
        voltage_drop = None
        if len(voltage_samples) >= 2 and voltage_samples[0] > 0:
            voltage_drop = max(
                0.0,
                (voltage_samples[0] - voltage_samples[-1]) * 100 / voltage_samples[0],
            )
        capacity_samples = [
            sample["capacity_percent"]
            for sample in samples
            if isinstance(sample.get("capacity_percent"), (int, float))
        ]
        capacity_drop = None
        if len(capacity_samples) >= 2:
            capacity_drop = max(0.0, capacity_samples[0] - capacity_samples[-1])
        requested_process_id = job["parameters"].get("process_id")
        workload_samples = [
            sample.get("workload_process")
            for sample in samples
            if sample.get("workload_process") is not None
        ]
        return {
            "execution_status": "completed",
            "message": "Battery endurance observation finished. Voltage is reported only when the platform exposes it.",
            "duration_minutes": job["parameters"]["duration_minutes"],
            "workload_label": job["parameters"].get("workload_label") or None,
            "monitored_process_id": job["parameters"].get("process_id"),
            "sample_count": len(samples),
            "measurements": {
                "initial": samples[0] if samples else None,
                "final": samples[-1] if samples else None,
                "voltage_drop_percent": voltage_drop,
                "capacity_drop_percentage_points": capacity_drop,
                "workload_process_samples": workload_samples,
                "workload_process_alive_for_observation": (
                    all(sample.get("running") is True for sample in workload_samples)
                    if requested_process_id
                    and workload_samples
                    and all(sample.get("running") is not None for sample in workload_samples)
                    else None
                ),
                "samples": samples,
            },
            "criteria": job["criteria_profile"],
        }

    def _sample_cpu_temperature(self) -> float | None:
        try:
            sensors = psutil.sensors_temperatures()
        except (AttributeError, NotImplementedError, OSError):
            return None
        values = [
            entry.current
            for sensor_name, entries in sensors.items()
            if any(
                token in sensor_name.lower()
                for token in ("cpu", "coretemp", "k10temp", "zenpower", "package")
            )
            for entry in entries
            if isinstance(entry.current, (int, float))
            and entry.current > 0
        ]
        if not values and platform.system() == "Windows":
            try:
                from app.hal.diagnostics.windows_utils import run_powershell

                raw = run_powershell(
                    """
                    Get-CimInstance -Namespace root/LibreHardwareMonitor -ClassName Sensor -ErrorAction Stop |
                    Where-Object { $_.SensorType -eq "Temperature" -and $_.Name -match "CPU|Core|Package" } |
                    Select-Object -ExpandProperty Value |
                    ConvertTo-Json -Compress
                    """
                )
                raw_values = raw if isinstance(raw, list) else [raw]
                values = [
                    float(value)
                    for value in raw_values
                    if str(value).replace(".", "", 1).isdigit()
                ]
            except (OSError, RuntimeError, ValueError):
                return None
        return max(values) if values else None

    def _sample_gpu_temperature(self, previous: float | None = None) -> float | None:
        nvidia_smi = shutil.which("nvidia-smi")
        if not nvidia_smi:
            return previous
        try:
            result = subprocess.run(
                [nvidia_smi, "--query-gpu=temperature.gpu", "--format=csv,noheader,nounits"],
                capture_output=True,
                text=True,
                timeout=3,
                check=False,
            )
            values = [
                float(line.strip())
                for line in result.stdout.splitlines()
                if line.strip().replace(".", "", 1).isdigit()
            ]
            return max([previous, *values]) if values else previous
        except (OSError, subprocess.SubprocessError, ValueError):
            return previous

    def _battery_measurement(
        self,
        parameters: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        try:
            battery = psutil.sensors_battery()
        except (AttributeError, NotImplementedError, OSError):
            battery = None
        sample: dict[str, Any] = {
            "recorded_at": _utc_now(),
            "capacity_percent": battery.percent if battery else None,
            "power_plugged": battery.power_plugged if battery else None,
            "voltage_mv": None,
            "voltage_source": None,
        }
        process_id = (parameters or {}).get("process_id")
        if process_id:
            try:
                process = psutil.Process(process_id)
                sample["workload_process"] = {
                    "pid": process_id,
                    "name": process.name(),
                    "cpu_percent": process.cpu_percent(interval=None),
                    "running": process.is_running(),
                }
            except (psutil.NoSuchProcess, psutil.ZombieProcess) as exc:
                sample["workload_process"] = {
                    "pid": process_id,
                    "running": False,
                    "error": str(exc),
                }
            except psutil.AccessDenied as exc:
                sample["workload_process"] = {
                    "pid": process_id,
                    "running": None,
                    "error": str(exc),
                }
        if platform.system() == "Linux":
            for path in Path("/sys/class/power_supply").glob("*/voltage_now"):
                try:
                    sample["voltage_mv"] = int(path.read_text().strip()) / 1000
                    sample["voltage_source"] = str(path)
                    break
                except (OSError, ValueError):
                    continue
        elif platform.system() == "Windows":
            try:
                from app.hal.diagnostics.windows_utils import as_list, run_powershell

                status = as_list(run_powershell(
                    """
                    Get-CimInstance -Namespace root/wmi -ClassName BatteryStatus |
                    Select-Object Voltage,PowerOnline |
                    ConvertTo-Json -Compress
                    """
                ))
                if status and isinstance(status[0], dict):
                    sample["voltage_mv"] = status[0].get("Voltage")
                    sample["voltage_source"] = "Windows WMI BatteryStatus"
                    sample["power_plugged"] = status[0].get("PowerOnline")
            except (OSError, RuntimeError):
                pass
        return sample

    def _evaluate(self, job: dict[str, Any], result: dict[str, Any]) -> None:
        if result.get("execution_status") == "unsupported":
            result["evaluation_status"] = "unsupported"
            result["evaluation_message"] = result["message"]
            return
        if result.get("execution_status") in {"failed", "error"}:
            result["evaluation_status"] = result["execution_status"]
            result["evaluation_message"] = result.get("message", "The diagnostic did not complete successfully.")
            return
        if result.get("execution_status") == "not_applicable":
            result["evaluation_status"] = "not_applicable"
            result["evaluation_message"] = result["message"]
            return
        if (
            job["test_type"] == "battery_endurance"
            and job["parameters"].get("process_id")
            and result.get("measurements", {}).get(
                "workload_process_alive_for_observation"
            ) is False
        ):
            result["evaluation_status"] = "failed"
            result["evaluation_message"] = (
                "The selected workload process was not alive for the entire observation."
            )
            return
        if (
            job["test_type"] == "memory_stress"
            and result.get("details", {}).get("pattern_mismatches", 0) > 0
        ):
            result["evaluation_status"] = "failed"
            result["evaluation_message"] = "Memory readback detected pattern mismatches."
            return
        criteria = job["criteria_profile"]["criteria"]
        measurements = result.get("measurements", {})
        tested = 0
        failures = []

        for criterion, threshold in criteria.items():
            measurement_key = {
                "max_cpu_temp_c": "max_cpu_temperature_c",
                "max_gpu_temp_c": "max_gpu_temperature_c",
                "max_voltage_drop_percent": "voltage_drop_percent",
                "max_capacity_drop_percent": "capacity_drop_percentage_points",
            }[criterion]
            measurement = measurements.get(measurement_key)
            if measurement is None:
                continue
            tested += 1
            if measurement > threshold:
                failures.append(
                    f"{measurement_key} {measurement:.1f} exceeded {threshold:.1f}"
                )

        if failures:
            result["evaluation_status"] = "failed"
            result["evaluation_message"] = "; ".join(failures)
        elif criteria and tested == 0:
            result["evaluation_status"] = "inconclusive"
            result["evaluation_message"] = "Configured criteria could not be evaluated because the required sensor was unavailable."
        elif tested < len(criteria):
            result["evaluation_status"] = "inconclusive"
            result["evaluation_message"] = "Some configured criteria could not be evaluated because telemetry was unavailable."
        elif job["test_type"] == "cpu_stress" and not criteria:
            result["evaluation_status"] = "inconclusive"
            result["evaluation_message"] = "CPU load completed, but no thermal threshold was configured."
        elif job["test_type"] == "gpu_stress" and not criteria:
            result["evaluation_status"] = "inconclusive"
            result["evaluation_message"] = "GPU load completed, but no thermal threshold was configured."
        elif job["test_type"] == "battery_endurance" and not criteria:
            result["evaluation_status"] = "inconclusive"
            result["evaluation_message"] = "Battery observation completed, but no evaluation threshold was configured."
        elif (
            job["test_type"] == "battery_endurance"
            and job["parameters"].get("process_id")
            and result["measurements"].get(
                "workload_process_alive_for_observation"
            ) is None
        ):
            result["evaluation_status"] = "inconclusive"
            result["evaluation_message"] = "The selected process could not be monitored for the full observation."
        else:
            result["evaluation_status"] = "passed"
            result["evaluation_message"] = "All configured measurable criteria were met."

    def _update_progress(
        self,
        job_id: str,
        progress: int,
        measurement: dict[str, Any] | None,
    ) -> None:
        with self._lock:
            job = self._jobs[job_id]
            job["progress_percent"] = max(
                job["progress_percent"],
                min(99, max(0, progress)),
            )
            if measurement is not None:
                job["latest_measurement"] = measurement
                history = job["measurement_history"]
                previous = history[-1] if history else None
                if (
                    previous is None
                    or measurement.get("recorded_at") is None
                    or measurement.get("recorded_at") != previous.get("recorded_at")
                ):
                    history.append(measurement)
            self._persist(job)

    def _snapshot(self, job: dict[str, Any]) -> dict[str, Any]:
        return json.loads(json.dumps(job))

    def _persist(self, job: dict[str, Any]) -> None:
        target = self._directory / f"{job['job_id']}.json"
        temporary = target.with_suffix(".tmp")
        temporary.write_text(
            json.dumps(job, indent=2),
            encoding="utf-8",
        )
        temporary.replace(target)

    def _load_jobs(self) -> None:
        for path in self._directory.glob("*.json"):
            try:
                job = json.loads(path.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError) as exc:
                logger.warning(
                    "Skipping unreadable diagnostic job record %s: %s",
                    path,
                    exc,
                )
                continue
            if job.get("state") in {"queued", "running"}:
                job["state"] = "failed"
                job["error"] = "The server restarted before this diagnostic job finished."
                job["completed_at"] = _utc_now()
                self._persist(job)
            self._jobs[job["job_id"]] = job


diagnostic_job_service = DiagnosticJobService()
