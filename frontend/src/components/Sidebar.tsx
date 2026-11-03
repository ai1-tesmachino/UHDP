import { useEffect, useState } from "react";
import { NavLink, useLocation, useNavigate } from "react-router-dom";
import { getHealth } from "../api/health";
import { getSyncStatus, SyncStatus } from "../api/sync";
import { useQcSession } from "../session/SessionContext";
import { getQcResumePath } from "../session/workflow";
import { getStationProfile } from "../station";

function navClass({ isActive }: { isActive: boolean }) {
    return `sidebar-link${isActive ? " active" : ""}`;
}

function isComplete(status: string) {
    return ["complete", "completed"].includes(status.toLowerCase());
}

export default function Sidebar() {
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
        <aside className="sidebar">
            <div className="sidebar-brand">
                <div className="sidebar-brand-mark" aria-hidden="true">U</div>
                <div>
                    <div className="sidebar-brand-title">UHDP</div>
                    <div className="sidebar-brand-subtitle">HARDWARE QC PLATFORM</div>
                </div>
            </div>

            <nav className="sidebar-nav" aria-label="Main navigation">
                <div className="sidebar-section-title">Workspace</div>
                <NavLink to="/" end className={navClass}>
                    <span className="sidebar-link-icon" aria-hidden="true">▦</span>
                    <span>Dashboard</span>
                </NavLink>
                <button
                    className={`sidebar-link sidebar-action${startingNewQc ? " active" : ""}`}
                    type="button"
                    onClick={() => void beginNewQc()}
                    disabled={sessionLoading}
                >
                    <span className="sidebar-link-icon" aria-hidden="true">＋</span>
                    <span>Start New QC</span>
                </button>
                <NavLink to={activeQcHref} className={navClass}>
                    <span className="sidebar-link-icon" aria-hidden="true">✓</span>
                    <span>Active QC</span>
                    {currentSession && <span className="sidebar-count" aria-label="Session in progress">●</span>}
                </NavLink>
                <NavLink to="/history" className={navClass}>
                    <span className="sidebar-link-icon" aria-hidden="true">◷</span>
                    <span>QC History</span>
                </NavLink>

                <div className="sidebar-section-title">Diagnostics</div>
                <NavLink to="/diagnostics" className={navClass}>
                    <span className="sidebar-link-icon" aria-hidden="true">⌁</span>
                    <span>Functional Tests</span>
                </NavLink>
                <NavLink to="/diagnostic-jobs" className={navClass}>
                    <span className="sidebar-link-icon" aria-hidden="true">▥</span>
                    <span>Performance &amp; Burn-in</span>
                </NavLink>
                <NavLink to="/capabilities" className={navClass}>
                    <span className="sidebar-link-icon" aria-hidden="true">▤</span>
                    <span>Test Library</span>
                </NavLink>

                <div className="sidebar-section-title">Documentation</div>
                <NavLink to="/reports" className={navClass}>
                    <span className="sidebar-link-icon" aria-hidden="true">▧</span>
                    <span>Reports</span>
                </NavLink>

                <div className="sidebar-section-title">System</div>
                <NavLink to="/setup" className={navClass}>
                    <span className="sidebar-link-icon" aria-hidden="true">⚙</span>
                    <span>Station Setup &amp; Settings</span>
                </NavLink>
            </nav>

            <div className="sidebar-footer">
                <div className="sidebar-status">
                    <span className={`sidebar-status-dot ${localOnline ? "is-online" : localOnline === false ? "is-offline" : ""}`} />
                    <span>{localOnline === null ? "Checking local system" : localOnline ? "Local system operational" : "Local system offline"}</span>
                </div>
                <div className="sidebar-status">
                    <span className={`sidebar-status-dot ${localOnline === true ? "is-online" : localOnline === false ? "is-offline" : ""}`} />
                    <span>
                        {localOnline === null
                            ? "Checking local storage"
                            : localOnline
                              ? "Local storage available"
                              : "Local storage status unavailable"}
                    </span>
                </div>
                <div className="sidebar-status">
                    <span className={`sidebar-status-dot ${!syncStatus ? "" : syncStatus.cloud_configured ? "is-online" : "is-pending"}`} />
                    <span>
                        {!syncStatus
                            ? "Cloud sync status unavailable"
                            : syncStatus.cloud_configured
                              ? `${syncStatus.states.Pending} cloud sync pending`
                              : "Cloud sync not configured"}
                    </span>
                </div>
                <div className="sidebar-station">
                    {station?.station_id || "Station not configured"}
                    <small>UHDP v0.1.0</small>
                </div>
            </div>
        </aside>
    );
}
