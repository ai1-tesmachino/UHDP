import { useEffect, useState } from "react";
import { useLocation, useNavigate, useSearchParams } from "react-router-dom";

import { getDevice } from "../api/devices";
import { getProfiles, TestProfile } from "../api/profiles";
import { Device } from "../types/device";
import { getStationProfile } from "../station";

const PROFILE_OPTIONS: Array<{
    name: string;
    label: string;
    description: string;
}> = [
    {
        name: "quick_test",
        label: "Quick Inspection",
        description: "A short CPU and memory check using the backend quick profile.",
    },
    {
        name: "extended_test",
        label: "Full Hardware QA",
        description: "The available extended CPU, memory, storage, and network profile.",
    },
    {
        name: "refurbishment_qa",
        label: "Refurbishment QA",
        description: "The configured refurbishment profile for service and resale inspections.",
    },
    {
        name: "manufacturing_qa",
        label: "Manufacturing QA",
        description: "The configured manufacturing validation profile.",
    },
];

interface IntakeRecord {
    asset_tag?: string;
    technician?: string;
    station_id?: string;
    customer_reference?: string;
    workflow_type?: string;
    retest_of_session_id?: string;
}

export default function TestProfiles() {
    const [params] = useSearchParams();
    const location = useLocation();
    const navigate = useNavigate();
    const deviceId = params.get("deviceId") || "";
    const navigationState = location.state as {
        device?: Device;
        intake?: IntakeRecord;
    } | null;
    const [device, setDevice] = useState<Device | undefined>(navigationState?.device);
    const [profiles, setProfiles] = useState<TestProfile[]>([]);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState("");

    useEffect(() => {
        if (!deviceId) {
            setError("A detected device is required. Return to device discovery and continue from the inventory.");
            setLoading(false);
            return;
        }
        let active = true;
        Promise.all([
            getProfiles(),
            navigationState?.device?.device_id === deviceId
                ? Promise.resolve(navigationState.device)
                : deviceId
                  ? getDevice(deviceId)
                  : Promise.resolve(undefined),
        ])
            .then(([loadedProfiles, loadedDevice]) => {
                if (active) {
                    setProfiles(loadedProfiles);
                    setDevice(loadedDevice);
                }
            })
            .catch((loadError: unknown) => {
                if (active) {
                    setError(loadError instanceof Error ? loadError.message : "Profiles or device details could not be loaded.");
                }
            })
            .finally(() => {
                if (active) {
                    setLoading(false);
                }
            });
        return () => {
            active = false;
        };
    }, [deviceId, navigationState]);

    function choose(profileName: string, diagnostics: string[]) {
        if (!deviceId || !device) {
            setError("Return to device discovery and select a detected system before continuing.");
            return;
        }
        const station = getStationProfile();
        const intake = {
            ...navigationState?.intake,
            technician: navigationState?.intake?.technician || station?.technician || "",
            station_id: navigationState?.intake?.station_id || station?.station_id || "",
            retest_of_session_id: navigationState?.intake?.retest_of_session_id || params.get("retestOf") || undefined,
        };
        const query = new URLSearchParams({
            deviceId,
            selected: diagnostics.join(","),
            profileName,
            retestOf: intake.retest_of_session_id || "",
            assetTag: intake.asset_tag || "",
            technician: intake.technician || "",
            stationId: intake.station_id || "",
            customerReference: intake.customer_reference || "",
            workflowType: intake.workflow_type || "service_center",
        });
        navigate(`/diagnostics?${query.toString()}`, {
            state: { device, intake, profileName },
        });
    }

    const loadedProfiles = new Map(profiles.map((profile) => [profile.name, profile]));

    return (
        <div className="page-flow">
            <div className="page-header">
                <div>
                    <span className="eyebrow">STEP 4 OF 9 · TEST PLAN</span>
                    <h1 className="page-title">Select a test profile</h1>
                    <p className="page-description">
                        Profiles are loaded from the backend. You can adjust the selected automated checks and add guided manual tests next.
                    </p>
                </div>
            </div>

            {device && (
                <section className="selection-device">
                    <span className="selection-device-icon" aria-hidden="true">◈</span>
                    <div className="selection-device-info">
                        <span>DETECTED SYSTEM</span>
                        <strong>{device.name}</strong>
                        <code>{device.device_id}</code>
                    </div>
                </section>
            )}

            {error && <div className="error-box">{error}</div>}
            {loading ? (
                <div className="loading-panel">Loading backend test profiles…</div>
            ) : (
                <section className="profile-grid" aria-label="Available test profiles">
                    {PROFILE_OPTIONS.map((option) => {
                        const profile = loadedProfiles.get(option.name);
                        return (
                            <article className="profile-card" key={option.name}>
                                <div>
                                    <span className="eyebrow">{profile ? "BACKEND PROFILE" : "NOT CONFIGURED"}</span>
                                    <h2>{option.label}</h2>
                                    <p>{profile?.description || option.description}</p>
                                </div>
                                <span className="profile-check-count">
                                    {profile ? `${profile.diagnostics.length} automated checks` : "Profile unavailable"}
                                </span>
                                {profile && (
                                    <p className="profile-diagnostic-list">
                                        {profile.diagnostics.join(" · ") || "No automated checks configured"}
                                    </p>
                                )}
                                <button
                                    className="button button-primary"
                                    type="button"
                                    disabled={!profile || !device}
                                    onClick={() => profile && choose(profile.name, profile.diagnostics)}
                                >
                                    Use profile <span aria-hidden="true">→</span>
                                </button>
                            </article>
                        );
                    })}
                    <article className="profile-card profile-card-custom">
                        <div>
                            <span className="eyebrow">TECHNICIAN-SELECTED</span>
                            <h2>Custom Selection</h2>
                            <p>Choose any available backend diagnostic and individual guided manual checks.</p>
                        </div>
                        <span className="profile-check-count">No checks preselected</span>
                        <button
                            className="button button-secondary"
                            type="button"
                            disabled={!device}
                            onClick={() => choose("custom_selection", [])}
                        >
                            Build custom plan <span aria-hidden="true">→</span>
                        </button>
                    </article>
                </section>
            )}
        </div>
    );
}
