import { useCallback, useEffect, useRef } from "react";
import { Link, useLocation, useNavigate } from "react-router-dom";
import { Activity, Gauge, Play, Square, Timer, Workflow } from "lucide-react";
import { useDemoInspection } from "../demo/DemoInspectionContext";
import {
    browserBenchmarkOptions,
    browserTabCountOptions,
    browserTestDurationOptions,
    type BrowserBenchmarkId,
    type BrowserPerformanceResult,
} from "../demo/browserPerformanceTest";
import "./browser-performance-test.css";

function formatDuration(seconds: number): string {
    const minutes = Math.floor(seconds / 60).toString().padStart(2, "0");
    const remainingSeconds = (seconds % 60).toString().padStart(2, "0");
    return `${minutes}:${remainingSeconds}`;
}

function getBrowserName(): string {
    const userAgent = navigator.userAgent;
    if (/Edg\//.test(userAgent)) return "Microsoft Edge (Chromium)";
    if (/Chrome|Chromium|HeadlessChrome/.test(userAgent)) return "Chromium";
    if (/Firefox\//.test(userAgent)) return "Firefox";
    if (/Safari\//.test(userAgent)) return "Safari";
    return "Unknown browser";
}

function formatScore(score: number | null | undefined): string {
    return score === null || score === undefined ? "—" : `${score} / 100`;
}

function ResultCard({
    label,
    value,
    note,
}: {
    label: string;
    value: string;
    note?: string;
}) {
    return (
        <article className="browser-performance-result-card">
            <span>{label}</span>
            <strong>{value}</strong>
            {note && <small>{note}</small>}
        </article>
    );
}

function ResultGrid({ result }: { result: BrowserPerformanceResult | null }) {
    return (
        <section className="browser-performance-results-card" aria-labelledby="browser-results-title">
            <header className="browser-performance-section-heading">
                <div>
                    <h2 id="browser-results-title">Test Results</h2>
                    <p>Deterministic sample scores only. These values are not measured from this browser.</p>
                </div>
                <span className="browser-performance-demo-label">SIMULATED RESULTS</span>
            </header>
            <div className="browser-performance-results-grid" aria-live="polite">
                <ResultCard label="Web Application Score" value={formatScore(result?.webApplicationScore)} />
                <ResultCard label="JavaScript Score" value={formatScore(result?.javascriptScore)} />
                <ResultCard label="Graphics Score" value={formatScore(result?.graphicsScore)} />
                <ResultCard
                    label="Multi-Tab Responsiveness"
                    value={result ? `${result.multiTabResponsiveness} / 100` : "—"}
                    note={result ? "Simulated tab configuration" : undefined}
                />
                <ResultCard
                    label="Peak Memory Usage"
                    value={result ? `${result.peakMemoryUsageMb} MB (demo)` : "—"}
                    note={result ? "Not browser process memory" : undefined}
                />
                <ResultCard
                    label="Browser Crashes"
                    value={result ? `${result.browserCrashes} (demo)` : "—"}
                    note={result ? "No browser crash monitoring performed" : undefined}
                />
            </div>
            <div className="browser-performance-overall-result">
                <span>Overall Result</span>
                <strong>{result?.overallResult ?? "—"}</strong>
            </div>
        </section>
    );
}

export default function BrowserPerformanceTest() {
    const navigate = useNavigate();
    const location = useLocation();
    const {
        browserPerformanceTest,
        setBrowserPerformanceBenchmarks,
        setBrowserPerformanceTabCount,
        setBrowserPerformanceDuration,
        startBrowserPerformanceTest,
        advanceBrowserPerformanceTest,
        stopBrowserPerformanceTest,
    } = useDemoInspection();
    const intervalRef = useRef<number | null>(null);
    const testRef = useRef(browserPerformanceTest);
    const locationRef = useRef(location);
    testRef.current = browserPerformanceTest;
    locationRef.current = location;

    const clearTimer = useCallback(() => {
        if (intervalRef.current !== null) {
            window.clearInterval(intervalRef.current);
            intervalRef.current = null;
        }
    }, []);

    const stopTest = useCallback(() => {
        clearTimer();
        stopBrowserPerformanceTest();
    }, [clearTimer, stopBrowserPerformanceTest]);

    useEffect(() => {
        if (browserPerformanceTest.status !== "Running" || intervalRef.current !== null) return;
        intervalRef.current = window.setInterval(() => {
            const current = testRef.current;
            if (current.status !== "Running") {
                clearTimer();
                return;
            }
            const durationSeconds = current.selectedDurationMinutes * 60;
            const nextElapsed = Math.min(current.elapsedSeconds + 1, durationSeconds);
            advanceBrowserPerformanceTest(nextElapsed);
            if (nextElapsed >= durationSeconds) clearTimer();
        }, 1000);
        return clearTimer;
    }, [advanceBrowserPerformanceTest, browserPerformanceTest.status, clearTimer]);

    useEffect(() => {
        const requestLeaveConfirmation = (): boolean => {
            if (testRef.current.status !== "Running") return true;
            if (!window.confirm("The browser performance demo is running. Stop it and leave this screen? Current demo results will be retained.")) {
                return false;
            }
            stopTest();
            return true;
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

    const test = browserPerformanceTest;
    const isRunning = test.status === "Running";
    const durationSeconds = test.selectedDurationMinutes * 60;
    const remainingSeconds = Math.max(durationSeconds - test.elapsedSeconds, 0);
    const progress = Math.min((test.elapsedSeconds / durationSeconds) * 100, 100);

    function toggleBenchmark(benchmarkId: BrowserBenchmarkId) {
        const selected = new Set(test.selectedBenchmarks);
        if (selected.has(benchmarkId)) selected.delete(benchmarkId);
        else selected.add(benchmarkId);
        setBrowserPerformanceBenchmarks([...selected]);
    }

    return (
        <main className="browser-performance-test page-flow" aria-labelledby="browser-performance-title">
            <header className="device-id-page-header">
                <div>
                    <span className="eyebrow">BROWSER DIAGNOSTICS</span>
                    <h1 className="page-title" id="browser-performance-title">Browser Performance Test</h1>
                    <p className="page-description">
                        A bounded interface demo with deterministic sample results. No browser stress workload is executed.
                    </p>
                </div>
                <span className="device-id-demo-label">DEMO DATA</span>
            </header>

            <section className="browser-performance-session-card" aria-label="Browser test configuration">
                <div className="browser-performance-session-summary">
                    <span>Browser</span>
                    <strong>{getBrowserName()}</strong>
                    <span>Test status</span>
                    <strong className={`browser-performance-status is-${test.status.toLowerCase()}`}>{test.status}</strong>
                </div>
                <p>
                    Metrics are deterministic demo values. Multi-tab choices simulate a tab count only; no extra tabs or benchmark workloads are opened.
                </p>
            </section>

            <section className="browser-performance-config-grid" aria-label="Test options">
                <fieldset className="browser-performance-option-card" disabled={isRunning}>
                    <legend><Activity size={16} aria-hidden="true" /> Benchmark Tests</legend>
                    <div className="browser-performance-benchmark-options">
                        {browserBenchmarkOptions.map((option) => (
                            <label className="browser-performance-benchmark-option" key={option.id}>
                                <input
                                    type="checkbox"
                                    checked={test.selectedBenchmarks.includes(option.id)}
                                    onChange={() => toggleBenchmark(option.id)}
                                />
                                <span>
                                    <strong>{option.label}</strong>
                                    <small>{option.description}</small>
                                </span>
                            </label>
                        ))}
                    </div>
                </fieldset>

                <fieldset className="browser-performance-option-card" disabled={isRunning}>
                    <legend><Workflow size={16} aria-hidden="true" /> Multi-Tab Test</legend>
                    <p className="browser-performance-option-description">Simulated tab count. This demo will not open browser tabs.</p>
                    <div className="browser-performance-choice-grid" role="radiogroup" aria-label="Simulated tabs to open">
                        {browserTabCountOptions.map((count) => (
                            <label className="browser-performance-choice" key={count}>
                                <input
                                    type="radio"
                                    name="browser-tab-count"
                                    value={count}
                                    checked={test.selectedTabCount === count}
                                    onChange={() => setBrowserPerformanceTabCount(count)}
                                />
                                <span>{count}</span>
                            </label>
                        ))}
                    </div>
                </fieldset>

                <fieldset className="browser-performance-option-card" disabled={isRunning}>
                    <legend><Timer size={16} aria-hidden="true" /> Test Duration</legend>
                    <p className="browser-performance-option-description">Configured simulation duration.</p>
                    <div className="browser-performance-choice-grid" role="radiogroup" aria-label="Test duration">
                        {browserTestDurationOptions.map((minutes) => (
                            <label className="browser-performance-choice" key={minutes}>
                                <input
                                    type="radio"
                                    name="browser-test-duration"
                                    value={minutes}
                                    checked={test.selectedDurationMinutes === minutes}
                                    onChange={() => setBrowserPerformanceDuration(minutes)}
                                />
                                <span>{minutes} min</span>
                            </label>
                        ))}
                    </div>
                </fieldset>
            </section>

            {isRunning && (
                <section className="browser-performance-running-card" aria-live="polite">
                    <div className="browser-performance-running-label">
                        <span><Gauge size={15} aria-hidden="true" /> Simulated test in progress</span>
                        <strong>{formatDuration(test.elapsedSeconds)} / {formatDuration(durationSeconds)}</strong>
                    </div>
                    <div
                        className="browser-performance-progress-track"
                        role="progressbar"
                        aria-label="Simulated test progress"
                        aria-valuemin={0}
                        aria-valuemax={100}
                        aria-valuenow={Math.round(progress)}
                    >
                        <span style={{ width: `${progress}%` }} />
                    </div>
                    <p>Remaining: {formatDuration(remainingSeconds)} · No actual performance workload is running.</p>
                </section>
            )}

            <div className="browser-performance-actions">
                <Link className="button button-secondary" to="/hardware-diagnostics">BACK TO HARDWARE DIAGNOSTICS</Link>
                <div>
                    {isRunning && (
                        <button className="button button-secondary" type="button" onClick={stopTest}>
                            <Square size={14} aria-hidden="true" /> STOP TEST
                        </button>
                    )}
                    <button
                        className="button button-primary"
                        type="button"
                        disabled={test.selectedBenchmarks.length === 0 || isRunning}
                        onClick={startBrowserPerformanceTest}
                    >
                        <Play size={14} aria-hidden="true" /> {test.finalResult ? "RUN TEST AGAIN" : "START TEST"}
                    </button>
                </div>
            </div>
            {test.selectedBenchmarks.length === 0 && (
                <p className="browser-performance-selection-hint">Select at least one benchmark to start the demo.</p>
            )}

            <ResultGrid result={test.finalResult} />

            <p className="browser-performance-disclaimer">
                This screen does not measure real JavaScript speed, graphics performance, process memory, or browser crashes. All scores and results are simulated and are not diagnostic findings.
            </p>
        </main>
    );
}
