import { useEffect, useMemo, useState } from "react";
import { Link, useNavigate, useSearchParams } from "react-router-dom";

import {
    completeDiagnosticSession,
    createDiagnosticSession,
    assetResolutionConfirmed,
    assetResolutionRequestFields,
    DiagnosticSession,
    getDiagnosticSession,
    getManualChecks,
    ManualCheck,
    recordManualResult,
} from "../api/execution";
import { useQcSession } from "../session/SessionContext";
import { getStationProfile } from "../station";
import AssetResolutionPicker from "../components/AssetResolutionPicker";
import type { AssetResolutionSelection } from "../api/execution";

type ManualOutcome = "passed" | "failed" | "warning" | "not_applicable" | "blocked" | "not_run";
type Condition = "Excellent" | "Good" | "Average" | "Damaged" | "Missing" | "N/A";

const COSMETIC_CONDITIONS: Condition[] = ["Excellent", "Good", "Average", "Damaged", "Missing", "N/A"];
const COSMETIC_IDS = new Set([
    "chassis_cosmetic",
    "display_cosmetic",
    "hinges_cosmetic",
    "keyboard_cosmetic",
    "ports_cosmetic",
    "physical_inspection",
]);
const HIDDEN_MANUAL_CHECKS = new Set([
    "usb_read_write",
    "memtest86_result",
    "display_pattern",
    "display_brightness",
]);

function isCosmetic(check: ManualCheck) {
    return COSMETIC_IDS.has(check.id) || check.id.endsWith("_cosmetic");
}

function checkCategory(check: ManualCheck) {
    const id = check.id;
    if (/cosmetic|physical_inspection/.test(id)) return "Physical condition";
    if (/display|touchscreen/.test(id)) return "Display";
    if (/keyboard|mouse|touchpad/.test(id)) return "Input";
    if (/speaker|microphone|headset/.test(id)) return "Audio";
    if (/ethernet|wifi|bluetooth/.test(id)) return "Connectivity";
    if (/usb|hdmi|displayport|vga|card_reader/.test(id)) return "Ports and readers";
    if (/webcam|face_recognition/.test(id)) return "Camera and biometrics";
    if (/charger|charging|battery/.test(id)) return "Power";
    return "Other components";
}

function conditionOutcome(condition: Condition): ManualOutcome {
    if (condition === "Excellent" || condition === "Good") return "passed";
    if (condition === "Average") return "warning";
    if (condition === "Damaged" || condition === "Missing") return "failed";
    return "not_applicable";
}

function outcomeLabel(outcome: ManualOutcome) {
    return ({
        passed: "Pass",
        failed: "Fail",
        warning: "Attention",
        not_applicable: "N/A",
        blocked: "Unable to verify",
        not_run: "Not checked",
    })[outcome];
}

function statusClass(outcome?: ManualOutcome) {
    if (outcome === "passed") return "is-pass";
    if (outcome === "failed") return "is-fail";
    if (outcome === "warning" || outcome === "blocked") return "is-warning";
    return "is-neutral";
}

function getSavedOutcome(value: unknown): ManualOutcome | undefined {
    if (typeof value !== "object" || value === null || Array.isArray(value)) return undefined;
    const status = (value as Record<string, unknown>).status;
    return ["passed", "failed", "warning", "not_applicable", "blocked", "not_run"].includes(String(status))
        ? status as ManualOutcome
        : undefined;
}

function getSavedNotes(value: unknown) {
    if (typeof value !== "object" || value === null || Array.isArray(value)) return "";
    const notes = (value as Record<string, unknown>).notes;
    return typeof notes === "string" ? notes : "";
}

function savedCondition(notes: string): Condition | undefined {
    const match = notes.match(/^Condition: (Excellent|Good|Average|Damaged|Missing|N\/A)(?:\.|$)/);
    return match?.[1] as Condition | undefined;
}

export default function QcInspection() {
    const [params] = useSearchParams();
    const navigate = useNavigate();
    const { activeSession, activeSessionId, activateSession } = useQcSession();
    const stage = params.get("stage") === "cosmetic" ? "cosmetic" : "functional";
    const standalone = params.get("standalone") === "1";
    const sessionId = params.get("sessionId") || (standalone ? "" : activeSessionId);
    const [session, setSession] = useState<DiagnosticSession | null>(null);
    const [checks, setChecks] = useState<ManualCheck[]>([]);
    const [outcomes, setOutcomes] = useState<Record<string, ManualOutcome>>({});
    const [conditions, setConditions] = useState<Record<string, Condition>>({});
    const [notes, setNotes] = useState<Record<string, string>>({});
    const [saved, setSaved] = useState<Record<string, boolean>>({});
    const [saving, setSaving] = useState<Record<string, boolean>>({});
    const [loading, setLoading] = useState(true);
    const [finishing, setFinishing] = useState(false);
    const [error, setError] = useState("");
    const [assetResolution, setAssetResolution] = useState<AssetResolutionSelection | null>(null);

    useEffect(() => {
        let current = true;
        setLoading(true);
        setError("");

        Promise.all([
            getManualChecks(),
            sessionId ? getDiagnosticSession(sessionId) : Promise.resolve(null),
        ])
            .then(([availableChecks, loadedSession]) => {
                if (!current) return;
                const visibleChecks = availableChecks.filter((check) => !HIDDEN_MANUAL_CHECKS.has(check.id));
                setChecks(visibleChecks);
                setSession(loadedSession);
                const results = loadedSession?.manual_results || {};
                const nextOutcomes: Record<string, ManualOutcome> = {};
                const nextConditions: Record<string, Condition> = {};
                const nextNotes: Record<string, string> = {};
                const nextSaved: Record<string, boolean> = {};
                for (const check of visibleChecks) {
                    const record = results[check.id];
                    const outcome = getSavedOutcome(record);
                    const recordNotes = getSavedNotes(record);
                    if (outcome) {
                        nextOutcomes[check.id] = outcome;
                        nextSaved[check.id] = true;
                    }
                    nextNotes[check.id] = recordNotes.replace(/^Condition: (?:Excellent|Good|Average|Damaged|Missing|N\/A)\.\s*/, "");
                    const condition = savedCondition(recordNotes);
                    if (condition) nextConditions[check.id] = condition;
                }
                setOutcomes(nextOutcomes);
                setConditions(nextConditions);
                setNotes(nextNotes);
                setSaved(nextSaved);
            })
            .catch((loadError: unknown) => {
                if (current) setError(loadError instanceof Error ? loadError.message : "Inspection checks could not be loaded.");
            })
            .finally(() => {
                if (current) setLoading(false);
            });

        return () => {
            current = false;
        };
    }, [sessionId]);

    const stageChecks = useMemo(
        () => checks.filter((check) => isCosmetic(check) === (stage === "cosmetic")),
        [checks, stage],
    );
    const categories = useMemo(
        () => [...new Set(stageChecks.map(checkCategory))],
        [stageChecks],
    );
    const savedCount = stageChecks.filter((check) => saved[check.id]).length;
    const allSaved = stageChecks.length > 0 && savedCount === stageChecks.length;
    const canContinue = standalone ? savedCount > 0 : allSaved;
    const readOnly = ["complete", "completed"].includes((session?.status || "").toLowerCase());

    function chooseCondition(checkId: string, condition: Condition) {
        setConditions((current) => ({ ...current, [checkId]: condition }));
        setOutcomes((current) => ({ ...current, [checkId]: conditionOutcome(condition) }));
        setSaved((current) => ({ ...current, [checkId]: false }));
    }

    function chooseOutcome(checkId: string, outcome: ManualOutcome) {
        setOutcomes((current) => ({ ...current, [checkId]: outcome }));
        setSaved((current) => ({ ...current, [checkId]: false }));
    }

    async function saveCheck(check: ManualCheck) {
        const outcome = outcomes[check.id];
        if (!outcome || saving[check.id] || readOnly) return;
        if (standalone && !session && !assetResolution) {
            setError("Choose how this inspection will resolve its asset identity.");
            return;
        }
        setSaving((current) => ({ ...current, [check.id]: true }));
        setError("");
        try {
            let targetSession = session;
            if (!targetSession) {
                const station = getStationProfile();
                if (!assetResolution) {
                    throw new Error("Choose how this inspection will resolve its asset identity.");
                }
                const assetFields = assetResolutionRequestFields(assetResolution);
                const created = await createDiagnosticSession(undefined, {
                    technician: station?.technician || undefined,
                    station_id: station?.station_id || undefined,
                    workflow_type: "standalone_manual_diagnostic",
                    ...assetFields,
                });
                if (typeof created.session_id !== "string" || !created.session_id) {
                    throw new Error("The standalone inspection could not be assigned a session ID.");
                }
                if (!assetResolutionConfirmed(created.asset_id, assetResolution)) {
                    throw new Error("The backend did not confirm the requested asset identity. The result was not saved.");
                }
                targetSession = await activateSession(created.session_id);
                setSession(targetSession);
                const nextParams = new URLSearchParams({ sessionId: targetSession.session_id, stage });
                if (standalone) nextParams.set("standalone", "1");
                navigate(`/qc?${nextParams.toString()}`, { replace: true });
            }

            const condition = conditions[check.id];
            const note = notes[check.id]?.trim() || "";
            const recordedNotes = condition
                ? `Condition: ${condition}.${note ? ` ${note}` : ""}`
                : note;
            await recordManualResult(targetSession.session_id, check.id, {
                outcome,
                notes: recordedNotes,
                scan_status: "not_attempted",
                detected_devices: [],
                technician_decision: outcome === "passed"
                    ? "working"
                    : outcome === "failed"
                      ? "not_working"
                      : outcome === "blocked"
                        ? "unable_to_verify"
                        : null,
                evidence: {},
            });
            setSaved((current) => ({ ...current, [check.id]: true }));
            const refreshed = await getDiagnosticSession(targetSession.session_id);
            setSession(refreshed);
        } catch (saveError) {
            setError(saveError instanceof Error ? saveError.message : "This inspection result could not be saved.");
        } finally {
            setSaving((current) => ({ ...current, [check.id]: false }));
        }
    }

    async function continueWorkflow() {
        if (!session) {
            setError("Confirm the inspection record before continuing.");
            return;
        }
        if (stage === "cosmetic") {
            navigate(`/qc?sessionId=${encodeURIComponent(session.session_id)}&stage=functional`);
            return;
        }

        setFinishing(true);
        setError("");
        try {
            await completeDiagnosticSession(session.session_id);
            navigate(standalone
                ? `/results?sessionId=${encodeURIComponent(session.session_id)}`
                : `/photos?sessionId=${encodeURIComponent(session.session_id)}`);
        } catch (finishError) {
            setError(finishError instanceof Error ? finishError.message : "The inspection could not be saved for final review.");
        } finally {
            setFinishing(false);
        }
    }

    if (!standalone && !sessionId) {
        return (
            <section className="empty-panel">
                <span className="empty-panel-icon" aria-hidden="true">✓</span>
                <h1>No QC session selected</h1>
                <p>Start a new QC intake or resume an inspection from QC History before recording results.</p>
                <div className="active-qc-actions">
                    <Link className="button button-primary" to="/devices?new=1">Start New QC</Link>
                    <Link className="button button-secondary" to="/history">Open QC History</Link>
                </div>
            </section>
        );
    }

    if (loading) return <div className="loading-panel">Loading inspection checklist…</div>;

    return (
        <div className="page-flow qc-inspection-page">
            <header className="page-header">
                <div>
                    <span className="eyebrow">{standalone ? "STANDALONE MANUAL INSPECTION" : `QC SESSION · ${sessionId}`}</span>
                    <h1 className="page-title">{stage === "cosmetic" ? "Cosmetic inspection" : "Functional inspection"}</h1>
                    <p className="page-description">
                        {stage === "cosmetic"
                            ? "Record visible condition by component. Each selection is saved to this QC session."
                            : "Record whether each component works, needs attention, or could not be verified."}
                    </p>
                </div>
                <span className={`qc-context-status ${readOnly || allSaved ? "is-complete" : ""}`}>
                    {readOnly ? "Read-only completed record" : `${savedCount} of ${stageChecks.length} saved`}
                </span>
            </header>

            {stage === "functional" && sessionId && (
                <section className="display-diagnostic-launch">
                    <div>
                        <span className="eyebrow">DISPLAY WORKSPACE</span>
                        <h2>Run dedicated display diagnostics</h2>
                        <p>
                            Inspect the panel with full-screen patterns and save technician
                            results to this QC session.
                        </p>
                    </div>
                    <Link
                        className="button button-primary"
                        to={`/diagnostics/display/${encodeURIComponent(sessionId)}`}
                        state={{
                            returnTo: `/qc?sessionId=${encodeURIComponent(sessionId)}&stage=functional`,
                        }}
                    >
                        Open Display Diagnostics
                    </Link>
                </section>
            )}

            {error && <div className="error-box" role="alert">{error}</div>}

            {standalone && !session && (
                <AssetResolutionPicker
                    value={assetResolution}
                    onChange={(selection) => {
                        setAssetResolution(selection);
                        setError("");
                    }}
                />
            )}

            {stageChecks.length === 0 ? (
                <div className="empty-panel">
                    <h2>No {stage} checks available</h2>
                    <p>The station did not return any manual checks for this section.</p>
                </div>
            ) : (
                <div className="qc-check-sections">
                    {categories.map((category) => (
                        <section className="qc-check-section" key={category}>
                            <header className="qc-check-section-heading">
                                <h2>{category}</h2>
                                <span>
                                    {stageChecks.filter((check) => checkCategory(check) === category && saved[check.id]).length}
                                    {" / "}
                                    {stageChecks.filter((check) => checkCategory(check) === category).length} saved
                                </span>
                            </header>
                            <div className="qc-check-list">
                                {stageChecks.filter((check) => checkCategory(check) === category).map((check) => {
                                    const condition = conditions[check.id];
                                    const outcome = outcomes[check.id];
                                    return (
                                        <article className={`qc-check-card ${saved[check.id] ? "is-saved" : ""}`} key={check.id}>
                                            <div className="qc-check-copy">
                                                <div className="qc-check-title">
                                                    <h3>{check.name}</h3>
                                                    <span className={`qc-check-status ${statusClass(saved[check.id] ? outcome : undefined)}`}>
                                                        {saved[check.id] && outcome ? outcomeLabel(outcome) : "Not checked"}
                                                    </span>
                                                </div>
                                                <p>{check.instructions}</p>
                                            </div>
                                            {stage === "cosmetic" ? (
                                                <div className="qc-condition-options" aria-label={`${check.name} condition`}>
                                                    {COSMETIC_CONDITIONS.map((item) => (
                                                        <button
                                                            className={`qc-condition-button${condition === item ? " selected" : ""}`}
                                                            type="button"
                                                            key={item}
                                                            aria-pressed={condition === item}
                                                            disabled={readOnly}
                                                            onClick={() => chooseCondition(check.id, item)}
                                                        >
                                                            {item}
                                                        </button>
                                                    ))}
                                                </div>
                                            ) : (
                                                <div className="qc-outcome-options" aria-label={`${check.name} result`}>
                                                    {([
                                                        ["passed", "Pass"],
                                                        ["failed", "Fail"],
                                                        ["not_applicable", "N/A"],
                                                        ["blocked", "Unable to verify"],
                                                    ] as const).map(([value, label]) => (
                                                        <button
                                                            className={`qc-outcome-button${outcome === value ? " selected" : ""}`}
                                                            type="button"
                                                            key={value}
                                                            aria-pressed={outcome === value}
                                                            disabled={readOnly}
                                                            onClick={() => chooseOutcome(check.id, value)}
                                                        >
                                                            {label}
                                                        </button>
                                                    ))}
                                                </div>
                                            )}
                                            <label className="qc-check-notes">
                                                Technician note
                                                <textarea
                                                    rows={2}
                                                    maxLength={2000}
                                                    disabled={readOnly}
                                                    value={notes[check.id] || ""}
                                                    onChange={(event) => {
                                                        setNotes((current) => ({ ...current, [check.id]: event.target.value }));
                                                        setSaved((current) => ({ ...current, [check.id]: false }));
                                                    }}
                                                    placeholder="Add a note or describe the observed issue"
                                                />
                                            </label>
                                            <div className="qc-check-actions">
                                                <button
                                                    className="button button-primary"
                                                    type="button"
                                                    disabled={
                                                        readOnly ||
                                                        !outcome ||
                                                        saving[check.id] ||
                                                        saved[check.id] ||
                                                        (standalone &&
                                                            !session &&
                                                            (!assetResolution ||
                                                                (assetResolution.mode === "existing" &&
                                                                    !assetResolution.assetId.trim())))
                                                    }
                                                    onClick={() => void saveCheck(check)}
                                                >
                                                    {saving[check.id] ? "Saving…" : saved[check.id] ? "Saved" : "Save result"}
                                                </button>
                                            </div>
                                        </article>
                                    );
                                })}
                            </div>
                        </section>
                    ))}
                </div>
            )}

            {readOnly ? (
                <footer className="qc-workflow-footer">
                    <span>This completed QC record is read-only.</span>
                    <Link className="button button-primary" to={`/report?sessionId=${encodeURIComponent(sessionId)}`}>
                        Open completed report →
                    </Link>
                </footer>
            ) : (
            <footer className="qc-workflow-footer">
                    {!standalone ? (
                    <button
                        className="button button-secondary"
                        type="button"
                        onClick={() => navigate(stage === "functional"
                            ? `/qc?sessionId=${encodeURIComponent(sessionId)}&stage=cosmetic`
                            : `/devices?sessionId=${encodeURIComponent(sessionId)}`)}
                    >
                        ← {stage === "functional" ? "Cosmetic inspection" : "Device intake"}
                    </button>
                    ) : (
                        <Link className="button button-secondary" to="/">← Dashboard</Link>
                    )}
                    <span>{savedCount} / {stageChecks.length} results saved</span>
                    <button
                        className="button button-primary"
                        type="button"
                        disabled={!canContinue || finishing}
                        onClick={() => void continueWorkflow()}
                    >
                        {finishing
                            ? "Saving inspection…"
                            : standalone
                              ? "Complete standalone report →"
                              : stage === "cosmetic"
                                ? "Continue to functional inspection →"
                                : "Save checks & continue to evidence →"}
                    </button>
                </footer>
            )}
        </div>
    );
}
