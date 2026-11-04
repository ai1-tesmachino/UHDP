import { useEffect, useState } from "react";
import { NavLink, useLocation, useNavigate } from "react-router-dom";
import {
    ClipboardCheck,
    FileClock,
    FileText,
    HardDrive,
    LayoutDashboard,
    PanelLeftClose,
    Search,
    Settings,
    SlidersHorizontal,
    Workflow,
    X,
} from "lucide-react";
import { getHealth } from "../api/health";
import { getSyncStatus, SyncStatus } from "../api/sync";
import { useQcSession } from "../session/SessionContext";
import { getQcResumePath } from "../session/workflow";
import { getStationProfile } from "../station";

interface SidebarProps {
    collapsed: boolean;
    mobileOpen: boolean;
    onToggleCollapsed: () => void;
    onCloseMobile: () => void;
}

function navClass({ isActive }: { isActive: boolean }) {
    return `sidebar-link${isActive ? " active" : ""}`;
}

function isComplete(status: string) {
    return ["complete", "completed"].includes(status.toLowerCase());
}

export default function Sidebar({ collapsed, mobileOpen, onToggleCollapsed, onCloseMobile }: SidebarProps) {
    const navigate = useNavigate();
    const location = useLocation();
    const { activeSession, deactivateSession, loading: sessionLoading } = useQcSession();
    const [localOnline, setLocalOnline] = useState<boolean | null>(null);
    const [syncStatus, setSyncStatus] = useState<SyncStatus | null>(null);
    const station = getStationProfile();
    const currentSession = activeSession && !isComplete(activeSession.status) ? activeSession : null;
    const activeQcHref = currentSession
        ? getQcResumePath(currentSession.session_id, currentSession.status, currentSession.device_id)
        : "/active-qc";
    const functionalHref = currentSession
        ? `/qc?sessionId=${encodeURIComponent(currentSession.session_id)}&stage=functional${currentSession.intake_record?.workflow_type === "standalone_manual_diagnostic" ? "&standalone=1" : ""}`
        : "/qc?stage=functional&standalone=1";
    const startingNewQc = location.pathname === "/devices" &&
        new URLSearchParams(location.search).get("new") === "1";

    useEffect(() => {
        void getHealth()
            .then(() => setLocalOnline(true))
            .catch(() => setLocalOnline(false));
        void getSyncStatus()
            .then(setSyncStatus)
            .catch(() => setSyncStatus(null));
    }, []);

    useEffect(() => {
        onCloseMobile();
    }, [location.pathname, location.search, onCloseMobile]);

    async function beginNewQc() {
        if (sessionLoading) return;
        if (
            currentSession &&
            !window.confirm(
                `QC session ${currentSession.session_id} is still in progress. Start a new session? The current session will remain saved and can be resumed from QC History.`,
            )
        ) {
            return;
        }
        if (activeSession) deactivateSession();
        navigate("/devices?new=1");
    }

    return (
        <>
        {mobileOpen && <button className="sidebar-backdrop" type="button" aria-label="Close navigation" onClick={onCloseMobile} />}
        <aside className={`sidebar${collapsed ? " is-collapsed" : ""}${mobileOpen ? " is-mobile-open" : ""}`} aria-label="Application sidebar">
            <div className="sidebar-brand">
                <div className="sidebar-brand-mark" aria-hidden="true"><HardDrive size={19} /></div>
                <div>
                    <div className="sidebar-brand-title">UHDP</div>
                    <div className="sidebar-brand-subtitle">HARDWARE QC PLATFORM</div>
                </div>
                <button className="sidebar-collapse-button" type="button" onClick={onToggleCollapsed} aria-label={collapsed ? "Expand sidebar" : "Collapse sidebar"} title={collapsed ? "Expand sidebar" : "Collapse sidebar"}>
                    {mobileOpen ? <X size={16} /> : <PanelLeftClose size={16} />}
                </button>
            </div>

            <nav className="sidebar-nav" aria-label="Main navigation">
                <div className="sidebar-section-title"><span>Overview</span></div>
                <NavLink to="/" end className={navClass} title="Hardware Inventory">
                    <LayoutDashboard className="sidebar-link-icon" aria-hidden="true" size={17} />
                    <span className="sidebar-label">Hardware Inventory</span>
                </NavLink>
                <div className="sidebar-section-title"><span>Quality control</span></div>
                <button
                    className={`sidebar-link sidebar-action${startingNewQc ? " active" : ""}`}
                    type="button"
                    onClick={() => void beginNewQc()}
                    disabled={sessionLoading}
                    title="Start New QC"
                >
                    <ClipboardCheck className="sidebar-link-icon" aria-hidden="true" size={17} />
                    <span className="sidebar-label">Start New QC</span>
                </button>
                <NavLink to="/sessions" className={navClass} title="QC Sessions">
                    <Workflow className="sidebar-link-icon" aria-hidden="true" size={17} />
                    <span className="sidebar-label">QC Sessions</span>
                    {currentSession && <span className="sidebar-count" aria-label="Session in progress">●</span>}
                </NavLink>
                <NavLink to={activeQcHref} className={navClass} title="Active QC">
                    <ClipboardCheck className="sidebar-link-icon" aria-hidden="true" size={17} />
                    <span className="sidebar-label">Active QC</span>
                </NavLink>
                <NavLink to="/history" className={navClass} title="QC History">
                    <FileClock className="sidebar-link-icon" aria-hidden="true" size={17} />
                    <span className="sidebar-label">QC History</span>
                </NavLink>

                <div className="sidebar-section-title"><span>Hardware</span></div>
                <NavLink to="/devices" className={navClass} title="Device Intake">
                    <Search className="sidebar-link-icon" aria-hidden="true" size={17} />
                    <span className="sidebar-label">Device Intake</span>
                </NavLink>
                <NavLink to={functionalHref} className={navClass} title="Functional Inspection">
                    <SlidersHorizontal className="sidebar-link-icon" aria-hidden="true" size={17} />
                    <span className="sidebar-label">Functional Inspection</span>
                </NavLink>

                <div className="sidebar-section-title"><span>Reports</span></div>
                <NavLink to="/reports" className={navClass} title="QC Reports">
                    <FileText className="sidebar-link-icon" aria-hidden="true" size={17} />
                    <span className="sidebar-label">QC Reports</span>
                </NavLink>

                <div className="sidebar-section-title"><span>Administration</span></div>
                <NavLink to="/settings/field-requirements" className={navClass} title="QC Field Requirements">
                    <Settings className="sidebar-link-icon" aria-hidden="true" size={17} />
                    <span className="sidebar-label">QC Field Requirements</span>
                </NavLink>
                <NavLink to="/setup" className={navClass} title="Station Setup">
                    <Settings className="sidebar-link-icon" aria-hidden="true" size={17} />
                    <span className="sidebar-label">Station Setup</span>
                </NavLink>
            </nav>

            <div className="sidebar-footer">
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
            </div>
        </aside>
        </>
    );
}
