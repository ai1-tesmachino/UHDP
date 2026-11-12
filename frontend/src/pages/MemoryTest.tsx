import { memo, useCallback, useEffect, useRef, useState } from "react";
import { Link, useLocation, useNavigate } from "react-router-dom";
import {
    CartesianGrid,
    Line,
    LineChart,
    ResponsiveContainer,
    Tooltip,
    XAxis,
    YAxis,
} from "recharts";
import { Dialog, DialogContent, DialogDescription, DialogHeader, DialogTitle } from "../components/ui/dialog";
import { useDemoInspection } from "../demo/DemoInspectionContext";
import { demoDevice, getTotalInstalledRamGb } from "../demo/demoDevice";
import {
    createMemoryTestResult,
    memoryTemperatureSensorAvailable,
    memoryTestDurations,
    type MemoryTestStatus,
} from "../demo/memoryStorageTests";
import "./memory-storage-tests.css";

const statusClassNames: Record<MemoryTestStatus, string> = {
    "Not Started": "is-not-started",
    Ready: "is-ready",
    Running: "is-running",
    Stopped: "is-stopped",
    Finalized: "is-finalized",
};

function formatDuration(seconds: number): string {
    const hours = Math.floor(seconds / 3600);
    const minutes = Math.floor((seconds % 3600) / 60);
    const remainingSeconds = seconds % 60;
    return hours > 0
        ? `${hours.toString().padStart(2, "0")}:${minutes.toString().padStart(2, "0")}:${remainingSeconds.toString().padStart(2, "0")}`
        : `${minutes.toString().padStart(2, "0")}:${remainingSeconds.toString().padStart(2, "0")}`;
}

const MemoryTemperatureChart = memo(function MemoryTemperatureChart({
    durationSeconds,
    elapsedSeconds,
}: {
    durationSeconds: number;
    elapsedSeconds: number;
}) {
    const tickInterval = durationSeconds <= 15 * 60 ? 60 : durationSeconds <= 60 * 60 ? 10 * 60 : 60 * 60;
    const ticks = Array.from({ length: Math.floor(durationSeconds / tickInterval) + 1 }, (_, index) => index * tickInterval);

    return (
        <section className="memory-test-chart-card" aria-labelledby="memory-temperature-title">
            <header className="memory-test-chart-heading">
                <div>
                    <h2 id="memory-temperature-title">Memory Temperature</h2>
                    <p>Memory temperature readings are shown only when a memory sensor is available.</p>
                </div>
                <span className="memory-storage-demo-label">SIMULATED TEST — DEMO DATA</span>
            </header>
            <div className="memory-test-chart" role="img" aria-label="Memory temperature chart; temperature sensor unavailable">
                <ResponsiveContainer width="100%" height="100%">
                    <LineChart data={[]} margin={{ top: 16, right: 20, bottom: 14, left: 12 }}>
                        <CartesianGrid stroke="var(--border)" strokeDasharray="3 5" />
                        <XAxis
                            type="number"
                            dataKey="elapsedSeconds"
                            domain={[0, durationSeconds]}
                            ticks={ticks}
                            tickFormatter={(value: number) => value < 60 ? `${value}s` : `${Math.round(value / 60)}m`}
                            stroke="var(--muted-foreground)"
                            tick={{ fontSize: 11 }}
                            label={{ value: "Elapsed time", position: "insideBottom", offset: -6, fill: "var(--muted-foreground)", fontSize: 11 }}
                        />
                        <YAxis
                            type="number"
                            domain={[0, 100]}
                            ticks={[0, 20, 40, 60, 80, 100]}
                            stroke="var(--muted-foreground)"
                            tick={{ fontSize: 11 }}
                            label={{ value: "Temperature (°C)", angle: -90, position: "insideLeft", fill: "var(--muted-foreground)", fontSize: 11 }}
                        />
                        <Tooltip
                            contentStyle={{
                                backgroundColor: "var(--card)",
                                borderColor: "var(--border)",
                                borderRadius: "var(--radius-md)",
                                color: "var(--foreground)",
                            }}
                        />
                        <Line
                            type="monotone"
                            dataKey="temperatureC"
                            name="Temperature"
                            stroke="var(--information)"
                            strokeWidth={2.5}
                            activeDot={{ r: 5, strokeWidth: 2 }}
                            isAnimationActive={false}
                            connectNulls={false}
                        />
                    </LineChart>
                </ResponsiveContainer>
                <div className="memory-test-chart-empty" aria-live="polite">
                    <strong>{memoryTemperatureSensorAvailable ? "Temperature data unavailable" : "Memory temperature unavailable."}</strong>
                    <span>{memoryTemperatureSensorAvailable
                        ? "No simulated memory sensor readings are available."
                        : "This device does not expose a memory temperature sensor. CPU temperature is not used as a substitute."}</span>
                    <span>Test elapsed: {formatDuration(elapsedSeconds)}</span>
                </div>
            </div>
        </section>
    );
});

export default function MemoryTest() {
    const navigate = useNavigate();
    const location = useLocation();
    const {
        memoryTest,
        prepareMemoryTest,
        selectMemoryTestDuration,
        confirmMemoryTestDuration,
        startMemoryTest,
        advanceMemoryTest,
        stopMemoryTest,
        finalizeMemoryTest,
    } = useDemoInspection();
    const [confirmFinalize, setConfirmFinalize] = useState(false);
    const intervalRef = useRef<number | null>(null);
    const testRef = useRef(memoryTest);
    const locationRef = useRef(location);
    testRef.current = memoryTest;
    locationRef.current = location;

    const clearTimer = useCallback(() => {
        if (intervalRef.current !== null) {
            window.clearInterval(intervalRef.current);
            intervalRef.current = null;
        }
    }, []);

    const stopTest = useCallback((reason: "manual" | "duration") => {
        clearTimer();
        stopMemoryTest(reason);
    }, [clearTimer, stopMemoryTest]);

    useEffect(() => {
        prepareMemoryTest();
    }, [prepareMemoryTest]);

    useEffect(() => {
        if (memoryTest.status !== "Running" || intervalRef.current !== null) return;
        intervalRef.current = window.setInterval(() => {
            const current = testRef.current;
            if (current.status !== "Running") {
                clearTimer();
                return;
            }
            const nextElapsed = Math.min(current.elapsedSeconds + 1, current.selectedDurationSeconds);
            advanceMemoryTest(nextElapsed);
            if (nextElapsed >= current.selectedDurationSeconds) stopTest("duration");
        }, 1000);
        return clearTimer;
    }, [advanceMemoryTest, clearTimer, memoryTest.status, stopTest]);

    useEffect(() => {
        const requestLeaveConfirmation = (): boolean => {
            if (testRef.current.status !== "Running") return true;
            const shouldLeave = window.confirm(
                "The memory test is running. Stop it and leave this screen? Elapsed demo time will be retained.",
            );
            if (shouldLeave) {
                stopTest("manual");
                return true;
            }
            return false;
        };
        const onDocumentClick = (event: MouseEvent) => {
            if (!(event.target instanceof Element)) return;
            const link = event.target.closest<HTMLAnchorElement>("a[href]");
            if (!link) return;
            const target = new URL(link.href, window.location.href);
            const current = locationRef.current;
            if (target.origin === window.location.origin
                && target.pathname === current.pathname
                && target.search === current.search) return;
            if (requestLeaveConfirmation()) return;
            event.preventDefault();
            event.stopImmediatePropagation();
        };
        const onPopState = (event: PopStateEvent) => {
            if (testRef.current.status !== "Running") return;
            const destination = `${window.location.pathname}${window.location.search}${window.location.hash}`;
            if (window.location.pathname === locationRef.current.pathname
                && window.location.search === locationRef.current.search) return;
            event.stopImmediatePropagation();
            window.history.pushState(
                window.history.state,
                "",
                locationRef.current.pathname + locationRef.current.search + locationRef.current.hash,
            );
            if (requestLeaveConfirmation()) navigate(destination, { replace: true });
        };
        const onBeforeUnload = (event: BeforeUnloadEvent) => {
            if (testRef.current.status !== "Running") return;
            event.preventDefault();
            event.returnValue = "";
        };
        document.addEventListener("click", onDocumentClick, true);
        window.addEventListener("popstate", onPopState, true);
        window.addEventListener("beforeunload", onBeforeUnload);
        return () => {
            document.removeEventListener("click", onDocumentClick, true);
            window.removeEventListener("popstate", onPopState, true);
            window.removeEventListener("beforeunload", onBeforeUnload);
        };
    }, [navigate, stopTest]);

    function finalizeTest() {
        clearTimer();
        const current = testRef.current;
        const finalState = current.status === "Running"
            ? {
                ...current,
                status: "Stopped" as const,
                stopReason: "manual" as const,
            }
            : current;
        if (current.status === "Running") stopMemoryTest("manual");
        finalizeMemoryTest(createMemoryTestResult(finalState));
        setConfirmFinalize(false);
        navigate("/hardware-diagnostics");
    }

    const selectedDuration = memoryTestDurations.find((duration) => duration.seconds === memoryTest.selectedDurationSeconds);
    const elapsed = memoryTest.elapsedSeconds;
    const remaining = Math.max(memoryTest.selectedDurationSeconds - elapsed, 0);
    const progressPercent = Math.min((elapsed / memoryTest.selectedDurationSeconds) * 100, 100);
    const moduleTypes = [...new Set(demoDevice.memory.modules.map((module) => module.type))].join(", ") || "Not Available";
    const isRunning = memoryTest.status === "Running";
    const canStart = memoryTest.status === "Ready" && memoryTest.durationConfirmed;

    return (
        <main className="memory-storage-test page-flow" aria-labelledby="memory-test-title">
            <header className="device-id-page-header">
                <div>
                    <span className="eyebrow">HARDWARE DIAGNOSTICS</span>
                    <h1 className="page-title" id="memory-test-title">Memory Test</h1>
                    <p className="page-description">Run a bounded simulated memory test. No memory contents are accessed or modified.</p>
                </div>
                <span className="device-id-demo-label">DEMO DATA</span>
            </header>

            <section className="memory-storage-device-card" aria-labelledby="memory-device-title">
                <header className="memory-storage-section-heading">
                    <div>
                        <h2 id="memory-device-title">Detected Memory</h2>
                        <p>Specifications from the current Phase 1 device inventory.</p>
                    </div>
                    <span className={`memory-storage-status ${statusClassNames[memoryTest.status]}`}>{memoryTest.status}</span>
                </header>
                <dl className="memory-storage-device-summary">
                    <div><dt>Total installed memory</dt><dd>{getTotalInstalledRamGb(demoDevice)} GB</dd></div>
                    <div><dt>Modules</dt><dd>{demoDevice.memory.modules.length}</dd></div>
                    <div><dt>Memory type</dt><dd>{moduleTypes}</dd></div>
                </dl>
                <div className="memory-storage-module-grid">
                    {demoDevice.memory.modules.map((module, index) => (
                        <article key={`${module.slot}-${index}`} className="memory-storage-module">
                            <strong>Module {index + 1} · {module.slot}</strong>
                            <span>{module.capacityGb} GB · {module.type}</span>
                            <span>{module.speedMts === null ? "Speed not available" : `${module.speedMts} MT/s`}</span>
                            <span>Serial: {module.serialNumber ?? "Not Available"}</span>
                        </article>
                    ))}
                </div>
            </section>

            <section className="memory-storage-summary-grid" aria-label="Memory test summary">
                <article><span>Test Status</span><strong>{memoryTest.status}</strong></article>
                <article><span>Selected Duration</span><strong>{selectedDuration?.label ?? formatDuration(memoryTest.selectedDurationSeconds)}</strong></article>
                <article><span>Elapsed Time</span><strong>{formatDuration(elapsed)}</strong></article>
                <article><span>Remaining Time</span><strong>{formatDuration(remaining)}</strong></article>
                <article><span>Memory Under Test</span><strong>{getTotalInstalledRamGb(demoDevice)} GB</strong></article>
                <article><span>Errors Detected</span><strong>{memoryTest.errorsDetected === null ? "—" : memoryTest.errorsDetected}</strong></article>
            </section>

            <section className="memory-storage-control-card" aria-labelledby="memory-duration-title">
                <header className="memory-storage-section-heading">
                    <div>
                        <h2 id="memory-duration-title">Test Duration</h2>
                        <p>Confirm the configured duration before starting. Progress reflects elapsed time only, not memory coverage.</p>
                    </div>
                    <strong className="memory-storage-duration-value">{selectedDuration?.label ?? formatDuration(memoryTest.selectedDurationSeconds)}</strong>
                </header>
                <div className="memory-storage-duration-options" role="radiogroup" aria-label="Memory test duration">
                    {memoryTestDurations.map((duration) => (
                        <label key={duration.seconds} className="memory-storage-duration-option">
                            <input
                                type="radio"
                                name="memory-test-duration"
                                value={duration.seconds}
                                checked={memoryTest.selectedDurationSeconds === duration.seconds}
                                disabled={memoryTest.status !== "Not Started" && memoryTest.status !== "Ready"}
                                onChange={() => selectMemoryTestDuration(duration.seconds)}
                            />
                            <span>{duration.label}</span>
                        </label>
                    ))}
                </div>
                <label className="memory-storage-confirm-duration">
                    <input
                        type="checkbox"
                        checked={memoryTest.durationConfirmed}
                        disabled={memoryTest.status !== "Ready"}
                        onChange={(event) => {
                            if (event.target.checked) confirmMemoryTestDuration();
                            else selectMemoryTestDuration(memoryTest.selectedDurationSeconds);
                        }}
                    />
                    I confirm the selected duration before starting this simulated test.
                </label>
                <div className="memory-storage-progress">
                    <div className="memory-storage-progress-label">
                        <span>Elapsed-time progress (not memory coverage)</span>
                        <strong>{Math.round(progressPercent)}%</strong>
                    </div>
                    <div
                        className="memory-storage-progress-track"
                        role="progressbar"
                        aria-label="Elapsed-time progress, not memory coverage"
                        aria-valuemin={0}
                        aria-valuemax={100}
                        aria-valuenow={Math.round(progressPercent)}
                    >
                        <span style={{ width: `${progressPercent}%` }} />
                    </div>
                </div>
            </section>

            <MemoryTemperatureChart durationSeconds={memoryTest.selectedDurationSeconds} elapsedSeconds={elapsed} />

            <section className="memory-storage-live-metrics" aria-label="Memory test live metrics">
                <article><span>Current Memory Temperature</span><strong>{memoryTemperatureSensorAvailable && memoryTest.currentTemperatureC !== null ? `${memoryTest.currentTemperatureC} °C` : "Unavailable"}</strong></article>
                <article><span>Maximum Memory Temperature</span><strong>{memoryTemperatureSensorAvailable && memoryTest.maximumTemperatureC !== null ? `${memoryTest.maximumTemperatureC} °C` : "Unavailable"}</strong></article>
                <article><span>Errors Detected</span><strong>{memoryTest.errorsDetected === null ? "Not evaluated" : memoryTest.errorsDetected}</strong></article>
                <article><span>Configured Duration</span><strong>{selectedDuration?.label ?? formatDuration(memoryTest.selectedDurationSeconds)}</strong></article>
            </section>

            <p className="memory-storage-safety-note">
                DEMO DATA ONLY. No memory contents, coverage, errors or hardware temperatures are measured. Memory temperature unavailable.
            </p>

            <footer className="memory-storage-actions">
                <Link className="button button-secondary" to="/hardware-diagnostics">
                    BACK TO HARDWARE DIAGNOSTICS
                </Link>
                <div>
                    <button className="button button-primary" type="button" disabled={!canStart} onClick={startMemoryTest}>
                        START TEST
                    </button>
                    <button className="button button-secondary" type="button" disabled={!isRunning} onClick={() => stopTest("manual")}>
                        STOP TEST
                    </button>
                    <button className="button button-primary" type="button" disabled={memoryTest.status === "Finalized"} onClick={() => setConfirmFinalize(true)}>
                        FINALIZE TEST
                    </button>
                </div>
            </footer>

            <Dialog open={confirmFinalize} onOpenChange={setConfirmFinalize}>
                <DialogContent className="memory-storage-confirmation-dialog">
                    <DialogHeader>
                        <DialogTitle>Finalize memory test?</DialogTitle>
                        <DialogDescription>
                            {isRunning
                                ? "This stops the simulated test now and records an incomplete result."
                                : "The collected demo data will be recorded. An unstarted or incomplete test will not be marked as passed."}
                        </DialogDescription>
                    </DialogHeader>
                    <div className="memory-storage-confirmation-actions">
                        <button className="button button-secondary" type="button" onClick={() => setConfirmFinalize(false)}>CANCEL</button>
                        <button className="button button-primary" type="button" onClick={finalizeTest}>FINALIZE AND RETURN</button>
                    </div>
                </DialogContent>
            </Dialog>
        </main>
    );
}
