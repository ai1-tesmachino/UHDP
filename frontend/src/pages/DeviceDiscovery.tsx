import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { useNavigate, useSearchParams } from "react-router-dom";

import { getDevices } from "../api/devices";
import { getStationInventory, mergeDiscoveredInventory } from "../api/inventory";
import {
    DiagnosticSessionIntake,
    updateSessionIntake,
} from "../api/execution";
import { getStationProfile } from "../station";
import { useQcSession } from "../session/SessionContext";
import { Device } from "../types/device";
import FieldLabel from "../components/FieldLabel";
import AssetResolutionPicker from "../components/AssetResolutionPicker";
import type { AssetResolutionSelection } from "../api/execution";
import { SaveIndicator } from "../components/shared/SaveIndicator";

const INTAKE_DRAFT_KEY = "uhdp.qc_intake_draft";

interface IntakeDraft {
    assetTag: string;
    technician: string;
    customerReference: string;
    workflowType: string;
    selectedDeviceId: string;
    assetResolution: AssetResolutionSelection | null;
}

function readIntakeDraft(): Partial<IntakeDraft> {
    try {
        const value: unknown = JSON.parse(localStorage.getItem(INTAKE_DRAFT_KEY) || "null");
        if (typeof value !== "object" || value === null || Array.isArray(value)) return {};
        const draft = value as Record<string, unknown>;
        const resolution = draft.assetResolution;
        const assetResolution =
            typeof resolution === "object" && resolution !== null &&
            "mode" in resolution && resolution.mode === "existing" &&
            "assetId" in resolution && typeof resolution.assetId === "string"
                ? { mode: "existing" as const, assetId: resolution.assetId }
                : typeof resolution === "object" && resolution !== null &&
                    "mode" in resolution && resolution.mode === "new"
                  ? { mode: "new" as const }
                  : typeof resolution === "object" && resolution !== null &&
                    "mode" in resolution && resolution.mode === "unresolved"
                    ? { mode: "unresolved" as const }
                    : null;
        return {
            assetTag: typeof draft.assetTag === "string" ? draft.assetTag : undefined,
            technician: typeof draft.technician === "string" ? draft.technician : undefined,
            customerReference: typeof draft.customerReference === "string"
                ? draft.customerReference
                : undefined,
            workflowType: typeof draft.workflowType === "string" ? draft.workflowType : undefined,
            selectedDeviceId: typeof draft.selectedDeviceId === "string"
                ? draft.selectedDeviceId
                : undefined,
            assetResolution,
        };
    } catch {
        return {};
    }
}

function formatValue(value: unknown): string {
    if (value === null || value === undefined || value === "") {
        return value === "" ? '""' : "null";
    }

    if (typeof value === "number") {
        return value.toLocaleString();
    }

    if (typeof value === "boolean") {
        return value ? "Yes" : "No";
    }

    return typeof value === "object"
        ? JSON.stringify(value, null, 2)
        : String(value);
}

export default function DeviceDiscovery() {
    const navigate = useNavigate();
    const [params] = useSearchParams();
    const {
        activeSession,
        activeSessionId,
        startSession,
        loading: sessionLoading,
    } = useQcSession();
    const isNewIntake = params.get("new") === "1";
    const sessionId = params.get("sessionId") || (isNewIntake ? "" : activeSessionId);
    const initialDraft = useMemo(readIntakeDraft, []);
    const [devices, setDevices] = useState<Device[]>([]);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState("");
    const [assetTag, setAssetTag] = useState(initialDraft.assetTag || "");
    const [technician, setTechnician] = useState(
        initialDraft.technician || getStationProfile()?.technician || "",
    );
    const [customerReference, setCustomerReference] = useState(initialDraft.customerReference || "");
    const [workflowType, setWorkflowType] = useState(initialDraft.workflowType || "service_center");
    const [assetResolution, setAssetResolution] = useState<AssetResolutionSelection | null>(
        initialDraft.assetResolution || null,
    );
    const [selectedDeviceId, setSelectedDeviceId] = useState(initialDraft.selectedDeviceId || "");
    const [savingIntake, setSavingIntake] = useState(false);
    const restoredSessionId = useRef("");

    useEffect(() => {
        const intake = activeSession?.intake_record;
        if (
            isNewIntake ||
            !intake ||
            activeSession.session_id !== sessionId ||
            restoredSessionId.current === sessionId
        ) return;
        restoredSessionId.current = sessionId;
        setAssetTag(typeof intake.asset_tag === "string" ? intake.asset_tag : "");
        setTechnician(
            typeof intake.technician === "string"
                ? intake.technician
                : getStationProfile()?.technician || "",
        );
        setCustomerReference(typeof intake.customer_reference === "string" ? intake.customer_reference : "");
        setWorkflowType(typeof intake.workflow_type === "string" ? intake.workflow_type : "service_center");
    }, [activeSession, isNewIntake, sessionId]);

    const loadDevices = useCallback(async () => {
        setLoading(true);
        setError("");

        try {
            const [discovered, stored] = await Promise.all([
                getDevices(),
                getStationInventory(),
            ]);
            setDevices(mergeDiscoveredInventory(discovered, stored).devices);
        } catch {
            setError("We couldn’t discover devices. Check that the UHDP backend is running, then try again.");
        } finally {
            setLoading(false);
        }
    }, []);

    useEffect(() => {
        void loadDevices();
    }, [loadDevices]);

    const systemDevices = useMemo(
        () => devices.filter((device) => device.device_type.toLowerCase() === "system"),
        [devices],
    );
    const loadedSession = Boolean(
        sessionId && activeSession?.session_id === sessionId,
    );
    const associatedDeviceId = loadedSession ? activeSession?.device_id || "" : "";
    useEffect(() => {
        if (loading || (sessionId && !loadedSession)) return;
        if (associatedDeviceId) {
            setSelectedDeviceId(associatedDeviceId);
            return;
        }
        if (systemDevices.some((device) => device.device_id === selectedDeviceId)) return;
        setSelectedDeviceId(systemDevices.length === 1 ? systemDevices[0].device_id : "");
    }, [associatedDeviceId, loadedSession, loading, selectedDeviceId, sessionId, systemDevices]);
    const selectedSystemDevice = systemDevices.find(
        (device) => device.device_id === selectedDeviceId,
    );

    useEffect(() => {
        if (sessionId) return;
        const draft: IntakeDraft = {
            assetTag,
            technician,
            customerReference,
            workflowType,
            selectedDeviceId,
            assetResolution,
        };
        localStorage.setItem(INTAKE_DRAFT_KEY, JSON.stringify(draft));
    }, [
        assetResolution,
        assetTag,
        customerReference,
        selectedDeviceId,
        sessionId,
        technician,
        workflowType,
    ]);

    const savedIntake = loadedSession ? activeSession?.intake_record || {} : {};
    const intakeMatchesSaved = loadedSession &&
        assetTag === String(savedIntake.asset_tag || "") &&
        technician === String(savedIntake.technician || "") &&
        customerReference === String(savedIntake.customer_reference || "") &&
        workflowType === String(savedIntake.workflow_type || "service_center") &&
        selectedDeviceId === associatedDeviceId;
    const physicalDrives = [
        ...new Map(
            devices.flatMap((device) => {
                const properties = device.properties || {};
                if (properties.physical_drive === true || properties.inventory_kind === "physical_drive") {
                    const key = String(properties.device || device.device_id);
                    return [[key, { key, properties }] as const];
                }

                const nested = properties.physical_disks;
                if (!Array.isArray(nested)) {
                    return [];
                }
                return nested.flatMap((entry, index) => {
                    if (typeof entry !== "object" || entry === null || Array.isArray(entry)) {
                        return [];
                    }
                    const driveProperties = entry as Record<string, unknown>;
                    const observedPath = driveProperties.device;
                    const identity = observedPath || driveProperties.FriendlyName ||
                        driveProperties.Model || driveProperties.SerialNumber;
                    if (!identity) {
                        return [];
                    }
                    const key = String(observedPath || `${device.device_id}:legacy:${index}`);
                    return [[key, { key, properties: driveProperties }] as const];
                });
            })
        ).values(),
    ];

    async function continueToDiagnostics() {
        if (!selectedSystemDevice) {
            setError(
                systemDevices.length > 1
                    ? "Select the system device this QC session should inspect."
                    : "The backend did not identify a selectable system device.",
            );
            return;
        }
        if (sessionId && !loadedSession) {
            setError("Wait for the selected QC session identity to load before continuing.");
            return;
        }
        if (!sessionId && !assetResolution) {
            setError("Choose how this QC session will resolve its asset identity.");
            return;
        }
        if (savingIntake) return;
        setSavingIntake(true);
        setError("");
        const intake: DiagnosticSessionIntake = {
            asset_tag: assetTag,
            technician,
            station_id: getStationProfile()?.station_id || "",
            customer_reference: customerReference,
            workflow_type: workflowType,
        };
        let targetSessionId = sessionId;
        try {
            if (!targetSessionId) {
                if (!assetResolution) {
                    throw new Error("Choose how this QC session will resolve its asset identity.");
                }
                const created = await startSession(
                    assetResolution,
                    selectedSystemDevice.device_id,
                    intake,
                );
                targetSessionId = created.session_id;
                navigate(`/devices?sessionId=${encodeURIComponent(targetSessionId)}#intake`, { replace: true });
            }
            await updateSessionIntake(
                targetSessionId,
                selectedSystemDevice.device_id,
                { ...intake },
                devices.map((device) => ({ ...device })),
            );
            localStorage.removeItem(INTAKE_DRAFT_KEY);
        } catch (saveError) {
            setError(saveError instanceof Error ? saveError.message : "The device intake could not be saved.");
            return;
        } finally {
            setSavingIntake(false);
        }
        const query = new URLSearchParams({
            sessionId: targetSessionId,
            stage: "cosmetic",
        });
        navigate(`/qc?${query.toString()}`, {
            state: {
                device: selectedSystemDevice,
                intake,
            },
        });
    }

    return (
        <div className="page-flow">
            <div className="page-header">
                <div>
                    <span className="eyebrow">DEVICE INVENTORY</span>
                    <h1 className="page-title">Review detected hardware</h1>
                    <p className="page-description">
                        {sessionId ? `QC session ${sessionId}` : "New QC intake"}
                    </p>
                    <p className="page-description">
                        Review hardware detected on this machine before confirming intake.
                    </p>
                </div>
                <button
                    className="button button-secondary"
                    type="button"
                    onClick={() => void loadDevices()}
                    disabled={loading}
                >
                    <span aria-hidden="true">↻</span>
                    {loading ? "Scanning…" : "Refresh devices"}
                </button>
            </div>

            <div className="device-list-heading">
                <strong>System inventory <span className="required-field-mark" aria-label="required">*</span></strong>
                <span>{loading ? "Scanning system…" : `${devices.length} ${devices.length === 1 ? "entry" : "entries"}`}</span>
            </div>
            {!loading && systemDevices.length > 1 && (
                <p className="info-box" role="status">
                    Select the system device associated with this QC session. No device is preselected because multiple candidates were found.
                </p>
            )}

            {error && <div className="error-box">{error}</div>}

            {loading ? (
                <div className="device-table-wrapper">
                    <div className="device-table-loading" role="status">
                        Scanning and collecting hardware information…
                    </div>
                </div>
            ) : devices.length === 0 && !error ? (
                <div className="empty-panel">
                    <span className="empty-panel-icon" aria-hidden="true">⌕</span>
                    <h2>No devices found</h2>
                    <p>Refresh the scan or check that the backend can access this machine’s hardware.</p>
                    <button className="button button-primary" type="button" onClick={() => void loadDevices()}>
                        Scan again
                    </button>
                </div>
            ) : (
                <>
                <div className="hardware-entry-grid">
                    {devices.map((device) => {
                        const properties = Object.entries(device.properties || {});
                        return (
                            <article
                                className={`hardware-entry-card${device.device_type.toLowerCase() === "system" && selectedDeviceId === device.device_id ? " is-selected" : ""}`}
                                key={device.device_id}
                            >
                                <div className="hardware-entry-heading">
                                    <span className="device-type-pill">{device.device_type}</span>
                                    <span>{properties.length} reported properties</span>
                                </div>
                                <h2>{device.name || "Unnamed hardware"}</h2>
                                {device.device_type.toLowerCase() === "system" && (
                                    <label className="device-selection-control">
                                        <input
                                            type="radio"
                                            name="qc-system-device"
                                            value={device.device_id}
                                            checked={selectedDeviceId === device.device_id}
                                            disabled={Boolean(associatedDeviceId)}
                                            onChange={() => setSelectedDeviceId(device.device_id)}
                                        />
                                        {associatedDeviceId
                                            ? selectedDeviceId === device.device_id
                                                ? "Device associated with this session"
                                                : "Session device cannot be changed"
                                            : "Use this system for the QC session"}
                                    </label>
                                )}
                                {properties.length ? (
                                    <dl className="device-properties">
                                        {properties.map(([name, value]) => (
                                            <div className="device-property" key={name}>
                                                <dt>{name.replaceAll("_", " ")}</dt>
                                                <dd><code>{formatValue(value)}</code></dd>
                                            </div>
                                        ))}
                                    </dl>
                                ) : (
                                    <span className="device-property-empty">No additional properties were reported by the backend.</span>
                                )}
                                <code className="device-table-id">{device.device_id}</code>
                            </article>
                        );
                    })}
                </div>
                <section className="results-table-panel">
                    <div className="section-heading">
                        <div>
                            <span className="eyebrow">PHYSICAL DRIVE RECORDS</span>
                            <h2>Backend-reported storage devices</h2>
                        </div>
                        <span className="section-count">{physicalDrives.length} drives</span>
                    </div>
                    {physicalDrives.length ? (
                        <div className="hardware-entry-grid">
                            {physicalDrives.map((drive, index) => (
                                <article className="hardware-entry-card" key={`${drive.key}-${index}`}>
                                    <h2>
                                        {String(
                                            drive.properties.model ||
                                            drive.properties.FriendlyName ||
                                            drive.properties.Model ||
                                            drive.properties.device ||
                                            "Drive identity unavailable"
                                        )}
                                    </h2>
                                    <dl className="device-properties">
                                        {Object.entries(drive.properties).map(([name, value]) => (
                                            <div className="device-property" key={name}>
                                                <dt>{name.replaceAll("_", " ")}</dt>
                                                <dd><code>{formatValue(value)}</code></dd>
                                            </div>
                                        ))}
                                    </dl>
                                </article>
                            ))}
                        </div>
                    ) : (
                        <p className="empty-state">The current backend discovery response did not include physical drive identity records. No model or serial number is inferred from mounted volumes.</p>
                    )}
                </section>
                <div className="inventory-limit-note">
                    <strong>Memory-module detail availability</strong>
                    <span>System capacity and available memory are reported separately from per-module inventory. Some component details depend on firmware exposure and station permissions; unavailable details remain unverified.</span>
                </div>
                <div className="inventory-limit-note">
                    <strong>Storage-health detail availability</strong>
                    <span>Physical drives, partitions, and mounted filesystems are reported separately. Read-only SMART/NVMe data may be included when supported by the station; unavailable drive details remain unverified.</span>
                </div>
                </>
            )}

            {!loading && devices.length > 0 && (
                <section className="technician-record-panel" id="intake">
                    <div>
                        <span className="eyebrow">DEVICE INTAKE</span>
                        <h2>Technician and work order</h2>
                        <p>Scan or type the device asset tag / serial, then confirm the technician and work order.</p>
                    </div>
                    {sessionId ? loadedSession ? (
                        <div className={`asset-identity-notice${activeSession?.asset_id ? "" : " is-unresolved"}`} role="status">
                            {activeSession?.asset_id
                                ? `This session is linked to asset ${activeSession.asset_id}. Its identity cannot be changed here.`
                                : "This session has unresolved asset identity. It will remain unassociated; retests preserve that identity."}
                        </div>
                    ) : (
                        <div className="asset-identity-notice" role="status">Loading the selected QC session identity…</div>
                    ) : (
                        <AssetResolutionPicker
                            value={assetResolution}
                            onChange={(selection) => {
                                setAssetResolution(selection);
                                setError("");
                            }}
                        />
                    )}
                    <SaveIndicator
                        state={savingIntake ? "saving" : intakeMatchesSaved ? "saved" : "unsaved"}
                    />
                    {!loadedSession && (
                        <p className="empty-state">
                            This intake draft is kept in this browser until you confirm it for a QC session.
                        </p>
                    )}
                    <FieldLabel>
                        Asset tag / serial / barcode
                        <input
                            value={assetTag}
                            onChange={(event) => setAssetTag(event.target.value)}
                            maxLength={100}
                        />
                    </FieldLabel>
                    <FieldLabel>
                        Technician
                        <input
                            value={technician}
                            onChange={(event) => setTechnician(event.target.value)}
                            maxLength={150}
                        />
                    </FieldLabel>
                    <FieldLabel>
                        Customer / work-order reference
                        <input
                            value={customerReference}
                            onChange={(event) => setCustomerReference(event.target.value)}
                            maxLength={150}
                        />
                    </FieldLabel>
                    <FieldLabel>
                        Technician workflow
                        <select
                            value={workflowType}
                            onChange={(event) => setWorkflowType(event.target.value)}
                        >
                            <option value="service_center">Service center</option>
                            <option value="refurbishment">Refurbishment</option>
                            <option value="manufacturing_qa">Manufacturing QA</option>
                            <option value="rma_validation">RMA validation</option>
                            <option value="incoming_inspection">Incoming inspection</option>
                            <option value="outgoing_certification">Outgoing certification</option>
                        </select>
                    </FieldLabel>
                </section>
            )}

            {!loading && devices.length > 0 && (
                <section className="inventory-continue">
                    <div>
                        <strong>Ready to begin the inspection?</strong>
                        <span>
                            {selectedSystemDevice
                                ? `Selected system: ${selectedSystemDevice.name || selectedSystemDevice.device_id}. Confirm intake to save this QC session.`
                                : systemDevices.length > 1
                                  ? "Select the intended system device before confirming intake."
                                  : "The backend did not identify a selectable system-level device."}
                        </span>
                    </div>
                    <button
                        className="button button-primary"
                        type="button"
                        onClick={() => void continueToDiagnostics()}
                        disabled={
                            !selectedSystemDevice ||
                            savingIntake ||
                            sessionLoading ||
                            (Boolean(sessionId) && !loadedSession) ||
                            (!sessionId &&
                                (!assetResolution ||
                                    (assetResolution.mode === "existing" && !assetResolution.assetId.trim())))
                        }
                    >
                        {savingIntake
                            ? "Saving intake…"
                            : sessionId
                            ? "Save intake & begin inspection"
                              : "Confirm intake & start QC"} <span aria-hidden="true">→</span>
                    </button>
                </section>
            )}
        </div>
    );
}
