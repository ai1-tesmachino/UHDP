import { useEffect, useMemo, useRef, useState } from "react";
import { useLocation, useNavigate, useSearchParams } from "react-router-dom";

import {
    completeDiagnosticSession,
    executeDiagnostic,
    getDiagnosticSession,
    getManualChecks,
    ManualCheck,
    recordManualResult,
    reopenDiagnosticSession,
} from "../api/execution";
import { executeProfile } from "../api/profiles";
import { getReport } from "../api/reports";
import { getSessionEvidence, EvidenceMetadata, uploadEvidence } from "../api/evidence";
import ManualHardwareTest from "../components/ManualHardwareTest";
import { useQcSession } from "../session/SessionContext";

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
        station_id?: string;
        customer_reference?: string;
        workflow_type?: string;
        profile_name?: string;
        retest_of_session_id?: string;
        planned_diagnostics?: string[];
        planned_manual_checks?: string[];
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
    const {
        activeSessionId,
        loading: sessionLoading,
        startSession,
        activateSession,
    } = useQcSession();
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
    const requestedSessionId = params.get("sessionId") || activeSessionId;
    const isRetest = params.get("retest") === "1";
    const deviceName = params.get("deviceName") || execution?.deviceName || deviceId;
    const intake = execution?.intake || {
        asset_tag: params.get("assetTag") || undefined,
        technician: params.get("technician") || undefined,
        station_id: params.get("stationId") || undefined,
        customer_reference: params.get("customerReference") || undefined,
        workflow_type: params.get("workflowType") || undefined,
        profile_name: params.get("profileName") || undefined,
        retest_of_session_id: params.get("retestOf") || undefined,
        planned_diagnostics: diagnostics,
        planned_manual_checks: manualCheckIds,
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
    const [evidenceItems, setEvidenceItems] = useState<EvidenceMetadata[]>([]);
    const [evidenceFile, setEvidenceFile] = useState<File | null>(null);
    const [evidenceConfirmed, setEvidenceConfirmed] = useState(false);
    const [uploadingEvidence, setUploadingEvidence] = useState(false);
    const [manualChecks, setManualChecks] = useState<ManualCheck[]>([]);
    const [manualOutcome, setManualOutcome] = useState<"passed" | "failed" | "warning" | "not_applicable" | "blocked" | "not_run" | null>(null);
    const [manualNotes, setManualNotes] = useState("");
    const [manualEvidence, setManualEvidence] = useState("");
    const [scanStatus, setScanStatus] = useState<"success" | "no_results" | "unsupported" | "error" | "not_attempted">("not_attempted");
    const [detectedDevicesInput, setDetectedDevicesInput] = useState("");
    const [savingManual, setSavingManual] = useState(false);
    const [stopRequested, setStopRequested] = useState(false);
    const stopRequestedRef = useRef(false);
    const terminalRef = useRef<HTMLDivElement>(null);

    useEffect(() => {
        if (!sessionId) return;
        let active = true;
        getSessionEvidence(sessionId)
            .then((items) => {
                if (active) setEvidenceItems(items);
            })
            .catch((evidenceError: unknown) => {
                if (active) {
                    appendLog(
                        "warning",
                        `Evidence inventory unavailable · ${
                            evidenceError instanceof Error
                                ? evidenceError.message
                                : "local SQLite evidence storage may not be enabled"
                        }`,
                    );
                }
            });
        return () => {
            active = false;
        };
    }, [sessionId]);

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

    function stopAfterCurrentCheck() {
        stopRequestedRef.current = true;
        setStopRequested(true);
        appendLog("warning", "Stop requested · the current backend request will finish before another check is started.");
    }

    useEffect(() => {
        const output = terminalRef.current;
        if (output) {
            output.scrollTop = output.scrollHeight;
        }
    }, [terminal]);

    useEffect(() => {
        if (sessionLoading) return;
        if (!deviceId || (mode === "manual" ? manualCheckIds.length === 0 : diagnostics.length === 0)) {
            setPhase("failed");
            setError("A system target and at least one diagnostic are required.");
            return;
        }

        let cancelled = false;
        let sessionId = requestedSessionId;
        let checksToRun = diagnostics;
        let manualChecksToRun = manualCheckIds;
        let completedBeforeRun = 0;

        async function execute() {
            try {
                stopRequestedRef.current = false;
                appendLog("system", `UHDP diagnostic session · target ${deviceName}`);
                appendLog(
                    "system",
                    `Plan loaded · ${mode === "manual" ? manualCheckIds.length : diagnostics.length} checks`,
                );
                setMessage(requestedSessionId ? "Restoring QC session…" : "Creating QC session…");

                if (requestedSessionId) {
                    await activateSession(requestedSessionId);
                    if (isRetest) {
                        await reopenDiagnosticSession(requestedSessionId);
                    }
                    const session = await getDiagnosticSession(requestedSessionId);
                    if (!isRetest && session.status === "completed") {
                        sessionId = session.session_id;
                        setSessionId(sessionId);
                        const report = await getReport(sessionId);
                        setResult({
                            session_id: sessionId,
                            device_id: deviceId,
                            status: report.status,
                            workflow_status: report.status,
                            report: { ...report, session_id: sessionId },
                        });
                        setMessage("Saved results loaded for this QC session.");
                        setPhase("complete");
                        return;
                    }
                    if (!isRetest) {
                        const existingResults = session.test_results || {};
                        const hasSavedOutcome = (checkId: string) => {
                            const prior = existingResults[checkId];
                            if (typeof prior !== "object" || prior === null) return false;
                            const status = (prior as Record<string, unknown>).test_status;
                            return typeof status === "string" &&
                                !["not_run", "pending", "running"].includes(status.toLowerCase());
                        };
                        if (mode === "manual") {
                            manualChecksToRun = manualCheckIds.filter((checkId) => !hasSavedOutcome(checkId));
                        } else {
                            checksToRun = diagnostics.filter((diagnostic) => !hasSavedOutcome(diagnostic));
                            completedBeforeRun = diagnostics.length - checksToRun.length;
                            setDiagnosticStatuses(
                                Object.fromEntries(
                                    diagnostics.flatMap((diagnostic) => {
                                        const prior = existingResults[diagnostic];
                                        if (typeof prior !== "object" || prior === null) return [];
                                        const status = (prior as Record<string, unknown>).test_status;
                                        return typeof status === "string" ? [[diagnostic, status]] : [];
                                    }),
                                ),
                            );
                            setCompleted(completedBeforeRun);
                        }
                        if ((mode === "manual" ? manualChecksToRun : checksToRun).length === 0) {
                            sessionId = session.session_id;
                            setSessionId(sessionId);
                            const report = await getReport(sessionId);
                            setResult({
                                session_id: sessionId,
                                device_id: deviceId,
                                status: report.status,
                                workflow_status: report.status,
                                report: { ...report, session_id: sessionId },
                            });
                            setMessage("All selected checks already have saved results.");
                            setPhase("complete");
                            return;
                        }
                    }
                } else {
                    const session = await startSession();
                    sessionId = session.session_id;
                }

                if (!sessionId) {
                    throw new Error("The backend did not return a session ID.");
                }

                appendLog("success", `QC session · ${sessionId}`);
                setSessionId(sessionId);

                if (mode === "manual") {
                    const catalog = await getManualChecks();
                    if (cancelled) {
                        return;
                    }
                    const selectedChecks = catalog.filter((check) => manualChecksToRun.includes(check.id));
                    if (selectedChecks.length !== manualChecksToRun.length) {
                        throw new Error("One or more selected manual checks are no longer available.");
                    }
                    setManualChecks(selectedChecks);
                    setMessage("Follow the operator instructions and record each result.");
                    appendLog("system", `Manual checklist loaded · ${selectedChecks.length} checks`);
                    setPhase("manual");
                    return;
                }

                let stoppedByOperator = false;
                for (const [index, diagnostic] of checksToRun.entries()) {
                    if (cancelled) {
                        return;
                    }
                    if (stopRequestedRef.current) {
                        stoppedByOperator = true;
                        setDiagnosticStatuses((current) => ({
                            ...current,
                            ...Object.fromEntries(checksToRun.slice(index).map((item) => [item, "not_run"])),
                        }));
                        break;
                    }

                    setActiveDiagnostic(diagnostic);
                    setMessage(`Running ${diagnostic} diagnostic…`);
                    appendLog("running", `[${completedBeforeRun + index + 1}/${diagnostics.length}] ${diagnostic} · starting`);

                    try {
                        const diagnosticParameters = diagnostic.endsWith("_stress")
                            ? { duration_seconds: durationSeconds }
                            : {};
                        const item: DiagnosticResult =
                            intake.profile_name &&
                            intake.profile_name !== "custom_selection"
                            ? (
                                await executeProfile(
                                    intake.profile_name,
                                    sessionId,
                                    deviceId,
                                    [diagnostic],
                                    { [diagnostic]: diagnosticParameters },
                                )
                            ).results[0]
                            : await executeDiagnostic(
                                sessionId,
                                deviceId,
                                diagnostic,
                                diagnosticParameters,
                            );
                        if (!item) {
                            throw new Error(`Profile execution returned no result for ${diagnostic}.`);
                        }

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
                            `[${completedBeforeRun + index + 1}/${diagnostics.length}] ${diagnostic} · ${status.toUpperCase()} · ${item.message || "No message"}`
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
                        appendLog("error", `[${completedBeforeRun + index + 1}/${diagnostics.length}] ${diagnostic} · REQUEST ERROR · ${diagnosticMessage}`);
                    }

                    setCompleted(completedBeforeRun + index + 1);
                }

                if (cancelled) {
                    return;
                }

                setActiveDiagnostic("");
                setMessage(stoppedByOperator ? "Saving partial results…" : "Finalizing report…");
                appendLog(
                    stoppedByOperator ? "warning" : "system",
                    stoppedByOperator
                        ? "Stop requested · no additional checks were started; saving results from completed checks."
                        : "Saving the complete diagnostic report…",
                );
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
                if (stoppedByOperator) {
                    appendLog("warning", "Unstarted checks remain not run; review the partial report before making a QA decision.");
                }
                setMessage(stoppedByOperator ? "Stopped after the current check; partial results are saved." : "All selected diagnostics have finished.");
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
    }, [deviceId, deviceName, diagnostics, durationSeconds, manualCheckIds, mode, requestedSessionId, sessionLoading, startSession, activateSession, isRetest]);

    async function submitManualResult() {
        const check = manualChecks[completed];
        if (!sessionId || !check || savingManual || !manualOutcome) {
            return;
        }

        setSavingManual(true);
        setError("");
        try {
            const notes = [manualEvidence, manualNotes.trim()].filter(Boolean).join("\nTechnician note: ");
            const technicianDecision = {
                passed: "working",
                failed: "not_working",
                warning: null,
                not_applicable: null,
                blocked: "unable_to_verify",
                not_run: null,
            } as const;
            const legacyOutcome = manualOutcome;
            await recordManualResult(sessionId, check.id, {
                outcome: legacyOutcome,
                notes,
                scan_status: scanStatus,
                detected_devices: detectedDevicesInput
                    .split(",")
                    .map((item) => item.trim())
                    .filter(Boolean),
                technician_decision: technicianDecision[legacyOutcome],
                evidence: manualEvidence ? { interactive_observation: manualEvidence } : {},
            });
            appendLog(
                manualOutcome === "passed" ? "success" : manualOutcome === "failed" ? "warning" : "system",
                `Manual check · ${check.name} · ${manualOutcome.toUpperCase()}${notes ? ` · ${notes}` : ""}`,
            );
            setDiagnosticStatuses((current) => ({ ...current, [check.id]: manualOutcome }));
            const nextCompleted = completed + 1;
            setCompleted(nextCompleted);
            setManualNotes("");
            setManualEvidence("");
            setScanStatus("not_attempted");
            setDetectedDevicesInput("");
            setManualOutcome(null);

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

    async function saveEvidence() {
        if (!sessionId || !evidenceFile || !evidenceConfirmed || uploadingEvidence) return;
        if (evidenceFile.size > 100 * 1024 * 1024) {
            setError("Evidence files must be 100 MiB or smaller.");
            return;
        }
        setUploadingEvidence(true);
        setError("");
        try {
            const metadata = await uploadEvidence(sessionId, evidenceFile);
            setEvidenceItems((items) => [...items, metadata]);
            appendLog("success", `Evidence saved locally · ${metadata.original_filename} · SHA-256 ${metadata.sha256}`);
            setEvidenceFile(null);
            setEvidenceConfirmed(false);
        } catch (uploadError) {
            const message = uploadError instanceof Error
                ? uploadError.message
                : "Evidence could not be saved.";
            setError(message);
            appendLog("error", `EVIDENCE NOT SAVED · ${message}`);
        } finally {
            setUploadingEvidence(false);
        }
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
                    onClick={() => navigate(requestedSessionId ? `/devices?sessionId=${encodeURIComponent(requestedSessionId)}` : "/devices")}
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
                    <span className="eyebrow">INSPECTION · STEP BY STEP</span>
                    <h1 className="page-title">
                        {mode === "manual" ? "Guided manual check" : "Automatic checks"}
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
                            <span className="eyebrow">STEP {completed + 1} OF {manualChecks.length}</span>
                            <h3>{manualChecks[completed].name}</h3>
                            <p>{manualChecks[completed].instructions}</p>
                            <ManualHardwareTest
                                checkId={manualChecks[completed].id}
                                onEvidence={setManualEvidence}
                            />
                            <div className="manual-feedback" role="group" aria-label="How did the test go?">
                                <span>How did the test go?</span>
                                <div className="manual-outcome-buttons">
                                    {([
                                        [
                                            "passed",
                                            manualChecks[completed].id === "speaker_output"
                                                ? "I can hear it"
                                                : manualChecks[completed].id === "microphone_input"
                                                  ? "Recording is clear"
                                                  : manualChecks[completed].id === "webcam_image"
                                                    ? "Image is clear"
                                                    : "Works",
                                        ],
                                        [
                                            "failed",
                                            manualChecks[completed].id === "speaker_output"
                                                ? "Can't hear it"
                                                : manualChecks[completed].id === "microphone_input"
                                                  ? "Recording failed"
                                                  : manualChecks[completed].id === "webcam_image"
                                                    ? "No clear image"
                                                    : "Failed",
                                        ],
                                        ["warning", "Warning"],
                                        ["not_applicable", "Not fitted"],
                                        ["blocked", "Unable to verify"],
                                        ["not_run", "Not run"],
                                    ] as const).map(([value, label]) => (
                                        <button
                                            className={`manual-outcome-button${manualOutcome === value ? " selected" : ""}`}
                                            key={value}
                                            type="button"
                                            aria-pressed={manualOutcome === value}
                                            onClick={() => setManualOutcome(value)}
                                        >
                                            {label}
                                        </button>
                                    ))}
                                </div>
                            </div>
                            <div className="manual-evidence-fields">
                                <label>
                                    Scan / detection status
                                    <select
                                        value={scanStatus}
                                        onChange={(event) => setScanStatus(event.target.value as typeof scanStatus)}
                                    >
                                        <option value="not_attempted">Not attempted</option>
                                        <option value="success">Found / scan succeeded</option>
                                        <option value="no_results">No results</option>
                                        <option value="unsupported">Unsupported</option>
                                        <option value="error">Scan error</option>
                                    </select>
                                </label>
                                <label>
                                    Detected device(s), if any
                                    <input
                                        value={detectedDevicesInput}
                                        onChange={(event) => setDetectedDevicesInput(event.target.value)}
                                        placeholder="Comma-separated device names or identifiers"
                                    />
                                </label>
                                <small>Detection is recorded separately and never marks the functional test as passed by itself.</small>
                            </div>
                            <details className="manual-extra-notes">
                                <summary>Add a note (optional)</summary>
                                <textarea
                                    aria-label="Technician note"
                                    value={manualNotes}
                                    onChange={(event) => setManualNotes(event.target.value)}
                                    rows={2}
                                    maxLength={1000}
                                    placeholder="Describe any issue or observation"
                                />
                            </details>
                            <button
                                className="button button-primary"
                                type="button"
                                onClick={() => void submitManualResult()}
                                disabled={savingManual || !manualOutcome}
                            >
                                {savingManual ? "Saving…" : completed + 1 === manualChecks.length ? "Continue to results" : "Save and next step"}
                            </button>
                        </section>
                    )}

                {mode === "automated" && <section className="terminal-panel" aria-label="Diagnostic terminal output">
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
                </section>}

                {sessionId && (
                    <section className="manual-check-panel evidence-capture-panel">
                        <span className="eyebrow">LOCAL EVIDENCE</span>
                        <h3>Photos, logs, or attachments</h3>
                        <p>
                            Evidence is stored on the appliance, outside the database,
                            with a SHA-256 integrity checksum. It is not uploaded to cloud
                            storage until the local sync engine is configured.
                        </p>
                        <label>
                            Select an evidence file
                            <input
                                type="file"
                                accept="image/jpeg,image/png,image/webp,video/mp4,video/webm,text/plain,text/csv,application/json,application/pdf,application/octet-stream"
                                disabled={uploadingEvidence}
                                onChange={(event) => {
                                    setEvidenceFile(event.target.files?.[0] || null);
                                    setEvidenceConfirmed(false);
                                }}
                            />
                        </label>
                        {evidenceFile && (
                            <>
                                <span>{evidenceFile.name} · {(evidenceFile.size / 1024 / 1024).toFixed(2)} MiB</span>
                                <label className="storage-confirmation">
                                    <input
                                        type="checkbox"
                                        checked={evidenceConfirmed}
                                        onChange={(event) => setEvidenceConfirmed(event.target.checked)}
                                    />
                                    I confirm this file is relevant to this QC session.
                                </label>
                                <button
                                    className="button button-secondary"
                                    type="button"
                                    disabled={uploadingEvidence || !evidenceConfirmed}
                                    onClick={() => void saveEvidence()}
                                >
                                    {uploadingEvidence ? "Saving evidence…" : "Save evidence locally"}
                                </button>
                            </>
                        )}
                        {evidenceItems.length > 0 && (
                            <ul className="evidence-file-list">
                                {evidenceItems.map((item) => (
                                    <li key={item.evidence_id}>
                                        <a
                                            href={`${window.location.protocol}//${window.location.hostname === "localhost" ? "127.0.0.1" : window.location.hostname}:8000/evidence/${encodeURIComponent(item.evidence_id)}`}
                                            target="_blank"
                                            rel="noreferrer"
                                        >
                                            {item.original_filename}
                                        </a>
                                        <span>{(item.size_bytes / 1024 / 1024).toFixed(2)} MiB · {item.sync_state || "Pending sync"}</span>
                                    </li>
                                ))}
                            </ul>
                        )}
                    </section>
                )}

                <div className="execution-actions">
                    {phase === "running" && mode === "automated" && (
                        <button
                            className="button button-danger"
                            type="button"
                            onClick={stopAfterCurrentCheck}
                            disabled={!sessionId || stopRequested}
                        >
                            {stopRequested ? "Stopping after current check…" : "Stop after current check"}
                        </button>
                    )}
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
                                        sessionId: String(result.session_id || ""),
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
