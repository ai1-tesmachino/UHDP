import { Link, useNavigate } from "react-router-dom";
import { useQcSession } from "../session/SessionContext";
import {
    getQcResumePath,
    getSessionDeviceName,
    getSessionSerialNumber,
    isCompletedSession,
} from "../session/workflow";

function formatDate(value: string) {
    const date = new Date(value);
    return Number.isNaN(date.getTime()) ? "Date unavailable" : date.toLocaleString();
}

export default function ActiveQc() {
    const navigate = useNavigate();
    const { activeSession, loading, error } = useQcSession();

    if (loading) return <div className="loading-panel">Loading active QC session…</div>;
    if (!activeSession) {
        return (
            <section className="empty-panel active-qc-empty">
                <span className="empty-panel-icon" aria-hidden="true">✓</span>
                <h1>No active QC session</h1>
                <p>Start a new inspection or open an incomplete session from QC History.</p>
                {error && <p className="error-text">{error}</p>}
                <div className="active-qc-actions">
                    <button className="button button-primary" type="button" onClick={() => navigate("/devices?new=1")}>
                        Start New QC
                    </button>
                    <Link className="button button-secondary" to="/history">Open QC History</Link>
                </div>
            </section>
        );
    }

    const completed = isCompletedSession(activeSession);
    const technician = activeSession.intake_record?.technician;
    const href = completed
        ? `/report?sessionId=${encodeURIComponent(activeSession.session_id)}`
        : getQcResumePath(activeSession.session_id, activeSession.status, activeSession.device_id);

    return (
        <div className="page-flow">
            <header className="page-header">
                <div>
                    <span className="eyebrow">WORKSPACE / ACTIVE INSPECTION</span>
                    <h1 className="page-title">{completed ? "Most recent QC session" : "Active QC session"}</h1>
                    <p className="page-description">Continue this inspection or review its saved record.</p>
                </div>
                <span className={`history-status ${completed ? "is-complete" : "is-progress"}`}>
                    {completed ? "Completed" : activeSession.status.replaceAll("_", " ")}
                </span>
            </header>

            <section className="active-qc-card">
                <div className="active-qc-heading">
                    <div className="active-qc-device-icon" aria-hidden="true">▣</div>
                    <div>
                        <span className="eyebrow">QC SESSION</span>
                        <h2>{activeSession.session_id}</h2>
                        <p>{getSessionDeviceName(activeSession)}</p>
                    </div>
                </div>
                <dl className="active-qc-details">
                    <div><dt>Serial number</dt><dd>{getSessionSerialNumber(activeSession)}</dd></div>
                    <div><dt>Technician</dt><dd>{typeof technician === "string" && technician ? technician : "Not recorded"}</dd></div>
                    <div><dt>Started</dt><dd>{formatDate(activeSession.created_at)}</dd></div>
                    <div><dt>Session status</dt><dd>{completed ? "Completed" : activeSession.status.replaceAll("_", " ")}</dd></div>
                </dl>
                <div className="active-qc-actions">
                    <Link className="button button-primary" to={href}>
                        {completed ? "Open report" : "Resume inspection"}
                    </Link>
                    <Link className="button button-secondary" to="/history">View QC History</Link>
                </div>
            </section>
        </div>
    );
}
