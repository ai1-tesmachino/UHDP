import { useCallback, useEffect, useRef, useState } from "react";
import { useNavigate, useSearchParams } from "react-router-dom";

import { getDevices } from "../api/devices";
import { getStationInventory, mergeDiscoveredInventory } from "../api/inventory";
import { createDiagnosticSession, updateSessionIntake } from "../api/execution";
import { getStationProfile } from "../station";
import { useQcSession } from "../session/SessionContext";
import { Device } from "../types/device";
import FieldLabel from "../components/FieldLabel";

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
    const { activeSession, activeSessionId, activateSession, loading: sessionLoading } = useQcSession();
    const isNewIntake = params.get("new") === "1";
    const sessionId = params.get("sessionId") || (isNewIntake ? "" : activeSessionId);
    const [devices, setDevices] = useState<Device[]>([]);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState("");
    const [assetTag, setAssetTag] = useState("");
    const [technician, setTechnician] = useState(() => getStationProfile()?.technician || "");
    const [customerReference, setCustomerReference] = useState("");
    const [workflowType, setWorkflowType] = useState("service_center");
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

    const systemDevice = devices.find(
        (device) => device.device_type.toLowerCase() === "system"
    );
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
        if (!systemDevice) {
            return;
        }

        setSavingIntake(true);
        setError("");
        const intake = {
            asset_tag: assetTag,
            technician,
            station_id: getStationProfile()?.station_id || "",
            customer_reference: customerReference,
            workflow_type: workflowType,
        };
        let targetSessionId = sessionId;
        try {
            if (!targetSessionId) {
                const created = await createDiagnosticSession(systemDevice.device_id, intake);
                if (typeof created.session_id !== "string" || !created.session_id) {
                    throw new Error("The new QC session was created without an identifier.");
                }
                targetSessionId = created.session_id;
                navigate(`/devices?sessionId=${encodeURIComponent(targetSessionId)}#intake`, { replace: true });
                await activateSession(targetSessionId);
            }
            await updateSessionIntake(
                targetSessionId,
                systemDevice.device_id,
                intake,
                devices.map((device) => ({ ...device })),
            );
        } catch (saveError) {
            setError(saveError instanceof Error ? saveError.message : "The device intake could not be saved.");
            setSavingIntake(false);
            return;
        }
        if (!targetSessionId) {
            setError("The QC session could not be confirmed. Retry the intake before continuing.");
            setSavingIntake(false);
            return;
        }
        const query = new URLSearchParams({
            sessionId: targetSessionId,
            stage: "cosmetic",
        });
        navigate(`/qc?${query.toString()}`, {
            state: {
                device: systemDevice,
                intake,
            },
        });
        setSavingIntake(false);
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
                            <article className="hardware-entry-card" key={device.device_id}>
                                <div className="hardware-entry-heading">
                                    <span className="device-type-pill">{device.device_type}</span>
                                    <span>{properties.length} reported properties</span>
                                </div>
                                <h2>{device.name || "Unnamed hardware"}</h2>
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
                            {systemDevice
                                ? "Confirm intake to save this QC session, then record the device condition and functional checks."
                                : "The backend did not identify a system-level device, so intake cannot be confirmed."}
                        </span>
                    </div>
                    <button
                        className="button button-primary"
                        type="button"
                        onClick={() => void continueToDiagnostics()}
                        disabled={!systemDevice || savingIntake || sessionLoading}
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
