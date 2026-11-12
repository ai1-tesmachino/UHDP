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
import {
    Dialog,
    DialogContent,
    DialogDescription,
    DialogHeader,
    DialogTitle,
} from "../components/ui/dialog";
import { useDemoInspection } from "../demo/DemoInspectionContext";
import { demoDevice } from "../demo/demoDevice";
import {
    createCpuStressTestResult,
    createCpuTemperatureReading,
    cpuStressTestDurationSeconds,
    type CpuStressTestStatus,
    type CpuTemperatureReading,
} from "../demo/cpuStressTest";
import "./cpu-stress-test.css";

const statusClassNames: Record<CpuStressTestStatus, string> = {
    "Not Started": "is-not-started",
    Ready: "is-ready",
    Running: "is-running",
    Stopped: "is-stopped",
    Finalized: "is-finalized",
};

function formatDuration(seconds: number): string {
    const minutes = Math.floor(seconds / 60).toString().padStart(2, "0");
    const remainingSeconds = (seconds % 60).toString().padStart(2, "0");
    return `${minutes}:${remainingSeconds}`;
}

function formatTemperature(value: number | null): string {
    return value === null ? "—" : `${value.toFixed(1)} °C`;
}

const CpuTemperatureChart = memo(function CpuTemperatureChart({
    readings,
}: {
    readings: CpuTemperatureReading[];
}) {
    return (
        <section className="cpu-stress-chart-card" aria-labelledby="cpu-temperature-title">
            <header className="cpu-stress-chart-heading">
                <div>
                    <h2 id="cpu-temperature-title">CPU Temperature</h2>
                    <p>Simulated temperature readings during the CPU stress test.</p>
                </div>
                <span className="cpu-stress-simulated-label">SIMULATED TEMPERATURE — DEMO DATA</span>
            </header>

            <div
                className="cpu-stress-chart"
                role="img"
                aria-label="CPU temperature over elapsed test time"
                data-reading-count={readings.length}
                data-latest-reading={readings.length > 0 ? readings[readings.length - 1].temperatureC : ""}
            >
                <ResponsiveContainer width="100%" height="100%">
                    <LineChart
                        data={readings}
                        margin={{ top: 16, right: 20, bottom: 14, left: 12 }}
                    >
                        <CartesianGrid stroke="var(--border)" strokeDasharray="3 5" />
                        <XAxis
                            type="number"
                            dataKey="elapsedSeconds"
                            domain={[0, cpuStressTestDurationSeconds]}
                            ticks={[0, 60, 120, 180, 240, 300]}
                            tickFormatter={(value: number) => `${Math.round(value / 60)}`}
                            stroke="var(--muted-foreground)"
                            tick={{ fontSize: 11 }}
                            label={{
                                value: "Elapsed time (minutes)",
                                position: "insideBottom",
                                offset: -6,
                                fill: "var(--muted-foreground)",
                                fontSize: 11,
                            }}
                        />
                        <YAxis
                            type="number"
                            domain={[35, 85]}
                            ticks={[35, 45, 55, 65, 75, 85]}
                            stroke="var(--muted-foreground)"
                            tick={{ fontSize: 11 }}
                            label={{
                                value: "Temperature (°C)",
                                angle: -90,
                                position: "insideLeft",
                                fill: "var(--muted-foreground)",
                                fontSize: 11,
                            }}
                        />
                        <Tooltip
                            formatter={(value) => [`${Number(value).toFixed(1)} °C`, "Temperature"]}
                            labelFormatter={(value) => {
                                const seconds = Number(value);
                                return `Elapsed time: ${formatDuration(seconds)} (${(seconds / 60).toFixed(2)} min)`;
                            }}
                            contentStyle={{
                                backgroundColor: "var(--card)",
                                borderColor: "var(--border)",
                                borderRadius: "var(--radius-md)",
                                color: "var(--foreground)",
                            }}
                            labelStyle={{ color: "var(--foreground)" }}
                            itemStyle={{ color: "var(--information)" }}
                        />
                        <Line
                            type="monotone"
                            dataKey="temperatureC"
                            name="Temperature"
                            stroke="var(--information)"
                            strokeWidth={2.5}
                            dot={false}
                            activeDot={{ r: 5, strokeWidth: 2 }}
                            isAnimationActive={false}
                        />
                    </LineChart>
                </ResponsiveContainer>
                {readings.length === 0 && (
                    <div className="cpu-stress-chart-empty">
                        Start the test to collect simulated temperature readings.
                    </div>
                )}
            </div>
            {readings.length > 0 && (
                <div className="cpu-stress-latest-reading" aria-live="polite">
                    Latest reading: <strong>{formatTemperature(readings[readings.length - 1].temperatureC)}</strong>
                </div>
            )}
        </section>
    );
});

export default function CpuStressTest() {
    const navigate = useNavigate();
    const location = useLocation();
    const {
        cpuStressTest,
        prepareCpuStressTest,
        startCpuStressTest,
        appendCpuStressReading,
        stopCpuStressTest,
        finalizeCpuStressTest,
    } = useDemoInspection();
    const [confirmFinalize, setConfirmFinalize] = useState(false);
    const intervalRef = useRef<number | null>(null);
    const testRef = useRef(cpuStressTest);
    const locationRef = useRef(location);
    testRef.current = cpuStressTest;
    locationRef.current = location;

    const clearTimer = useCallback(() => {
        if (intervalRef.current !== null) {
            window.clearInterval(intervalRef.current);
            intervalRef.current = null;
        }
    }, []);

    const stopTest = useCallback((reason: "manual" | "duration") => {
        clearTimer();
        stopCpuStressTest(reason);
    }, [clearTimer, stopCpuStressTest]);

    useEffect(() => {
        prepareCpuStressTest();
    }, [prepareCpuStressTest]);

    useEffect(() => {
        if (cpuStressTest.status !== "Running" || intervalRef.current !== null) return;

        intervalRef.current = window.setInterval(() => {
            const current = testRef.current;
            if (current.status !== "Running") {
                clearTimer();
                return;
            }

            const nextElapsed = Math.min(current.elapsedSeconds + 1, current.durationSeconds);
            appendCpuStressReading(createCpuTemperatureReading(nextElapsed));
            if (nextElapsed >= current.durationSeconds) stopTest("duration");
        }, 1000);

        return clearTimer;
    }, [appendCpuStressReading, clearTimer, cpuStressTest.status, stopTest]);

    useEffect(() => {
        const requestLeaveConfirmation = (): boolean => {
            if (testRef.current.status !== "Running") return true;
            const shouldLeave = window.confirm(
                "The CPU stress test is running. Stop it and leave this screen? Collected demo readings will be retained.",
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
            if (
                target.origin === window.location.origin
                && target.pathname === current.pathname
                && target.search === current.search
            ) return;

            if (requestLeaveConfirmation()) return;
            event.preventDefault();
            event.stopImmediatePropagation();
        };

        const onPopState = (event: PopStateEvent) => {
            if (testRef.current.status !== "Running") return;
            const destination = `${window.location.pathname}${window.location.search}${window.location.hash}`;
            if (
                window.location.pathname === locationRef.current.pathname
                && window.location.search === locationRef.current.search
            ) return;

            event.stopImmediatePropagation();
            window.history.pushState(window.history.state, "", locationRef.current.pathname + locationRef.current.search + locationRef.current.hash);
            if (requestLeaveConfirmation()) {
                navigate(destination, { replace: true });
            }
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
        const stateForFinalResult = current.status === "Running"
            ? {
                ...current,
                status: "Stopped" as const,
                stopReason: current.elapsedSeconds >= current.durationSeconds ? "duration" as const : "manual" as const,
            }
            : current;
        if (current.status === "Running") {
            stopCpuStressTest(stateForFinalResult.stopReason ?? "manual");
        }
        finalizeCpuStressTest(createCpuStressTestResult(stateForFinalResult));
        setConfirmFinalize(false);
        navigate("/hardware-diagnostics");
    }

    const processor = demoDevice.processor;
    const isRunning = cpuStressTest.status === "Running";
    const canStart = cpuStressTest.status === "Ready" || cpuStressTest.status === "Not Started";
    const canFinalize = cpuStressTest.status !== "Finalized";

    return (
        <main className="cpu-stress-test page-flow" aria-labelledby="cpu-stress-test-title">
            <header className="device-id-page-header">
                <div>
                    <span className="eyebrow">HARDWARE DIAGNOSTICS</span>
                    <h1 className="page-title" id="cpu-stress-test-title">CPU Stress Test</h1>
                    <p className="page-description">
                        Observe a bounded, simulated CPU test sequence. No real processor load or sensor readings are used.
                    </p>
                </div>
                <span className="device-id-demo-label">DEMO DATA</span>
            </header>

            <section className="cpu-stress-processor-card" aria-labelledby="cpu-stress-processor-title">
                <div className="cpu-stress-section-heading">
                    <div>
                        <h2 id="cpu-stress-processor-title">Processor</h2>
                        <p>{processor.manufacturer} {processor.model}</p>
                    </div>
                    <div className={`cpu-stress-state-badge ${statusClassNames[cpuStressTest.status]}`} aria-live="polite">
                        {cpuStressTest.status}
                    </div>
                </div>
                <dl className="cpu-stress-processor-details">
                    <div><dt>Manufacturer</dt><dd>{processor.manufacturer}</dd></div>
                    <div><dt>Model</dt><dd>{processor.model}</dd></div>
                    <div><dt>Physical cores</dt><dd>{processor.physicalCores}</dd></div>
                    <div><dt>Logical threads</dt><dd>{processor.logicalThreads}</dd></div>
                    <div><dt>Base frequency</dt><dd>{processor.baseFrequencyGhz === null ? "Not Available" : `${processor.baseFrequencyGhz} GHz`}</dd></div>
                    <div><dt>Maximum frequency</dt><dd>{processor.maxFrequencyGhz === null ? "Not Available" : `${processor.maxFrequencyGhz} GHz`}</dd></div>
                </dl>
            </section>

            <section className="cpu-stress-summary" aria-label="Test summary">
                <article className="cpu-stress-summary-card">
                    <span>Test Status</span>
                    <strong>{cpuStressTest.status}</strong>
                </article>
                <article className="cpu-stress-summary-card">
                    <span>Elapsed Time</span>
                    <strong>{formatDuration(cpuStressTest.elapsedSeconds)}</strong>
                </article>
                <article className="cpu-stress-summary-card">
                    <span>CPU Utilisation</span>
                    <strong>{cpuStressTest.cpuUtilisationPercent.toFixed(1)}%</strong>
                </article>
            </section>

            <CpuTemperatureChart readings={cpuStressTest.readings} />

            <section className="cpu-stress-live-metrics" aria-label="Live test measurements">
                <article><span>Current CPU Temperature</span><strong>{formatTemperature(cpuStressTest.currentTemperatureC)}</strong></article>
                <article><span>Maximum Recorded Temperature</span><strong>{formatTemperature(cpuStressTest.maximumTemperatureC)}</strong></article>
                <article><span>CPU Utilisation</span><strong>{cpuStressTest.cpuUtilisationPercent.toFixed(1)}%</strong></article>
                <article><span>Elapsed Test Time</span><strong>{formatDuration(cpuStressTest.elapsedSeconds)}</strong></article>
                <article><span>Configured Test Duration</span><strong>{formatDuration(cpuStressTest.durationSeconds)}</strong></article>
            </section>

            <p className="cpu-stress-safety-note">
                All readings are deterministic demo data. No thermal thresholds or real hardware tests are applied.
            </p>

            <footer className="cpu-stress-actions">
                <Link className="button button-secondary" to="/hardware-diagnostics">
                    Back to Hardware Diagnostics
                </Link>
                <div>
                    <button
                        className="button button-primary"
                        type="button"
                        disabled={!canStart}
                        onClick={startCpuStressTest}
                    >
                        START TEST
                    </button>
                    <button
                        className="button button-secondary"
                        type="button"
                        disabled={!isRunning}
                        onClick={() => stopTest("manual")}
                    >
                        STOP TEST
                    </button>
                    <button
                        className="button button-primary"
                        type="button"
                        disabled={!canFinalize}
                        onClick={() => setConfirmFinalize(true)}
                    >
                        FINALIZE TEST
                    </button>
                </div>
            </footer>

            <Dialog open={confirmFinalize} onOpenChange={setConfirmFinalize}>
                <DialogContent className="cpu-stress-confirmation-dialog">
                    <DialogHeader>
                        <DialogTitle>Finalize CPU Stress Test?</DialogTitle>
                        <DialogDescription>
                            {cpuStressTest.status === "Running"
                                ? "Finalizing now will stop the simulation and record it as incomplete unless the configured duration has been reached."
                                : cpuStressTest.status === "Stopped" && cpuStressTest.stopReason === "duration"
                                    ? "The configured duration was reached. Finalization will record the completed simulated result."
                                    : cpuStressTest.readings.length > 0
                                        ? "The test stopped before its configured duration. Finalization will record an incomplete result."
                                        : "The test has not started. Finalization will not mark it as passed."}
                        </DialogDescription>
                    </DialogHeader>
                    <div className="cpu-stress-confirmation-actions">
                        <button className="button button-secondary" type="button" onClick={() => setConfirmFinalize(false)}>
                            Keep Testing
                        </button>
                        <button className="button button-primary" type="button" onClick={finalizeTest}>
                            Confirm Finalize
                        </button>
                    </div>
                </DialogContent>
            </Dialog>
        </main>
    );
}
