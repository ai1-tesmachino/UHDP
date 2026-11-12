import { useEffect, useState } from "react";
import { useLocation } from "react-router-dom";
import { Menu, Moon, Sun } from "lucide-react";
import { Button } from "./ui/button";
import { getHealth } from "../api/health";
import { getSyncStatus, retrySync, SyncStatus } from "../api/sync";
import { getStationProfile } from "../station";
import { notifications } from "../lib/notifications";
import { demoWorkflowRoutes } from "../demo/demoWorkflowRoutes";

interface NavbarProps {
    onToggleSidebar: () => void;
    onToggleTheme: () => void;
    theme: "light" | "dark";
}

export default function Navbar({ onToggleSidebar, onToggleTheme, theme }: NavbarProps) {
    const location = useLocation();
    const demoMode = demoWorkflowRoutes.has(location.pathname);
    const [online, setOnline] = useState<boolean | null>(null);
    const [syncStatus, setSyncStatus] = useState<SyncStatus | null>(null);
    const [syncError, setSyncError] = useState("");
    const [retrying, setRetrying] = useState(false);
    const [now, setNow] = useState(() => new Date());
    const station = demoMode ? null : getStationProfile();
    const routeLabels: Record<string, string> = {
        "/": "Hardware Diagnostics Platform",
        "/device-identification": "Device Identification",
        "/physical-assessment": "Physical Assessment",
        "/hardware-diagnostics": "Hardware Diagnostics",
        "/cpu-stress-test": "CPU Stress Test",
        "/memory-test": "Memory Test",
        "/storage-test": "Storage Test",
        "/browser-performance-test": "Browser Performance Test",
        "/technician-checks": "Technician Checks",
        "/review-results": "Review Results",
        "/inventory": "Hardware Inventory",
        "/sessions": "QC Sessions",
        "/devices": "Device Intake",
        "/qc": "Inspection",
        "/photos": "Photos & Evidence",
        "/results": "QC Report Review",
        "/qa": "Final QC & Disposition",
        "/report": "Report Preview",
        "/history": "QC History",
        "/reports": "Reports",
        "/setup": "Station Setup & Settings",
        "/settings/field-requirements": "QC Field Requirements",
        "/active-qc": "Active QC",
    };
    const routeParams = new URLSearchParams(location.search);
    const routeLabel = location.pathname === "/qc"
        ? routeParams.get("stage") === "cosmetic"
            ? routeParams.get("phase") === "final" ? "Final Cosmetic Verification" : "Cosmetic Inspection"
            : "Functional Inspection"
        : routeLabels[location.pathname] || "QC Workstation";

    useEffect(() => {
        if (demoMode) {
            setSyncStatus(null);
            setSyncError("");
            return;
        }
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
    }, [demoMode]);

    useEffect(() => {
        if (demoMode) return;
        const timer = window.setInterval(() => setNow(new Date()), 60000);
        return () => window.clearInterval(timer);
    }, [demoMode]);

    async function retryPendingSync() {
        setRetrying(true);
        try {
            await retrySync();
            setSyncStatus(await getSyncStatus());
            setSyncError("");
            notifications.success("Cloud synchronization retry started.");
        } catch {
            setSyncError("Cloud synchronization could not be retried.");
            notifications.error("Cloud synchronization could not be retried.");
        } finally {
            setRetrying(false);
        }
    }

    return (
        <header className="navbar">
            <Button className="navbar-menu-button" variant="ghost" size="icon" type="button" aria-label="Toggle navigation" onClick={onToggleSidebar}>
                <Menu size={18} />
            </Button>
            <div className="navbar-breadcrumb">
                <span>UHDP</span>
                <span aria-hidden="true">/</span>
                <strong>{routeLabel}</strong>
            </div>

            <div className="navbar-right">
                {demoMode ? (
                    <span className="navbar-demo-mode">DEMO MODE</span>
                ) : (
                    <>
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
                    </>
                )}
                {!demoMode && <span className="navbar-date">{now.toLocaleDateString()}</span>}
                <Button className="navbar-theme-button" variant="ghost" size="icon" type="button" aria-label={`Switch to ${theme === "dark" ? "light" : "dark"} theme`} onClick={onToggleTheme}>
                    {theme === "dark" ? <Sun size={17} /> : <Moon size={17} />}
                </Button>
                {!demoMode && (
                    <div className="navbar-avatar" aria-hidden="true">
                        {(station?.technician || "T").trim().charAt(0).toUpperCase()}
                    </div>
                )}
            </div>
        </header>
    );
}