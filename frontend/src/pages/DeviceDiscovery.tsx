import { useCallback, useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";

import { getDevices } from "../api/devices";
import { getStationProfile } from "../station";
import { Device } from "../types/device";

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
    const [devices, setDevices] = useState<Device[]>([]);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState("");
    const [assetTag, setAssetTag] = useState("");
    const [technician, setTechnician] = useState(() => getStationProfile()?.technician || "");
    const [customerReference, setCustomerReference] = useState("");
    const [workflowType, setWorkflowType] = useState("service_center");

    const loadDevices = useCallback(async () => {
        setLoading(true);
        setError("");

        try {
            setDevices(await getDevices());
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
                const value = device.properties?.physical_disks;
                if (!Array.isArray(value)) {
                    return [];
                }
                return value.flatMap((entry) => {
                    if (typeof entry !== "object" || entry === null || Array.isArray(entry)) {
                        return [];
                    }
                    const properties = entry as Record<string, unknown>;
                    const identity = properties.FriendlyName || properties.Model || properties.SerialNumber;
                    if (!identity) {
                        return [];
                    }
                    const key = [
                        properties.FriendlyName,
                        properties.SerialNumber,
                        properties.Size,
                    ].map((part) => String(part ?? "")).join("|");
                    return [[key, properties] as const];
                });
            })
        ).values(),
    ];

    function continueToDiagnostics() {
        if (!systemDevice) {
            return;
        }

        const query = new URLSearchParams({
            deviceId: systemDevice.device_id,
            assetTag,
            technician,
            stationId: getStationProfile()?.station_id || "",
            customerReference,
            workflowType,
        });
        navigate(`/test-profiles?${query.toString()}`, {
            state: {
                device: systemDevice,
                intake: {
                    asset_tag: assetTag,
                    technician,
                    station_id: getStationProfile()?.station_id || "",
                    customer_reference: customerReference,
                    workflow_type: workflowType,
                },
            },
        });
    }

    return (
        <div className="page-flow">
            <div className="page-header">
                <div>
                    <span className="eyebrow">STEP 3 OF 9 · HARDWARE INVENTORY</span>
                    <h1 className="page-title">Review detected hardware</h1>
                    <p className="page-description">
                        This inventory summarizes hardware detected on this machine. Diagnostics run across the system, not one component at a time.
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
                <button
                    className="button button-secondary"
                    type="button"
                    onClick={() => navigate("/capabilities")}
                >
                    Runtime capabilities
                </button>
            </div>

            <div className="device-list-heading">
                <strong>System inventory</strong>
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
                                <article className="hardware-entry-card" key={`${String(drive.SerialNumber || drive.FriendlyName)}-${index}`}>
                                    <h2>{String(drive.FriendlyName || drive.Model || "Drive identity unavailable")}</h2>
                                    <dl className="device-properties">
                                        {Object.entries(drive).map(([name, value]) => (
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
                    <span>The current discovery endpoint does not expose individual RAM-module SPD records. The memory diagnostic reports system-level capacity and utilization only; module serials, part numbers, and per-slot speeds remain unavailable.</span>
                </div>
                <div className="inventory-limit-note">
                    <strong>Storage-health detail availability</strong>
                    <span>Physical-drive properties are shown only when returned by the OS discovery provider. The current standard storage diagnostic reports mounted volume capacity and utilization; SMART/NVMe health, firmware, temperature, power-on hours, and read/write benchmarks are not provided by that diagnostic.</span>
                </div>
                </>
            )}

            {!loading && devices.length > 0 && (
                <section className="technician-record-panel">
                    <div>
                        <span className="eyebrow">DEVICE INTAKE</span>
                        <h2>Technician and work order</h2>
                        <p>Scan or type the device asset tag / serial, then confirm the technician and work order.</p>
                    </div>
                    <label>
                        Asset tag / serial / barcode
                        <input
                            value={assetTag}
                            onChange={(event) => setAssetTag(event.target.value)}
                            maxLength={100}
                        />
                    </label>
                    <label>
                        Technician
                        <input
                            value={technician}
                            onChange={(event) => setTechnician(event.target.value)}
                            maxLength={150}
                        />
                    </label>
                    <label>
                        Customer / work-order reference
                        <input
                            value={customerReference}
                            onChange={(event) => setCustomerReference(event.target.value)}
                            maxLength={150}
                        />
                    </label>
                    <label>
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
                            <option value="burn_in">Burn-in</option>
                        </select>
                    </label>
                </section>
            )}

            {!loading && devices.length > 0 && (
                <section className="inventory-continue">
                    <div>
                        <strong>Ready to run a system check?</strong>
                        <span>
                            {systemDevice
                                ? "Choose diagnostics for this machine."
                                : "The backend did not identify a system-level device, so a run cannot be started."}
                        </span>
                    </div>
                    <button
                        className="button button-primary"
                        type="button"
                        onClick={continueToDiagnostics}
                        disabled={!systemDevice}
                    >
                        Continue to diagnostics <span aria-hidden="true">→</span>
                    </button>
                </section>
            )}
        </div>
    );
}
