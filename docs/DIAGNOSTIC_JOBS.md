# Diagnostic jobs API

Long-running stress and endurance tests use `/diagnostic-jobs/` instead of holding a diagnostic-session request open. Jobs are stored under `DATA_DIR/diagnostic_jobs`; active jobs are marked failed with an interruption message if the server restarts.

## Start and poll a job

```http
POST /diagnostic-jobs/
Content-Type: application/json
```

```json
{
  "test_type": "cpu_stress",
  "device_id": "system",
  "session_id": "optional-session-id",
  "parameters": { "duration_seconds": 10 },
  "criteria": { "max_cpu_temp_c": 90 }
}
```

The response is `202 Accepted` and includes a `job_id`. Poll `GET /diagnostic-jobs/{job_id}` for state, progress, live and historical measurements, and the final evaluation. `GET /diagnostic-jobs/` lists recent jobs. `POST /diagnostic-jobs/{job_id}/cancel` requests cooperative cancellation. Job `state` describes execution; `result.evaluation_status` describes whether the configured criteria were satisfied.

Supported `test_type` values are `cpu_stress`, `memory_stress`, `gpu_stress`, and `battery_endurance`. CPU, RAM, and GPU stress durations are limited to 1–30 seconds. The in-OS RAM test allocates no more than half of currently available RAM or 512 MiB, whichever is smaller; it is not equivalent to boot-time MemTest86+. A separate Manual Tests item records MemTest86+ results. Battery endurance accepts only 30- or 60-minute observations.

Battery jobs can include `workload_label` and `process_id`. UHDP never launches an arbitrary program: start the intended workload yourself and optionally provide its process ID so the job can record whether it stayed alive and its observed CPU use.

## Evaluation and hardware capability

Criteria are persisted with profile version `1.0`. Available thresholds are `max_cpu_temp_c`, `max_gpu_temp_c`, `max_voltage_drop_percent`, and `max_capacity_drop_percent`, according to test type. No universal pass threshold is assumed. A missing sensor needed by a configured threshold produces `inconclusive`, not a pass. A run without a thermal or battery-drop criterion can complete while its health evaluation remains inconclusive.

CPU load uses `stress-ng` when present on Linux and a bounded, single-core UHDP load otherwise (including Windows, where stress-ng is not natively available). Install `stress-ng` on Linux with the host package manager for its external engine (for example `sudo apt install stress-ng` on Debian/Ubuntu); UHDP does not download or execute an unverified binary. CPU stress jobs allow 5, 15, 30, and 60 minute presets plus custom durations from 1 to 60 minutes, and can be cancelled at any time. Temperature is sampled every five seconds from supported `psutil` CPU sensors or LibreHardwareMonitor's WMI provider when available and plotted in the Stress Testing page. Windows machines need LibreHardwareMonitor installed and running with the privileges needed to expose its WMI sensors. Missing sensors are shown as unavailable; a temperature criterion without sensor evidence remains inconclusive. The CPU load uses one worker and technicians should stop the test if temperatures approach the device manufacturer's limit.

GPU load uses `gpu-burn`, a `stress-ng` GPU worker, or `glmark2` (reported as a graphics benchmark, not burn-in); NVIDIA temperature is available when `nvidia-smi` is installed. Missing tools and sensors are reported explicitly.

Battery samples use `psutil` capacity/power state plus Linux power-supply sysfs or Windows WMI voltage when exposed. Some systems do not expose voltage; in that case a voltage-drop criterion is inconclusive. The API records measurements and does not execute or collect arbitrary user workloads.

## Manual browser checks

The Manual Tests flow includes scoped keyboard activity detection, pointer/touch targets, browser display patterns, a live webcam preview, and a short generated speaker tone. Keyboard text is masked and not saved; webcam frames and audio are not recorded. USB read/write remains operator-guided and must only use a disposable file on an explicitly selected test drive.

## Technician workflow and current integration scope

Sessions can carry an asset tag, technician, customer/work-order reference, and workflow type (`service_center`, `refurbishment`, `manufacturing_qa`, `rma_validation`, `incoming_inspection`, `outgoing_certification`, or `burn_in`). Reports retain this intake metadata and a snapshot of discovered inventory. Results accept observed issue, repair, replacement, customer notes, and an operator-selected disposition.

The health analytics report scores only observed passed/failed/error diagnostic outcomes, excluding unsupported and not-applicable tests. Scores are evidence counts, not OEM health certification. The refurbishment recommendation is `insufficient_data` unless battery, storage, thermal, display, and overall health evidence all exist. Thresholds for actual component certification remain site/profile policy.

`GET /capabilities/` inventories the 22 planned component areas and checks for known optional packages/tools in the current environment. A tool marked available is only detected, not automatically validated. OEM families are listed as extension points and are not yet OEM integrations. Component coverage still varies by platform; unavailable probes must remain clearly distinguishable from passing results.
