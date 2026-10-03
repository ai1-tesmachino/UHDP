import { FormEvent, useCallback, useEffect, useState } from "react";

import {
    cancelDiagnosticJob,
    createDiagnosticJob,
    DiagnosticJob,
    DiagnosticJobType,
    getDiagnosticJobs,
} from "../api/diagnosticJobs";

const TEST_TYPES: Array<{
    value: DiagnosticJobType;
    label: string;
    description: string;
}> = [
    {
        value: "cpu_stress",
        label: "CPU stress",
        description: "A one-worker CPU load with selectable 5, 15, 30, or 60 minute runs and a custom duration up to one hour.",
    },
    {
        value: "memory_stress",
        label: "RAM pattern and readback",
        description: "Allocates at most half of available RAM and 512 MiB, then verifies written pages. MemTest86+ is a separate boot-time test and is not represented as an in-OS equivalent.",
    },
    {
        value: "gpu_stress",
        label: "GPU stress",
        description: "Uses gpu-burn or a stress-ng GPU worker; unsupported when no compatible tool is installed.",
    },
    {
        value: "battery_endurance",
        label: "Battery endurance",
        description: "Runs a 30/60 minute observation and records capacity, power state and exposed voltage.",
    },
];

function pretty(value: unknown) {
    return JSON.stringify(value, null, 2) ?? String(value);
}

function CpuTemperatureChart({ job }: { job: DiagnosticJob }) {
    const history = job.measurement_history || [];
    const values = history.map((sample) => (
        typeof sample.cpu_temperature_c === "number"
            ? sample.cpu_temperature_c
            : null
    ));
    const available = values.filter((value): value is number => value !== null);
    const minimum = available.length ? Math.floor(Math.min(...available)) : 0;
    const maximum = available.length ? Math.ceil(Math.max(...available)) : 0;
    const range = Math.max(1, maximum - minimum);
    const points = values.map((value, index) => {
        if (value === null) {
            return "";
        }
        const x = 12 + (index / Math.max(1, values.length - 1)) * 696;
        const y = 128 - ((value - minimum) / range) * 104;
        return `${index > 0 && values[index - 1] !== null ? "L" : "M"}${x.toFixed(1)},${y.toFixed(1)}`;
    }).filter(Boolean).join(" ");
    const currentTemperature = available.at(-1);
    const peakTemperature = Math.max(
        ...history.map((sample) => (
            typeof sample.max_cpu_temperature_c === "number"
                ? sample.max_cpu_temperature_c
                : -Infinity
        )),
    );

    return (
        <section className="cpu-temperature-panel" aria-label="CPU temperature telemetry">
            <div className="cpu-temperature-heading">
                <strong>CPU temperature</strong>
                <span>
                    {currentTemperature === undefined
                        ? "Sensor unavailable"
                        : `${currentTemperature.toFixed(1)} °C now`}
                    {Number.isFinite(peakTemperature) && ` · ${peakTemperature.toFixed(1)} °C peak`}
                </span>
            </div>
            {available.length ? (
                <>
                    <svg
                        className="cpu-temperature-chart"
                        viewBox="0 0 720 150"
                        role="img"
                        aria-label={`CPU temperature over time, from ${minimum} to ${maximum} degrees Celsius`}
                        preserveAspectRatio="none"
                    >
                        {[24, 76, 128].map((y) => (
                            <line key={y} x1="12" x2="708" y1={y} y2={y} className="cpu-chart-grid" />
                        ))}
                        <path d={points} className="cpu-chart-line" />
                    </svg>
                    <div className="cpu-temperature-scale">
                        <span>{maximum} °C</span>
                        <span>{history.length} samples · one every 5 seconds</span>
                        <span>{minimum} °C</span>
                    </div>
                </>
            ) : (
                <p className="cpu-temperature-empty">
                    {job.state === "running"
                        ? "Waiting for the first temperature sample. The test can continue without a sensor, but thermal evaluation will be inconclusive."
                        : "No CPU temperature samples were reported by the host sensor."}
                </p>
            )}
        </section>
    );
}

export default function DiagnosticJobs({ cpuOnly = false }: { cpuOnly?: boolean }) {
    const [testType, setTestType] = useState<DiagnosticJobType>(
        cpuOnly ? "cpu_stress" : "memory_stress",
    );
    const [durationPreset, setDurationPreset] = useState("5");
    const [customDurationMinutes, setCustomDurationMinutes] = useState(10);
    const [durationSeconds, setDurationSeconds] = useState(10);
    const [durationMinutes, setDurationMinutes] = useState(30);
    const [deviceId, setDeviceId] = useState("system");
    const [sessionId, setSessionId] = useState("");
    const [cpuThreshold, setCpuThreshold] = useState("");
    const [gpuThreshold, setGpuThreshold] = useState("");
    const [voltageDropThreshold, setVoltageDropThreshold] = useState("");
    const [capacityDropThreshold, setCapacityDropThreshold] = useState("");
    const [workloadLabel, setWorkloadLabel] = useState("");
    const [processId, setProcessId] = useState("");
    const [jobs, setJobs] = useState<DiagnosticJob[]>([]);
    const [loading, setLoading] = useState(true);
    const [submitting, setSubmitting] = useState(false);
    const [error, setError] = useState("");

    const refresh = useCallback(async () => {
        try {
            setJobs(await getDiagnosticJobs());
            setError("");
        } catch (loadError) {
            setError(
                loadError instanceof Error
                    ? loadError.message
                    : "Diagnostic jobs could not be loaded.",
            );
        } finally {
            setLoading(false);
        }
    }, []);

    useEffect(() => {
        void refresh();
        const timer = window.setInterval(() => void refresh(), 2000);
        return () => window.clearInterval(timer);
    }, [refresh]);

    async function startJob(event: FormEvent<HTMLFormElement>) {
        event.preventDefault();
        setSubmitting(true);
        setError("");
        try {
            const criteria: Record<string, number> = {};
            if (testType === "cpu_stress" && cpuThreshold) {
                criteria.max_cpu_temp_c = Number(cpuThreshold);
            }
            if (testType === "gpu_stress" && gpuThreshold) {
                criteria.max_gpu_temp_c = Number(gpuThreshold);
            }
            if (testType === "battery_endurance" && voltageDropThreshold) {
                criteria.max_voltage_drop_percent = Number(voltageDropThreshold);
            }
            if (testType === "battery_endurance" && capacityDropThreshold) {
                criteria.max_capacity_drop_percent = Number(capacityDropThreshold);
            }

            await createDiagnosticJob({
                test_type: testType,
                device_id: deviceId.trim(),
                ...(sessionId.trim() ? { session_id: sessionId.trim() } : {}),
                parameters: testType === "battery_endurance"
                    ? {
                        duration_minutes: durationMinutes,
                        ...(workloadLabel.trim() ? { workload_label: workloadLabel.trim() } : {}),
                        ...(processId.trim() ? { process_id: Number(processId) } : {}),
                    }
                    : testType === "cpu_stress"
                        ? { duration_seconds: cpuDurationMinutes * 60 }
                        : { duration_seconds: durationSeconds },
                criteria,
            });
            await refresh();
        } catch (submitError) {
            setError(
                submitError instanceof Error
                    ? submitError.message
                    : "Diagnostic job could not be started.",
            );
        } finally {
            setSubmitting(false);
        }
    }

    async function cancel(jobId: string) {
        try {
            await cancelDiagnosticJob(jobId);
            await refresh();
        } catch (cancelError) {
            setError(
                cancelError instanceof Error
                    ? cancelError.message
                    : "Diagnostic job could not be cancelled.",
            );
        }
    }

    const availableTypes = cpuOnly
        ? TEST_TYPES.filter((test) => test.value === "cpu_stress")
        : TEST_TYPES.filter((test) => test.value !== "cpu_stress");
    const activeType = TEST_TYPES.find((item) => item.value === testType);
    const visibleJobs = jobs.filter((job) => (
        cpuOnly ? job.test_type === "cpu_stress" : job.test_type !== "cpu_stress"
    ));
    const cpuDurationMinutes = durationPreset === "custom"
        ? customDurationMinutes
        : Number(durationPreset);

    return (
        <div className="page-flow">
            <div className="page-header">
                <div>
                    <span className="eyebrow">{cpuOnly ? "CPU VALIDATION" : "HARDWARE TEST JOBS"}</span>
                    <h1 className="page-title">{cpuOnly ? "CPU stress testing" : "Long-running tests"}</h1>
                    <p className="page-description">
                        {cpuOnly
                            ? "Run a controlled CPU load, monitor reported temperatures in real time, and stop the test at any time."
                            : "Start bounded stress or endurance jobs, follow progress, and review the measurements and criteria outcome."}
                    </p>
                </div>
            </div>

            {error && <div className="error-box">{error}</div>}

            <form className="job-create-panel" onSubmit={(event) => void startJob(event)}>
                {!cpuOnly && (
                    <label>
                        Test type
                        <select
                            value={testType}
                            onChange={(event) => setTestType(event.target.value as DiagnosticJobType)}
                        >
                            {availableTypes.map((test) => (
                                <option value={test.value} key={test.value}>{test.label}</option>
                            ))}
                        </select>
                    </label>
                )}
                <p>{activeType?.description}</p>
                <label>
                    Device ID
                    <input
                        value={deviceId}
                        onChange={(event) => setDeviceId(event.target.value)}
                        required
                        maxLength={200}
                    />
                </label>
                <label>
                    Link to diagnostic session (optional)
                    <input
                        value={sessionId}
                        onChange={(event) => setSessionId(event.target.value)}
                        maxLength={200}
                        placeholder="Session ID"
                    />
                </label>

                {testType === "battery_endurance" ? (
                    <>
                        <label>
                            Observation duration
                            <select
                                value={durationMinutes}
                                onChange={(event) => setDurationMinutes(Number(event.target.value))}
                            >
                                <option value={30}>30 minutes</option>
                                <option value={60}>60 minutes</option>
                            </select>
                        </label>
                        <label>
                            Maximum voltage drop (%) — optional evaluation criterion
                            <input
                                type="number"
                                min={0}
                                max={100}
                                step={0.1}
                                value={voltageDropThreshold}
                                onChange={(event) => setVoltageDropThreshold(event.target.value)}
                                placeholder="No default threshold"
                            />
                        </label>
                        <label>
                            Maximum capacity drop (percentage points) — optional evaluation criterion
                            <input
                                type="number"
                                min={0}
                                max={100}
                                step={0.1}
                                value={capacityDropThreshold}
                                onChange={(event) => setCapacityDropThreshold(event.target.value)}
                                placeholder="No default threshold"
                            />
                        </label>
                        <label>
                            Workload label (optional; start that workload yourself)
                            <input
                                value={workloadLabel}
                                onChange={(event) => setWorkloadLabel(event.target.value)}
                                maxLength={100}
                                placeholder="For example, video playback or office workload"
                            />
                        </label>
                        <label>
                            Workload process ID (optional; monitor only, never launched by UHDP)
                            <input
                                type="number"
                                min={1}
                                step={1}
                                value={processId}
                                onChange={(event) => setProcessId(event.target.value)}
                                placeholder="PID"
                            />
                        </label>
                    </>
                ) : (
                    <>
                        <label>
                            {testType === "cpu_stress" ? "Test duration" : "Duration (seconds; capped at 30)"}
                            {testType === "cpu_stress" ? (
                                <select
                                    value={durationPreset}
                                    onChange={(event) => setDurationPreset(event.target.value)}
                                >
                                    <option value="5">5 minutes</option>
                                    <option value="15">15 minutes</option>
                                    <option value="30">30 minutes</option>
                                    <option value="60">1 hour</option>
                                    <option value="custom">Custom (1–60 minutes)</option>
                                </select>
                            ) : (
                                <input
                                    type="number"
                                    min={1}
                                    max={30}
                                    value={durationSeconds}
                                    onChange={(event) => setDurationSeconds(
                                        Math.min(30, Math.max(1, Number(event.target.value) || 1)),
                                    )}
                                />
                            )}
                        </label>
                        {testType === "cpu_stress" && durationPreset === "custom" && (
                            <label>
                                Custom duration in minutes
                                <input
                                    type="number"
                                    min={1}
                                    max={60}
                                    step={1}
                                    value={customDurationMinutes}
                                    onChange={(event) => setCustomDurationMinutes(
                                        Math.min(60, Math.max(1, Number(event.target.value) || 1)),
                                    )}
                                />
                            </label>
                        )}
                        {testType === "cpu_stress" && (
                            <label>
                                Maximum CPU temperature (°C) — optional evaluation criterion
                                <input
                                    type="number"
                                    min={40}
                                    max={120}
                                    value={cpuThreshold}
                                    onChange={(event) => setCpuThreshold(event.target.value)}
                                    placeholder="No default threshold"
                                />
                            </label>
                        )}
                        {testType === "gpu_stress" && (
                            <label>
                                Maximum GPU temperature (°C) — optional evaluation criterion
                                <input
                                    type="number"
                                    min={40}
                                    max={120}
                                    value={gpuThreshold}
                                    onChange={(event) => setGpuThreshold(event.target.value)}
                                    placeholder="No default threshold"
                                />
                            </label>
                        )}
                    </>
                )}

                <p className="job-criteria-note">
                    {testType === "cpu_stress"
                ? "CPU load is limited to one worker. Stop the test if temperatures approach the device maker’s limit. Missing temperature telemetry is reported as inconclusive, never as a thermal pass."
                : "Thresholds are saved with criteria profile version 1.0. If a configured sensor is unavailable, the result is inconclusive rather than passed."}
                </p>
                <button
                    className="button button-primary"
                    type="submit"
                    disabled={submitting || !deviceId.trim()}
                >
                    {submitting ? "Starting…" : "Start test job"}
                </button>
            </form>

            <section className="job-list-panel">
                <div className="section-heading">
                    <div>
                        <span className="eyebrow">POLLABLE JOB API</span>
                        <h2>Recent jobs</h2>
                    </div>
                    <button
                        className="button button-quiet"
                        type="button"
                        onClick={() => void refresh()}
                    >
                        Refresh
                    </button>
                </div>
                {loading ? (
                    <div className="loading-panel">Loading jobs…</div>
                ) : visibleJobs.length === 0 ? (
                    <div className="empty-state">
                        {cpuOnly ? "No CPU stress tests have been started." : "No long-running test jobs have been started."}
                    </div>
                ) : (
                    <div className="job-list">
                        {visibleJobs.map((job) => (
                            <article className="job-card" key={job.job_id}>
                                <div className="job-card-heading">
                                    <div>
                                        <strong>{TEST_TYPES.find((test) => test.value === job.test_type)?.label || job.test_type}</strong>
                                        <code>{job.job_id}</code>
                                    </div>
                                    <span className={`result-badge ${job.state === "failed" ? "result-fail" : "result-neutral"}`}>
                                        {job.state}
                                    </span>
                                </div>
                                <p>Device {job.device_id} · criteria v{job.criteria_profile.version}</p>
                                {job.session_id && <p>Linked session {job.session_id}</p>}
                                <div
                                    className="execution-progress"
                                    role="progressbar"
                                    aria-valuenow={job.progress_percent}
                                    aria-valuemin={0}
                                    aria-valuemax={100}
                                >
                                    <span style={{ width: `${job.progress_percent}%` }} />
                                </div>
                                <small>{job.progress_percent}%</small>
                                {job.latest_measurement && (
                                    <pre className="job-json">{pretty(job.latest_measurement)}</pre>
                                )}
                                {job.test_type === "cpu_stress" && <CpuTemperatureChart job={job} />}
                                {(job.measurement_history?.length || 0) > 1 && (
                                    <details>
                                        <summary>Measurement history ({job.measurement_history?.length || 0} samples)</summary>
                                        <pre className="job-json">{pretty(job.measurement_history)}</pre>
                                    </details>
                                )}
                                {job.error && <div className="error-box">{job.error}</div>}
                                {job.result && (
                                    <div className="job-result">
                                        <div>
                                            Evaluation: <strong>{String(job.result.evaluation_status || job.result.execution_status || "not evaluated")}</strong>
                                        </div>
                                        <p>{String(job.result.evaluation_message || job.result.message || "")}</p>
                                        <pre className="job-json">{pretty(job.result)}</pre>
                                    </div>
                                )}
                                {["queued", "running"].includes(job.state) && (
                                    <button
                                        className="button button-secondary"
                                        type="button"
                                        onClick={() => void cancel(job.job_id)}
                                    >
                                        Cancel job
                                    </button>
                                )}
                            </article>
                        ))}
                    </div>
                )}
            </section>
        </div>
    );
}
