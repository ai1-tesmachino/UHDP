import axios from "axios";
import {
    ArrowLeft,
    ArrowRight,
    Check,
    ChevronLeft,
    ChevronRight,
    Expand,
    Eye,
    EyeOff,
    Monitor,
    Pause,
    Play,
    RotateCcw,
    X,
} from "lucide-react";
import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { Link, useLocation, useNavigate, useParams } from "react-router-dom";
import { toast } from "sonner";
import {
    completeDisplayDiagnostic,
    DisplayDiagnostic,
    DisplayTestOutcome,
    DiagnosticSession,
    getDiagnosticSession,
    recordDisplayTestResult,
    startDisplayDiagnostic,
    startDisplayTest,
    updateDisplayProgress,
} from "@/api/execution";
import {
    AlertDialog,
    AlertDialogAction,
    AlertDialogCancel,
    AlertDialogContent,
    AlertDialogDescription,
    AlertDialogFooter,
    AlertDialogHeader,
    AlertDialogTitle,
} from "@/components/ui/alert-dialog";
import DisplayCanvas from "./DisplayCanvas";
import {
    DEFECT_TYPES,
    DISPLAY_TEST_CATALOG,
    getTestOutcome,
    REQUIRED_DISPLAY_TESTS,
} from "./displayTestTypes";
import "./displayDiagnostic.css";

type DefectDraft = {
    type: string;
    location: string;
    count: string;
};

type PendingResult = {
    testId: string;
    attemptId: string;
    status: DisplayTestOutcome;
    notes: string;
    defects: Array<{ type: string; location: string; count?: number }>;
};

function getErrorMessage(error: unknown): string {
    if (axios.isAxiosError(error)) {
        if (!error.response) return "Unable to connect to UHDP diagnostic service.";
        const detail = error.response.data?.detail;
        if (typeof detail === "string" && detail.trim()) return detail;
        if (error.response.status === 404) return "The QC session or display diagnostic could not be found.";
        if (error.response.status === 409) return "This QC record is read-only or is not ready for that action.";
        return "The display diagnostic request could not be saved.";
    }
    return error instanceof Error ? error.message : "The display diagnostic request could not be completed.";
}

function createAttemptId() {
    if (typeof crypto !== "undefined" && typeof crypto.randomUUID === "function") {
        return crypto.randomUUID();
    }
    return "xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx".replace(/[xy]/g, (character) => {
        const value = Math.floor(Math.random() * 16);
        return (character === "x" ? value : (value & 0x3) | 0x8).toString(16);
    });
}

function testStatusLabel(
    status: string,
) {
    if (status === "passed") return "Passed";
    if (status === "failed") return "Failed";
    if (status === "skipped") return "Skipped";
    if (status === "in_progress") return "In progress";
    if (status === "inconclusive") return "Requires verification";
    if (status === "complete") return "Completed";
    return "Not started";
}

function statusClass(status: string) {
    if (status === "passed") return "is-passed";
    if (status === "failed") return "is-failed";
    if (status === "skipped") return "is-skipped";
    if (status === "in_progress") return "is-in-progress";
    if (status === "inconclusive") return "is-inconclusive";
    return "is-not-started";
}

function getCurrentAttempt(test?: DisplayDiagnostic["tests"][string]) {
    const attempts = test?.attempts || [];
    return [...attempts]
        .reverse()
        .find((attempt) => attempt.status === "in_progress");
}

function getLatestAttempt(test?: DisplayDiagnostic["tests"][string]) {
    const attempts = test?.attempts || [];
    return attempts.length ? attempts[attempts.length - 1] : undefined;
}

function readMetadata(metadata: Record<string, unknown>, key: string) {
    const value = metadata[key];
    if (value === null || value === undefined || value === "") return "Not available";
    if (typeof value === "number" && key === "refresh_rate_hz") return `${value} Hz`;
    if (typeof value === "object") return JSON.stringify(value);
    return String(value);
}

function getConnectedOutputs(metadata: Record<string, unknown>) {
    const connectors = metadata.connectors;
    if (!Array.isArray(connectors)) return "Not available";
    const connected = connectors.flatMap((connector) => {
        if (typeof connector !== "object" || connector === null) return [];
        const record = connector as Record<string, unknown>;
        return record.status === "connected" && typeof record.name === "string"
            ? [record.name]
            : [];
    });
    return connected.length ? connected.join(", ") : "No connected outputs reported";
}

export default function DisplayDiagnosticPage() {
    const { sessionId = "" } = useParams();
    const location = useLocation();
    const navigate = useNavigate();
    const stageRef = useRef<HTMLDivElement>(null);
    const pendingStartRef = useRef<{ testId: string; attemptId: string } | null>(null);
    const [session, setSession] = useState<DiagnosticSession | null>(null);
    const [diagnostic, setDiagnostic] = useState<DisplayDiagnostic | null>(null);
    const [currentTestId, setCurrentTestId] = useState("display_information");
    const [patternIndex, setPatternIndex] = useState(0);
    const [patternActive, setPatternActive] = useState(true);
    const [controlsVisible, setControlsVisible] = useState(true);
    const [instructionsVisible, setInstructionsVisible] = useState(true);
    const [autoSequence, setAutoSequence] = useState(false);
    const [loading, setLoading] = useState(true);
    const [saving, setSaving] = useState(false);
    const [progressSaving, setProgressSaving] = useState(false);
    const [pendingStart, setPendingStart] = useState(false);
    const [progressNeedsRetry, setProgressNeedsRetry] = useState(false);
    const [pendingResult, setPendingResult] = useState<PendingResult | null>(null);
    const [exitConfirmation, setExitConfirmation] = useState(false);
    const [fullscreen, setFullscreen] = useState(false);
    const [showDefectForm, setShowDefectForm] = useState(false);
    const [notes, setNotes] = useState<Record<string, string>>({});
    const [defects, setDefects] = useState<Record<string, DefectDraft>>({});
    const [error, setError] = useState("");

    useEffect(() => {
        let current = true;
        setLoading(true);
        setError("");
        Promise.all([
            getDiagnosticSession(sessionId),
            startDisplayDiagnostic(sessionId),
        ])
            .then(([loadedSession, loadedDiagnostic]) => {
                if (!current) return;
                setSession(loadedSession);
                setDiagnostic(loadedDiagnostic);
                setCurrentTestId(
                    DISPLAY_TEST_CATALOG.some(
                        (test) => test.id === loadedDiagnostic.current_test_id,
                    )
                        ? loadedDiagnostic.current_test_id
                        : "display_information",
                );
            })
            .catch((loadError: unknown) => {
                if (current) setError(getErrorMessage(loadError));
            })
            .finally(() => {
                if (current) setLoading(false);
            });
        return () => {
            current = false;
        };
    }, [sessionId]);

    useEffect(() => {
        const updateFullscreen = () => setFullscreen(document.fullscreenElement === stageRef.current);
        document.addEventListener("fullscreenchange", updateFullscreen);
        return () => document.removeEventListener("fullscreenchange", updateFullscreen);
    }, []);

    useEffect(() => {
        if (!autoSequence || currentTestId !== "dead_pixel" || !patternActive) return;
        const timer = window.setInterval(() => {
            setPatternIndex((index) => (index + 1) % 5);
        }, 1400);
        return () => window.clearInterval(timer);
    }, [autoSequence, currentTestId, patternActive]);

    const currentTest = DISPLAY_TEST_CATALOG.find((test) => test.id === currentTestId)
        || DISPLAY_TEST_CATALOG[0];
    const testState = diagnostic?.tests?.[currentTest.id];
    const activeAttempt = getCurrentAttempt(testState);
    const latestAttempt = getLatestAttempt(testState);
    const currentNote = notes[currentTest.id] ?? testState?.latest_result?.notes ?? "";
    const defectDraft = defects[currentTest.id] || { type: "DEAD_PIXEL", location: "", count: "" };
    const isReadOnly = diagnostic?.status === "completed" ||
        ["completed", "complete"].includes((session?.status || "").toLowerCase());
    const completedCount = REQUIRED_DISPLAY_TESTS.filter(
        (test) => Boolean(diagnostic?.tests?.[test.id]?.latest_result),
    ).length;
    const allRequiredDone = completedCount === REQUIRED_DISPLAY_TESTS.length &&
        REQUIRED_DISPLAY_TESTS.every(
            (test) => !diagnostic?.tests?.[test.id]?.attempts.some(
                (attempt) => attempt.status === "in_progress",
            ),
        );
    const currentIndex = DISPLAY_TEST_CATALOG.findIndex((test) => test.id === currentTest.id);
    const patternCount = currentTest.patterns.length;
    const patternName = currentTest.patterns[patternIndex % Math.max(patternCount, 1)];
    const displayMetadata = diagnostic?.display_metadata || {};

    const updateCurrentTest = useCallback(async (testId: string) => {
        setCurrentTestId(testId);
        setPatternIndex(0);
        setPatternActive(true);
        setAutoSequence(false);
        setShowDefectForm(false);
        setError("");
        if (!sessionId || !diagnostic || diagnostic.status === "completed") return;
        setProgressSaving(true);
        try {
            const updated = await updateDisplayProgress(sessionId, testId);
            setDiagnostic(updated);
            setProgressNeedsRetry(false);
        } catch (saveError) {
            setProgressNeedsRetry(true);
            setError(getErrorMessage(saveError));
        } finally {
            setProgressSaving(false);
        }
    }, [diagnostic, sessionId]);

    async function retryProgress() {
        if (!sessionId) return;
        setProgressSaving(true);
        try {
            const updated = await updateDisplayProgress(sessionId, currentTestId);
            setDiagnostic(updated);
            setProgressNeedsRetry(false);
            setError("");
        } catch (saveError) {
            setProgressNeedsRetry(true);
            setError(getErrorMessage(saveError));
        } finally {
            setProgressSaving(false);
        }
    }

    const savePendingStart = useCallback(async (testId: string, attemptId: string) => {
        setPendingStart(true);
        setError("");
        try {
            const response = await startDisplayTest(sessionId, testId, attemptId);
            setDiagnostic(response.diagnostic);
            pendingStartRef.current = null;
            setPendingStart(false);
            toast.success("Display test started.");
        } catch (startError) {
            pendingStartRef.current = { testId, attemptId };
            setPendingStart(false);
            setError(getErrorMessage(startError));
        }
    }, [sessionId]);

    async function startOrResumeTest(retest = false) {
        if (isReadOnly || currentTest.kind === "assessment" || pendingStart) return;
        if (
            !retest &&
            pendingStartRef.current?.testId === currentTest.id
        ) {
            await retryStart();
            return;
        }
        if (activeAttempt && !retest) {
            setError("");
            return;
        }
        const attemptId = createAttemptId();
        pendingStartRef.current = { testId: currentTest.id, attemptId };
        await savePendingStart(currentTest.id, attemptId);
    }

    async function retryStart() {
        const pending = pendingStartRef.current;
        if (pending) await savePendingStart(pending.testId, pending.attemptId);
    }

    const saveResult = useCallback(async (pending: PendingResult) => {
        setSaving(true);
        setError("");
        try {
            const response = await recordDisplayTestResult(sessionId, pending.testId, {
                attempt_id: pending.attemptId,
                status: pending.status,
                notes: pending.notes,
                defects: pending.defects,
            });
            setDiagnostic(response.diagnostic);
            setPendingResult(null);
            setShowDefectForm(false);
            toast.success("Display test result saved.");
        } catch (saveError) {
            setPendingResult(pending);
            setError(getErrorMessage(saveError));
        } finally {
            setSaving(false);
        }
    }, [sessionId]);

    async function submitOutcome(status: DisplayTestOutcome, defect?: PendingResult["defects"][number]) {
        if (!activeAttempt || saving || isReadOnly) return;
        const note = notes[currentTest.id] ?? "";
        const nextDefects = defect ? [defect] : [];
        const pending = {
            testId: currentTest.id,
            attemptId: activeAttempt.attempt_id,
            status,
            notes: note,
            defects: nextDefects,
        };
        setPendingResult(pending);
        await saveResult(pending);
    }

    async function submitDefect() {
        const note = (notes[currentTest.id] ?? "").trim();
        if (defectDraft.type === "OTHER" && !note) {
            setError("Add a technician note when the defect category is Other.");
            return;
        }
        const parsedCount = defectDraft.count.trim() ? Number(defectDraft.count) : undefined;
        if (parsedCount !== undefined && (!Number.isInteger(parsedCount) || parsedCount < 1)) {
            setError("Defect count must be a positive whole number.");
            return;
        }
        const defect = {
            type: defectDraft.type,
            location: defectDraft.location.trim(),
            ...(parsedCount !== undefined ? { count: parsedCount } : {}),
        };
        await submitOutcome("failed", defect);
    }

    async function retryResult() {
        if (pendingResult) await saveResult(pendingResult);
    }

    async function completeDiagnostic() {
        if (!sessionId || !allRequiredDone || isReadOnly || saving || pendingResult) return;
        setSaving(true);
        setError("");
        try {
            const completed = await completeDisplayDiagnostic(sessionId);
            setDiagnostic(completed);
            toast.success("Display diagnostic completed.");
        } catch (completeError) {
            setError(getErrorMessage(completeError));
        } finally {
            setSaving(false);
        }
    }

    const rawReturnTo = (location.state as { returnTo?: string } | null)?.returnTo
        || new URLSearchParams(location.search).get("returnTo")
        || "";
    const safeReturnTo = rawReturnTo.startsWith("/") && !rawReturnTo.startsWith("//")
        ? rawReturnTo
        : `/qc?sessionId=${encodeURIComponent(sessionId)}&stage=functional`;

    function exitWorkspace() {
        if (activeAttempt || pendingResult || pendingStart) {
            setExitConfirmation(true);
            return;
        }
        navigate(safeReturnTo);
    }

    function confirmExit() {
        setExitConfirmation(false);
        navigate(safeReturnTo);
    }

    async function toggleFullscreen() {
        if (!stageRef.current) return;
        try {
            if (document.fullscreenElement) {
                await document.exitFullscreen();
            } else if (stageRef.current.requestFullscreen) {
                await stageRef.current.requestFullscreen();
            } else {
                setError("Fullscreen is unavailable in this browser. You can continue in the testing workspace.");
            }
        } catch {
            setError("Fullscreen is unavailable in this browser. You can continue in the testing workspace.");
        }
    }

    function navigateRelative(direction: -1 | 1) {
        const nextIndex = Math.max(
            0,
            Math.min(DISPLAY_TEST_CATALOG.length - 1, currentIndex + direction),
        );
        const next = DISPLAY_TEST_CATALOG[nextIndex];
        if (next) void updateCurrentTest(next.id);
    }

    function restartCurrentTest() {
        setPatternIndex(0);
        setPatternActive(true);
        setAutoSequence(false);
        if (testState?.latest_result && !activeAttempt && !isReadOnly) {
            void startOrResumeTest(true);
        }
    }

    function setPattern(nextIndex: number) {
        if (patternCount <= 0) return;
        setPatternIndex((nextIndex + patternCount) % patternCount);
        setPatternActive(true);
    }

    const outcomeForAssessment = useMemo(
        () => REQUIRED_DISPLAY_TESTS.map((test) => ({
            ...test,
            outcome: getTestOutcome(diagnostic, test.id),
            result: diagnostic?.tests?.[test.id]?.latest_result,
        })),
        [diagnostic],
    );

    if (loading) {
        return (
            <main className="display-diagnostic-loading">
                <Monitor aria-hidden="true" />
                <p>Connecting to UHDP diagnostic service…</p>
            </main>
        );
    }

    if (error && !diagnostic) {
        return (
            <main className="display-diagnostic-error">
                <Monitor aria-hidden="true" />
                <h1>Display diagnostics unavailable</h1>
                <p role="alert">{error}</p>
                <Link className="display-button display-button-primary" to={safeReturnTo}>
                    <ArrowLeft size={16} aria-hidden="true" /> Return to QC
                </Link>
            </main>
        );
    }

    if (!diagnostic || !session) return null;

    const currentStatus = currentTest.kind === "assessment"
        ? diagnostic.status === "completed"
            ? diagnostic.overall_status || "inconclusive"
            : allRequiredDone
              ? "in_progress"
              : "not_started"
        : getTestOutcome(diagnostic, currentTest.id);
    const canRecord = Boolean(activeAttempt) && !isReadOnly && !saving && !pendingResult;

    return (
        <main className={`display-workspace${instructionsVisible ? "" : " instructions-hidden"}`}>
            <header className="display-topbar">
                <div className="display-brand">
                    <span className="display-brand-mark"><Monitor size={18} aria-hidden="true" /></span>
                    <span><strong>UHDP</strong><small>Display Diagnostics</small></span>
                </div>
                <div className="display-session-identity">
                    <strong>{getDeviceName(session)}</strong>
                    <span>Session {session.session_id}</span>
                    <span>Serial {getSerial(session)}</span>
                </div>
                <div className="display-top-progress" aria-label={`${completedCount} of ${REQUIRED_DISPLAY_TESTS.length} tests complete`}>
                    <span>{currentTest.kind === "assessment" ? "Final review" : `Test ${currentIndex + 1} of ${REQUIRED_DISPLAY_TESTS.length}`}</span>
                    <span className="display-progress-track">
                        <span style={{ width: `${completedCount / REQUIRED_DISPLAY_TESTS.length * 100}%` }} />
                    </span>
                    <strong>{completedCount}/{REQUIRED_DISPLAY_TESTS.length}</strong>
                </div>
                <button className="display-icon-button display-exit-button" type="button" onClick={exitWorkspace}>
                    <X size={17} aria-hidden="true" /> Exit
                </button>
            </header>

            {isReadOnly && (
                <div className="display-readonly-banner" role="status">
                    This display diagnostic is complete and read-only.
                </div>
            )}

            {error && (
                <div className="display-error-banner" role="alert">
                    <span>{error}</span>
                    {pendingResult && (
                        <button className="display-text-button" type="button" disabled={saving} onClick={() => void retryResult()}>
                            Retry result save
                        </button>
                    )}
                    {(pendingStart || pendingStartRef.current) && (
                        <button className="display-text-button" type="button" onClick={() => void retryStart()}>
                            Retry test start
                        </button>
                    )}
                    {progressNeedsRetry && !pendingResult && !pendingStart && !isReadOnly &&
                        (
                            <button className="display-text-button" type="button" onClick={() => void retryProgress()}>
                                Retry progress save
                            </button>
                        )}
                </div>
            )}

            <div className="display-workspace-body">
                <nav className="display-test-navigation" aria-label="Display diagnostic tests">
                    <div className="display-nav-heading">
                        <span className="eyebrow">TEST PLAN</span>
                        <span>{completedCount}/{REQUIRED_DISPLAY_TESTS.length}</span>
                    </div>
                    {DISPLAY_TEST_CATALOG.map((test, index) => {
                        const status = test.kind === "assessment"
                            ? currentStatus === "completed"
                                ? diagnostic.overall_status || "inconclusive"
                                : allRequiredDone
                                  ? "in_progress"
                                  : "not_started"
                            : getTestOutcome(diagnostic, test.id);
                        return (
                            <button
                                type="button"
                                className={`display-test-nav-item${currentTest.id === test.id ? " is-active" : ""}`}
                                key={test.id}
                                onClick={() => void updateCurrentTest(test.id)}
                                aria-current={currentTest.id === test.id ? "step" : undefined}
                            >
                                <span className="display-test-nav-number">
                                    {status === "passed" ? <Check size={14} aria-hidden="true" /> : String(index + 1).padStart(2, "0")}
                                </span>
                                <span className="display-test-nav-copy">
                                    <strong>{test.name}</strong>
                                    <small className={statusClass(status)}>{testStatusLabel(status)}</small>
                                </span>
                                <span className={`display-status-dot ${statusClass(status)}`} aria-hidden="true" />
                            </button>
                        );
                    })}
                    <div className="display-nav-footer">
                        <span className="display-local-indicator" />
                        Local UHDP session
                    </div>
                </nav>

                <section className="display-test-main" aria-label="Display testing area">
                    <div className="display-test-heading">
                        <div>
                            <span className="eyebrow">DISPLAY CHECK</span>
                            <h1>{currentTest.name}</h1>
                            <p>{currentTest.purpose}</p>
                        </div>
                        <span className={`display-result-label ${statusClass(currentStatus)}`}>
                            {testStatusLabel(currentStatus)}
                        </span>
                    </div>

                    {currentTest.kind === "assessment" ? (
                        <section className="display-assessment-panel">
                            <div className="display-assessment-intro">
                                <h2>Review technician results</h2>
                                <p>Completed visual checks are based on technician observations, not automatic pixel detection.</p>
                            </div>
                            <div className="display-assessment-list">
                                {outcomeForAssessment.map((item) => (
                                    <button
                                        type="button"
                                        className="display-assessment-row"
                                        key={item.id}
                                        onClick={() => void updateCurrentTest(item.id)}
                                    >
                                        <span><strong>{item.name}</strong><small>{item.result?.notes || item.purpose}</small></span>
                                        <span className={`display-result-label ${statusClass(item.outcome)}`}>
                                            {testStatusLabel(item.outcome)}
                                        </span>
                                    </button>
                                ))}
                            </div>
                            {diagnostic.status === "completed" ? (
                                <div className={`display-completion-result ${statusClass(diagnostic.overall_status || "inconclusive")}`}>
                                    <strong>Overall result: {testStatusLabel(diagnostic.overall_status || "inconclusive")}</strong>
                                    <span>Saved to the current QC session and report.</span>
                                </div>
                            ) : (
                                <button
                                    className="display-button display-button-primary display-complete-button"
                                    type="button"
                                    disabled={!allRequiredDone || saving || Boolean(pendingResult)}
                                    onClick={() => void completeDiagnostic()}
                                >
                                    {saving ? "Completing…" : "Complete Display Diagnostics"}
                                </button>
                            )}
                        </section>
                    ) : (
                        <>
                            <div className="display-pattern-toolbar">
                                <div className="display-pattern-name">
                                    <span className="eyebrow">PATTERN</span>
                                    <strong>{patternName}</strong>
                                </div>
                                {patternCount > 1 && (
                                    <div className="display-pattern-controls" aria-label="Pattern controls">
                                        <button className="display-icon-button" type="button" onClick={() => setPattern(patternIndex - 1)} aria-label="Previous pattern">
                                            <ChevronLeft size={17} aria-hidden="true" />
                                        </button>
                                        <span>{patternIndex + 1} / {patternCount}</span>
                                        <button className="display-icon-button" type="button" onClick={() => setPattern(patternIndex + 1)} aria-label="Next pattern">
                                            <ChevronRight size={17} aria-hidden="true" />
                                        </button>
                                        {currentTest.id === "dead_pixel" && (
                                            <button
                                                className={`display-icon-button display-auto-button${autoSequence ? " is-on" : ""}`}
                                                type="button"
                                                onClick={() => setAutoSequence((value) => !value)}
                                            >
                                                {autoSequence ? <Pause size={15} aria-hidden="true" /> : <Play size={15} aria-hidden="true" />}
                                                {autoSequence ? "Pause sequence" : "Auto sequence"}
                                            </button>
                                        )}
                                    </div>
                                )}
                            </div>

                            {currentTest.id === "display_information" && (
                                <div className="display-metadata-warning" role="note">
                                    Metadata collection is informational. It does not determine whether the physical panel is healthy.
                                </div>
                            )}

                            <div className="display-pattern-stage-wrap" ref={stageRef}>
                                <DisplayCanvas
                                    testId={currentTest.id}
                                    patternIndex={patternIndex}
                                    patternCount={patternCount}
                                    metadata={displayMetadata}
                                    patternActive={patternActive}
                                    onPatternChange={setPattern}
                                />
                                <div className={`display-pattern-overlay${controlsVisible ? "" : " is-hidden"}`}>
                                    {controlsVisible ? (
                                        <>
                                            <button type="button" onClick={() => setControlsVisible(false)} aria-label="Hide pattern controls">
                                                <EyeOff size={16} aria-hidden="true" />
                                            </button>
                                            <button type="button" onClick={() => setPatternActive((value) => !value)}>
                                                {patternActive ? <Pause size={15} aria-hidden="true" /> : <Play size={15} aria-hidden="true" />}
                                                {patternActive ? "Pause pattern" : "Show pattern"}
                                            </button>
                                            <button type="button" onClick={() => { setPatternActive(false); setAutoSequence(false); }}>
                                                <X size={15} aria-hidden="true" /> Exit pattern
                                            </button>
                                        </>
                                    ) : (
                                        <button type="button" onClick={() => setControlsVisible(true)} aria-label="Show pattern controls">
                                            <Eye size={16} aria-hidden="true" /> Show controls
                                        </button>
                                    )}
                                </div>
                            </div>

                            {currentTest.id === "display_information" && (
                                <div className="display-information-grid">
                                    <MetadataItem label="Resolution" value={readMetadata(displayMetadata, "resolution")} />
                                    <MetadataItem label="Refresh rate" value={readMetadata(displayMetadata, "refresh_rate_hz")} />
                                    <MetadataItem label="Display name" value={readMetadata(displayMetadata, "display_name")} />
                                    <MetadataItem label="Manufacturer" value={readMetadata(displayMetadata, "manufacturer")} />
                                    <MetadataItem label="Model" value={readMetadata(displayMetadata, "model")} />
                                    <MetadataItem label="Connection" value={getConnectedOutputs(displayMetadata)} />
                                    <MetadataItem label="EDID" value={getEdidSummary(displayMetadata)} />
                                    <MetadataItem label="Inventory source" value={readMetadata(displayMetadata, "inventory_source")} />
                                </div>
                            )}

                            <div className="display-observation-row">
                                <p>{currentTest.instructions}</p>
                                {currentTest.kind === "visual" && (
                                    <button
                                        type="button"
                                        className="display-text-button"
                                        onClick={() => setInstructionsVisible((visible) => !visible)}
                                    >
                                        {instructionsVisible ? "Hide instructions" : "Show instructions"}
                                    </button>
                                )}
                            </div>
                        </>
                    )}
                </section>

                {instructionsVisible && (
                    <aside className="display-instruction-panel" aria-label="Technician instructions and result controls">
                        <div className="display-panel-heading">
                            <div>
                                <span className="eyebrow">TECHNICIAN GUIDE</span>
                                <h2>What to inspect</h2>
                            </div>
                            <button className="display-icon-button" type="button" onClick={() => setInstructionsVisible(false)} aria-label="Hide instructions panel">
                                <X size={16} aria-hidden="true" />
                            </button>
                        </div>
                        <p className="display-instruction-copy">{currentTest.instructions}</p>

                        {currentTest.id === "display_information" && (
                            <div className="display-compact-metadata">
                                <MetadataItem label="Mode" value={readMetadata(displayMetadata, "resolution")} />
                                <MetadataItem label="Refresh" value={readMetadata(displayMetadata, "refresh_rate_hz")} />
                                <MetadataItem label="EDID" value={getEdidSummary(displayMetadata)} />
                                <p>Missing metadata does not indicate a defective display.</p>
                            </div>
                        )}

                        {currentTest.kind !== "assessment" && (
                            <>
                                <label className="display-form-label" htmlFor="display-technician-notes">
                                    Technician notes <span>Optional</span>
                                </label>
                                <textarea
                                    id="display-technician-notes"
                                    className="display-notes-field"
                                    rows={3}
                                    maxLength={2000}
                                    value={currentNote}
                                    disabled={isReadOnly}
                                    onChange={(event) => setNotes((value) => ({
                                        ...value,
                                        [currentTest.id]: event.target.value,
                                    }))}
                                    placeholder="Record what you observed"
                                />
                            </>
                        )}

                        {showDefectForm && (
                            <div className="display-defect-form">
                                <div className="display-form-section-title">
                                    <strong>Report a display defect</strong>
                                    <span>Required for a failed result</span>
                                </div>
                                <label className="display-form-label" htmlFor="display-defect-type">Defect category</label>
                                <select
                                    id="display-defect-type"
                                    className="display-select"
                                    value={defectDraft.type}
                                    onChange={(event) => setDefects((value) => ({
                                        ...value,
                                        [currentTest.id]: { ...defectDraft, type: event.target.value },
                                    }))}
                                >
                                    {DEFECT_TYPES.map((item) => (
                                        <option value={item.value} key={item.value}>{item.label}</option>
                                    ))}
                                </select>
                                <label className="display-form-label" htmlFor="display-defect-location">Approximate location <span>Optional</span></label>
                                <input
                                    id="display-defect-location"
                                    className="display-input"
                                    value={defectDraft.location}
                                    maxLength={200}
                                    onChange={(event) => setDefects((value) => ({
                                        ...value,
                                        [currentTest.id]: { ...defectDraft, location: event.target.value },
                                    }))}
                                    placeholder="e.g. upper right area"
                                />
                                <label className="display-form-label" htmlFor="display-defect-count">Defect count <span>If known</span></label>
                                <input
                                    id="display-defect-count"
                                    className="display-input"
                                    type="number"
                                    min="1"
                                    max="10000"
                                    step="1"
                                    value={defectDraft.count}
                                    onChange={(event) => setDefects((value) => ({
                                        ...value,
                                        [currentTest.id]: { ...defectDraft, count: event.target.value },
                                    }))}
                                />
                                <div className="display-defect-actions">
                                    <button type="button" className="display-button display-button-danger" disabled={!canRecord} onClick={() => void submitDefect()}>
                                        {saving ? "Saving…" : "Save as failed"}
                                    </button>
                                    <button type="button" className="display-button display-button-muted" onClick={() => setShowDefectForm(false)}>
                                        Cancel
                                    </button>
                                </div>
                            </div>
                        )}

                        <div className="display-result-actions">
                            {!activeAttempt && !isReadOnly && currentTest.kind !== "assessment" && (
                                <button
                                    type="button"
                                    className="display-button display-button-primary"
                                    disabled={pendingStart || saving}
                                    onClick={() => void startOrResumeTest(Boolean(testState?.latest_result))}
                                >
                                    {pendingStart ? "Starting…" : testState?.latest_result ? "Retest" : "Start test"}
                                </button>
                            )}
                            {activeAttempt && (
                                <div className="display-active-attempt" role="status">
                                    Attempt {activeAttempt.attempt_number} · Started {new Date(activeAttempt.started_at).toLocaleTimeString()}
                                </div>
                            )}
                            <button type="button" className="display-button display-button-success" disabled={!canRecord} onClick={() => void submitOutcome("passed")}>
                                <Check size={15} aria-hidden="true" /> Mark passed
                            </button>
                            <button
                                type="button"
                                className="display-button display-button-danger"
                                disabled={!canRecord}
                                onClick={() => setShowDefectForm(true)}
                            >
                                Report defect
                            </button>
                            <button type="button" className="display-button display-button-muted" disabled={!canRecord} onClick={() => void submitOutcome("inconclusive")}>
                                Requires verification
                            </button>
                            <button type="button" className="display-text-button display-skip-button" disabled={!canRecord} onClick={() => void submitOutcome("skipped")}>
                                Skip test
                            </button>
                            {testState?.latest_result && (
                                <div className="display-last-result">
                                    Last result: <strong>{testStatusLabel(testState.latest_result.status)}</strong>
                                    {testState.latest_result.notes && <p>{testState.latest_result.notes}</p>}
                                    {testState.latest_result.defects.length > 0 && (
                                        <p>{testState.latest_result.defects.map((defect) => defect.type.replaceAll("_", " ")).join(", ")}</p>
                                    )}
                                </div>
                            )}
                            {currentTest.kind === "visual" && testState?.latest_result && !activeAttempt && (
                                <button type="button" className="display-text-button" disabled={isReadOnly} onClick={restartCurrentTest}>
                                    <RotateCcw size={14} aria-hidden="true" /> Restart / retest
                                </button>
                            )}
                        </div>
                        {!isReadOnly && (
                            <div className="display-metadata-footnote">
                                A displayed pattern is not an automated hardware pass. Record your visual assessment.
                            </div>
                        )}
                    </aside>
                )}
            </div>

            <footer className="display-bottom-bar">
                <button
                    type="button"
                    className="display-button display-button-muted"
                    disabled={currentIndex <= 0 || progressSaving}
                    onClick={() => navigateRelative(-1)}
                >
                    <ArrowLeft size={15} aria-hidden="true" /> Previous test
                </button>
                <div className="display-bottom-status">
                    {progressSaving ? "Saving progress…" : `${completedCount} of ${REQUIRED_DISPLAY_TESTS.length} required checks saved`}
                    {pendingResult && <span>Result pending save · retry available</span>}
                </div>
                {currentTest.kind !== "assessment" && (
                    <button
                        type="button"
                        className="display-button display-button-muted"
                        onClick={restartCurrentTest}
                        disabled={isReadOnly || saving || pendingStart}
                    >
                        <RotateCcw size={15} aria-hidden="true" /> Restart test
                    </button>
                )}
                <button type="button" className="display-button display-button-muted" onClick={() => void toggleFullscreen()}>
                    <Expand size={15} aria-hidden="true" /> {fullscreen ? "Exit fullscreen" : "Fullscreen"}
                </button>
                {currentTest.kind !== "assessment" ? (
                    <button
                        type="button"
                        className="display-button display-button-primary"
                        disabled={currentIndex >= DISPLAY_TEST_CATALOG.length - 1 || progressSaving}
                        onClick={() => navigateRelative(1)}
                    >
                        Next test <ArrowRight size={15} aria-hidden="true" />
                    </button>
                ) : (
                    <button
                        type="button"
                        className="display-button display-button-primary"
                        disabled={!allRequiredDone || saving || isReadOnly || Boolean(pendingResult)}
                        onClick={() => void completeDiagnostic()}
                    >
                        {diagnostic.status === "completed" ? "Completed" : saving ? "Completing…" : "Complete diagnostic"}
                    </button>
                )}
                {diagnostic.status === "completed" && (
                    <Link className="display-button display-button-muted" to={`/results?sessionId=${encodeURIComponent(sessionId)}`}>
                        View QC results
                    </Link>
                )}
            </footer>

            <AlertDialog open={exitConfirmation} onOpenChange={setExitConfirmation}>
                <AlertDialogContent>
                    <AlertDialogHeader>
                        <AlertDialogTitle>Leave this display test?</AlertDialogTitle>
                        <AlertDialogDescription>
                            This test attempt is still in progress. Completed results are already saved; any unfinished assessment is not submitted.
                        </AlertDialogDescription>
                    </AlertDialogHeader>
                    <AlertDialogFooter>
                        <AlertDialogCancel>Stay here</AlertDialogCancel>
                        <AlertDialogAction onClick={confirmExit}>Exit to QC</AlertDialogAction>
                    </AlertDialogFooter>
                </AlertDialogContent>
            </AlertDialog>
        </main>
    );
}

function getDeviceName(session: DiagnosticSession) {
    const inventory = session.device_inventory || [];
    const device = inventory.find((item) => item.device_id === session.device_id);
    return typeof device?.name === "string" && device.name.trim()
        ? device.name
        : session.device_id || "Device not identified";
}

function getSerial(session: DiagnosticSession) {
    const device = session.device_inventory?.find((item) => item.device_id === session.device_id);
    if (!device?.properties || typeof device.properties !== "object") return "Not recorded";
    const properties = device.properties as Record<string, unknown>;
    const serial = properties.serial_number || properties.serial || properties.SerialNumber;
    return typeof serial === "string" && serial.trim() ? serial : "Not recorded";
}

function MetadataItem({ label, value }: { label: string; value: string }) {
    return (
        <div className="display-metadata-item">
            <span>{label}</span>
            <strong>{value}</strong>
        </div>
    );
}

function getEdidSummary(metadata: Record<string, unknown>) {
    const connectors = metadata.connectors;
    if (!Array.isArray(connectors)) return "Not available";
    const edid = connectors.flatMap((connector) => {
        if (typeof connector !== "object" || connector === null) return [];
        const value = (connector as Record<string, unknown>).edid;
        return typeof value === "object" && value !== null
            ? [value as Record<string, unknown>]
            : [];
    });
    return edid.length
        ? edid.map((item) => [item.manufacturer, item.model].filter(Boolean).join(" ")).join(", ")
        : "Not available";
}
