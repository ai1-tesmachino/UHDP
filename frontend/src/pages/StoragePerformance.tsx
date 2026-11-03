import { FormEvent, useCallback, useEffect, useMemo, useState } from "react";
import {
    cancelStorageBenchmark,
    getStorageBenchmark,
    getStorageBenchmarks,
    getStorageBenchmarkTargets,
    startStorageBenchmark,
    StorageBenchmark,
    StorageBenchmarkTarget,
} from "../api/storageBenchmarks";
import { Link, useSearchParams } from "react-router-dom";
import { useQcSession } from "../session/SessionContext";

function formatBytes(bytes: number) {
    if (!Number.isFinite(bytes) || bytes < 0) return "Unknown";
    const units = ["B", "KiB", "MiB", "GiB", "TiB"];
    let value = bytes;
    let unit = 0;
    while (value >= 1024 && unit < units.length - 1) {
        value /= 1024;
        unit += 1;
    }
    return `${value.toFixed(unit > 0 ? 2 : 0)} ${units[unit]}`;
}

function speed(data: Record<string, unknown>, key: string) {
    const value = data[key];
    return typeof value === "number" && Number.isFinite(value) ? value : null;
}

function SpeedChart({
    title,
    values,
}: {
    title: string;
    values: Array<{ label: string; value: number }>;
}) {
    const max = Math.max(1, ...values.map((entry) => entry.value));
    return (
        <section className="storage-chart-card">
            <h2>{title}</h2>
            {values.length === 0 ? (
                <p>No completed benchmark measurements yet.</p>
            ) : (
                <svg
                    className="storage-speed-chart"
                    viewBox={`0 0 720 ${Math.max(150, values.length * 52)}`}
                    role="img"
                    aria-label={`${title} in megabytes per second`}
                >
                    {values.map((entry, index) => {
                        const y = 12 + index * 52;
                        const width = Math.max(1, (entry.value / max) * 500);
                        return (
                            <g key={`${entry.label}-${index}`}>
                                <text x="8" y={y + 16} className="storage-chart-label">
                                    {entry.label.slice(0, 20)}
                                </text>
                                <rect
                                    x="150"
                                    y={y}
                                    width={width}
                                    height="28"
                                    rx="5"
                                    className="storage-chart-bar"
                                />
                                <text
                                    x={Math.min(660, 160 + width)}
                                    y={y + 19}
                                    className="storage-chart-value"
                                >
                                    {entry.value.toFixed(1)} MB/s
                                </text>
                            </g>
                        );
                    })}
                </svg>
            )}
        </section>
    );
}

export default function StoragePerformance() {
    const [params] = useSearchParams();
    const { activeSession } = useQcSession();
    const sessionId = params.get("sessionId") || activeSession?.session_id || "";
    const [targets, setTargets] = useState<StorageBenchmarkTarget[]>([]);
    const [selectedTargetId, setSelectedTargetId] = useState("");
    const [benchmarks, setBenchmarks] = useState<StorageBenchmark[]>([]);
    const [activeId, setActiveId] = useState<string | null>(null);
    const [loading, setLoading] = useState(true);
    const [submitting, setSubmitting] = useState(false);
    const [error, setError] = useState("");

    const selectedTarget = targets.find((target) => target.target_id === selectedTargetId);

    const refresh = useCallback(async () => {
        try {
            const [availableTargets, history] = await Promise.all([
                getStorageBenchmarkTargets(),
                getStorageBenchmarks(undefined, sessionId || undefined),
            ]);
            setTargets(availableTargets);
            setBenchmarks(history);
            setError("");
        } catch (loadError) {
            setError(
                loadError instanceof Error
                    ? loadError.message
                    : "Storage benchmark information could not be loaded.",
            );
        } finally {
            setLoading(false);
        }
    }, [sessionId]);

    useEffect(() => {
        void refresh();
        const timer = window.setInterval(() => void refresh(), activeId ? 2000 : 15000);
        return () => window.clearInterval(timer);
    }, [activeId, refresh]);

    useEffect(() => {
        if (!activeId) return;
        let mounted = true;
        const timer = window.setInterval(() => {
            void getStorageBenchmark(activeId).then((benchmark) => {
                if (!mounted) return;
                if (benchmark.status !== "Running") {
                    setActiveId(null);
                    void refresh();
                }
            }).catch(() => undefined);
        }, 2000);
        return () => {
            mounted = false;
            window.clearInterval(timer);
        };
    }, [activeId, refresh]);

    async function runBenchmark(event: FormEvent<HTMLFormElement>) {
        event.preventDefault();
        if (!sessionId || !selectedTarget) return;
        setSubmitting(true);
        setError("");
        try {
            const run = await startStorageBenchmark(selectedTarget.target_id, sessionId);
            setActiveId(run.benchmark_id);
            await refresh();
        } catch (startError) {
            setError(
                startError instanceof Error
                    ? startError.message
                    : "Storage benchmark could not be started.",
            );
        } finally {
            setSubmitting(false);
        }
    }

    async function cancelBenchmark() {
        if (!activeId) return;
        try {
            await cancelStorageBenchmark(activeId);
        } catch (cancelError) {
            setError(
                cancelError instanceof Error
                    ? cancelError.message
                    : "Cancellation request failed.",
            );
        }
    }

    const completed = useMemo(
        () => benchmarks.filter((run) => run.status === "Completed"),
        [benchmarks],
    );
    const currentHistory = selectedTarget
        ? completed.filter((run) => run.device_id === selectedTarget.device_id)
        : completed;
    const latest = currentHistory[0];
    const writeSpeed = latest ? speed(latest.data, "write_speed_mb_per_second") : null;
    const readSpeed = latest ? speed(latest.data, "read_speed_mb_per_second") : null;
    const chartHistory = currentHistory.slice(0, 8).reverse();

    return (
        <div className="page-flow">
            <div className="page-header">
                <div>
                    <span className="eyebrow">STORAGE PERFORMANCE · SESSION {sessionId || "UNASSIGNED"}</span>
                    <h1 className="page-title">Sequential read/write benchmark</h1>
                    <p className="page-description">
                        A single 2 GiB sequential file test measures this mounted filesystem;
                        it is not a full storage health assessment.
                    </p>
                </div>
            </div>

            <div className="action-row">
                <Link className="button button-secondary" to={`/diagnostic-jobs?sessionId=${encodeURIComponent(sessionId)}`}>
                    Back to performance jobs
                </Link>
                {!sessionId && <Link className="button button-primary" to="/">Start or resume QC</Link>}
            </div>

            {!sessionId && (
                <div className="info-box" role="status">
                    Start or resume a QC session before running a storage benchmark. Results are recorded against that session.
                </div>
            )}

            {error && <div className="error-box" role="alert">{error}</div>}

            <form className="job-create-panel storage-benchmark-form" onSubmit={(event) => void runBenchmark(event)}>
                <label>
                    Mounted storage device
                    <select
                        value={selectedTargetId}
                        onChange={(event) => setSelectedTargetId(event.target.value)}
                        required
                        disabled={activeId !== null || loading}
                    >
                        <option value="">Select a local mounted filesystem</option>
                        {targets.map((target) => (
                            <option key={target.target_id} value={target.target_id}>
                                {target.model || target.device_id} — {target.mountpoint}
                            </option>
                        ))}
                    </select>
                </label>
                {selectedTarget && (
                    <dl className="device-properties">
                        <div className="device-property"><dt>Model</dt><dd>{selectedTarget.model || "Not reported"}</dd></div>
                        <div className="device-property"><dt>Device</dt><dd>{selectedTarget.device_id}</dd></div>
                        <div className="device-property"><dt>Interface</dt><dd>{selectedTarget.interface || "Not reported"}</dd></div>
                        <div className="device-property"><dt>Filesystem</dt><dd>{selectedTarget.filesystem}</dd></div>
                        <div className="device-property"><dt>Capacity / free</dt><dd>{formatBytes(selectedTarget.capacity_bytes)} / {formatBytes(selectedTarget.free_bytes)}</dd></div>
                        <div className="device-property"><dt>Test file / block</dt><dd>2 GiB / 1 MiB</dd></div>
                    </dl>
                )}
                <label className="storage-confirmation">
                    <input type="checkbox" required disabled={activeId !== null || submitting} />
                    I selected the intended filesystem and confirm UHDP may create a unique
                    2 GiB temporary file, synchronize writes, read and checksum it, then
                    delete only that run’s file.
                </label>
                <p className="storage-warning">
                    Do not run during another storage benchmark. This test writes 2 GiB and
                    requires an additional 64 MiB free-space reserve. No raw device is
                    written, formatted, partitioned, or erased.
                </p>
                <button
                    className="button-primary"
                    type="submit"
                    disabled={submitting || activeId !== null || !selectedTarget || !sessionId}
                >
                    {submitting ? "Starting…" : "Start 2 GiB benchmark"}
                </button>
                {activeId && (
                    <button className="button-secondary" type="button" onClick={() => void cancelBenchmark()}>
                        Cancel benchmark
                    </button>
                )}
            </form>

            {activeId && (
                <div className="info-box" role="status">
                    Benchmark {activeId} is running. Other UHDP pages remain available.
                </div>
            )}

            {latest && (
                <div className="card-grid storage-result-grid">
                    <article className="metric-card">
                        <span>Write speed</span>
                        <strong>{writeSpeed === null ? "—" : `${writeSpeed.toFixed(1)} MB/s`}</strong>
                        <small>{String(latest.data.write_duration_seconds ?? "—")} s · 2 GiB</small>
                    </article>
                    <article className="metric-card">
                        <span>Read speed</span>
                        <strong>{readSpeed === null ? "—" : `${readSpeed.toFixed(1)} MB/s`}</strong>
                        <small>{String(latest.data.read_duration_seconds ?? "—")} s · checksum {latest.data.checksum_verified ? "verified" : "not verified"}</small>
                    </article>
                    <article className="metric-card">
                        <span>Read measurement</span>
                        <strong>{String(latest.data.read_cache_mode ?? "Unknown")}</strong>
                        <small>{String(latest.data.read_cache_warning ?? "Cache status is reported with the run.")}</small>
                    </article>
                </div>
            )}

            <div className="storage-charts">
                <SpeedChart
                    title="Write speed"
                    values={chartHistory.flatMap((run) => {
                        const value = speed(run.data, "write_speed_mb_per_second");
                        return value === null ? [] : [{ label: run.started_at, value }];
                    })}
                />
                <SpeedChart
                    title="Read speed"
                    values={chartHistory.flatMap((run) => {
                        const value = speed(run.data, "read_speed_mb_per_second");
                        return value === null ? [] : [{ label: run.started_at, value }];
                    })}
                />
                <SpeedChart
                    title="Read versus write — latest result"
                    values={[
                        ...(writeSpeed === null ? [] : [{ label: "Write", value: writeSpeed }]),
                        ...(readSpeed === null ? [] : [{ label: "Read", value: readSpeed }]),
                    ]}
                />
            </div>

            <section className="report-card">
                <div className="report-card-heading">
                    <h2>Benchmark history</h2>
                    <button className="button-secondary" type="button" onClick={() => void refresh()}>
                        Refresh
                    </button>
                </div>
                {loading ? (
                    <p>Loading storage inventory…</p>
                ) : benchmarks.length === 0 ? (
                    <p>No benchmark runs have been recorded.</p>
                ) : (
                    <div className="device-table-wrapper">
                        <table className="device-table">
                            <thead><tr><th>Time</th><th>Device</th><th>Status</th><th>Write MB/s</th><th>Read MB/s</th><th>Checksum</th></tr></thead>
                            <tbody>
                                {benchmarks.map((run) => (
                                    <tr key={run.benchmark_id}>
                                        <td>{new Date(run.started_at).toLocaleString()}</td>
                                        <td>{run.device_id}</td>
                                        <td>{run.status}</td>
                                        <td>{speed(run.data, "write_speed_mb_per_second")?.toFixed(1) ?? "—"}</td>
                                        <td>{speed(run.data, "read_speed_mb_per_second")?.toFixed(1) ?? "—"}</td>
                                        <td>{run.data.checksum_verified === true ? "Verified" : run.data.checksum_verified === false ? "Mismatch" : "—"}</td>
                                    </tr>
                                ))}
                            </tbody>
                        </table>
                    </div>
                )}
            </section>
            <p className="storage-disclaimer">
                A sequential benchmark does not establish overall drive health or represent
                random I/O, sustained workloads, thermals, or SMART/NVMe health. Cached
                reads are labeled and are not represented as physical-device throughput.
            </p>
        </div>
    );
}
