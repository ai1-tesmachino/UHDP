import { useEffect, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { PageHeader } from "../components/shared/PageHeader";
import { useDemoInspection } from "../demo/DemoInspectionContext";
import { demoDevice } from "../demo/demoDevice";
import {
    isPhysicalAssessmentComplete,
    physicalConditionNeedsRemarks,
    physicalInspectionAreas,
    physicalPortConditionOptions,
    physicalPortTypes,
    type PhysicalAreaAssessment,
    type PhysicalCondition,
    type PhysicalInspectionArea,
    type PhysicalPortAssessment,
} from "../demo/physicalAssessment";
import { notifications } from "../lib/notifications";
import "./physical-assessment.css";

const assessmentGroups: PhysicalInspectionArea["group"][] = [
    "External Body",
    "Input Devices",
    "Display & Camera",
    "Other Components",
];

function formatInspectionTimestamp(timestamp: string | null) {
    if (!timestamp) return "Starting inspection…";
    const date = new Date(timestamp);
    if (Number.isNaN(date.getTime())) return "Unavailable";

    const dateLabel = new Intl.DateTimeFormat("en-GB", {
        day: "2-digit",
        month: "short",
        year: "numeric",
    }).format(date);
    const timeLabel = new Intl.DateTimeFormat("en-US", {
        hour: "numeric",
        minute: "2-digit",
    }).format(date);
    return `${dateLabel}, ${timeLabel}`;
}

function allSelectedConditions(assessment: PhysicalAreaAssessment) {
    return [
        ...assessment.conditions,
        ...assessment.ports.flatMap((port) => port.conditions),
    ];
}

function hasDefect(conditions: PhysicalCondition[]) {
    return conditions.some((condition) => !["Good", "Not applicable", "Unable to verify"].includes(condition));
}

function getAreaStatus(assessment: PhysicalAreaAssessment) {
    if (assessment.status === "skipped") {
        return { label: "Skipped", tone: "is-skipped" };
    }
    if (assessment.status !== "assessed") {
        return { label: "Pending", tone: "is-pending" };
    }
    return hasDefect(allSelectedConditions(assessment))
        ? { label: "Needs attention", tone: "is-attention" }
        : { label: "Assessed", tone: "is-assessed" };
}

function getActiveInvalidField(
    technicianName: string,
    area: PhysicalInspectionArea,
    assessment: PhysicalAreaAssessment,
) {
    if (!technicianName.trim()) return "technician-name";
    if (assessment.status === "skipped") return null;

    if (area.id === "ports-connectors") {
        if (assessment.ports.length === 0) return "new-port-type";
        const incompletePort = assessment.ports.find((port) => port.conditions.length === 0);
        if (incompletePort) return `port-condition-${incompletePort.id}-0`;
    } else if (assessment.conditions.length === 0) {
        return `condition-${area.id}-0`;
    }

    if (
        allSelectedConditions(assessment).some((condition) => physicalConditionNeedsRemarks.has(condition))
        && !assessment.remarks.trim()
    ) {
        return `remarks-${area.id}`;
    }
    return null;
}

function toggleCondition(
    conditions: PhysicalCondition[],
    condition: PhysicalCondition,
    checked: boolean,
) {
    return checked
        ? [...conditions, condition]
        : conditions.filter((current) => current !== condition);
}

function newPortId() {
    return globalThis.crypto?.randomUUID?.() ?? `port-${Date.now()}-${Math.random()}`;
}

export default function PhysicalAssessment() {
    const navigate = useNavigate();
    const {
        technicianName,
        setTechnicianName,
        physicalAssessments,
        updatePhysicalAssessment,
        selectedPhysicalAreaId,
        setSelectedPhysicalAreaId,
        physicalInspectionStartedAt,
        startPhysicalInspection,
    } = useDemoInspection();
    const [showValidation, setShowValidation] = useState(false);
    const [newPortType, setNewPortType] = useState<(typeof physicalPortTypes)[number]>(physicalPortTypes[0]);

    useEffect(() => {
        startPhysicalInspection();
    }, [startPhysicalInspection]);

    const activeArea = physicalInspectionAreas.find(({ id }) => id === selectedPhysicalAreaId)
        ?? physicalInspectionAreas[0];
    const activeAssessment = physicalAssessments[activeArea.id];
    const activeIndex = physicalInspectionAreas.findIndex(({ id }) => id === activeArea.id);
    const isLastArea = activeIndex === physicalInspectionAreas.length - 1;
    const isPortsArea = activeArea.id === "ports-connectors";
    const isSkipped = activeAssessment.status === "skipped";
    const selectedConditions = allSelectedConditions(activeAssessment);
    const needsRemarks = selectedConditions.some((condition) => physicalConditionNeedsRemarks.has(condition));
    const conditionError = showValidation
        && !isSkipped
        && !isPortsArea
        && activeAssessment.conditions.length === 0;
    const portListError = showValidation && !isSkipped && isPortsArea && activeAssessment.ports.length === 0;
    const remarksError = showValidation
        && !isSkipped
        && needsRemarks
        && !activeAssessment.remarks.trim();
    const technicianNameError = showValidation && !technicianName.trim();
    const assessedCount = physicalInspectionAreas.filter(
        ({ id }) => physicalAssessments[id].status === "assessed",
    ).length;
    const skippedCount = physicalInspectionAreas.filter(
        ({ id }) => physicalAssessments[id].status === "skipped",
    ).length;
    const pendingCount = physicalInspectionAreas.length - assessedCount - skippedCount;
    const assessmentComplete = isPhysicalAssessmentComplete(physicalAssessments)
        && Boolean(technicianName.trim());

    function focusInvalidField(fieldId: string) {
        window.requestAnimationFrame(() => {
            const field = document.getElementById(fieldId);
            field?.focus();
            field?.scrollIntoView({ behavior: "smooth", block: "center" });
        });
    }

    function selectArea(areaId: typeof selectedPhysicalAreaId) {
        setSelectedPhysicalAreaId(areaId);
        setShowValidation(false);
    }

    function updateActiveAssessment(updates: Partial<PhysicalAreaAssessment>) {
        if (isSkipped) return;
        updatePhysicalAssessment(activeArea.id, {
            ...activeAssessment,
            ...updates,
            status: "pending",
            isSaved: false,
        });
    }

    function updatePort(portId: string, updates: Partial<PhysicalPortAssessment>) {
        updateActiveAssessment({
            ports: activeAssessment.ports.map((port) => port.id === portId
                ? { ...port, ...updates }
                : port),
        });
    }

    function addPort() {
        updateActiveAssessment({
            ports: [
                ...activeAssessment.ports,
                {
                    id: newPortId(),
                    type: newPortType,
                    conditions: [],
                },
            ],
        });
    }

    function removePort(portId: string) {
        updateActiveAssessment({
            ports: activeAssessment.ports.filter((port) => port.id !== portId),
        });
    }

    function togglePortCondition(portId: string, condition: PhysicalCondition, checked: boolean) {
        const port = activeAssessment.ports.find((item) => item.id === portId);
        if (!port) return;
        updatePort(portId, {
            conditions: toggleCondition(port.conditions, condition, checked),
        });
    }

    function saveActiveAssessment() {
        setShowValidation(true);
        const invalidField = getActiveInvalidField(technicianName, activeArea, activeAssessment);
        if (invalidField) {
            focusInvalidField(invalidField);
            return false;
        }

        if (!isSkipped) {
            updatePhysicalAssessment(activeArea.id, {
                ...activeAssessment,
                status: "assessed",
                isSaved: true,
            });
        }
        return true;
    }

    function saveAndNext() {
        if (!saveActiveAssessment()) return;
        if (isLastArea) {
            notifications.success("Physical assessment saved.");
            return;
        }
        selectArea(physicalInspectionAreas[activeIndex + 1].id);
    }

    function goToPrevious() {
        if (activeIndex > 0) {
            selectArea(physicalInspectionAreas[activeIndex - 1].id);
        }
    }

    function continueToDiagnostics() {
        if (!assessmentComplete) return;
        navigate("/hardware-diagnostics");
    }

    function toggleSkip(checked: boolean) {
        updatePhysicalAssessment(activeArea.id, {
            ...activeAssessment,
            status: checked
                ? "skipped"
                : activeAssessment.isSaved
                    ? "assessed"
                    : "pending",
        });
        setShowValidation(false);
    }

    const messageTone = technicianNameError
        ? "is-error"
        : assessmentComplete
            ? "is-success"
            : "is-info";
    const messageText = technicianNameError
        ? "Please provide the technician name before saving this assessment."
        : pendingCount > 0
            ? `${pendingCount} component${pendingCount === 1 ? " is" : "s are"} still pending. Assess or explicitly skip each item to enable Continue.${technicianName.trim() ? "" : " A technician name is also required."}`
            : technicianName.trim()
                ? "All physical assessment items have been addressed. You can continue to the next workflow stage."
                : "All items are addressed. Enter the technician name to enable Continue.";

    return (
        <main className="physical-assessment page-flow min-w-0 gap-4" aria-labelledby="physical-assessment-title">
            <div className="space-y-3">
                <PageHeader
                    title="Physical Assessment"
                    titleId="physical-assessment-title"
                    description="Inspect the physical condition of the device."
                    eyebrow="DEVICE INSPECTION"
                    actions={<Link className="button button-secondary" to="/device-identification">Back</Link>}
                />

                <div className="grid min-w-0 grid-cols-1 gap-3 border-b border-border pb-4 sm:grid-cols-2 lg:grid-cols-3">
                    <div className="min-w-0 text-sm">
                        <span className="text-muted-foreground">Device</span>
                        <p className="mt-1 font-semibold text-foreground">
                            {demoDevice.manufacturer} {demoDevice.model}
                        </p>
                        <p className="text-xs text-muted-foreground">
                            Serial number: {demoDevice.systemSerialNumber || "Not available"}
                        </p>
                    </div>
                    <div className="min-w-0">
                        <label className="mb-1 block text-xs font-semibold text-foreground" htmlFor="technician-name">
                            Technician name <span aria-hidden="true">*</span>
                        </label>
                        <input
                            id="technician-name"
                            className="physical-assessment-input w-full"
                            type="text"
                            name="technicianName"
                            autoComplete="name"
                            value={technicianName}
                            onChange={(event) => setTechnicianName(event.target.value)}
                            aria-invalid={technicianNameError}
                            aria-describedby={technicianNameError ? "technician-name-error" : undefined}
                        />
                        {technicianNameError && (
                            <span className="physical-assessment-error mt-1 block" id="technician-name-error" role="alert">
                                Technician name is required.
                            </span>
                        )}
                    </div>
                    <div className="min-w-0 text-sm">
                        <span className="text-muted-foreground">Inspection started</span>
                        <p className="mt-1 font-semibold tabular-nums text-foreground">
                            {formatInspectionTimestamp(physicalInspectionStartedAt)}
                        </p>
                    </div>
                </div>
            </div>

            <div className="physical-assessment-workspace flex min-w-0 flex-col gap-4 md:flex-row md:gap-0">
                <aside className="physical-assessment-sidebar min-w-0 md:sticky md:top-4 md:max-h-[calc(100vh-2rem)] md:w-[270px] md:shrink-0 md:overflow-y-auto md:self-start md:border-r md:border-border md:pr-4">
                    <div className="hidden md:block">
                        <h2 className="mb-3 text-xs font-bold uppercase tracking-wide text-muted-foreground">Components</h2>
                        <nav aria-label="Physical assessment components" className="space-y-4">
                            {assessmentGroups.map((group) => (
                                <section key={group}>
                                    <h3 className="mb-1 text-[11px] font-bold uppercase tracking-wide text-muted-foreground">
                                        {group}
                                    </h3>
                                    <ul className="space-y-1">
                                        {physicalInspectionAreas
                                            .filter((area) => area.group === group)
                                            .map((area) => {
                                                const status = getAreaStatus(physicalAssessments[area.id]);
                                                const isActive = area.id === activeArea.id;
                                                return (
                                                    <li key={area.id}>
                                                        <button
                                                            className={`physical-assessment-nav-item${isActive ? " is-active" : ""}`}
                                                            type="button"
                                                            onClick={() => selectArea(area.id)}
                                                            aria-current={isActive ? "step" : undefined}
                                                        >
                                                            <span className={`physical-assessment-status-dot ${status.tone}`} aria-hidden="true" />
                                                            <span className="min-w-0 flex-1 text-left">{area.title}</span>
                                                            <span className={`physical-assessment-nav-status ${status.tone}`}>
                                                                {status.label === "Needs attention" ? "Attention" : status.label}
                                                            </span>
                                                        </button>
                                                    </li>
                                                );
                                            })}
                                    </ul>
                                </section>
                            ))}
                        </nav>
                    </div>

                    <label className="block text-xs font-semibold text-foreground md:hidden" htmlFor="physical-assessment-component">
                        Select component
                        <select
                            id="physical-assessment-component"
                            className="physical-assessment-input mt-1 w-full"
                            value={activeArea.id}
                            onChange={(event) => {
                                const area = physicalInspectionAreas.find(({ id }) => id === event.target.value);
                                if (area) selectArea(area.id);
                            }}
                        >
                            {assessmentGroups.map((group) => (
                                <optgroup label={group} key={group}>
                                    {physicalInspectionAreas
                                        .filter((area) => area.group === group)
                                        .map((area) => {
                                            const status = getAreaStatus(physicalAssessments[area.id]);
                                            return (
                                                <option value={area.id} key={area.id}>
                                                    {area.title} — {status.label}
                                                </option>
                                            );
                                        })}
                                </optgroup>
                            ))}
                        </select>
                    </label>
                </aside>

                <section className="min-w-0 flex-1 md:pl-5" aria-labelledby={`active-title-${activeArea.id}`}>
                    <div className="physical-assessment-form-panel min-w-0 rounded-md border border-border bg-card p-4 sm:p-5">
                        <div className="mb-5 flex flex-wrap items-start justify-between gap-3 border-b border-border pb-4">
                            <div className="min-w-0">
                                <h2 className="text-lg font-bold text-foreground" id={`active-title-${activeArea.id}`}>
                                    {activeArea.title}
                                </h2>
                                <p className="mt-1 max-w-3xl text-sm leading-6 text-muted-foreground">
                                    {activeArea.guidance}
                                </p>
                            </div>
                            <span className={`physical-assessment-active-status ${getAreaStatus(activeAssessment).tone}`}>
                                {getAreaStatus(activeAssessment).label}
                            </span>
                        </div>

                        {isPortsArea ? (
                            <section aria-labelledby="ports-assessment-title">
                                <h3 className="mb-3 text-sm font-bold text-foreground" id="ports-assessment-title">
                                    Port assessments
                                </h3>
                                <div className="flex flex-col gap-2 sm:flex-row sm:items-end">
                                    <label className="block flex-1 text-xs font-semibold text-foreground" htmlFor="new-port-type">
                                        Port type
                                        <select
                                            id="new-port-type"
                                            className="physical-assessment-input mt-1 w-full"
                                            value={newPortType}
                                            disabled={isSkipped}
                                            onChange={(event) => setNewPortType(event.target.value as (typeof physicalPortTypes)[number])}
                                        >
                                            {physicalPortTypes.map((portType) => (
                                                <option value={portType} key={portType}>{portType}</option>
                                            ))}
                                        </select>
                                    </label>
                                    <button
                                        className="button button-secondary"
                                        type="button"
                                        onClick={addPort}
                                        disabled={isSkipped}
                                    >
                                        Add Port
                                    </button>
                                </div>
                                {portListError && (
                                    <p className="physical-assessment-error mt-2" role="alert">
                                        Add at least one port and select its physical condition, or skip this item.
                                    </p>
                                )}

                                {activeAssessment.ports.length > 0 && (
                                    <ul className="mt-4 space-y-3">
                                        {activeAssessment.ports.map((port, index) => {
                                            const portConditionError = showValidation
                                                && !isSkipped
                                                && port.conditions.length === 0;
                                            return (
                                                <li className="physical-assessment-port-row rounded-md border border-border p-3" key={port.id}>
                                                    <div className="mb-3 flex flex-wrap items-center justify-between gap-2">
                                                        <label className="block min-w-0 flex-1 text-xs font-semibold text-foreground" htmlFor={`port-type-${port.id}`}>
                                                            Port {index + 1}
                                                            <select
                                                                id={`port-type-${port.id}`}
                                                                className="physical-assessment-input mt-1 w-full"
                                                                value={port.type}
                                                                disabled={isSkipped}
                                                                onChange={(event) => updatePort(port.id, {
                                                                    type: event.target.value,
                                                                })}
                                                            >
                                                                {physicalPortTypes.map((portType) => (
                                                                    <option value={portType} key={portType}>{portType}</option>
                                                                ))}
                                                            </select>
                                                        </label>
                                                        <button
                                                            className="button button-secondary"
                                                            type="button"
                                                            onClick={() => removePort(port.id)}
                                                            disabled={isSkipped}
                                                            aria-label={`Remove port ${index + 1}`}
                                                        >
                                                            Remove
                                                        </button>
                                                    </div>
                                                    <fieldset
                                                        className="min-w-0"
                                                        disabled={isSkipped}
                                                        aria-describedby={portConditionError ? `port-condition-error-${port.id}` : undefined}
                                                    >
                                                        <legend className="mb-2 text-xs font-semibold text-foreground">
                                                            Physical condition <span aria-hidden="true">*</span>
                                                        </legend>
                                                        <div className="grid grid-cols-1 gap-2 sm:grid-cols-2 xl:grid-cols-3">
                                                            {physicalPortConditionOptions.map((condition, optionIndex) => {
                                                                const isSelected = port.conditions.includes(condition);
                                                                return (
                                                                    <label
                                                                        className={`physical-assessment-option${isSelected ? " is-selected" : ""}`}
                                                                        key={condition}
                                                                    >
                                                                        <input
                                                                            id={`port-condition-${port.id}-${optionIndex}`}
                                                                            type="checkbox"
                                                                            checked={isSelected}
                                                                            disabled={isSkipped}
                                                                            aria-invalid={portConditionError}
                                                                            onChange={(event) => togglePortCondition(port.id, condition, event.target.checked)}
                                                                        />
                                                                        <span>{condition}</span>
                                                                    </label>
                                                                );
                                                            })}
                                                        </div>
                                                    </fieldset>
                                                    {portConditionError && (
                                                        <p className="physical-assessment-error mt-2" id={`port-condition-error-${port.id}`} role="alert">
                                                            Select at least one physical condition for this port.
                                                        </p>
                                                    )}
                                                </li>
                                            );
                                        })}
                                    </ul>
                                )}
                            </section>
                        ) : (
                            <>
                                <fieldset
                                    className="min-w-0"
                                    disabled={isSkipped}
                                    aria-describedby={conditionError ? `condition-error-${activeArea.id}` : undefined}
                                >
                                    <legend className="mb-3 text-sm font-bold text-foreground">
                                        Physical Condition <span aria-hidden="true">*</span>
                                        <span className="ml-2 font-normal text-muted-foreground">Select all that apply</span>
                                    </legend>
                                    <div className="grid grid-cols-1 gap-2 sm:grid-cols-2 xl:grid-cols-3">
                                        {activeArea.options.map((condition, index) => {
                                            const isSelected = activeAssessment.conditions.includes(condition);
                                            return (
                                                <label
                                                    className={`physical-assessment-option${isSelected ? " is-selected" : ""}`}
                                                    key={condition}
                                                >
                                                    <input
                                                        id={`condition-${activeArea.id}-${index}`}
                                                        type="checkbox"
                                                        checked={isSelected}
                                                        onChange={(event) => updateActiveAssessment({
                                                            conditions: toggleCondition(
                                                                activeAssessment.conditions,
                                                                condition,
                                                                event.target.checked,
                                                            ),
                                                        })}
                                                        aria-invalid={conditionError}
                                                    />
                                                    <span>{condition}</span>
                                                </label>
                                            );
                                        })}
                                    </div>
                                </fieldset>
                                {conditionError && (
                                    <p className="physical-assessment-error mt-2" id={`condition-error-${activeArea.id}`} role="alert">
                                        Please select at least one physical condition.
                                    </p>
                                )}
                            </>
                        )}

                        <label className="mt-5 block" htmlFor={`remarks-${activeArea.id}`}>
                            <span className="mb-2 block text-sm font-bold text-foreground">
                                Observations / Remarks
                                {needsRemarks ? <span aria-hidden="true"> *</span> : <span className="font-normal text-muted-foreground"> (optional)</span>}
                            </span>
                            <textarea
                                id={`remarks-${activeArea.id}`}
                                className="physical-assessment-input min-h-24 w-full resize-y"
                                value={activeAssessment.remarks}
                                rows={3}
                                disabled={isSkipped}
                                placeholder="Enter any visible damage or additional observations..."
                                aria-invalid={remarksError}
                                aria-describedby={remarksError ? `remarks-error-${activeArea.id}` : undefined}
                                onChange={(event) => updateActiveAssessment({ remarks: event.target.value })}
                            />
                            {remarksError && (
                                <span className="physical-assessment-error mt-1 block" id={`remarks-error-${activeArea.id}`} role="alert">
                                    Please enter an observation for this defect.
                                </span>
                            )}
                        </label>

                        <div className="mt-5 border-t border-border pt-4">
                            <label className="inline-flex min-h-8 cursor-pointer items-center gap-2 text-sm font-medium text-foreground">
                                <input
                                    type="checkbox"
                                    checked={isSkipped}
                                    onChange={(event) => toggleSkip(event.target.checked)}
                                    className="size-4 accent-primary"
                                />
                                <span>Skip this assessment</span>
                            </label>
                            {isSkipped && (
                                <p className="mt-2 text-xs text-muted-foreground">
                                    This component is explicitly skipped and is not counted as assessed.
                                </p>
                            )}
                        </div>
                    </div>

                    <div className="mt-4 border-t border-border pt-3">
                        <div className="flex flex-wrap items-center justify-between gap-3">
                            <p className="m-0 text-xs font-medium text-muted-foreground" aria-live="polite">
                                <span>Assessed: <strong className="text-foreground">{assessedCount}</strong></span>
                                <span className="mx-2" aria-hidden="true">|</span>
                                <span>Skipped: <strong className="text-foreground">{skippedCount}</strong></span>
                                <span className="mx-2" aria-hidden="true">|</span>
                                <span>Pending: <strong className="text-foreground">{pendingCount}</strong></span>
                            </p>
                            <div className="physical-assessment-action-buttons flex flex-wrap items-center gap-2">
                                <button
                                    className="button button-secondary"
                                    type="button"
                                    onClick={goToPrevious}
                                    disabled={activeIndex === 0}
                                >
                                    Previous
                                </button>
                                <button className="button button-secondary" type="button" onClick={saveAndNext}>
                                    {isLastArea ? "Save Assessment" : "Save & Next"}
                                </button>
                            </div>
                        </div>
                        <div className="physical-assessment-continue-row mt-4 flex flex-col gap-3 border-t border-border pt-4 sm:flex-row sm:items-center">
                            <div
                                className={`physical-assessment-message rounded-md border p-3 text-sm ${messageTone}`}
                                role={technicianNameError ? "alert" : "status"}
                            >
                                {messageText}
                            </div>
                            <button
                                className="button button-primary physical-assessment-continue-button"
                                type="button"
                                onClick={continueToDiagnostics}
                                disabled={!assessmentComplete}
                                aria-describedby="physical-assessment-continue-hint"
                            >
                                Continue
                            </button>
                        </div>
                        <p className="mt-2 text-right text-xs text-muted-foreground" id="physical-assessment-continue-hint">
                            Continue is available after every item is assessed or skipped and a technician name is provided.
                        </p>
                    </div>
                </section>
            </div>
        </main>
    );
}
