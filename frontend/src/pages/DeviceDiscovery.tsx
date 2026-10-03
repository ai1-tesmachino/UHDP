import { useCallback, useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";

import { getDevices } from "../api/devices";
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
    const [technician, setTechnician] = useState("");
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

    function continueToDiagnostics() {
        if (!systemDevice) {
            return;
        }

        const query = new URLSearchParams({
            deviceId: systemDevice.device_id,
            assetTag,
            technician,
            customerReference,
            workflowType,
        });
        navigate(`/diagnostics?${query.toString()}`, {
            state: {
                device: systemDevice,
                intake: {
                    asset_tag: assetTag,
                    technician,
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
                    <span className="eyebrow">STEP 2 OF 6 · HARDWARE</span>
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
                <div className="device-table-wrapper">
                    <table className="device-table">
                        <thead>
                            <tr>
                                <th>Component</th>
                                <th>Detected hardware</th>
                                <th>Reported information</th>
                                <th>Device ID</th>
                            </tr>
                        </thead>
                        <tbody>
                            {devices.map((device) => {
                                const properties = Object.entries(device.properties || {});

                                return (
                                    <tr key={device.device_id}>
                                        <td>
                                            <span className="device-type-pill">
                                                {device.device_type}
                                            </span>
                                        </td>
                                        <td className="device-table-name">
                                            <strong>{device.name || "Unnamed hardware"}</strong>
                                            <span>{device.device_type} inventory entry</span>
                                        </td>
                                        <td>
                                            {properties.length > 0 ? (
                                                <dl className="device-properties">
                                                    {properties.map(([name, value]) => (
                                                        <div className="device-property" key={name}>
                                                            <dt>{name.replaceAll("_", " ")}</dt>
                                                            <dd>
                                                                <code>{formatValue(value)}</code>
                                                            </dd>
                                                        </div>
                                                    ))}
                                                </dl>
                                            ) : (
                                                <span className="device-property-empty">
                                                    No additional properties were reported.
                                                </span>
                                            )}
                                        </td>
                                        <td><code className="device-table-id">{device.device_id}</code></td>
                                    </tr>
                                );
                            })}
                        </tbody>
                    </table>
                </div>
            )}

            {!loading && devices.length > 0 && (
                <section className="technician-record-panel">
                    <div>
                        <span className="eyebrow">DEVICE INTAKE</span>
                        <h2>Technician and work order</h2>
                        <p>Optional identifiers are included with the diagnostic session and report.</p>
                    </div>
                    <label>
                        Asset tag
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
