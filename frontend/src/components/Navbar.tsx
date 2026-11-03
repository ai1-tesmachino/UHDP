import { useEffect, useState } from "react";
import { useLocation } from "react-router-dom";
import { getHealth } from "../api/health";
import { getSyncStatus, retrySync, SyncStatus } from "../api/sync";
import { getStationProfile } from "../station";

export default function Navbar() {
    const location = useLocation();
    const [online, setOnline] = useState<boolean | null>(null);
    const [syncStatus, setSyncStatus] = useState<SyncStatus | null>(null);
    const [syncError, setSyncError] = useState("");
    const [retrying, setRetrying] = useState(false);
    const [now, setNow] = useState(() => new Date());
    const station = getStationProfile();
    const routeLabels: Record<string, string> = {
        "/": "Dashboard",
        "/devices": "Device Intake & Inventory",
        "/test-profiles": "Pre-QC",
        "/diagnostics": "Inspection",
        "/execution": "Functional Tests",
        "/diagnostic-jobs": "Performance & Burn-in",
        "/stress-testing": "Performance & Burn-in",
        "/storage-performance": "Performance & Burn-in",
        "/photos": "Photos & Evidence",
        "/results": "Report Review",
        "/qa": "Final QC & Disposition",
        "/report": "Report Preview",
        "/history": "QC History",
        "/reports": "Reports",
        "/capabilities": "Test Library",
        "/setup": "Station Setup & Settings",
        "/active-qc": "Active QC",
        "/analytics": "Station Analytics",
    };

    useEffect(() => {
        let mounted = true;

        async function refresh() {
            try {
                await getHealth();
                if (!mounted) return;
                setOnline(true);
            } catch {
                if (mounted) {
                    setOnline(false);
                    setSyncError("Local sync status is unavailable.");
                }
                return;
            }
            try {
                const status = await getSyncStatus();
                if (mounted) {
                    setSyncStatus(status);
                    setSyncError("");
                }
            } catch {
                if (mounted) {
                    setSyncError("Local sync status is unavailable.");
                }
            }
        }

        void refresh();
        const timer = window.setInterval(() => void refresh(), 15000);

        return () => {
            mounted = false;
            window.clearInterval(timer);
        };
    }, []);

    useEffect(() => {
        const timer = window.setInterval(() => setNow(new Date()), 60000);
        return () => window.clearInterval(timer);
    }, []);

    async function retryPendingSync() {
        setRetrying(true);
        try {
            await retrySync();
            setSyncStatus(await getSyncStatus());
            setSyncError("");
        } catch (error) {
            setSyncError(error instanceof Error ? error.message : "Retry request failed.");
        } finally {
            setRetrying(false);
        }
    }

    return (
        <header className="navbar">
            <div className="navbar-breadcrumb">
                <span>UHDP</span>
                <span aria-hidden="true">/</span>
                <strong>{routeLabels[location.pathname] || "QC Workstation"}</strong>
            </div>

            <div className="navbar-right">
                <div className="navbar-system-status">
                    <span className={`health-dot ${online ? "is-online" : online === false ? "is-offline" : ""}`} />
                    <span>{online === null ? "Checking system" : online ? "Local system operational" : "Local system offline"}</span>
                </div>
                {online && (
                    <div className="navbar-sync" aria-live="polite">
                        {!syncStatus?.enabled ? (
                            <span>Local storage · cloud sync disabled</span>
                        ) : (
                            <>
                                <span>
                                    {syncStatus.cloud_configured ? "Cloud sync" : "Offline mode"}
                                    {" · "}
                                    {syncStatus.states.Pending} pending
                                    {" · "}
                                    {syncStatus.states["Needs attention"]} needs attention
                                </span>
                                {syncStatus.states["Needs attention"] > 0 && (
                                    <button
                                        type="button"
                                        className="sync-retry-button"
                                        disabled={retrying}
                                        onClick={() => void retryPendingSync()}
                                    >
                                        {retrying ? "Retrying…" : "Retry sync"}
                                    </button>
                                )}
                            </>
                        )}
                        {syncError && <span className="sync-error">{syncError}</span>}
                    </div>
                )}
                <div className="navbar-station" aria-label="Current technician and station">
                    <strong>{station?.technician || "Technician not assigned"}</strong>
                    <span>{station?.station_id || "Station not configured"}</span>
                </div>
                <span className="navbar-date">{now.toLocaleDateString()}</span>
                <div className="navbar-avatar" aria-hidden="true">
                    {(station?.technician || "T").trim().charAt(0).toUpperCase()}
                </div>
            </div>
        </header>
    );
}