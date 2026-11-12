import { useEffect, useState } from "react";
import { NavLink, useLocation } from "react-router-dom";
import {
    Activity,
    ClipboardCheck,
    ClipboardList,
    FileCheck2,
    HardDrive,
    LayoutDashboard,
    ListChecks,
    PanelLeftClose,
    ScanSearch,
    Settings,
    X,
} from "lucide-react";
import { getHealth } from "../api/health";
import { getSyncStatus, SyncStatus } from "../api/sync";
import { getStationProfile } from "../station";
import { demoWorkflowRoutes } from "../demo/demoWorkflowRoutes";

interface SidebarProps {
    collapsed: boolean;
    mobileOpen: boolean;
    onToggleCollapsed: () => void;
    onCloseMobile: () => void;
}

function navClass({ isActive }: { isActive: boolean }) {
    return `sidebar-link${isActive ? " active" : ""}`;
}

const diagnosticRoutes = new Set([
    "/cpu-stress-test",
    "/memory-test",
    "/storage-test",
    "/browser-performance-test",
]);

export default function Sidebar({ collapsed, mobileOpen, onToggleCollapsed, onCloseMobile }: SidebarProps) {
    const location = useLocation();
    const demoMode = demoWorkflowRoutes.has(location.pathname);
    const [localOnline, setLocalOnline] = useState<boolean | null>(null);
    const [syncStatus, setSyncStatus] = useState<SyncStatus | null>(null);
    const station = demoMode ? null : getStationProfile();

    useEffect(() => {
        if (demoMode) {
            setSyncStatus(null);
            return;
        }
        void getHealth()
            .then(() => setLocalOnline(true))
            .catch(() => setLocalOnline(false));
        void getSyncStatus()
            .then(setSyncStatus)
            .catch(() => setSyncStatus(null));
    }, [demoMode]);

    useEffect(() => {
        onCloseMobile();
    }, [location.pathname, location.search, onCloseMobile]);

    return (
        <>
        {mobileOpen && <button className="sidebar-backdrop" type="button" aria-label="Close navigation" onClick={onCloseMobile} />}
        <aside className={`sidebar${collapsed ? " is-collapsed" : ""}${mobileOpen ? " is-mobile-open" : ""}`} aria-label="Application sidebar">
            <div className="sidebar-brand">
                <div className="sidebar-brand-mark" aria-hidden="true"><HardDrive size={19} /></div>
                <div>
                    <div className="sidebar-brand-title">UHDP</div>
                    <div className="sidebar-brand-subtitle">HARDWARE DIAGNOSTICS PLATFORM</div>
                </div>
                <button className="sidebar-collapse-button" type="button" onClick={onToggleCollapsed} aria-label={collapsed ? "Expand sidebar" : "Collapse sidebar"} title={collapsed ? "Expand sidebar" : "Collapse sidebar"}>
                    {mobileOpen ? <X size={16} /> : <PanelLeftClose size={16} />}
                </button>
            </div>

            <nav className="sidebar-nav" aria-label="Main navigation">
                <NavLink to="/" end className={navClass} title="Dashboard">
                    <LayoutDashboard className="sidebar-link-icon" aria-hidden="true" size={17} />
                    <span className="sidebar-label">Dashboard</span>
                </NavLink>
                <NavLink to="/device-identification" className={navClass} title="Device Identification">
                    <ScanSearch className="sidebar-link-icon" aria-hidden="true" size={17} />
                    <span className="sidebar-label">Device Identification</span>
                </NavLink>
                <NavLink to="/physical-assessment" className={navClass} title="Physical Assessment">
                    <ClipboardCheck className="sidebar-link-icon" aria-hidden="true" size={17} />
                    <span className="sidebar-label">Physical Assessment</span>
                </NavLink>
                <NavLink
                    to="/hardware-diagnostics"
                    className={({ isActive }) => navClass({ isActive: isActive || diagnosticRoutes.has(location.pathname) })}
                    title="Hardware Diagnostics"
                >
                    <Activity className="sidebar-link-icon" aria-hidden="true" size={17} />
                    <span className="sidebar-label">Hardware Diagnostics</span>
                </NavLink>
                <NavLink to="/technician-checks" className={navClass} title="Technician Checks">
                    <ListChecks className="sidebar-link-icon" aria-hidden="true" size={17} />
                    <span className="sidebar-label">Technician Checks</span>
                </NavLink>
                <NavLink to="/review-results" className={navClass} title="Review Results">
                    <ClipboardList className="sidebar-link-icon" aria-hidden="true" size={17} />
                    <span className="sidebar-label">Review Results</span>
                </NavLink>
                <NavLink to="/report" className={navClass} title="Inspection Report">
                    <FileCheck2 className="sidebar-link-icon" aria-hidden="true" size={17} />
                    <span className="sidebar-label">Inspection Report</span>
                </NavLink>
            </nav>

            <div className="sidebar-footer">
                <NavLink
                    to="/setup"
                    className={({ isActive }) => `${navClass({ isActive })} sidebar-settings-link`}
                    title="Settings"
                >
                    <Settings className="sidebar-link-icon" aria-hidden="true" size={17} />
                    <span className="sidebar-label">Settings</span>
                </NavLink>
                {demoMode ? (
                    <div className="sidebar-station">
                        DEMO MODE
                        <small className="sidebar-label">Sample data only</small>
                    </div>
                ) : (
                    <>
                        <div className="sidebar-status">
                            <span className={`sidebar-status-dot ${localOnline ? "is-online" : localOnline === false ? "is-offline" : ""}`} />
                            <span className="sidebar-label">{localOnline === null ? "Checking local system" : localOnline ? "Local system operational" : "Local system offline"}</span>
                        </div>
                        <div className="sidebar-status">
                            <span className={`sidebar-status-dot ${localOnline === true ? "is-online" : localOnline === false ? "is-offline" : ""}`} />
                            <span className="sidebar-label">
                                {localOnline === null
                                    ? "Checking local storage"
                                    : localOnline
                                      ? "Local storage available"
                                      : "Local storage status unavailable"}
                            </span>
                        </div>
                        <div className="sidebar-status">
                            <span className={`sidebar-status-dot ${!syncStatus ? "" : syncStatus.cloud_configured ? "is-online" : "is-pending"}`} />
                            <span className="sidebar-label">
                                {!syncStatus
                                    ? "Cloud sync status unavailable"
                                    : syncStatus.cloud_configured
                                      ? `${syncStatus.states.Pending} cloud sync pending`
                                      : "Cloud sync not configured"}
                            </span>
                        </div>
                        <div className="sidebar-station">
                            {station?.station_id || "Station not configured"}
                            <small className="sidebar-label">UHDP v0.1.0</small>
                        </div>
                    </>
                )}
            </div>
        </aside>
        </>
    );
}
