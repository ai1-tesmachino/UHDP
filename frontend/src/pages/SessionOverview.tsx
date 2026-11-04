import { useEffect, useMemo, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { PageHeader } from "../components/shared/PageHeader";

import { DiagnosticSession, getDiagnosticSessions } from "../api/execution";
import { useQcSession } from "../session/SessionContext";
import {
    getQcResumePath,
    getSessionDeviceName,
    getSessionSerialNumber,
    isCompletedSession,
} from "../session/workflow";

export default function SessionOverview() {
    const navigate = useNavigate();
    const { activeSession, activateSession } = useQcSession();
    const [sessions, setSessions] = useState<DiagnosticSession[]>([]);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState("");

    useEffect(() => {
        let current = true;
        getDiagnosticSessions()
            .then((items) => {
                if (current) setSessions(items);
            })
            .catch((loadError: unknown) => {
                if (current) setError(loadError instanceof Error ? loadError.message : "QC session activity could not be loaded.");
            })
            .finally(() => {
                if (current) setLoading(false);
            });
        return () => {
            current = false;
        };
    }, []);

    const inProgress = useMemo(() => sessions.filter((session) => !isCompletedSession(session)), [sessions]);
    const completed = sessions.filter(isCompletedSession);
    const active = activeSession && !isCompletedSession(activeSession)
        ? activeSession
        : inProgress[0];
    const recent = sessions.slice(0, 8);

    async function resume(session: DiagnosticSession) {
        try {
            const loaded = await activateSession(session.session_id);
            navigate(getQcResumePath(loaded.session_id, loaded.status, loaded.device_id));
        } catch (resumeError) {
            setError(resumeError instanceof Error ? resumeError.message : "The QC session could not be resumed.");
        }
    }

    return (
        <div className="page-flow session-overview-page">
            <PageHeader
                eyebrow="WORKSPACE / QC SESSIONS"
                title="QC Sessions"
                description="Review current inspection activity and return to saved QC work."
                actions={<Link className="button button-secondary" to="/history">Open full QC history</Link>}
            />
            {error && <div className="error-box" role="alert">{error}</div>}
            <section className="session-overview-counts">
                {[
                    ["All sessions", sessions.length],
                    ["In progress", inProgress.length],
                    ["Completed", completed.length],
                ].map(([label, count]) => (
                    <article className="session-overview-count" key={label}>
                        <span>{label}</span>
                        <strong>{loading ? "—" : count}</strong>
                    </article>
                ))}
            </section>
            <section className="dashboard-section-card">
                <header className="dashboard-section-heading">
                    <div><span className="eyebrow">CURRENT INSPECTION</span><h2>Active QC</h2></div>
                    {active && <span className="qc-context-status">{active.status.replaceAll("_", " ")}</span>}
                </header>
                {loading ? <div className="loading-panel">Loading QC sessions…</div> : active ? (
                    <div className="session-overview-active">
                        <div>
                            <strong>{getSessionDeviceName(active)}</strong>
                            <span>{getSessionSerialNumber(active)}</span>
                            <small>{active.session_id} · Started {new Date(active.created_at).toLocaleString()}</small>
                        </div>
                        <button className="button button-primary" type="button" onClick={() => void resume(active)}>Resume session →</button>
                    </div>
                ) : (
                    <div className="history-empty"><strong>No active QC session</strong><p>Start a new intake to begin an inspection.</p></div>
                )}
            </section>
            <section className="dashboard-section-card">
                <header className="dashboard-section-heading">
                    <div><span className="eyebrow">LATEST ACTIVITY</span><h2>Recent sessions</h2></div>
                    <Link className="button button-secondary" to="/history">View all sessions</Link>
                </header>
                {loading ? <div className="loading-panel">Loading recent sessions…</div> : recent.length ? (
                    <div className="history-table-wrap">
                        <table className="history-table">
                            <thead><tr><th>QC ID</th><th>Device</th><th>Serial</th><th>Date</th><th>Status</th><th>Action</th></tr></thead>
                            <tbody>
                                {recent.map((session) => (
                                    <tr key={session.session_id}>
                                        <td><strong>{session.session_id}</strong></td>
                                        <td>{getSessionDeviceName(session)}</td>
                                        <td>{getSessionSerialNumber(session)}</td>
                                        <td>{new Date(session.created_at).toLocaleString()}</td>
                                        <td>{session.status.replaceAll("_", " ")}</td>
                                        <td>{isCompletedSession(session)
                                            ? <Link className="button button-secondary" to={`/report?sessionId=${encodeURIComponent(session.session_id)}`}>Report</Link>
                                            : <button className="button button-secondary" type="button" onClick={() => void resume(session)}>Resume</button>}
                                        </td>
                                    </tr>
                                ))}
                            </tbody>
                        </table>
                    </div>
                ) : <div className="history-empty"><strong>No QC sessions recorded</strong><p>New and saved inspections will appear here.</p></div>}
            </section>
        </div>
    );
}
