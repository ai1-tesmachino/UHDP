import { useCallback, useEffect, useMemo, useState } from "react";
import {
    useLocation,
    useNavigate,
    useSearchParams,
} from "react-router-dom";

import { getDevice } from "../api/devices";
import { getDiagnostics } from "../api/diagnostics";
import { getManualChecks, ManualCheck } from "../api/execution";
import { Device } from "../types/device";

const diagnosticDescriptions: Record<string, string> = {
    cpu: "Processor performance and health",
    memory: "System memory availability and integrity",
    storage: "Storage device health and capacity",
    network: "Network connectivity and adapters",
    usb: "Connected USB devices and ports",
    battery: "Battery status and capacity",
    system: "General system health checks",
};

export default function DiagnosticSelection() {
    const [params] = useSearchParams();
    const location = useLocation();
    const navigate = useNavigate();

    const deviceId = params.get("deviceId") || "";
    const navigationDevice = (location.state as { device?: Device } | null)?.device;
    const navigationIntake = (
        location.state as {
            intake?: {
                asset_tag?: string;
                technician?: string;
                customer_reference?: string;
                workflow_type?: string;
            };
        } | null
    )?.intake;
    const [device, setDevice] = useState<Device | undefined>(navigationDevice);
    const [diagnostics, setDiagnostics] = useState<string[]>([]);
    const [manualChecks, setManualChecks] = useState<ManualCheck[]>([]);
    const [mode, setMode] = useState<"automated" | "manual">(
        params.get("mode") === "manual" ? "manual" : "automated"
    );
    const selectedQuery = params.get("selected") || "";
    const [selected, setSelected] = useState<string[]>(
        () => selectedQuery ? selectedQuery.split(",").filter(Boolean) : []
    );
    const [selectedManual, setSelectedManual] = useState<string[]>(
        () => (params.get("manualChecks") || "").split(",").filter(Boolean)
    );
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState("");

    const loadDiagnostics = useCallback(async () => {
        setLoading(true);
        setError("");

        try {
            const [automated, manual] = await Promise.all([
                getDiagnostics(),
                getManualChecks(),
            ]);
            setDiagnostics(automated);
            setManualChecks(manual);
        } catch {
            setError("Available diagnostics could not be loaded. Check the backend connection and try again.");
        } finally {
            setLoading(false);
        }
    }, []);

    useEffect(() => {
        void loadDiagnostics();
    }, [loadDiagnostics]);

    useEffect(() => {
        if (!deviceId) {
            navigate("/devices", { replace: true });
            return;
        }

        if (navigationDevice?.device_id === deviceId) {
            setDevice(navigationDevice);
            return;
        }

        let active = true;
        getDevice(deviceId)
            .then((loadedDevice) => {
                if (active) {
                    setDevice(loadedDevice);
                }
            })
            .catch(() => {
                if (active) {
                    setError("The system inventory could not be restored. Return to device discovery and continue again.");
                }
            });

        return () => {
            active = false;
        };
    }, [deviceId, navigate, navigationDevice]);

    function toggleDiagnostic(diagnostic: string) {
        setSelected((current) =>
            current.includes(diagnostic)
                ? current.filter((item) => item !== diagnostic)
                : [...current, diagnostic]
        );
    }

    function toggleManualCheck(checkId: string) {
        setSelectedManual((current) =>
            current.includes(checkId)
                ? current.filter((item) => item !== checkId)
                : [...current, checkId]
        );
    }

    function runSession() {
        const standardSelected = selected.filter((item) => ordinaryDiagnostics.includes(item));
        const chosen = mode === "automated" ? standardSelected : selectedManual;
        if (!deviceId || chosen.length === 0) {
            return;
        }

        const query = new URLSearchParams({
            deviceId,
            deviceName: device?.name || "This system",
            mode,
            diagnostics: mode === "automated" ? standardSelected.join(",") : "",
            manualChecks: mode === "manual" ? selectedManual.join(",") : "",
            assetTag: navigationIntake?.asset_tag || params.get("assetTag") || "",
            technician: navigationIntake?.technician || params.get("technician") || "",
            customerReference:
                navigationIntake?.customer_reference || params.get("customerReference") || "",
            workflowType: navigationIntake?.workflow_type || params.get("workflowType") || "service_center",
        });

        navigate(`/execution?${query.toString()}`, {
            state: {
                deviceId,
                deviceName: device?.name || "This system",
                diagnostics: standardSelected,
                mode,
                manualChecks: selectedManual,
                intake: navigationIntake,
            },
        });
    }

    const ordinaryDiagnostics = diagnostics.filter(
        (diagnostic) => !["cpu_stress", "memory_stress"].includes(diagnostic)
    );
    const stressDiagnostics = diagnostics.filter(
        (diagnostic) => ["cpu_stress", "memory_stress"].includes(diagnostic)
    );
    const currentCount = mode === "automated"
        ? selected.filter((item) => ordinaryDiagnostics.includes(item)).length
        : selectedManual.length;

    return (
        <div className="page-flow">
            <div className="page-header">
                <div>
                    <span className="eyebrow">STEP 3 OF 6 · TEST PLAN</span>
                    <h1 className="page-title">Select diagnostics</h1>
                    <p className="page-description">
                        Choose an automated hardware probe or a guided operator-confirmed test. Run modes are separate.
                    </p>
                </div>
                <button
                    className="button button-quiet"
                    type="button"
                    onClick={() => void loadDiagnostics()}
                    disabled={loading}
                >
                    {loading ? "Loading…" : "Refresh list"}
                </button>
            </div>

            <section className="selection-device">
                <span className="selection-device-icon" aria-hidden="true">◈</span>
                <div className="selection-device-info">
                    <span>WHOLE SYSTEM</span>
                    <strong>{device?.name || (deviceId ? "Loading system details…" : "No system selected")}</strong>
                    {device?.name && <code>{deviceId}</code>}
                </div>
                <button
                    className="button button-secondary"
                    type="button"
                    onClick={() => navigate("/devices")}
                >
                    View inventory
                </button>
            </section>

            {error && (
                <div className="error-box selection-error">
                    <span>{error}</span>
                    <button className="button button-secondary" type="button" onClick={() => void loadDiagnostics()}>
                        Try again
                    </button>
                </div>
            )}

            <div className="selection-heading">
                <div>
                    <h2>Available checks</h2>
                    <p>These checks run against the whole machine.</p>
                </div>
            </div>

            <div className="action-row" role="tablist" aria-label="Test mode">
                <button
                    className={`button ${mode === "automated" ? "button-primary" : "button-secondary"}`}
                    type="button"
                    role="tab"
                    aria-selected={mode === "automated"}
                    onClick={() => setMode("automated")}
                >
                    Automated tests
                </button>
                <button
                    className={`button ${mode === "manual" ? "button-primary" : "button-secondary"}`}
                    type="button"
                    role="tab"
                    aria-selected={mode === "manual"}
                    onClick={() => setMode("manual")}
                >
                    Manual tests
                </button>
            </div>

            {mode === "automated" && (
                <div className="action-row">
                    <button
                        className="button button-quiet"
                        type="button"
                        onClick={() => setSelected(ordinaryDiagnostics)}
                        disabled={loading || ordinaryDiagnostics.length === 0}
                    >
                        Select standard checks
                    </button>
                    <button
                        className="button button-quiet"
                        type="button"
                        onClick={() => setSelected([])}
                        disabled={selected.length === 0}
                    >
                        Clear
                    </button>
                </div>
            )}

            {mode === "automated" ? loading ? (
                <div className="diagnostic-grid">
                    {[1, 2, 3, 4].map((item) => (
                        <div className="diagnostic-card diagnostic-card-loading" key={item} aria-hidden="true">
                            <span />
                            <span />
                        </div>
                    ))}
                </div>
            ) : (
                <div className="diagnostic-grid">
                    {ordinaryDiagnostics.map((diagnostic) => {
                        const isSelected = selected.includes(diagnostic);
                        return (
                            <label
                                key={diagnostic}
                                className={`diagnostic-option${isSelected ? " selected" : ""}`}
                            >
                                <input
                                    className="diagnostic-checkbox"
                                    type="checkbox"
                                    checked={isSelected}
                                    onChange={() => toggleDiagnostic(diagnostic)}
                                />
                                <span className="diagnostic-checkmark" aria-hidden="true">
                                    {isSelected ? "✓" : ""}
                                </span>
                                <span className="diagnostic-option-copy">
                                    <strong>{diagnostic}</strong>
                                    <span>
                                        {diagnosticDescriptions[diagnostic.toLowerCase()] ||
                                            `Run the ${diagnostic} diagnostic check`}
                                    </span>
                                </span>
                            </label>
                        );
                    })}
                    {!error && ordinaryDiagnostics.length === 0 && (
                        <div className="empty-panel diagnostic-empty">
                            <h2>No diagnostics available</h2>
                            <p>The backend did not return any available checks.</p>
                        </div>
                    )}
                </div>
            ) : loading ? (
                <div className="loading-panel">Loading manual checks…</div>
            ) : (
                <div className="diagnostic-grid">
                    {manualChecks.map((check) => {
                        const isSelected = selectedManual.includes(check.id);
                        return (
                            <label
                                key={check.id}
                                className={`diagnostic-option${isSelected ? " selected" : ""}`}
                            >
                                <input
                                    className="diagnostic-checkbox"
                                    type="checkbox"
                                    checked={isSelected}
                                    onChange={() => toggleManualCheck(check.id)}
                                />
                                <span className="diagnostic-checkmark" aria-hidden="true">
                                    {isSelected ? "✓" : ""}
                                </span>
                                <span className="diagnostic-option-copy">
                                    <strong>{check.name}</strong>
                                    <span>{check.instructions}</span>
                                </span>
                            </label>
                        );
                    })}
                    {!error && manualChecks.length === 0 && (
                        <div className="empty-panel diagnostic-empty">
                            <h2>No manual checks available</h2>
                            <p>The backend did not return any operator checks.</p>
                        </div>
                    )}
                </div>
            )}

            {mode === "automated" && stressDiagnostics.length > 0 && (
                <section className="stress-checks">
                    <div className="selection-heading">
                        <div>
                            <h2>Optional stress checks</h2>
                            <p>Stress and endurance runs are separate pollable jobs. Save your work first; regular stress jobs are capped at 30 seconds.</p>
                        </div>
                    </div>
                    <p>CPU, RAM, GPU, and battery endurance jobs have live progress, cancellation, telemetry, and versioned evaluation criteria.</p>
                    <button
                        className="button button-secondary"
                        type="button"
                        onClick={() => navigate("/diagnostic-jobs")}
                    >
                        Open Test Jobs
                    </button>
                </section>
            )}

            <div className="selection-footer">
                <div className="selection-count">
                    <strong>{currentCount}</strong>
                    <span>{currentCount === 1 ? "check selected" : "checks selected"}</span>
                </div>
                <button
                    className="button button-primary"
                    type="button"
                    onClick={runSession}
                    disabled={!deviceId || !device || currentCount === 0 || loading}
                >
                    Continue to {mode === "manual" ? "manual checks" : "execution"} <span aria-hidden="true">→</span>
                </button>
            </div>
        </div>
    );
}
