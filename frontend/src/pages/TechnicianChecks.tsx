import { useEffect, useMemo, useState } from "react";
import { Link, useSearchParams } from "react-router-dom";
import {
    ArrowLeft,
    Check,
    ExternalLink,
    Keyboard,
    Monitor,
    Mouse,
    Plug,
    RotateCcw,
    Smartphone,
} from "lucide-react";
import { PageHeader } from "../components/shared/PageHeader";
import InspectionProgress from "../components/shared/InspectionProgress";
import { KeyboardGrid } from "../components/technician-checks/KeyboardGrid";
import { PortsPanel } from "../components/technician-checks/PortsPanel";
import { useQcSession } from "../session/SessionContext";
import {
    DiagnosticSession,
    ManualCheck,
    getDiagnosticSession,
    getManualChecks,
    recordManualResult,
} from "../api/execution";
import {
    BackendOutcome,
    CHECK_IDS,
    PORT_CHECK_IDS,
    PortRecord,
    PortType,
    aggregatePortOutcome,
    decisionForOutcome,
    extractDeviceContext,
    isTechnicianChecksComplete,
    keyboardKeyCount,
    parseKeyboardEvidence,
    parsePortsEvidence,
    parsePortsFinalized,
    serializeKeyboardEvidence,
    serializePortsEvidence,
    toBackendOutcome,
    usQwertyKeyboardRows,
} from "../technicianChecks/technicianCheckModels";
import "./technician-checks.css";

type ActiveCategory = "display" | "keyboard" | "touchscreen" | "touchpad" | "ports";

const manualOutcomes = ["Working correctly", "Issues found", "Unable to verify", "Not Applicable"];
const touchpadOutcomes = ["Working correctly", "Partially working", "Not working", "Unable to verify", "Not Applicable"];

const outcomeLabels: Record<BackendOutcome, string> = {
    passed: "Passed",
    failed: "Failed",
    warning: "Attention",
    not_applicable: "Not applicable",
    blocked: "Unable to verify",
    not_run: "Not checked",
};

const trackedCheckIds = Object.values(CHECK_IDS);

function asRecord(value: unknown): Record<string, unknown> | null {
    if (typeof value !== "object" || value === null || Array.isArray(value)) return null;
    return value as Record<string, unknown>;
}

function manualRecord(session: DiagnosticSession | null, checkId: string): Record<string, unknown> | null {
    return asRecord(session?.manual_results?.[checkId]);
}

function savedOutcomeFor(session: DiagnosticSession | null, checkId: string): BackendOutcome | undefined {
    const record = manualRecord(session, checkId);
    if (!record) return undefined;
    for (const key of ["status", "test_status"]) {
        const value = record[key];
        if (typeof value === "string" && value in outcomeLabels) return value as BackendOutcome;
    }
    return undefined;
}

function savedNotesFor(session: DiagnosticSession | null, checkId: string): string {
    const record = manualRecord(session, checkId);
    if (!record) return "";
    const notes = record.notes ?? record.technician_notes;
    return typeof notes === "string" ? notes : "";
}

function evidenceFor(session: DiagnosticSession | null, checkId: string): Record<string, unknown> {
    return asRecord(manualRecord(session, checkId)?.evidence) ?? {};
}

function OutcomeButtons({
    options,
    selected,
    disabled = false,
    onSelect,
}: {
    options: string[];
    selected: BackendOutcome | undefined;
    disabled?: boolean;
    onSelect: (outcome: BackendOutcome) => void;
}) {
    return (
        <div className="technician-outcome-buttons" role="group" aria-label="Manual check result">
            {options.map((option) => {
                const outcome = toBackendOutcome(option);
                const isSelected = selected === outcome;
                return (
                    <button
                        className={`button ${isSelected ? "button-primary" : "button-secondary"}`}
                        key={option}
                        type="button"
                        aria-pressed={isSelected}
                        disabled={disabled}
                        onClick={() => onSelect(outcome)}
                    >
                        {option}
                    </button>
                );
            })}
        </div>
    );
}

function ResultEditor({
    checkId,
    options,
    outcome,
    notes,
    saved,
    saving,
    readOnly,
    saveLabel,
    onOutcome,
    onNotes,
    onSave,
}: {
    checkId: string;
    options: string[];
    outcome: BackendOutcome | undefined;
    notes: string;
    saved: boolean;
    saving: boolean;
    readOnly: boolean;
    saveLabel: string;
    onOutcome: (outcome: BackendOutcome) => void;
    onNotes: (notes: string) => void;
    onSave: () => void;
}) {
    return (
        <>
            <OutcomeButtons options={options} selected={outcome} disabled={readOnly || saving} onSelect={onOutcome} />
            <label className="technician-notes-field">
                <span>Technician notes</span>
                <textarea
                    value={notes}
                    maxLength={1000}
                    rows={3}
                    disabled={readOnly}
                    onChange={(event) => onNotes(event.target.value.slice(0, 1000))}
                />
            </label>
            <div className="technician-control-row">
                <button
                    className="button button-primary"
                    type="button"
                    disabled={!outcome || readOnly || saving}
                    onClick={onSave}
                >
                    <Check size={14} aria-hidden="true" /> {saving ? "SAVING…" : saveLabel}
                </button>
                {saved && (
                    <span className="technician-check-saved-at">
                        Saved to QC session{outcome ? ` · ${outcomeLabels[outcome]}` : ""} · {checkId}
                    </span>
                )}
            </div>
        </>
    );
}

function FunctionalCheckCard({
    title,
    description,
    hardware,
    icon: Icon,
    status,
    disabled = false,
    onStart,
}: {
    title: string;
    description: string;
    hardware: string;
    icon: typeof Monitor;
    status: string;
    disabled?: boolean;
    onStart: () => void;
}) {
    return (
        <article className="technician-check-card">
            <header>
                <span className="technician-check-icon"><Icon size={17} aria-hidden="true" /></span>
                <span className="technician-check-status">{status}</span>
            </header>
            <div>
                <h3>{title}</h3>
                <p className="technician-check-hardware">{hardware}</p>
                <p>{description}</p>
            </div>
            <button className="button button-secondary" type="button" disabled={disabled} onClick={onStart}>
                START CHECK
            </button>
        </article>
    );
}

export default function TechnicianChecks() {
    const [params] = useSearchParams();
    const { activeSessionId } = useQcSession();
    const sessionId = params.get("sessionId") || activeSessionId;

    const [session, setSession] = useState<DiagnosticSession | null>(null);
    const [checks, setChecks] = useState<ManualCheck[]>([]);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState("");
    const [activeCategory, setActiveCategory] = useState<ActiveCategory | null>(null);
    const [outcomes, setOutcomes] = useState<Record<string, BackendOutcome>>({});
    const [notes, setNotes] = useState<Record<string, string>>({});
    const [saved, setSaved] = useState<Record<string, boolean>>({});
    const [saving, setSaving] = useState<Record<string, boolean>>({});
    const [keyboardTested, setKeyboardTested] = useState<string[]>([]);
    const [keyboardFaulty, setKeyboardFaulty] = useState<string[]>([]);
    const [selectedKeyboardKey, setSelectedKeyboardKey] = useState<string | null>(null);
    const [ports, setPorts] = useState<PortRecord[]>([]);
    const [selectedPortId, setSelectedPortId] = useState<string | null>(null);
    const [portsFinalized, setPortsFinalized] = useState(false);

    const readOnly = ["complete", "completed"].includes((session?.status || "").toLowerCase());
    const mappedCodes = useMemo(
        () => new Set(usQwertyKeyboardRows.flatMap((row) => row.map((key) => key.code))),
        [],
    );

    function hydrate(loaded: DiagnosticSession) {
        const nextOutcomes: Record<string, BackendOutcome> = {};
        const nextNotes: Record<string, string> = {};
        const nextSaved: Record<string, boolean> = {};
        for (const checkId of trackedCheckIds) {
            const outcome = savedOutcomeFor(loaded, checkId);
            if (outcome) {
                nextOutcomes[checkId] = outcome;
                nextSaved[checkId] = true;
            }
            nextNotes[checkId] = savedNotesFor(loaded, checkId);
        }

        const keyboard = parseKeyboardEvidence(evidenceFor(loaded, CHECK_IDS.keyboard));
        setKeyboardTested(keyboard.tested);
        setKeyboardFaulty(keyboard.faulty);

        const loadedPorts: PortRecord[] = [];
        let portGroups = 0;
        let allPortGroupsFinalized = true;
        for (const [type, checkId] of Object.entries(PORT_CHECK_IDS) as Array<[PortType, string]>) {
            const evidence = evidenceFor(loaded, checkId);
            const groupPorts = parsePortsEvidence(evidence, type);
            if (groupPorts.length === 0) continue;
            portGroups += 1;
            if (!parsePortsFinalized(evidence)) allPortGroupsFinalized = false;
            loadedPorts.push(...groupPorts);
        }
        setPorts(loadedPorts);
        setPortsFinalized(portGroups > 0 && allPortGroupsFinalized);

        setOutcomes(nextOutcomes);
        setNotes(nextNotes);
        setSaved(nextSaved);
    }

    useEffect(() => {
        if (!sessionId) {
            setLoading(false);
            return;
        }
        let current = true;
        setLoading(true);
        setError("");

        Promise.all([getManualChecks(), getDiagnosticSession(sessionId)])
            .then(([availableChecks, loadedSession]) => {
                if (!current) return;
                setChecks(availableChecks);
                setSession(loadedSession);
                hydrate(loadedSession);
            })
            .catch((loadError: unknown) => {
                if (current) setError(loadError instanceof Error ? loadError.message : "Technician checks could not be loaded.");
            })
            .finally(() => {
                if (current) setLoading(false);
            });

        return () => {
            current = false;
        };
        // hydrate is intentionally scoped to the loaded session.
        // eslint-disable-next-line react-hooks/exhaustive-deps
    }, [sessionId]);

    useEffect(() => {
        if (activeCategory !== "keyboard" || readOnly) return;
        function handleKeyDown(event: KeyboardEvent) {
            const target = event.target;
            if (target instanceof HTMLElement
                && (target.isContentEditable || ["INPUT", "TEXTAREA", "SELECT"].includes(target.tagName))) return;
            if (!mappedCodes.has(event.code)) return;
            event.preventDefault();
            setSelectedKeyboardKey(event.code);
            setKeyboardTested((current) => current.includes(event.code) ? current : [...current, event.code]);
            setSaved((current) => ({ ...current, [CHECK_IDS.keyboard]: false }));
        }
        window.addEventListener("keydown", handleKeyDown);
        return () => window.removeEventListener("keydown", handleKeyDown);
    }, [activeCategory, mappedCodes, readOnly]);

    const context = useMemo(
        () => session ? extractDeviceContext(session) : null,
        [session],
    );

    const displayDiagnosticStatus = session?.display_diagnostic?.status ?? null;
    const displayComplete = displayDiagnosticStatus === "completed";
    const technicianChecksComplete = Boolean(session) && isTechnicianChecksComplete({
        displayComplete,
        saved,
        ports,
        portsFinalized,
    });

    const summary = useMemo(() => {
        const values = trackedCheckIds
            .filter((checkId) => saved[checkId] && outcomes[checkId])
            .map((checkId) => outcomes[checkId]);
        const portOutcome = ports.length > 0 ? aggregatePortOutcome(ports) : undefined;
        const allValues = portOutcome ? [...values, portOutcome] : values;
        const notApplicable = allValues.filter((value) => value === "not_applicable").length;
        const completed = allValues.length - notApplicable;
        return {
            totalSelected: trackedCheckIds.length + (ports.length > 0 ? 1 : 0),
            completed,
            passed: allValues.filter((value) => value === "passed").length,
            failed: allValues.filter((value) => value === "failed" || value === "warning").length,
            unableToVerify: allValues.filter((value) => value === "blocked").length,
            notApplicable,
            notTested: trackedCheckIds.length + (ports.length > 0 ? 1 : 0) - completed - notApplicable,
        };
    }, [outcomes, ports, saved]);

    const missingChecks = trackedCheckIds.filter((checkId) => !checks.some((check) => check.id === checkId));

    function chooseOutcome(checkId: string, outcome: BackendOutcome) {
        if (readOnly) return;
        setOutcomes((current) => ({ ...current, [checkId]: outcome }));
        setSaved((current) => ({ ...current, [checkId]: false }));
    }

    function changeNotes(checkId: string, value: string) {
        if (readOnly) return;
        setNotes((current) => ({ ...current, [checkId]: value }));
        setSaved((current) => ({ ...current, [checkId]: false }));
    }

    function toggleFaultyKey(code: string) {
        if (readOnly) return;
        setKeyboardFaulty((current) => current.includes(code)
            ? current.filter((item) => item !== code)
            : [...current, code]);
        setSaved((current) => ({ ...current, [CHECK_IDS.keyboard]: false }));
    }

    async function saveCheck(checkId: string) {
        const outcome = outcomes[checkId];
        if (!sessionId || !outcome || saving[checkId] || readOnly) return;
        setSaving((current) => ({ ...current, [checkId]: true }));
        setError("");
        try {
            const existingEvidence = evidenceFor(session, checkId);
            const evidence = checkId === CHECK_IDS.keyboard
                ? { ...existingEvidence, ...serializeKeyboardEvidence(keyboardTested, keyboardFaulty) }
                : existingEvidence;
            await recordManualResult(sessionId, checkId, {
                outcome,
                notes: (notes[checkId] || "").slice(0, 1000),
                scan_status: "not_attempted",
                detected_devices: [],
                technician_decision: decisionForOutcome(outcome),
                evidence,
            });
            const refreshed = await getDiagnosticSession(sessionId);
            setSession(refreshed);
            setSaved((current) => ({ ...current, [checkId]: true }));
        } catch (saveError) {
            setError(saveError instanceof Error ? saveError.message : "This technician result could not be saved.");
        } finally {
            setSaving((current) => ({ ...current, [checkId]: false }));
        }
    }

    function portsForCheck(checkId: string): PortRecord[] {
        return ports.filter((port) => PORT_CHECK_IDS[port.type] === checkId);
    }

    function portsNote(group: PortRecord[]): string {
        const skipped = group.filter((port) => port.skipped).length;
        const working = group.filter((port) => !port.skipped && port.result === "Working").length;
        const failed = group.filter((port) => !port.skipped && (port.result === "Not working" || port.result === "Physically damaged")).length;
        const parts = [`${group.length} selected`];
        if (working) parts.push(`${working} working`);
        if (failed) parts.push(`${failed} failed`);
        if (skipped) parts.push(`${skipped} skipped`);
        return `Physical ports: ${parts.join(", ")}.`.slice(0, 1000);
    }

    async function persistPortGroup(group: PortRecord[], finalized: boolean) {
        if (!sessionId || group.length === 0) return;
        const checkId = PORT_CHECK_IDS[group[0].type];
        const outcome = aggregatePortOutcome(group);
        const existingEvidence = evidenceFor(session, checkId);
        await recordManualResult(sessionId, checkId, {
            outcome,
            notes: portsNote(group),
            scan_status: "not_attempted",
            detected_devices: [],
            technician_decision: decisionForOutcome(outcome),
            evidence: { ...existingEvidence, ...serializePortsEvidence(group, finalized) },
        });
    }

    async function refreshSession() {
        if (!sessionId) return;
        const refreshed = await getDiagnosticSession(sessionId);
        setSession(refreshed);
    }

    function addPort(type: PortType, customName?: string) {
        if (readOnly) return;
        const sameTypeCount = ports.filter((port) => port.type === type).length;
        const label = type === "Other"
            ? customName || "Other port"
            : sameTypeCount > 0 ? `${type} ${sameTypeCount + 1}` : type;
        const id = `${type.replace(/\s+/g, "-").toLowerCase()}-${Date.now()}-${ports.length + 1}`;
        setPorts((current) => [...current, {
            id,
            type,
            label,
            result: null,
            notes: "",
            skipped: false,
            saved: false,
        }]);
        setSelectedPortId(id);
        setPortsFinalized(false);
    }

    function changePort(id: string, updates: Partial<PortRecord>) {
        if (readOnly) return;
        setPorts((current) => current.map((port) => {
            if (port.id !== id) return port;
            const next = { ...port, ...updates, saved: false };
            if (updates.result !== undefined && updates.result !== null) next.skipped = false;
            return next;
        }));
        setPortsFinalized(false);
    }

    async function savePort(id: string) {
        const port = ports.find((item) => item.id === id);
        if (!port?.result || readOnly) return;
        setError("");
        try {
            await persistPortGroup(portsForCheck(PORT_CHECK_IDS[port.type]), false);
            await refreshSession();
            setPorts((current) => current.map((item) => item.id === id ? { ...item, saved: true } : item));
        } catch (saveError) {
            setError(saveError instanceof Error ? saveError.message : "This port result could not be saved.");
        }
    }

    async function skipPort(id: string) {
        if (readOnly) return;
        const nextPorts = ports.map((port) => port.id === id
            ? { ...port, skipped: true, result: null, saved: false }
            : port);
        setPorts(nextPorts);
        setPortsFinalized(false);
        const skipped = nextPorts.find((port) => port.id === id);
        if (!skipped) return;
        setError("");
        try {
            await persistPortGroup(nextPorts.filter((port) => PORT_CHECK_IDS[port.type] === PORT_CHECK_IDS[skipped.type]), false);
            await refreshSession();
            setPorts((current) => current.map((port) => port.id === id ? { ...port, saved: true } : port));
        } catch (saveError) {
            setError(saveError instanceof Error ? saveError.message : "This port could not be skipped.");
        }
    }

    async function finalizePorts() {
        if (readOnly) return;
        const unreviewed = ports.filter((port) => port.result === null && !port.skipped);
        if (unreviewed.length > 0) {
            const labels = unreviewed.map((port) => port.label).join(", ");
            setError(`Record a result or skip ${unreviewed.length === 1 ? labels : `${unreviewed.length} ports (${labels})`} before finishing the port inspection.`);
            return;
        }
        setError("");
        try {
            const groups = new Map<string, PortRecord[]>();
            for (const port of ports) {
                const checkId = PORT_CHECK_IDS[port.type];
                groups.set(checkId, [...(groups.get(checkId) ?? []), port]);
            }
            for (const group of groups.values()) {
                await persistPortGroup(group, true);
            }
            await refreshSession();
            setPorts((current) => current.map((port) => ({ ...port, saved: true })));
            setPortsFinalized(true);
            setActiveCategory(null);
        } catch (saveError) {
            setError(saveError instanceof Error ? saveError.message : "Port inspection could not be saved.");
        }
    }

    if (!sessionId) {
        return (
            <section className="empty-panel">
                <span className="empty-panel-icon" aria-hidden="true">✓</span>
                <h1>No QC session selected</h1>
                <p>Start a new QC intake or resume an inspection from QC History before recording technician checks.</p>
                <div className="active-qc-actions">
                    <Link className="button button-primary" to="/devices?new=1">Start New QC</Link>
                    <Link className="button button-secondary" to="/history">Open QC History</Link>
                </div>
            </section>
        );
    }

    if (loading) return <div className="loading-panel">Loading technician checks…</div>;

    if (!session) {
        return <div className="error-box" role="alert">{error || "The QC session could not be loaded."}</div>;
    }

    const keyboardSaved = Boolean(saved[CHECK_IDS.keyboard]);
    const touchscreenSaved = Boolean(saved[CHECK_IDS.touchscreen]);
    const touchpadSaved = Boolean(saved[CHECK_IDS.touchpad]);
    const gesturesSaved = Boolean(saved[CHECK_IDS.touchpadGestures]);
    const keyboardStatus = keyboardSaved && outcomes[CHECK_IDS.keyboard]
        ? outcomeLabels[outcomes[CHECK_IDS.keyboard]]
        : "Not checked";
    const touchscreenStatus = touchscreenSaved && outcomes[CHECK_IDS.touchscreen]
        ? outcomeLabels[outcomes[CHECK_IDS.touchscreen]]
        : context?.hasTouchscreen ? "Not checked" : "Not detected";
    const touchpadStatus = touchpadSaved && gesturesSaved
        ? "Movement + gestures saved"
        : touchpadSaved || gesturesSaved ? "1 of 2 saved" : "Not checked";
    const overallDisplayStatus = session.display_diagnostic?.overall_status;
    const displayStatus = displayComplete
        ? (overallDisplayStatus
            ? overallDisplayStatus.charAt(0).toUpperCase() + overallDisplayStatus.slice(1)
            : "Completed")
        : displayDiagnosticStatus === "in_progress" ? "In progress" : "Not started";
    const portsStatus = ports.length === 0
        ? "Not selected"
        : portsFinalized ? "Inspection saved" : `${ports.length} selected`;

    return (
        <main className="hardware-diagnostics page-flow technician-checks-page" aria-labelledby="technician-checks-title">
            <PageHeader
                title="Technician Functional Checks"
                titleId="technician-checks-title"
                description="Manually verify the operation of the device components and connections. Results are saved to this QC session."
                eyebrow={`QC SESSION · ${sessionId}`}
                actions={<span className="technician-check-status">{readOnly ? "READ-ONLY RECORD" : "TECHNICIAN ENTRY"}</span>}
            />

            <InspectionProgress
                activeStage={3}
                deviceConfirmed={Boolean(session.device_id)}
                physicalAssessmentComplete={Boolean(session.cosmetic_inspections)}
                diagnosticsComplete={Object.keys(session.test_results || {}).length > 0}
                technicianChecksComplete={technicianChecksComplete}
            />

            {error && <div className="error-box" role="alert">{error}</div>}
            {missingChecks.length > 0 && (
                <div className="technician-check-notice" role="status">
                    This build does not expose every required manual check ({missingChecks.join(", ")}). Results for those checks cannot be saved.
                </div>
            )}

            <section className="hardware-diagnostics-device-summary" aria-label="Current device summary">
                <strong>{context?.deviceName}</strong>
                <span>Serial {context?.serial}</span>
                <span>
                    {context?.displayResolution ?? "Resolution unavailable"}
                    {context?.refreshRateHz ? ` · ${context.refreshRateHz} Hz` : ""}
                </span>
                <span>{context?.usbDevices.length ?? 0} USB device{(context?.usbDevices.length ?? 0) === 1 ? "" : "s"} detected</span>
            </section>

            <section className="technician-check-summary" aria-labelledby="technician-summary-title">
                <div className="hardware-diagnostics-section-heading">
                    <div>
                        <h2 id="technician-summary-title">Manual Check Summary</h2>
                        <p>Counts reflect results saved to this QC session.</p>
                    </div>
                </div>
                <dl>
                    <div><dt>Total selected checks</dt><dd>{summary.totalSelected}</dd></div>
                    <div><dt>Completed</dt><dd>{summary.completed}</dd></div>
                    <div className="is-pass"><dt>Passed</dt><dd>{summary.passed}</dd></div>
                    <div className="is-fail"><dt>Failed</dt><dd>{summary.failed}</dd></div>
                    <div><dt>Unable to verify</dt><dd>{summary.unableToVerify}</dd></div>
                    <div><dt>Not applicable</dt><dd>{summary.notApplicable}</dd></div>
                    <div><dt>Not tested</dt><dd>{summary.notTested}</dd></div>
                </dl>
            </section>

            {activeCategory === null ? (
                <>
                    <section aria-labelledby="technician-checks-heading">
                        <div className="hardware-diagnostics-section-heading">
                            <div>
                                <h2 id="technician-checks-heading">Functional Checks</h2>
                                <p>Opening a check does not record a result. Each outcome is technician-entered and saved explicitly.</p>
                            </div>
                        </div>
                        <div className="technician-check-grid">
                            <FunctionalCheckCard
                                title="Display"
                                description="Run the full-screen display patterns and inspect resolution, colour, pixels and visible damage."
                                hardware={context?.displayName || context?.displayResolution || "Display metadata unavailable"}
                                icon={Monitor}
                                status={displayStatus}
                                onStart={() => setActiveCategory("display")}
                            />
                            <FunctionalCheckCard
                                title="Keyboard"
                                description="Check physical key response and identify faulty keys."
                                hardware={context?.keyboardNames.join(" · ") || "Keyboard not detected"}
                                icon={Keyboard}
                                status={keyboardStatus}
                                onStart={() => setActiveCategory("keyboard")}
                            />
                            <FunctionalCheckCard
                                title="Touchscreen"
                                description="Manual touch-area and edge responsiveness check."
                                hardware={context?.hasTouchscreen ? "Touchscreen detected" : "Touchscreen not detected"}
                                icon={Smartphone}
                                status={touchscreenStatus}
                                onStart={() => setActiveCategory("touchscreen")}
                            />
                            <FunctionalCheckCard
                                title="Touchpad"
                                description="Manually verify movement, buttons, scrolling and gestures."
                                hardware={context?.hasTouchpad ? "Touchpad detected" : "Touchpad not detected"}
                                icon={Mouse}
                                status={touchpadStatus}
                                onStart={() => setActiveCategory("touchpad")}
                            />
                            <FunctionalCheckCard
                                title="Ports"
                                description="Select physically present ports and inspect each one."
                                hardware="Technician-selected ports only"
                                icon={Plug}
                                status={portsStatus}
                                onStart={() => setActiveCategory("ports")}
                            />
                        </div>
                    </section>
                    <footer className="hardware-diagnostics-actions">
                        <Link className="button button-secondary" to={`/qc?sessionId=${encodeURIComponent(sessionId)}&stage=functional`}>
                            BACK TO FUNCTIONAL INSPECTION
                        </Link>
                        <div>
                            {!technicianChecksComplete && (
                                <span className="hardware-diagnostics-completion-hint">
                                    Complete the display diagnostic, save each applicable check, and review selected ports before continuing.
                                </span>
                            )}
                            <Link
                                className={`button ${technicianChecksComplete ? "button-primary" : "button-secondary"} ${technicianChecksComplete ? "" : "is-disabled"}`}
                                aria-disabled={!technicianChecksComplete}
                                tabIndex={technicianChecksComplete ? undefined : -1}
                                to={technicianChecksComplete ? `/results?sessionId=${encodeURIComponent(sessionId)}` : "#"}
                                onClick={(event) => { if (!technicianChecksComplete) event.preventDefault(); }}
                            >
                                CONTINUE TO REVIEW RESULTS
                            </Link>
                        </div>
                    </footer>
                </>
            ) : (
                <section className="technician-check-workspace" aria-label={`${activeCategory} manual check`}>
                    <header className="technician-workspace-heading">
                        <button className="button button-secondary" type="button" onClick={() => setActiveCategory(null)}>
                            <ArrowLeft size={14} aria-hidden="true" /> BACK TO FUNCTIONAL CHECKS
                        </button>
                        <div>
                            <h2>
                                {activeCategory === "touchpad" ? "Touchpad" : activeCategory.charAt(0).toUpperCase() + activeCategory.slice(1)} Check
                            </h2>
                            <span>Manual technician verification · saved to QC session</span>
                        </div>
                    </header>

                    {activeCategory === "display" && (
                        <div className="technician-workspace-body">
                            <p className="technician-instruction">
                                Display patterns are recorded by the display diagnostic workflow so defects, attempts and evidence stay together.
                            </p>
                            <div className="technician-check-meta">
                                <div><span>Resolution</span><strong>{context?.displayResolution ?? "Unknown"}</strong></div>
                                <div><span>Refresh rate</span><strong>{context?.refreshRateHz ? `${context.refreshRateHz} Hz` : "Unknown"}</strong></div>
                                <div><span>Panel</span><strong>{context?.displayName ?? "Unknown"}</strong></div>
                                <div><span>Status</span><strong>{displayStatus}</strong></div>
                            </div>
                            {context?.connectors.length ? (
                                <div className="technician-check-meta">
                                    {context.connectors.map((connector) => (
                                        <div key={connector.name}>
                                            <span>{connector.name}</span>
                                            <strong>{connector.status || "unknown"}</strong>
                                        </div>
                                    ))}
                                </div>
                            ) : null}
                            {readOnly ? (
                                <div className="technician-check-notice" role="status">
                                    This QC record is complete and read-only. Display diagnostic evidence is shown above.
                                </div>
                            ) : !session.device_id ? (
                                <div className="technician-check-notice" role="status">
                                    Display diagnostics need an identified device. Return to device identification before starting the display tests.
                                </div>
                            ) : (
                                <Link
                                    className="button button-primary"
                                    to={`/diagnostics/display/${encodeURIComponent(sessionId)}`}
                                    state={{ returnTo: `/technician-checks?sessionId=${encodeURIComponent(sessionId)}` }}
                                >
                                    <ExternalLink size={14} aria-hidden="true" /> OPEN DISPLAY DIAGNOSTICS
                                </Link>
                            )}
                        </div>
                    )}

                    {activeCategory === "keyboard" && (
                        <div className="technician-workspace-body">
                            <p className="technician-instruction">
                                Press physical keys to record responses. Select a key below to mark a reported fault. Key presses do not determine the result.
                            </p>
                            <KeyboardGrid
                                rows={usQwertyKeyboardRows}
                                tested={keyboardTested}
                                faulty={keyboardFaulty}
                                selected={selectedKeyboardKey}
                                disabled={readOnly}
                                onSelect={setSelectedKeyboardKey}
                            />
                            <div className="keyboard-test-stats">
                                <span>Keys tested <strong>{keyboardTested.length}</strong></span>
                                <span>Faulty keys <strong>{keyboardFaulty.length}</strong></span>
                                <span>Untested keys <strong>{keyboardKeyCount - keyboardTested.length}</strong></span>
                                <span>Detected response <strong>{selectedKeyboardKey ?? "None"}</strong></span>
                            </div>
                            <div className="technician-control-row">
                                <button
                                    className="button button-secondary"
                                    type="button"
                                    disabled={!selectedKeyboardKey || readOnly}
                                    onClick={() => selectedKeyboardKey && toggleFaultyKey(selectedKeyboardKey)}
                                >
                                    {selectedKeyboardKey && keyboardFaulty.includes(selectedKeyboardKey)
                                        ? "UNMARK SELECTED KEY FAULTY"
                                        : "MARK SELECTED KEY AS FAULTY"}
                                </button>
                                <button
                                    className="button button-secondary"
                                    type="button"
                                    disabled={readOnly}
                                    onClick={() => setSelectedKeyboardKey(null)}
                                >
                                    <RotateCcw size={14} aria-hidden="true" /> CLEAR SELECTION
                                </button>
                            </div>
                            <ResultEditor
                                checkId={CHECK_IDS.keyboard}
                                options={manualOutcomes}
                                outcome={outcomes[CHECK_IDS.keyboard]}
                                notes={notes[CHECK_IDS.keyboard] || ""}
                                saved={keyboardSaved}
                                saving={Boolean(saving[CHECK_IDS.keyboard])}
                                readOnly={readOnly}
                                saveLabel="SAVE KEYBOARD RESULT"
                                onOutcome={(outcome) => chooseOutcome(CHECK_IDS.keyboard, outcome)}
                                onNotes={(value) => changeNotes(CHECK_IDS.keyboard, value)}
                                onSave={() => void saveCheck(CHECK_IDS.keyboard)}
                            />
                        </div>
                    )}

                    {activeCategory === "touchscreen" && (
                        <div className="technician-workspace-body">
                            <p className="technician-instruction">
                                Tap different screen areas, including corners, centre and edges. Test multi-touch where supported.
                            </p>
                            {!context?.hasTouchscreen && (
                                <div className="technician-check-notice" role="status">
                                    Inventory did not detect a touchscreen. Continue only if this device has one; otherwise record Not Applicable.
                                </div>
                            )}
                            <div className="touchscreen-test-area">Use the device touchscreen to inspect this area</div>
                            <ResultEditor
                                checkId={CHECK_IDS.touchscreen}
                                options={manualOutcomes}
                                outcome={outcomes[CHECK_IDS.touchscreen]}
                                notes={notes[CHECK_IDS.touchscreen] || ""}
                                saved={touchscreenSaved}
                                saving={Boolean(saving[CHECK_IDS.touchscreen])}
                                readOnly={readOnly}
                                saveLabel="SAVE TOUCHSCREEN RESULT"
                                onOutcome={(outcome) => chooseOutcome(CHECK_IDS.touchscreen, outcome)}
                                onNotes={(value) => changeNotes(CHECK_IDS.touchscreen, value)}
                                onSave={() => void saveCheck(CHECK_IDS.touchscreen)}
                            />
                        </div>
                    )}

                    {activeCategory === "touchpad" && (
                        <div className="technician-workspace-body">
                            <p className="technician-instruction">
                                Manually perform each movement and click step on the device touchpad.
                            </p>
                            {!context?.hasTouchpad && (
                                <div className="technician-check-notice" role="status">
                                    Inventory did not detect a touchpad. Continue only if this device has one; otherwise record Not Applicable.
                                </div>
                            )}
                            <ol className="touchpad-instructions">
                                <li>Move the pointer across the touchpad.</li>
                                <li>Test single-finger movement.</li>
                                <li>Test left click.</li>
                                <li>Test right click.</li>
                                <li>Test scrolling.</li>
                            </ol>
                            <ResultEditor
                                checkId={CHECK_IDS.touchpad}
                                options={touchpadOutcomes}
                                outcome={outcomes[CHECK_IDS.touchpad]}
                                notes={notes[CHECK_IDS.touchpad] || ""}
                                saved={touchpadSaved}
                                saving={Boolean(saving[CHECK_IDS.touchpad])}
                                readOnly={readOnly}
                                saveLabel="SAVE MOVEMENT RESULT"
                                onOutcome={(outcome) => chooseOutcome(CHECK_IDS.touchpad, outcome)}
                                onNotes={(value) => changeNotes(CHECK_IDS.touchpad, value)}
                                onSave={() => void saveCheck(CHECK_IDS.touchpad)}
                            />
                            <p className="technician-instruction">
                                Then test the buttons and supported multi-finger gestures.
                            </p>
                            <ol className="touchpad-instructions">
                                <li>Left-click and right-click with the touchpad buttons.</li>
                                <li>Two-finger scroll.</li>
                                <li>Multi-finger gestures supported by this device.</li>
                            </ol>
                            <ResultEditor
                                checkId={CHECK_IDS.touchpadGestures}
                                options={touchpadOutcomes}
                                outcome={outcomes[CHECK_IDS.touchpadGestures]}
                                notes={notes[CHECK_IDS.touchpadGestures] || ""}
                                saved={gesturesSaved}
                                saving={Boolean(saving[CHECK_IDS.touchpadGestures])}
                                readOnly={readOnly}
                                saveLabel="SAVE GESTURE RESULT"
                                onOutcome={(outcome) => chooseOutcome(CHECK_IDS.touchpadGestures, outcome)}
                                onNotes={(value) => changeNotes(CHECK_IDS.touchpadGestures, value)}
                                onSave={() => void saveCheck(CHECK_IDS.touchpadGestures)}
                            />
                        </div>
                    )}

                    {activeCategory === "ports" && context && (
                        <PortsPanel
                            ports={ports}
                            selectedPortId={selectedPortId}
                            detectorHints={{ usbDevices: context.usbDevices, connectors: context.connectors }}
                            disabled={readOnly}
                            onAdd={addPort}
                            onSelect={setSelectedPortId}
                            onChange={changePort}
                            onSave={savePort}
                            onSkip={skipPort}
                            onFinalize={finalizePorts}
                        />
                    )}
                </section>
            )}
        </main>
    );
}
