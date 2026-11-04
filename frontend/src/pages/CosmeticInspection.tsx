import { ChangeEvent, useEffect, useMemo, useState } from "react";
import { Link, useNavigate, useSearchParams } from "react-router-dom";

import {
    CosmeticArea,
    CosmeticCondition,
    CosmeticInspectionPhase,
    CosmeticItemRecord,
    DamageSeverity,
    saveCosmeticInspection,
} from "../api/cosmeticInspection";
import { getEvidenceUrl, uploadEvidence } from "../api/evidence";
import { DiagnosticSession, getDiagnosticSession } from "../api/execution";
import { useQcSession } from "../session/SessionContext";
import FieldLabel from "../components/FieldLabel";

interface CosmeticItemDefinition {
    id: string;
    name: string;
    areas: CosmeticArea[];
    modelDependent?: boolean;
}

const AREAS: Array<{ id: CosmeticArea; name: string; short: string }> = [
    { id: "A", name: "Top lid", short: "Top lid" },
    { id: "B", name: "Bottom base", short: "Bottom base" },
    { id: "C", name: "Left side", short: "Left side" },
    { id: "D", name: "Right side", short: "Right side" },
    { id: "E", name: "Palmrest / keyboard area", short: "Palmrest" },
];

const BASE_ITEMS: CosmeticItemDefinition[] = [
    { id: "top_lid", name: "Top lid", areas: ["A"] },
    { id: "bezel", name: "Bezel", areas: ["A"] },
    { id: "palmrest_panel", name: "Palmrest panel", areas: ["E"] },
    { id: "bottom_cover", name: "Bottom cover", areas: ["B"] },
    { id: "left_hinge", name: "Left hinge", areas: ["C"] },
    { id: "right_hinge", name: "Right hinge", areas: ["D"] },
    { id: "keyboard_keys", name: "Keyboard keys", areas: ["E"] },
    { id: "keyboard_printing", name: "Keyboard printing", areas: ["E"] },
    { id: "touchpad_surface", name: "Touchpad surface", areas: ["E"] },
    { id: "touchpad_buttons", name: "Touchpad buttons", areas: ["E"] },
    { id: "display_panel", name: "Display panel", areas: ["A"] },
    { id: "windows_sticker", name: "Windows sticker", areas: ["E"], modelDependent: true },
    { id: "processor_sticker", name: "Processor sticker", areas: ["E"], modelDependent: true },
    { id: "rubber_feet", name: "Rubber feet", areas: ["B"] },
    { id: "screws", name: "Screws", areas: ["B"] },
    { id: "top_cover_logo", name: "Top cover logo", areas: ["A"] },
    { id: "palmrest_branding", name: "Palmrest branding", areas: ["E"] },
    { id: "side_panels_edges", name: "Side panels and edges", areas: ["C", "D"] },
];

const CONDITIONS: CosmeticCondition[] = [
    "Excellent",
    "Good",
    "Average",
    "Damaged",
    "Missing",
    "Not Applicable",
];
const SEVERITIES: DamageSeverity[] = ["None", "Minor", "Moderate", "Severe"];

function emptyRecord(item: CosmeticItemDefinition): CosmeticItemRecord {
    return {
        name: item.name,
        areas: item.areas,
        condition: null,
        severity: null,
        damage_description: "",
        damage_location: "",
        notes: "",
        evidence_ids: [],
        technician_confirmed: false,
        custom: Boolean(item.id.startsWith("custom_")),
        model_dependent: Boolean(item.modelDependent),
    };
}

function comparableCondition(condition: CosmeticCondition | null) {
    if (!condition || condition === "Not Applicable") return null;
    return ({
        Excellent: 5,
        Good: 4,
        Average: 3,
        Damaged: 2,
        Missing: 1,
    })[condition];
}

function comparisonStatus(current?: CosmeticItemRecord, initial?: CosmeticItemRecord) {
    if (!current?.condition || !initial?.condition) return "";
    const currentScore = comparableCondition(current.condition);
    const initialScore = comparableCondition(initial.condition);
    if (currentScore === null || initialScore === null) return "";
    if (currentScore > initialScore) return "Improved";
    if (currentScore < initialScore) return "Deteriorated";
    const severityRank: Record<DamageSeverity, number> = {
        None: 4,
        Minor: 3,
        Moderate: 2,
        Severe: 1,
    };
    if (current.severity && initial.severity && current.severity !== initial.severity) {
        return severityRank[current.severity] > severityRank[initial.severity]
            ? "Improved"
            : "Deteriorated";
    }
    return "Unchanged";
}

function itemIsComplete(item: CosmeticItemRecord) {
    const condition = item.condition;
    if (!condition || !item.severity) return false;
    if (
        (condition === "Damaged" || condition === "Missing") &&
        (!item.damage_description.trim() || !item.damage_location.trim() || item.severity === "None")
    ) {
        return false;
    }
    return true;
}

function itemMatches(left?: CosmeticItemRecord, right?: CosmeticItemRecord) {
    return JSON.stringify(left || null) === JSON.stringify(right || null);
}

export default function CosmeticInspection() {
    const [params] = useSearchParams();
    const navigate = useNavigate();
    const { activeSessionId } = useQcSession();
    const sessionId = params.get("sessionId") || activeSessionId;
    const phase: CosmeticInspectionPhase = params.get("phase") === "final" ? "final" : "initial";
    const [session, setSession] = useState<DiagnosticSession | null>(null);
    const [items, setItems] = useState<Record<string, CosmeticItemRecord>>({});
    const [savedItems, setSavedItems] = useState<Record<string, CosmeticItemRecord>>({});
    const [selectedArea, setSelectedArea] = useState<CosmeticArea | "all">("all");
    const [loading, setLoading] = useState(true);
    const [saving, setSaving] = useState(false);
    const [uploadingItem, setUploadingItem] = useState("");
    const [error, setError] = useState("");
    const [customName, setCustomName] = useState("");
    const [customArea, setCustomArea] = useState<CosmeticArea>("E");
    const busy = saving || Boolean(uploadingItem);

    useEffect(() => {
        let current = true;
        if (!sessionId) {
            setSession(null);
            setItems({});
            setSavedItems({});
            setLoading(false);
            return;
        }
        setLoading(true);
        setError("");
        getDiagnosticSession(sessionId)
            .then((loaded) => {
                if (!current) return;
                const inspections = loaded.cosmetic_inspections || {};
                const initialItems = inspections.initial?.items || {};
                const phaseItems = inspections[phase]?.items || {};
                const customIds = new Set(
                    Object.entries({ ...initialItems, ...phaseItems })
                        .filter(([, item]) => item.custom)
                        .map(([id]) => id),
                );
                const definitions = [
                    ...BASE_ITEMS,
                    ...[...customIds].map((id) => {
                        const saved = phaseItems[id] || initialItems[id];
                        return {
                            id,
                            name: saved?.name || "Custom item",
                            areas: saved?.areas?.length ? saved.areas : ["E" as CosmeticArea],
                        };
                    }),
                ];
                const loadedItems: Record<string, CosmeticItemRecord> = {};
                for (const definition of definitions) {
                    loadedItems[definition.id] = {
                        ...emptyRecord(definition),
                        ...(phaseItems[definition.id] || {}),
                        name: phaseItems[definition.id]?.name || definition.name,
                        areas: phaseItems[definition.id]?.areas?.length
                            ? phaseItems[definition.id].areas
                            : definition.areas,
                    };
                }
                setSession(loaded);
                setItems(loadedItems);
                setSavedItems(loadedItems);
            })
            .catch((loadError: unknown) => {
                if (current) {
                    setError(loadError instanceof Error ? loadError.message : "The cosmetic inspection could not be loaded.");
                }
            })
            .finally(() => {
                if (current) setLoading(false);
            });
        return () => {
            current = false;
        };
    }, [sessionId, phase]);

    const initialItems = session?.cosmetic_inspections?.initial?.items || {};
    const definitions = useMemo(() => {
        const customDefinitions = Object.entries(items)
            .filter(([id, item]) => item.custom && !BASE_ITEMS.some((base) => base.id === id))
            .map(([id, item]) => ({
                id,
                name: item.name,
                areas: item.areas.length ? item.areas : ["E" as CosmeticArea],
                modelDependent: item.model_dependent,
            }));
        return [...BASE_ITEMS, ...customDefinitions];
    }, [items]);
    const visibleItems = definitions.filter(
        (item) => selectedArea === "all" || item.areas.includes(selectedArea),
    );
    const inspectedCount = definitions.filter((item) => {
        const record = items[item.id];
        return Boolean(record?.technician_confirmed && itemIsComplete(record));
    }).length;
    const completeCount = definitions.filter((item) => itemIsComplete(items[item.id] || emptyRecord(item))).length;
    const readOnly = ["complete", "completed"].includes((session?.status || "").toLowerCase());
    const comparisonCounts = definitions.reduce(
        (counts, definition) => {
            const result = comparisonStatus(items[definition.id], initialItems[definition.id]);
            if (result === "Improved") counts.improved += 1;
            if (result === "Deteriorated") counts.deteriorated += 1;
            return counts;
        },
        { improved: 0, deteriorated: 0 },
    );
    const allSaved = definitions.every((item) =>
        itemMatches(items[item.id], savedItems[item.id]),
    );

    function updateItem(itemId: string, patch: Partial<CosmeticItemRecord>) {
        setItems((current) => ({
            ...current,
            [itemId]: {
                ...current[itemId],
                ...patch,
                technician_confirmed: false,
            },
        }));
    }

    async function persistItems(nextItems: Record<string, CosmeticItemRecord>) {
        if (!sessionId || readOnly || saving) return false;
        setSaving(true);
        setError("");
        try {
            const record = await saveCosmeticInspection(sessionId, phase, nextItems);
            setItems(nextItems);
            setSavedItems(record.items);
            setSession((current) => current
                ? {
                    ...current,
                    cosmetic_inspections: {
                        ...current.cosmetic_inspections,
                        [phase]: record,
                    },
                }
                : current);
            return true;
        } catch (saveError) {
            setItems(nextItems);
            setError(saveError instanceof Error ? saveError.message : "Cosmetic inspection changes could not be saved.");
            return false;
        } finally {
            setSaving(false);
        }
    }

    async function saveItem(itemId: string) {
        const item = items[itemId];
        if (!item || !item.technician_confirmed || !itemIsComplete(item)) {
            setError("Select a condition and severity, complete damage details when required, and confirm the item.");
            return;
        }
        await persistItems(items);
    }

    async function markAllInspected() {
        const next = { ...items };
        for (const definition of definitions) {
            const record = next[definition.id];
            if (record && itemIsComplete(record)) {
                next[definition.id] = { ...record, technician_confirmed: true };
            }
        }
        setItems(next);
        const saved = await persistItems(next);
        if (saved && completeCount !== definitions.length) {
            setError("Completed items were confirmed. Fill in each remaining condition, severity, and required damage details before continuing.");
        }
    }

    async function clearItem(itemId: string) {
        const definition = definitions.find((item) => item.id === itemId);
        if (!definition) return;
        const previous = items[itemId] || emptyRecord(definition);
        const next = {
            ...items,
            [itemId]: {
                ...previous,
                condition: null,
                severity: null,
                damage_description: "",
                damage_location: "",
                notes: "",
                technician_confirmed: false,
            },
        };
        await persistItems(next);
    }

    function handleConditionChange(itemId: string, condition: CosmeticCondition) {
        const severity: DamageSeverity | null =
            condition === "Excellent" || condition === "Good" || condition === "Not Applicable"
                ? "None"
                : null;
        updateItem(itemId, { condition, severity });
    }

    async function addCustomItem(event: ChangeEvent<HTMLFormElement>) {
        event.preventDefault();
        const name = customName.trim();
        if (!name || definitions.length >= 40) return;
        const id = `custom_${typeof crypto !== "undefined" && crypto.randomUUID
            ? crypto.randomUUID()
            : `${Date.now()}_${Math.random().toString(16).slice(2)}`}`;
        const definition = { id, name, areas: [customArea] };
        const next = { ...items, [id]: emptyRecord(definition) };
        setCustomName("");
        await persistItems(next);
    }

    async function attachPhoto(itemId: string, file?: File) {
        if (!sessionId || !file || !file.type.startsWith("image/")) {
            setError("Choose an image file for cosmetic evidence.");
            return;
        }
        if (file.size > 100 * 1024 * 1024) {
            setError("Evidence files must be 100 MiB or smaller.");
            return;
        }
        setUploadingItem(itemId);
        setError("");
        try {
            const metadata = await uploadEvidence(sessionId, file);
            const next = {
                ...items,
                [itemId]: {
                    ...items[itemId],
                    evidence_ids: [...(items[itemId]?.evidence_ids || []), metadata.evidence_id],
                    technician_confirmed: false,
                },
            };
            setItems(next);
            await persistItems(next);
        } catch (uploadError) {
            setError(uploadError instanceof Error ? uploadError.message : "The item photo could not be uploaded.");
        } finally {
            setUploadingItem("");
        }
    }

    async function continueInspection() {
        if (!allSaved || inspectedCount !== definitions.length) {
            setError("Save and confirm every cosmetic inspection item before continuing.");
            return;
        }
        navigate(phase === "initial"
            ? `/qc?sessionId=${encodeURIComponent(sessionId)}&stage=functional`
            : `/qa?sessionId=${encodeURIComponent(sessionId)}`);
    }

    if (!sessionId) {
        return (
            <section className="empty-panel">
                <h1>No QC session selected</h1>
                <p>Start or resume an inspection before recording cosmetic condition.</p>
                <div className="active-qc-actions">
                    <Link className="button button-primary" to="/devices?new=1">Start New QC</Link>
                    <Link className="button button-secondary" to="/history">Open QC History</Link>
                </div>
            </section>
        );
    }
    if (loading) return <div className="loading-panel">Loading cosmetic checklist…</div>;
    if (!session) return <div className="error-box" role="alert">{error || "The QC session could not be loaded."}</div>;

    return (
        <div className="page-flow cosmetic-inspection-page">
            <header className="page-header">
                <div>
                    <span className="eyebrow">{phase === "initial" ? "INITIAL COSMETIC ASSESSMENT" : "FINAL COSMETIC VERIFICATION"}</span>
                    <h1 className="page-title">{phase === "initial" ? "Cosmetic inspection" : "Final cosmetic verification"}</h1>
                    <p className="page-description">
                        Inspect each physical area, record visible condition, and attach photos to the item.
                        {phase === "final" ? " Initial assessment remains unchanged for comparison." : ""}
                    </p>
                </div>
                <div className="cosmetic-progress">
                    <strong>{inspectedCount} / {definitions.length}</strong>
                    <span>items confirmed</span>
                </div>
            </header>

            {error && <div className="error-box" role="alert">{error}</div>}

            <section className="cosmetic-area-panel" aria-label="Select device area">
                <div>
                    <span className="eyebrow">DEVICE AREAS</span>
                    <h2>Select an area to inspect</h2>
                </div>
                <div className="cosmetic-area-selector">
                    {AREAS.map((area) => {
                        const areaItems = definitions.filter((item) => item.areas.includes(area.id));
                        const areaInspected = areaItems.filter((item) =>
                            items[item.id]?.technician_confirmed && itemIsComplete(items[item.id]),
                        ).length;
                        return (
                            <button
                                type="button"
                                className={`cosmetic-area-button${selectedArea === area.id ? " selected" : ""}`}
                                key={area.id}
                                aria-pressed={selectedArea === area.id}
                                onClick={() => setSelectedArea(selectedArea === area.id ? "all" : area.id)}
                            >
                                <span className={`cosmetic-area-diagram area-${area.id.toLowerCase()}`} aria-hidden="true">{area.id}</span>
                                <strong>{area.name}</strong>
                                <small>{areaInspected} / {areaItems.length} checked</small>
                            </button>
                        );
                    })}
                    <button
                        type="button"
                        className={`cosmetic-area-button cosmetic-area-all${selectedArea === "all" ? " selected" : ""}`}
                        aria-pressed={selectedArea === "all"}
                        onClick={() => setSelectedArea("all")}
                    >
                        <span className="cosmetic-area-diagram" aria-hidden="true">ALL</span>
                        <strong>All areas</strong>
                        <small>{definitions.length} inspection items</small>
                    </button>
                </div>
            </section>

            {phase === "final" && (
                <section className="cosmetic-comparison-panel" aria-live="polite">
                    <div>
                        <span className="eyebrow">REFURBISHMENT COMPARISON</span>
                        <strong>Initial assessment vs. current condition</strong>
                    </div>
                    <span className="cosmetic-comparison-good">{comparisonCounts.improved} improved</span>
                    <span className="cosmetic-comparison-bad">{comparisonCounts.deteriorated} deteriorated</span>
                    <span className="cosmetic-comparison-note">Initial records are retained and cannot be changed here.</span>
                </section>
            )}

            <div className="cosmetic-list-toolbar">
                <span>{selectedArea === "all" ? "All physical components" : `${AREAS.find((area) => area.id === selectedArea)?.name} items`}</span>
                <button className="button button-secondary" type="button" onClick={() => void markAllInspected()} disabled={readOnly || busy}>
                    {busy ? "Saving…" : "Mark all inspected"}
                </button>
            </div>

            <section className="cosmetic-item-list" aria-label="Cosmetic inspection checklist">
                {visibleItems.map((definition) => {
                    const item = items[definition.id] || emptyRecord(definition);
                    const initial = initialItems[definition.id];
                    const comparison = phase === "final" ? comparisonStatus(item, initial) : "";
                    const itemSaved = itemMatches(item, savedItems[definition.id]);
                    return (
                        <article className={`cosmetic-item-card${item.technician_confirmed && itemSaved ? " is-confirmed" : ""}`} key={definition.id}>
                            <div className="cosmetic-item-heading">
                                <div>
                                    <span className="eyebrow">AREA {definition.areas.join(" / ")}</span>
                                    <h2>{item.name}</h2>
                                    {item.model_dependent && <span className="cosmetic-model-note">Model-dependent item</span>}
                                </div>
                                <div className="cosmetic-item-badges">
                                    {comparison && <span className={`cosmetic-comparison-badge is-${comparison.toLowerCase()}`}>{comparison}</span>}
                                    <span className={`qc-check-status${item.technician_confirmed && itemSaved ? " is-pass" : " is-neutral"}`}>
                                        {item.technician_confirmed && itemSaved ? "Confirmed" : "Not confirmed"}
                                    </span>
                                </div>
                            </div>

                            {phase === "final" && initial?.condition && (
                                <div className="cosmetic-initial-reference">
                                    Initial condition: <strong>{initial.condition}</strong>
                                    {initial.severity && initial.severity !== "None" ? ` · ${initial.severity} severity` : ""}
                                    {initial.damage_location ? ` · ${initial.damage_location}` : ""}
                                </div>
                            )}

                            <div className="cosmetic-fields-grid">
                                <FieldLabel required>
                                    Condition
                                    <select
                                        required
                                        disabled={readOnly || busy}
                                        value={item.condition || ""}
                                        onChange={(event) => handleConditionChange(definition.id, event.target.value as CosmeticCondition)}
                                    >
                                        <option value="">Select condition</option>
                                        {CONDITIONS.map((condition) => <option key={condition}>{condition}</option>)}
                                    </select>
                                </FieldLabel>
                                <FieldLabel required>
                                    Damage severity
                                    <select
                                        required
                                        disabled={readOnly || busy || item.condition === "Excellent" || item.condition === "Good" || item.condition === "Not Applicable"}
                                        value={item.severity || ""}
                                        onChange={(event) => updateItem(definition.id, { severity: (event.target.value || null) as DamageSeverity | null })}
                                    >
                                        <option value="">Select severity</option>
                                        {SEVERITIES.map((severity) => <option key={severity}>{severity}</option>)}
                                    </select>
                                </FieldLabel>
                                <FieldLabel required={item.condition === "Damaged" || item.condition === "Missing"}>
                                    Damage description
                                    <input
                                        required={item.condition === "Damaged" || item.condition === "Missing"}
                                        maxLength={2000}
                                        disabled={readOnly || busy}
                                        value={item.damage_description}
                                        onChange={(event) => updateItem(definition.id, { damage_description: event.target.value })}
                                        placeholder={item.condition === "Damaged" || item.condition === "Missing"
                                            ? "Describe the visible damage"
                                            : "Optional unless damage is recorded"}
                                    />
                                </FieldLabel>
                                <FieldLabel required={item.condition === "Damaged" || item.condition === "Missing"}>
                                    Damage location
                                    <input
                                        required={item.condition === "Damaged" || item.condition === "Missing"}
                                        maxLength={300}
                                        disabled={readOnly || busy}
                                        value={item.damage_location}
                                        onChange={(event) => updateItem(definition.id, { damage_location: event.target.value })}
                                        placeholder={item.condition === "Damaged" || item.condition === "Missing"
                                            ? "For example, upper-right corner"
                                            : "Optional unless damage is recorded"}
                                    />
                                </FieldLabel>
                                <FieldLabel className="cosmetic-notes-field">
                                    Notes
                                    <textarea
                                        rows={2}
                                        maxLength={2000}
                                        disabled={readOnly || busy}
                                        value={item.notes}
                                        onChange={(event) => updateItem(definition.id, { notes: event.target.value })}
                                        placeholder="Additional observation"
                                    />
                                </FieldLabel>
                            </div>

                            <div className="cosmetic-evidence-row">
                                <label className="cosmetic-photo-picker">
                                    Add or capture photo
                                    <input
                                        type="file"
                                        accept="image/*"
                                        capture="environment"
                                        disabled={readOnly || busy}
                                        onChange={(event) => {
                                            const file = event.target.files?.[0];
                                            void attachPhoto(definition.id, file);
                                            event.currentTarget.value = "";
                                        }}
                                    />
                                </label>
                                <div className="cosmetic-item-photos">
                                    {(item.evidence_ids || []).map((evidenceId, index) => (
                                        <a href={getEvidenceUrl(evidenceId)} target="_blank" rel="noreferrer" key={evidenceId}>
                                            Photo {index + 1} <span aria-hidden="true">↗</span>
                                        </a>
                                    ))}
                                    {uploadingItem === definition.id && <span>Uploading photo…</span>}
                                </div>
                            </div>

                            <div className="cosmetic-item-footer">
                                <label className="cosmetic-technician-confirmation">
                                    <input
                                        type="checkbox"
                                        checked={item.technician_confirmed}
                                        disabled={readOnly || busy || !itemIsComplete(item)}
                                        onChange={(event) => {
                                            setItems((current) => ({
                                                ...current,
                                                [definition.id]: {
                                                    ...current[definition.id],
                                                    technician_confirmed: event.target.checked,
                                                },
                                            }));
                                        }}
                                    />
                                    I inspected and confirm this item
                                </label>
                                <div className="cosmetic-item-actions">
                                    <button
                                        className="button button-quiet"
                                        type="button"
                                        disabled={readOnly || busy || item.condition === null}
                                        onClick={() => void clearItem(definition.id)}
                                    >
                                        Clear selection
                                    </button>
                                    <button
                                        className="button button-secondary"
                                        type="button"
                                        disabled={readOnly || busy || itemSaved || !item.technician_confirmed}
                                        onClick={() => void saveItem(definition.id)}
                                    >
                                        {saving && !itemSaved ? "Saving…" : itemSaved ? "Saved" : "Save item"}
                                    </button>
                                </div>
                            </div>
                        </article>
                    );
                })}
            </section>

            <form className="cosmetic-add-item-form" onSubmit={(event) => void addCustomItem(event)}>
                <div>
                    <span className="eyebrow">ADDITIONAL INSPECTION</span>
                    <h2>Add custom inspection item</h2>
                </div>
                <FieldLabel required>
                    Item name
                    <input
                        value={customName}
                        maxLength={150}
                        disabled={readOnly || busy || definitions.length >= 40}
                        onChange={(event) => setCustomName(event.target.value)}
                        placeholder="Describe another component or area"
                        required
                    />
                </FieldLabel>
                <FieldLabel>
                    Device area
                    <select value={customArea} disabled={readOnly} onChange={(event) => setCustomArea(event.target.value as CosmeticArea)}>
                        {AREAS.map((area) => <option key={area.id} value={area.id}>{area.id} — {area.name}</option>)}
                    </select>
                </FieldLabel>
                <button className="button button-secondary" type="submit" disabled={readOnly || busy || definitions.length >= 40}>
                    Add item
                </button>
            </form>

            <footer className="cosmetic-workflow-footer">
                <span className={`cosmetic-save-state${allSaved ? " is-saved" : ""}`}>
                    {readOnly ? "Completed inspection is read-only" : allSaved ? "All changes saved locally" : "Unsaved changes"}
                </span>
                <button
                    className="button button-primary"
                    type="button"
                    disabled={readOnly || busy || inspectedCount !== definitions.length || !allSaved}
                    onClick={() => void continueInspection()}
                >
                    {phase === "initial" ? "Continue to functional inspection →" : "Return to final QC →"}
                </button>
            </footer>
        </div>
    );
}
