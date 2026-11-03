import { useCallback, useEffect, useMemo, useState } from "react";
import {
    useLocation,
    useNavigate,
    useSearchParams,
} from "react-router-dom";

import { getDevice } from "../api/devices";
import { getDiagnostics } from "../api/diagnostics";
import { getManualChecks, ManualCheck, updateSessionIntake } from "../api/execution";
import { Device } from "../types/device";
import { useQcSession } from "../session/SessionContext";

const diagnosticDescriptions: Record<string, string> = {
    cpu: "Processor performance and health",
    memory: "System memory availability and integrity",
    storage: "Storage device health and capacity",
    network: "Network connectivity and adapters",
    usb: "Connected USB devices and ports",
    battery: "Battery status and capacity",
    system: "General system health checks",
};

function manualCategory(id: string) {
    if (/cosmetic/.test(id)) return "Cosmetic condition";
    if (/display|touchscreen/.test(id)) return "Display";
    if (/keyboard|mouse|touchpad/.test(id)) return "Input";
    if (/speaker|microphone|headset/.test(id)) return "Audio";
    if (/ethernet|wifi|bluetooth/.test(id)) return "Connectivity";
    if (/usb|hdmi|displayport|vga|card_reader/.test(id)) return "USB and external ports";
    if (/webcam|face_recognition/.test(id)) return "Webcam";
    if (/charger|charging|battery/.test(id)) return "Power and charging";
    if (/physical_inspection/.test(id)) return "Cosmetic and physical condition";
    return "Other peripherals";
}

function automatedCategory(id: string) {
    if (/display|monitor/.test(id)) return "Display";
    if (/keyboard|mouse|touchpad|input/.test(id)) return "Input";
    if (/audio|speaker|microphone/.test(id)) return "Audio";
    if (/network|wifi|bluetooth|ethernet/.test(id)) return "Connectivity";
    if (/usb|hdmi|displayport|vga|port|card_reader/.test(id)) return "USB and external ports";
    if (/webcam|camera/.test(id)) return "Webcam";
    if (/battery|charger|charging/.test(id)) return "Power and charging";
    if (/cpu|memory|ram|gpu|storage|thermal|stress/.test(id)) return "Performance";
    return "Other checks";
}

export default function DiagnosticSelection() {
    const [params] = useSearchParams();
    const location = useLocation();
    const navigate = useNavigate();
    const { activeSession, loading: sessionLoading } = useQcSession();

    const sessionId = params.get("sessionId") || activeSession?.session_id || "";
    const deviceId = params.get("deviceId") || activeSession?.device_id || "";
    const navigationDevice = (location.state as { device?: Device } | null)?.device;
    const navigationIntake = (
        location.state as {
            intake?: {
                asset_tag?: string;
                technician?: string;
                station_id?: string;
                customer_reference?: string;
                workflow_type?: string;
                profile_name?: string;
                retest_of_session_id?: string;
                planned_diagnostics?: string[];
                planned_manual_checks?: string[];
            };
            profileName?: string;
        } | null
    )?.intake;
    const profileName = params.get("profileName") ||
        (location.state as { profileName?: string } | null)?.profileName ||
        "custom_selection";
    const [device, setDevice] = useState<Device | undefined>(navigationDevice);
    const [diagnostics, setDiagnostics] = useState<string[]>([]);
    const [manualChecks, setManualChecks] = useState<ManualCheck[]>([]);
    const [mode, setMode] = useState<"automated" | "manual">(
        params.get("mode") === "manual" || params.get("category") === "cosmetic"
            ? "manual"
            : "automated"
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
    const [savingPlan, setSavingPlan] = useState(false);

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
        if (sessionLoading) return;
        if (!deviceId) {
            navigate(
                sessionId
                    ? `/devices?sessionId=${encodeURIComponent(sessionId)}`
                    : "/devices",
                { replace: true },
            );
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
    }, [deviceId, navigate, navigationDevice, sessionId, sessionLoading]);

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

    async function runSession() {
        const standardSelected = selected.filter((item) => ordinaryDiagnostics.includes(item));
        const chosen = mode === "automated" ? standardSelected : selectedManual;
        if (!deviceId || chosen.length === 0) {
            return;
        }
        const originalProfileDiagnostics = selectedQuery.split(",").filter(Boolean);
        const executionProfileName =
            profileName !== "custom_selection" &&
            standardSelected.every((item) => originalProfileDiagnostics.includes(item))
                ? profileName
                : "custom_selection";

        const query = new URLSearchParams({
            sessionId,
            deviceId,
            deviceName: device?.name || "This system",
            mode,
            diagnostics: mode === "automated" ? standardSelected.join(",") : "",
            manualChecks: mode === "manual" ? selectedManual.join(",") : "",
            assetTag: navigationIntake?.asset_tag || params.get("assetTag") || "",
            technician: navigationIntake?.technician || params.get("technician") || "",
            stationId: navigationIntake?.station_id || params.get("stationId") || "",
            customerReference:
                navigationIntake?.customer_reference || params.get("customerReference") || "",
            workflowType: navigationIntake?.workflow_type || params.get("workflowType") || "service_center",
            profileName: executionProfileName,
            retest: params.get("retest") || "",
        });

        setSavingPlan(true);
        setError("");
        try {
            if (!sessionId) {
                throw new Error("Start or resume a QC session before selecting checks.");
            }
            const intake = {
                ...navigationIntake,
                asset_tag: navigationIntake?.asset_tag || params.get("assetTag") || undefined,
                technician: navigationIntake?.technician || params.get("technician") || undefined,
                station_id: navigationIntake?.station_id || params.get("stationId") || undefined,
                customer_reference: navigationIntake?.customer_reference || params.get("customerReference") || undefined,
                workflow_type: navigationIntake?.workflow_type || params.get("workflowType") || "service_center",
                profile_name: executionProfileName,
                planned_diagnostics: mode === "automated" ? standardSelected : [],
                planned_manual_checks: mode === "manual" ? selectedManual : [],
            };
            await updateSessionIntake(
                sessionId,
                deviceId,
                intake,
                activeSession?.device_inventory || [],
            );
            navigate(`/execution?${query.toString()}`, {
            state: {
                deviceId,
                deviceName: device?.name || "This system",
                diagnostics: standardSelected,
                mode,
                manualChecks: selectedManual,
                intake: {
                    ...intake,
                    retest_of_session_id: navigationIntake?.retest_of_session_id || params.get("retestOf") || undefined,
                },
            },
            });
        } catch (saveError) {
            setError(saveError instanceof Error ? saveError.message : "The QC test plan could not be saved.");
        } finally {
            setSavingPlan(false);
        }
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
    const displayedManualChecks = params.get("retest") === "1"
        ? manualChecks
        : params.get("category") === "cosmetic"
            ? manualChecks.filter((check) => check.id === "physical_inspection" || check.id.endsWith("_cosmetic"))
            : manualChecks.filter((check) => check.id !== "physical_inspection" && !check.id.endsWith("_cosmetic"));

    return (
        <div className="page-flow">
            <div className="page-header">
                <div>
                    <span className="eyebrow">FUNCTIONAL QC · SESSION {sessionId || "UNASSIGNED"}</span>
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
                    onClick={() => navigate(`/devices?sessionId=${encodeURIComponent(sessionId)}`)}
                >
                    View inventory
                </button>
            </section>

            <section className="selected-profile-banner">
                <span>ACTIVE PROFILE</span>
                <strong>{profileName.replaceAll("_", " ")}</strong>
                <button className="button button-quiet" type="button" onClick={() => navigate(`/test-profiles?sessionId=${encodeURIComponent(sessionId)}&deviceId=${encodeURIComponent(deviceId)}`, { state: { device, intake: navigationIntake } })}>
                    Change profile
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
                <div className="manual-category-list">
                    {[...new Set(ordinaryDiagnostics.map(automatedCategory))].map((category) => (
                        <section className="manual-category" key={category}>
                            <h3>{category}</h3>
                            <div className="diagnostic-grid">
                                {ordinaryDiagnostics.filter((diagnostic) => automatedCategory(diagnostic) === category).map((diagnostic) => {
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
                            </div>
                        </section>
                    ))}
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
                <div className="manual-category-list">
                    {[...new Set(displayedManualChecks.map((check) => manualCategory(check.id)))].map((category) => (
                        <section className="manual-category" key={category}>
                            <h3>{category}</h3>
                            <div className="diagnostic-grid">
                                {displayedManualChecks.filter((check) => manualCategory(check.id) === category).map((check) => {
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
                            </div>
                        </section>
                    ))}
                    {!error && displayedManualChecks.length === 0 && (
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
                        onClick={() => navigate(`/diagnostic-jobs?sessionId=${encodeURIComponent(sessionId)}`)}
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
                    onClick={() => void runSession()}
                    disabled={!deviceId || !device || currentCount === 0 || loading || savingPlan || sessionLoading}
                >
                    {savingPlan ? "Saving test plan…" : `Continue to ${mode === "manual" ? "manual checks" : "execution"}`} <span aria-hidden="true">→</span>
                </button>
            </div>
        </div>
    );
}
