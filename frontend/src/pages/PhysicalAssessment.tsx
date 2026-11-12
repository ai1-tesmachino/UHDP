import { useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { Camera, Plus, Trash2 } from "lucide-react";
import {
    Dialog,
    DialogContent,
    DialogDescription,
    DialogHeader,
    DialogTitle,
} from "../components/ui/dialog";
import InspectionProgress from "../components/shared/InspectionProgress";
import { useDemoInspection } from "../demo/DemoInspectionContext";
import { demoDevice } from "../demo/demoDevice";
import {
    physicalConditionOptions,
    physicalInspectionAreas,
    isPhysicalAssessmentComplete,
    type PhysicalCondition,
    type PhysicalAssessmentStatus,
    type PhysicalInspectionAreaId,
} from "../demo/physicalAssessment";
import {
    isHardwareDiagnosticsComplete,
} from "../demo/hardwareDiagnostics";
import "./physical-assessment.css";

function defectCount(condition: PhysicalCondition | null, defects: string[]) {
    return condition === "Not applicable"
        ? 0
        : defects.filter((defect) => defect.trim().length > 0).length;
}
function conditionClass(condition: PhysicalCondition | null, status: PhysicalAssessmentStatus) {
    if (status === "not_assessed" || !condition) return "is-unassessed";
    if (condition === "Good") return "is-good";
    if (condition === "Not applicable") return "is-neutral";
    return "is-damaged";
}

export default function PhysicalAssessment() {
    const navigate = useNavigate();
    const {
        deviceConfirmed,
        physicalAssessments,
        updatePhysicalAssessment,
        generalObservations,
        setGeneralObservations,
        diagnosticResults,
    } = useDemoInspection();
    const [activeAreaId, setActiveAreaId] = useState<PhysicalInspectionAreaId | null>(null);
    const [draftCondition, setDraftCondition] = useState<PhysicalCondition | null>(null);
    const [draftDefects, setDraftDefects] = useState<string[]>([]);
    const [draftRemarks, setDraftRemarks] = useState("");
    const [draftPhotos, setDraftPhotos] = useState<string[]>([]);
    const activeArea = physicalInspectionAreas.find((area) => area.id === activeAreaId);

    const assessedCount = physicalInspectionAreas.filter(
        (area) => {
            const assessment = physicalAssessments[area.id];
            return assessment.status === "assessed" && assessment.condition !== null;
        },
    ).length;
    const notAssessedCount = physicalInspectionAreas.length - assessedCount;
    const defectsRecorded = physicalInspectionAreas.reduce((total, area) => {
        const assessment = physicalAssessments[area.id];
        return total + defectCount(assessment.condition, assessment.defects);
    }, 0);
    const assessmentComplete = isPhysicalAssessmentComplete(physicalAssessments);

    function openArea(areaId: PhysicalInspectionAreaId) {
        const assessment = physicalAssessments[areaId];
        setActiveAreaId(areaId);
        setDraftCondition(assessment.condition);
        setDraftDefects([...assessment.defects]);
        setDraftRemarks(assessment.remarks);
        setDraftPhotos([...assessment.photoRefs]);
    }

    function closeEditor(open: boolean) {
        if (!open) setActiveAreaId(null);
    }

    function saveAssessment() {
        if (!activeAreaId || !draftCondition) return;
        const defects = draftCondition === "Not applicable"
            ? []
            : draftDefects.map((defect) => defect.trim()).filter(Boolean);
        updatePhysicalAssessment(activeAreaId, {
            status: "assessed",
            condition: draftCondition,
            defects,
            remarks: draftRemarks.trim(),
            photoRefs: [...draftPhotos],
            isDemoSample: false,
        });
        setActiveAreaId(null);
    }

    function addDemoPhoto() {
        setDraftPhotos((current) => [
            ...current,
            `Demo photo placeholder ${current.length + 1}`,
        ]);
    }

    return (
        <main className="physical-assessment page-flow" aria-labelledby="physical-assessment-title">
            <header className="device-id-page-header">
                <div>
                    <span className="eyebrow">DEVICE INSPECTION</span>
                    <h1 className="page-title" id="physical-assessment-title">Physical Assessment</h1>
                    <p className="page-description">
                        Inspect the external condition of the device and record any visible damage or cosmetic defects.
                    </p>
                </div>
                <span className="device-id-demo-label">DEMO DATA</span>
            </header>

            <InspectionProgress
                activeStage={1}
                deviceConfirmed={deviceConfirmed}
                physicalAssessmentComplete={assessmentComplete}
                diagnosticsComplete={isHardwareDiagnosticsComplete(diagnosticResults)}
            />

            <section className="physical-assessment-device-summary" aria-label="Current device">
                <strong>{demoDevice.manufacturer} {demoDevice.model}</strong>
                <span>Serial: {demoDevice.systemSerialNumber || "Not Available"}</span>
            </section>

            <section aria-labelledby="inspection-areas-title">
                <div className="physical-assessment-section-heading">
                    <div>
                        <h2 id="inspection-areas-title">Physical Inspection Areas</h2>
                        <p>Record each visible defect in its most relevant area.</p>
                    </div>
                    <span className="physical-assessment-sample-note">Sample selections are demo values.</span>
                </div>
                <div className="physical-assessment-area-grid">
                    {physicalInspectionAreas.map((area) => {
                        const assessment = physicalAssessments[area.id];
                        const defects = defectCount(assessment.condition, assessment.defects);
                        const condition = assessment.status === "assessed" && assessment.condition
                            ? assessment.condition
                            : "Not assessed";
                        return (
                            <article className="physical-assessment-area-card" key={area.id}>
                                <div className="physical-assessment-area-heading">
                                    <div>
                                        <h3>{area.title}</h3>
                                        {area.bodyIdentifier && <span>{area.bodyIdentifier}</span>}
                                    </div>
                                    {assessment.isDemoSample && (
                                        <span className="physical-assessment-demo-sample">Demo sample</span>
                                    )}
                                </div>
                                <div className="physical-assessment-thumbnail" role="img" aria-label={`${area.imageLabel} illustration placeholder`}>
                                    <Camera size={20} aria-hidden="true" />
                                    <span>{area.bodyIdentifier || area.title}</span>
                                </div>
                                <div className="physical-assessment-area-status">
                                    <span>Condition</span>
                                    <strong className={`physical-assessment-condition ${conditionClass(assessment.condition, assessment.status)}`}>
                                        {condition}
                                    </strong>
                                </div>
                                <div className="physical-assessment-defect-count">
                                    <span>Defects</span>
                                    <strong>
                                        {assessment.status === "not_assessed"
                                            ? "Not assessed"
                                            : defects > 0
                                                ? `${defects} recorded`
                                                : "None recorded"}
                                    </strong>
                                </div>
                                {assessment.photoRefs.length > 0 && (
                                    <span className="physical-assessment-photo-count">
                                        {assessment.photoRefs.length} demo photo placeholder{assessment.photoRefs.length === 1 ? "" : "s"}
                                    </span>
                                )}
                                <button
                                    className="button button-secondary physical-assessment-inspect"
                                    type="button"
                                    onClick={() => openArea(area.id)}
                                    aria-label={`Inspect ${area.title}${area.bodyIdentifier ? `, ${area.bodyIdentifier}` : ""}`}
                                >
                                    Inspect
                                </button>
                            </article>
                        );
                    })}
                </div>
            </section>

            <section className="physical-assessment-general" aria-labelledby="general-observations-title">
                <div className="physical-assessment-section-heading">
                    <div>
                        <h2 id="general-observations-title">General Observations</h2>
                        <p>Record overall cosmetic or structural observations separately from area notes.</p>
                    </div>
                    <span className="physical-assessment-sample-note">Demo data · held in memory</span>
                </div>
                <label className="physical-assessment-notes-label" htmlFor="general-observations">
                    Overall observations
                </label>
                <textarea
                    className="physical-assessment-notes"
                    id="general-observations"
                    value={generalObservations}
                    onChange={(event) => setGeneralObservations(event.target.value)}
                    placeholder="Overall body condition, previous repairs, visible liquid damage, structural damage, or other observations."
                    rows={3}
                />
            </section>

            <section className="physical-assessment-summary" aria-labelledby="assessment-summary-title">
                <div className="physical-assessment-section-heading">
                    <div>
                        <h2 id="assessment-summary-title">Inspection Progress Summary</h2>
                    </div>
                    <span className="physical-assessment-sample-note">Calculated from current assessments</span>
                </div>
                <dl className="physical-assessment-summary-grid">
                    <div><dt>Inspection Areas</dt><dd>{physicalInspectionAreas.length}</dd></div>
                    <div><dt>Assessed</dt><dd>{assessedCount}</dd></div>
                    <div><dt>Not Assessed</dt><dd>{notAssessedCount}</dd></div>
                    <div><dt>Defects Recorded</dt><dd>{defectsRecorded}</dd></div>
                </dl>
            </section>

            <footer className="physical-assessment-actions">
                <Link className="button button-secondary" to="/device-identification">BACK</Link>
                <div>
                    {!assessmentComplete && (
                        <span className="physical-assessment-completion-hint">
                            Assess each applicable area to continue.
                        </span>
                    )}
                    <button
                        className="button button-primary"
                        type="button"
                        disabled={!assessmentComplete}
                        onClick={() => navigate("/hardware-diagnostics")}
                    >
                        CONTINUE TO HARDWARE DIAGNOSTICS
                    </button>
                </div>
            </footer>

            <Dialog open={activeAreaId !== null} onOpenChange={closeEditor}>
                <DialogContent className="physical-assessment-dialog">
                    {activeArea && (
                        <>
                            <DialogHeader>
                                <DialogTitle>
                                    {activeArea.title}
                                    {activeArea.bodyIdentifier ? ` — ${activeArea.bodyIdentifier}` : ""}
                                </DialogTitle>
                                <DialogDescription>
                                    Demo assessment data only. Record visible physical condition; do not perform functional tests here.
                                </DialogDescription>
                            </DialogHeader>
                            <div className="physical-assessment-dialog-body">
                                <section className="physical-assessment-checklist">
                                    <h3>Visual inspection points</h3>
                                    <ul>
                                        {activeArea.inspectionPoints.map((point) => <li key={point}>{point}</li>)}
                                    </ul>
                                    {activeArea.guidance && <p>{activeArea.guidance}</p>}
                                </section>

                                <fieldset className="physical-assessment-condition-group">
                                    <legend>Condition</legend>
                                    <div className="physical-assessment-condition-options">
                                        {physicalConditionOptions.map((condition) => (
                                            <label
                                                className={`physical-assessment-condition-option${draftCondition === condition ? " is-selected" : ""}`}
                                                key={condition}
                                            >
                                                <input
                                                    type="radio"
                                                    name="physical-condition"
                                                    value={condition}
                                                    checked={draftCondition === condition}
                                                    onChange={() => setDraftCondition(condition)}
                                                />
                                                <span>{condition}</span>
                                            </label>
                                        ))}
                                    </div>
                                </fieldset>

                                <section className="physical-assessment-defect-editor">
                                    <div className="physical-assessment-editor-heading">
                                        <h3>Defect details</h3>
                                        <button className="physical-assessment-add-button" type="button" onClick={() => setDraftDefects((current) => [...current, ""])}>
                                            <Plus size={14} aria-hidden="true" />
                                            Add defect
                                        </button>
                                    </div>
                                    {draftDefects.length === 0 ? (
                                        <p className="physical-assessment-empty-note">No defects entered.</p>
                                    ) : (
                                        <div className="physical-assessment-defect-list">
                                            {draftDefects.map((defect, index) => (
                                                <div className="physical-assessment-defect-row" key={`defect-${index}`}>
                                                    <input
                                                        className="physical-assessment-input"
                                                        type="text"
                                                        value={defect}
                                                        onChange={(event) => setDraftDefects((current) => current.map((item, itemIndex) => itemIndex === index ? event.target.value : item))}
                                                        aria-label={`Defect description ${index + 1}`}
                                                        placeholder="Describe a visible defect"
                                                    />
                                                    <button
                                                        className="physical-assessment-remove-button"
                                                        type="button"
                                                        onClick={() => setDraftDefects((current) => current.filter((_, itemIndex) => itemIndex !== index))}
                                                        aria-label={`Remove defect ${index + 1}`}
                                                    >
                                                        <Trash2 size={15} aria-hidden="true" />
                                                    </button>
                                                </div>
                                            ))}
                                        </div>
                                    )}
                                </section>

                                <label className="physical-assessment-field">
                                    <span>Technician remarks</span>
                                    <textarea
                                        className="physical-assessment-notes"
                                        value={draftRemarks}
                                        onChange={(event) => setDraftRemarks(event.target.value)}
                                        rows={3}
                                        placeholder="Additional observations for this area."
                                    />
                                </label>

                                <section className="physical-assessment-photo-area" aria-label="Optional photo attachments">
                                    <div>
                                        <Camera size={18} aria-hidden="true" />
                                        <div>
                                            <strong>Photographs (optional)</strong>
                                            <span>Placeholders only; no files are uploaded or saved.</span>
                                        </div>
                                    </div>
                                    <button className="button button-secondary" type="button" onClick={addDemoPhoto}>
                                        <Plus size={14} aria-hidden="true" />
                                        Add demo photo placeholder
                                    </button>
                                    {draftPhotos.length > 0 && (
                                        <ul className="physical-assessment-photo-list">
                                            {draftPhotos.map((photo, index) => (
                                                <li key={`${photo}-${index}`}>{photo}</li>
                                            ))}
                                        </ul>
                                    )}
                                </section>

                                <div className="physical-assessment-dialog-actions">
                                    <button className="button button-secondary" type="button" onClick={() => setActiveAreaId(null)}>
                                        Cancel
                                    </button>
                                    <button
                                        className="button button-primary"
                                        type="button"
                                        disabled={!draftCondition}
                                        onClick={saveAssessment}
                                    >
                                        Save Assessment
                                    </button>
                                </div>
                            </div>
                        </>
                    )}
                </DialogContent>
            </Dialog>
        </main>
    );
}
