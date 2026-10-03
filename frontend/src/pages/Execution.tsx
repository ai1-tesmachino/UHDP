import { useEffect, useMemo, useRef, useState } from "react";
import { useLocation, useNavigate, useSearchParams } from "react-router-dom";

import {
    completeDiagnosticSession,
    createDiagnosticSession,
    executeDiagnostic,
    getManualChecks,
    ManualCheck,
    recordManualResult,
} from "../api/execution";
import { getReport } from "../api/reports";
import ManualHardwareTest from "../components/ManualHardwareTest";

interface ExecutionState {
    deviceId: string;
    deviceName?: string;
    diagnostics: string[];
    mode?: "automated" | "manual";
    manualChecks?: string[];
    durationSeconds?: number;
    intake?: {
        asset_tag?: string;
        technician?: string;
        customer_reference?: string;
        workflow_type?: string;
    };
}

interface DiagnosticResult {
    diagnostic_id?: string;
    diagnostic_type?: string;
    device_id?: string;
    status?: string;
    message?: string;
    details?: Record<string, unknown>;
    evaluation?: unknown;
    created_at?: string;
    [key: string]: unknown;
}

interface TerminalEntry {
    id: number;
    time: string;
    level: "system" | "running" | "success" | "warning" | "error" | "value";
    text: string;
}

const EMPTY_DIAGNOSTICS: string[] = [];

function diagnosticStatusClass(status: string) {
    const value = status.toLowerCase();
    if (["passed", "pass", "success"].includes(value)) {
        return "result-pass";
    }
    if (["failed", "fail", "error"].includes(value)) {
        return "result-fail";
    }
    return "result-neutral";
}

function formatValue(value: unknown) {
    if (typeof value === "string") {
        return value;
    }
    return JSON.stringify(value, null, 2) ?? String(value);
}

export default function Execution() {
    const location = useLocation();
    const navigate = useNavigate();
    const [params] = useSearchParams();
    const execution = location.state as ExecutionState | null;
    const diagnosticsParam = params.get("diagnostics") || "";
    const mode = params.get("mode") || execution?.mode || "automated";
    const manualCheckIds = useMemo(
        () => (params.get("manualChecks") || execution?.manualChecks?.join(",") || "")
            .split(",")
            .filter(Boolean),
        [execution?.manualChecks, params]
    );
    const durationSeconds = Math.min(
        30,
        Math.max(1, Number(params.get("durationSeconds") || execution?.durationSeconds || 10)),
    );
    const diagnostics = useMemo(
        () =>
            diagnosticsParam
                ? diagnosticsParam.split(",").filter(Boolean)
                : execution?.diagnostics || EMPTY_DIAGNOSTICS,
        [diagnosticsParam, execution?.diagnostics]
    );
    const deviceId = params.get("deviceId") || execution?.deviceId || "";
    const deviceName = params.get("deviceName") || execution?.deviceName || deviceId;
    const intake = execution?.intake || {
        asset_tag: params.get("assetTag") || undefined,
        technician: params.get("technician") || undefined,
        customer_reference: params.get("customerReference") || undefined,
        workflow_type: params.get("workflowType") || undefined,
    };

    const [phase, setPhase] = useState<"running" | "manual" | "complete" | "failed">("running");
    const [message, setMessage] = useState("Preparing your diagnostic run…");
    const [error, setError] = useState("");
    const [activeDiagnostic, setActiveDiagnostic] = useState("");
    const [completed, setCompleted] = useState(0);
    const [result, setResult] = useState<Record<string, unknown> | null>(null);
    const [diagnosticStatuses, setDiagnosticStatuses] = useState<Record<string, string>>({});
    const [terminal, setTerminal] = useState<TerminalEntry[]>([]);
    const [sessionId, setSessionId] = useState("");
    const [manualChecks, setManualChecks] = useState<ManualCheck[]>([]);
    const [manualOutcome, setManualOutcome] = useState<"passed" | "failed" | "not_applicable">("passed");
    const [manualNotes, setManualNotes] = useState("");
    const [savingManual, setSavingManual] = useState(false);
    const terminalRef = useRef<HTMLDivElement>(null);

    function appendLog(level: TerminalEntry["level"], text: string) {
        setTerminal((current) => [
            ...current,
            {
                id: current.length + 1,
                time: new Date().toLocaleTimeString(),
                level,
                text,
            },
        ]);
    }

    useEffect(() => {
        const output = terminalRef.current;
        if (output) {
            output.scrollTop = output.scrollHeight;
        }
    }, [terminal]);

    useEffect(() => {
        if (!deviceId || (mode === "manual" ? manualCheckIds.length === 0 : diagnostics.length === 0)) {
            setPhase("failed");
            setError("A system target and at least one diagnostic are required.");
            return;
        }

        let cancelled = false;
        let sessionId = "";

        async function execute() {
            try {
                appendLog("system", `UHDP diagnostic session · target ${deviceName}`);
                appendLog(
                    "system",
                    `Plan loaded · ${mode === "manual" ? manualCheckIds.length : diagnostics.length} checks`,
                );
                setMessage("Creating diagnostic session…");

                const session = await createDiagnosticSession(deviceId, intake);
                sessionId = session.session_id;

                if (!sessionId) {
                    throw new Error("The backend did not return a session ID.");
                }

                appendLog("success", `Session created · ${sessionId}`);
                setSessionId(sessionId);

                if (mode === "manual") {
                    const catalog = await getManualChecks();
                    if (cancelled) {
                        return;
                    }
                    const selectedChecks = catalog.filter((check) => manualCheckIds.includes(check.id));
                    if (selectedChecks.length !== manualCheckIds.length) {
                        throw new Error("One or more selected manual checks are no longer available.");
                    }
                    setManualChecks(selectedChecks);
                    setMessage("Follow the operator instructions and record each result.");
                    appendLog("system", `Manual checklist loaded · ${selectedChecks.length} checks`);
                    setPhase("manual");
                    return;
                }

                for (const [index, diagnostic] of diagnostics.entries()) {
                    if (cancelled) {
                        return;
                    }

                    setActiveDiagnostic(diagnostic);
                    setMessage(`Running ${diagnostic} diagnostic…`);
                    appendLog("running", `[${index + 1}/${diagnostics.length}] ${diagnostic} · starting`);

                    try {
                        const item: DiagnosticResult = await executeDiagnostic(
                            sessionId,
                            deviceId,
                            diagnostic,
                            diagnostic.endsWith("_stress")
                                ? { duration_seconds: durationSeconds }
                                : {},
                        );

                        if (cancelled) {
                            return;
                        }

                        const status = item.status || "unknown";
                        setDiagnosticStatuses((current) => ({
                            ...current,
                            [diagnostic]: status,
                        }));
                        appendLog(
                            status === "passed" ? "success" : "warning",
                            `[${index + 1}/${diagnostics.length}] ${diagnostic} · ${status.toUpperCase()} · ${item.message || "No message"}`
                        );

                        if (item.details) {
                            for (const [name, value] of Object.entries(item.details)) {
                                appendLog("value", `  ${name}: ${formatValue(value)}`);
                            }
                        }
                        if (item.evaluation !== undefined && item.evaluation !== null) {
                            appendLog("value", `  evaluation: ${formatValue(item.evaluation)}`);
                        }
                    } catch (diagnosticError) {
                        const diagnosticMessage =
                            diagnosticError instanceof Error
                                ? diagnosticError.message
                                : "Diagnostic request failed.";
                        setDiagnosticStatuses((current) => ({
                            ...current,
                            [diagnostic]: "error",
                        }));
                        appendLog("error", `[${index + 1}/${diagnostics.length}] ${diagnostic} · REQUEST ERROR · ${diagnosticMessage}`);
                    }

                    setCompleted(index + 1);
                }

                if (cancelled) {
                    return;
                }

                setActiveDiagnostic("");
                setMessage("Finalizing report…");
                appendLog("system", "Saving the complete diagnostic report…");
                await completeDiagnosticSession(sessionId);

                const report = await getReport(sessionId);
                if (cancelled) {
                    return;
                }

                setResult({
                    session_id: sessionId,
                    device_id: deviceId,
                    status: report.status,
                    workflow_status: report.status,
                    report: {
                        ...report,
                        session_id: sessionId,
                    },
                });
                appendLog("success", "Report saved · all returned values are available in Results and Report.");
                setMessage("All selected diagnostics have finished.");
                setPhase("complete");
            } catch (executionError) {
                if (cancelled) {
                    return;
                }
                const executionMessage =
                    executionError instanceof Error
                        ? executionError.message
                        : "Diagnostic execution failed.";
                setError(executionMessage);
                appendLog("error", `SESSION ERROR · ${executionMessage}`);

                if (sessionId) {
                    try {
                        const partialReport = await getReport(sessionId);
                        if (!cancelled) {
                            setResult({
                                session_id: sessionId,
                                device_id: deviceId,
                                status: partialReport.status,
                                workflow_status: partialReport.status,
                                report: {
                                    ...partialReport,
                                    session_id: sessionId,
                                },
                            });
                            appendLog("warning", "A partial report is available; completed diagnostic values were preserved.");
                        }
                    } catch (reportError) {
                        if (!cancelled) {
                            appendLog(
                                "error",
                                `PARTIAL REPORT UNAVAILABLE · ${
                                    reportError instanceof Error
                                        ? reportError.message
                                        : "The stored values could not be loaded."
                                }`
                            );
                        }
                    }
                }

                setMessage("The diagnostic session could not be completed.");
                setPhase("failed");
            }
        }

        const timer = window.setTimeout(() => {
            void execute();
        }, 0);

        return () => {
            cancelled = true;
            window.clearTimeout(timer);
        };
    }, [deviceId, deviceName, diagnostics, durationSeconds, manualCheckIds, mode]);

    async function submitManualResult() {
        const check = manualChecks[completed];
        if (!sessionId || !check || savingManual) {
            return;
        }

        setSavingManual(true);
        setError("");
        try {
            await recordManualResult(sessionId, check.id, manualOutcome, manualNotes);
            appendLog(
                manualOutcome === "passed" ? "success" : manualOutcome === "failed" ? "warning" : "system",
                `Manual check · ${check.name} · ${manualOutcome.toUpperCase()}${manualNotes ? ` · ${manualNotes}` : ""}`,
            );
            setDiagnosticStatuses((current) => ({ ...current, [check.id]: manualOutcome }));
            const nextCompleted = completed + 1;
            setCompleted(nextCompleted);
            setManualNotes("");
            setManualOutcome("passed");

            if (nextCompleted === manualChecks.length) {
                await finishSession(sessionId);
            } else {
                setMessage("Record the next operator check.");
            }
        } catch (manualError) {
            const manualMessage = manualError instanceof Error
                ? manualError.message
                : "The manual result could not be saved.";
            setError(manualMessage);
            appendLog("error", `MANUAL RESULT NOT SAVED · ${manualMessage}`);
        } finally {
            setSavingManual(false);
        }
    }

    async function finishSession(id: string) {
        setMessage("Finalizing report…");
        await completeDiagnosticSession(id);
        const report = await getReport(id);
        setResult({
            session_id: id,
            device_id: deviceId,
            status: report.status,
            workflow_status: report.status,
            report: { ...report, session_id: id },
        });
        appendLog("success", "Report saved · automated values and operator outcomes are available.");
        setMessage("All selected checks have finished.");
        setPhase("complete");
    }

    function openResults() {
        if (!result) {
            return;
        }
        const sessionId = String(result.session_id || "");
        navigate(`/results?sessionId=${encodeURIComponent(sessionId)}`, {
            state: result,
        });
    }

    if (!deviceId || (mode === "manual" ? manualCheckIds.length === 0 : diagnostics.length === 0)) {
        return (
            <div className="empty-panel">
                <span className="empty-panel-icon" aria-hidden="true">!</span>
                <h2>Run details are missing</h2>
                <p>Return to device discovery, continue with the system inventory, and select at least one diagnostic.</p>
                <button
                    className="button button-primary"
                    type="button"
                    onClick={() => navigate("/devices")}
                >
                    Start again
                </button>
            </div>
        );
    }

    return (
        <div className="page-flow">
            <div className="page-header">
                <div>
                    <span className="eyebrow">STEP 4 OF 6 · DIAGNOSTIC RUN</span>
                    <h1 className="page-title">
                        {mode === "manual" ? "Manual checks" : "Running diagnostics"}
                    </h1>
                    <p className="page-description">
                        {mode === "manual"
                            ? "Follow each instruction and record the observed outcome; absent or unexpected hardware is operator-classified."
                            : "Each check runs in sequence. Live output and reported values appear in the terminal below."}
                    </p>
                </div>
            </div>

            <section className={`execution-panel execution-panel-${phase}`}>
                <div className="execution-panel-heading">
                    <div className={`execution-state-icon execution-state-${phase}`} aria-hidden="true">
                        {phase === "complete" ? "✓" : phase === "failed" ? "!" : <span />}
                    </div>
                    <div>
                        <span className="eyebrow">
                            {phase === "manual" ? "OPERATOR INPUT" : phase === "running" ? "IN PROGRESS" : phase === "complete" ? "RUN FINISHED" : "ACTION NEEDED"}
                        </span>
                        <h2>{message}</h2>
                        <p>{deviceName} <span aria-hidden="true">·</span> {completed} of {mode === "manual" ? manualCheckIds.length : diagnostics.length} checks finished</p>
                    </div>
                </div>

                {(phase === "running" || phase === "manual") && (
                    <div className="execution-progress" role="status" aria-label="Diagnostics are running">
                        <span style={{ width: `${Math.round((completed / (mode === "manual" ? manualCheckIds.length : diagnostics.length)) * 100)}%` }} />
                    </div>
                )}

                {error && <div className="error-box execution-error">{error}</div>}

                {mode === "automated" && (
                    <div className="execution-checks">
                        <div className="execution-checks-heading">
                            <strong>Diagnostic plan</strong>
                            <span>{activeDiagnostic ? `Running ${activeDiagnostic}` : phase === "running" ? "Processing" : phase === "complete" ? "Complete" : "Stopped"}</span>
                        </div>
                        {diagnostics.map((diagnostic) => {
                            const status = diagnosticStatuses[diagnostic] ||
                                (activeDiagnostic === diagnostic ? "running" : "pending");
                            return (
                                <div className="execution-item" key={diagnostic}>
                                    <span className="execution-item-name">
                                        <span className="execution-item-bullet" aria-hidden="true">
                                            {status === "running" ? "…" : status === "passed" ? "✓" : status === "pending" ? "·" : "!"}
                                        </span>
                                        {diagnostic}
                                    </span>
                                    <span className={`result-badge ${diagnosticStatusClass(status)}`}>
                                        {status}
                                    </span>
                                </div>
                            );
                        })}
                    </div>
                )}

                {phase === "manual" && manualChecks[completed] && (
                        <section className="manual-check-panel">
                            <span className="eyebrow">CHECK {completed + 1} OF {manualChecks.length}</span>
                            <h3>{manualChecks[completed].name}</h3>
                            <p>{manualChecks[completed].instructions}</p>
                            <ManualHardwareTest
                                checkId={manualChecks[completed].id}
                                onEvidence={setManualNotes}
                            />
                            <fieldset>
                                <legend>Operator result</legend>
                                {([
                                    ["passed", "Passed"],
                                    ["failed", "Failed"],
                                    ["not_applicable", "Not applicable / absent"],
                                ] as const).map(([value, label]) => (
                                    <label key={value}>
                                        <input
                                            type="radio"
                                            name="manual-outcome"
                                            value={value}
                                            checked={manualOutcome === value}
                                            onChange={() => setManualOutcome(value)}
                                        />
                                        {label}
                                    </label>
                                ))}
                            </fieldset>
                            <label className="manual-notes">
                                Notes (optional)
                                <textarea
                                    value={manualNotes}
                                    onChange={(event) => setManualNotes(event.target.value)}
                                    rows={3}
                                    maxLength={1000}
                                />
                            </label>
                            <button
                                className="button button-primary"
                                type="button"
                                onClick={() => void submitManualResult()}
                                disabled={savingManual}
                            >
                                {savingManual ? "Saving…" : completed + 1 === manualChecks.length ? "Save and finish" : "Save and continue"}
                            </button>
                        </section>
                    )}

                <section className="terminal-panel" aria-label="Diagnostic terminal output">
                    <div className="terminal-titlebar">
                        <div className="terminal-lights" aria-hidden="true">
                            <span /><span /><span />
                        </div>
                        <strong>UHDP · diagnostic output</strong>
                        <span className="terminal-live">
                            <span />{phase === "running" ? "LIVE" : phase === "complete" ? "SAVED" : "STOPPED"}
                        </span>
                    </div>
                    <div className="terminal-output" ref={terminalRef} role="log" aria-live="polite" aria-relevant="additions text">
                        {terminal.map((entry) => (
                            <div className={`terminal-line terminal-${entry.level}`} key={entry.id}>
                                <time>{entry.time}</time>
                                <span className="terminal-prompt" aria-hidden="true">›</span>
                                <pre>{entry.text}</pre>
                            </div>
                        ))}
                        {phase === "running" && (
                            <div className="terminal-cursor-line" aria-hidden="true">
                                <span>›</span><i />
                            </div>
                        )}
                        {terminal.length === 0 && <span className="terminal-waiting">Waiting for diagnostic output…</span>}
                    </div>
                </section>

                <div className="execution-actions">
                    {phase === "complete" && (
                        <button className="button button-primary" type="button" onClick={openResults}>
                            Review all values <span aria-hidden="true">→</span>
                        </button>
                    )}
                    {phase === "failed" && (
                        <>
                            {result && (
                                <button className="button button-primary" type="button" onClick={openResults}>
                                    Review available values
                                </button>
                            )}
                            <button
                                className="button button-secondary"
                                type="button"
                                onClick={() => {
                                    const query = new URLSearchParams({
                                        deviceId,
                                        selected: diagnostics.join(","),
                                    });
                                    navigate(`/diagnostics?${query.toString()}`);
                                }}
                            >
                                Return to diagnostics
                            </button>
                        </>
                    )}
                </div>
            </section>
        </div>
    );
}
